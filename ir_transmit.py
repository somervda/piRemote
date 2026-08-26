#!/usr/bin/env python3
"""
ir_transmit.py – Parse a keys.ir file (LIRC raw format) and transmit
a named IR signal on a Raspberry Pi GPIO pin using pigpio hardware waves.

Use as a standalone script:
    python ir_transmit.py <key_name> [--pin 22] [--repeat N]

Or import it into other programs:
    from ir_transmit import IRTransmitter

    # Context-manager form (recommended – cleans up pigpio automatically):
    with IRTransmitter(gpio_pin=22) as ir:
        ir.load_keys("keys.ir")
        ir.send("1", repeat=5)

    # Or manage the lifecycle yourself:
    ir = IRTransmitter(gpio_pin=17, carrier_hz=38000.0)
    ir.load_keys("keys.ir")
    ir.send("2")
    ir.disconnect()

IR signal format (keys.ir) – LIRC raw timings in microseconds:
    <space> <mark> <space> <mark> <space> ...
    where space = LED off, mark = LED on (38 kHz carrier modulated on GPIO)
"""

import os
import sys
import time
import argparse
import pigpio


# ──────────────────────────────────────────────
# IRTransmitter – importable IR transmitter
# ──────────────────────────────────────────────

class IRTransmitter:
    """Parse a keys.ir (LIRC raw) file and transmit named IR signals on a
    Raspberry Pi GPIO pin using pigpio's DMA waveform engine.

    Args:
        gpio_pin   – BCM GPIO pin number (default 22)
        carrier_hz – carrier frequency in Hz (default 38000). The mark
                     timing is derived from this (38 kHz → 26 µs period /
                     13 µs half-period, matching the original behaviour).
        auto_connect – if True, start pigpiod and configure the pin now
                      (default True). Set False to defer to a later
                      call to .connect().
    """

    def __init__(self, gpio_pin=22, carrier_hz=38000.0, auto_connect=True):
        self.gpio_pin = gpio_pin
        self.carrier_hz = carrier_hz
        # Derive carrier timing; round to ints to preserve original 26/13 µs.
        self.carrier_period_us = int(round(1e6 / carrier_hz))  # 26 @ 38 kHz
        self.half_period_us = self.carrier_period_us // 2       # 13 @ 38 kHz

        self.keys = {}          # {name: tuple(microsecond timings)}
        self._pi = None

        if auto_connect:
            self.connect()

    # ── connection lifecycle ───────────────────────────────────────
    def connect(self):
        """Start pigpio and configure the pin as an output. Idempotent."""
        if self._pi is not None:
            return self

        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise RuntimeError("pigpiod is not running. Start it with 'sudo pigpiod'")

        self._pi.set_mode(self.gpio_pin, pigpio.OUTPUT)
        return self

    def disconnect(self):
        """Drive the pin low and stop pigpio. Safe to call more than once."""
        if self._pi is None:
            return
        self._pi.write(self.gpio_pin, 0)
        self._pi.stop()
        self._pi = None

    def close(self):  # alias so it works with both names / gc
        self.disconnect()

    # context-manager support:  with IRTransmitter() as ir: ...
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    # ── key-file parsing ───────────────────────────────────────────
    @staticmethod
    def parse_ir_keys(filepath):
        """Parse a LIRC raw .ir file into {name: (timings, ...)}."""
        keys = {}
        current_name = None
        current_data = []

        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    if current_name is not None:
                        keys[current_name] = tuple(current_data)
                        current_name = None
                        current_data = []
                    continue

                if line.startswith("name:"):
                    # Save the previous signal before starting a new one
                    if current_name is not None:
                        keys[current_name] = tuple(current_data)

                    current_name = line.split(":", 1)[1].strip()
                    current_data = []
                elif line.startswith("data:"):
                    # Extract and convert space-separated integers to ints
                    data_str = line.split(":", 1)[1].strip()
                    if data_str:
                        current_data.extend(int(val) for val in data_str.split())

        # Ensure the last signal is saved even if the file doesn't end with '#'
        if current_name is not None:
            keys[current_name] = tuple(current_data)

        return keys

    def load_keys(self, filepath):
        """Load keys from a .ir file into this instance. Returns the dict."""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"'{filepath}' not found.")
        self.keys = self.parse_ir_keys(filepath)
        return self.keys

    # ── helpers ────────────────────────────────────────────────────
    def has_key(self, key_name):
        return key_name in self.keys

    def available_keys(self):
        return list(self.keys.keys())

    # ── pulse building ─────────────────────────────────────────────
    def build_raw_pulses(self, data_timings):
        """Convert microsecond timings into pigpio.pulse lists WITH 38 kHz
        carrier modulation.

        LIRC raw format: alternating <mark> <space> <mark> <space> ...
          Even-indexed values = MARK  → pin toggles ON/OFF at the carrier
          Odd-indexed  values = SPACE → pin goes LOW (no carrier)
        """
        pulses = []
        pin_on = 1 << self.gpio_pin              # flag for mark (LED on)
        carrier_period = self.carrier_period_us  # ~38 kHz
        half_period = self.half_period_us        # half the carrier period

        for idx, usecs in enumerate(data_timings):
            if usecs <= 0:
                continue

            if idx % 2 == 0:
                # MARK — produce carrier bursts
                remaining = usecs
                while remaining >= carrier_period:
                    pulses.append(pigpio.pulse(pin_on, 0, half_period))
                    pulses.append(pigpio.pulse(0, pin_on, half_period))
                    remaining -= carrier_period
                # Handle remainder (< full cycle)
                if remaining > 0:
                    pulses.append(pigpio.pulse(pin_on, 0, remaining))
            else:
                # SPACE — pin off (no carrier needed during gap)
                pulses.append(pigpio.pulse(0, pin_on, usecs))

        return pulses

    # ── transmission ───────────────────────────────────────────────
    def send(self, key_name, repeat=1):
        """Transmit a named signal, optionally repeated N times.

        Args:
            key_name – name of the key / signal to send
            repeat   – how many times to re-send the signal (default 1)
        """
        if self._pi is None:
            self.connect()

        if key_name not in self.keys:
            available = ", ".join(self.keys) or "(none loaded)"
            raise KeyError(f"Key '{key_name}' not found. Available keys: {available}")

        data = self.keys[key_name]
        pulses = self.build_raw_pulses(data)
        if not pulses:
            raise ValueError(f"No pulses generated for key '{key_name}'.")

        for rep in range(repeat):
            pi = self._pi

            pi.wave_clear()                        # Clear any previous wave
            pi.wave_add_generic(pulses)
            wave_id = pi.wave_create()
            if wave_id < 0:
                raise RuntimeError("Could not create waveform.")

            pi.wave_send_once(wave_id)             # Start transmission (DMA)

            # Wait for DMA transfer to finish (~blocks briefly)
            while pi.wave_tx_busy():
                time.sleep(0.001)

            pi.wave_delete(wave_id)                # Free DMA resources

            if rep + 1 < repeat:
                inter_gap_us = data[0] if data else 100_000  # ~100 ms gap
                print(f"  Repetition {rep + 1}/{repeat} sent. "
                      f"Gap before next ≈ {inter_gap_us / 1e3:.0f} ms")
                time.sleep(inter_gap_us / 1e6)

        return repeat


# ──────────────────────────────────────────────
# Script entry-point (unchanged CLI behaviour)
# ──────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Transmit an IR signal from keys.ir on GPIO pin 22."
    )
    parser.add_argument("key", help="Name of the key to transmit (e.g. '1', '2', '3')")
    parser.add_argument("--file", "-f", default="keys.ir",
                        help="Path to the .ir file (default: keys.ir)")
    parser.add_argument("--pin", "-p", type=int, default=22,
                        help="GPIO BCM pin number (default: 22)")
    parser.add_argument("--repeat", "-r", type=int, default=1,
                        help="How many times to repeat the signal (default: 1)")

    args = parser.parse_args(argv)

    ir = IRTransmitter(gpio_pin=args.pin)
    try:
        keys = ir.load_keys(args.file)
        print(f"\nLoaded {len(keys)} key(s) from '{args.file}'")
        ir.send(args.key, repeat=args.repeat)
        print(f"\nDone. Sent key '{args.key}' {args.repeat} time(s).")
    except (FileNotFoundError, KeyError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        ir.disconnect()


if __name__ == "__main__":
    main()