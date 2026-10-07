#!/usr/bin/env python3

import asyncio
import time
from bless import (
    BlessServer,
    GATTCharacteristicProperties,
    GATTAttributePermissions,
)
from ir_transmit import IRTransmitter

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHARACTERISTIC_UUID1 = "12345678-1234-5678-1234-56789abcdef1"

def handle_command(command):
    """Handle remote commands in the format '<operation> <parameter>'.

    Operations
    ----------
    T <key>   Transmit a single T-series key  (e.g. 'T 1', 'T Menu')
    D <key>   Transmit a single D-series key  (e.g. 'D Stop', 'D Popup')
    Y <Key>   Transmit a single Y-series key  (e.g. 'Y Tuner' to swap yamaha reciever to the tuner input)
    M <digits> Transmit up to 3 T-series keys in sequence
                (e.g. 'M 123' → T 1, T 2, T 3)
                (e.g. 'M 602' → T 6, T 0, T 2)
    """
    parts = command.split(maxsplit=1)

    if len(parts) < 2:
        print(f"Invalid command: {command!r}  (expected '<operation> <parameter>')")
        return

    operation, parameter = parts[0].upper(), parts[1]
    print(f"Operation:{operation} Parameter:{parameter}")

    with IRTransmitter(gpio_pin=22) as ir:
        ir.load_keys("keys.ir")

        if operation == "T":
            ir.send(f"T {parameter}", repeat=1)

        elif operation == "D":
            ir.send(f"D {parameter}", repeat=1)

        elif operation == "Y":
            ir.send(f"Y {parameter}", repeat=1)

        elif operation == "M":
            # Each character (up to 3) becomes a T-series key, sent in order``
            for digit in parameter[:3]:
                ir.send(f"T {digit}", repeat=1)
                time.sleep(0.1)

        else:
            print(f"Unknown operation: {operation!r}")



def on_write(characteristic, value, **kwargs):
    try:
        command = value.decode("utf-8").strip().lower()
        handle_command(command)
    except UnicodeDecodeError:
        print("Received non-text data")


async def main():
    server = BlessServer(name="BT Bliss Controller")
    server.write_request_func = on_write

    await server.add_new_service(SERVICE_UUID)

    await server.add_new_characteristic(
        SERVICE_UUID,
        CHARACTERISTIC_UUID1,
        GATTCharacteristicProperties.write,
        bytearray(),
        GATTAttributePermissions.writeable,
    )


    await server.start()
    print("Advertising as BT Bliss Controller")
    print("Waiting for commands...")

    try:
        await asyncio.Event().wait()
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())