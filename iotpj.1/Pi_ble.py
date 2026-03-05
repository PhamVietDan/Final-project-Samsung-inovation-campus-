import asyncio
from bleak import BleakClient, BleakScanner

CHARACTERISTIC_UUID = "abcdefab-1234-1234-1234-abcdefabcdef"
connected_devices = {}

async def connect_and_listen(address, name):
    if address in connected_devices:
        return  # already connected

    client = BleakClient(address)
    try:
        await client.connect()
        if client.is_connected:
            print(f"Connected to {name} ({address})")

            def notification_handler(sender, data):
                try:
                    text = data.decode()
                except:
                    text = str(data)
                print(f"[{name}] {text}")
                with open("log_ble.csv", "a") as f:
                    f.write(f"{name},{text}\n")

            await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
            connected_devices[address] = client
    except Exception as e:
        print(f"Error connecting to {name}: {e}")

async def main():
    print("Scanning BLE devices continuously...")
    while True:
        devices = await BleakScanner.discover(timeout=5.0)
        for d in devices:
            if d.name and d.name.startswith("ESP"):
                await connect_and_listen(d.address, d.name)
        await asyncio.sleep(2)

asyncio.run(main())

