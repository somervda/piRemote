#!/usr/bin/env python3

import asyncio
from bless import (
    BlessServer,
    GATTCharacteristicProperties,
    GATTAttributePermissions,
)
from ir_transmit import IRTransmitter

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHARACTERISTIC_UUID1 = "12345678-1234-5678-1234-56789abcdef1"



def handle_command(command):
    """Replace this with your controller logic."""
    print("Command:", command)

    if command == "up":
        pass
    elif command == "down":
        pass
    elif command == "left":
        pass
    elif command == "right":
        pass
    elif command =="1":
        with IRTransmitter(gpio_pin=22) as ir:
            ir.load_keys("keys.ir")
            ir.send("1", repeat=1)


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