#!/usr/bin/env python3

from bluezero import peripheral
from bluezero import adapter


SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHARACTERISTIC_UUID = "12345678-1234-5678-1234-56789abcdef1"


bluetooth = None


def command_received(value, options):
    global bluetooth

    try:
        command = bytes(value).decode("utf-8").strip().lower()
    except UnicodeDecodeError:
        print("Received invalid text")
        return

    if command in ("up", "down", "left", "right"):
        handle_command(command)

    elif command in ("exit", "quit", "stop"):
        print("Exiting Bluetooth service...")
        if bluetooth.mainloop:
            bluetooth.mainloop.quit()

    else:
        print("Unknown command:", command)


def handle_command(command):
    """Put your controller code here."""
    print("Command received:", command)

    if command == "up":
        print("Moving up")
    elif command == "down":
        print("Moving down")
    elif command == "left":
        print("Moving left")
    elif command == "right":
        print("Moving right")


def main():
    global bluetooth

    adapters = list(adapter.Adapter.available())

    if not adapters:
        raise RuntimeError("No Bluetooth adapter found")

    bluetooth = peripheral.Peripheral(
        adapter_address=adapters[0].address,
        local_name="Pizir",
        appearance=0
    )

    bluetooth.add_service(
        srv_id=1,
        uuid=SERVICE_UUID,
        primary=True
    )

    bluetooth.add_characteristic(
        srv_id=1,
        chr_id=1,
        uuid=CHARACTERISTIC_UUID,
        value=[],
        notifying=False,
        flags=["write", "write-without-response"],
        write_callback=command_received
    )

    print("Advertising as 'Simple Controller'")
    print("Send 'up', 'down', 'left', 'right', or 'exit'")

    bluetooth.publish()



if __name__ == "__main__":
    main()