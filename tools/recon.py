#!/usr/bin/env python3
"""Cloud RO BLE reconnaissance tool.

Usage:
    python tools/recon.py scan [seconds]
        Scan for nearby BLE devices and print name / address / RSSI /
        advertised service UUIDs / manufacturer data. Run this first
        (Cloud app CLOSED) to find the unit.

    python tools/recon.py dump <address-or-name-substring> [listen_seconds]
        Connect to the unit, dump the full GATT table (services +
        characteristics + properties), read every readable characteristic,
        then subscribe to every notify/indicate characteristic and log raw
        payloads for `listen_seconds` (default 60). Everything is also
        written to captures/ as JSON + a raw notification log.

Notes:
- On macOS, device "addresses" are CoreBluetooth UUIDs, not MAC addresses.
  Use `scan` to discover the identifier, then pass it (or a name substring)
  to `dump`.
- The first run will trigger a macOS Bluetooth permission prompt for the
  terminal app — accept it.
- BLE allows one central connection at a time. Keep the Cloud phone app
  CLOSED (or the phone out of range) while running `dump`.
"""

import asyncio
import datetime as dt
import json
import sys
from pathlib import Path

from bleak import BleakClient, BleakScanner

CAPTURE_DIR = Path(__file__).resolve().parent.parent / "captures"
CAPTURE_DIR.mkdir(exist_ok=True)


def _ts() -> str:
    return dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _hex(data: bytes) -> str:
    return data.hex(" ") if data else ""


def _ascii(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


async def cmd_scan(seconds: float) -> None:
    print(f"Scanning for {seconds:.0f}s ... (Cloud app should be CLOSED)\n")
    seen: dict[str, dict] = {}

    def detection(device, adv):
        seen[device.address] = {
            "address": device.address,
            "name": adv.local_name or device.name,
            "rssi": adv.rssi,
            "service_uuids": list(adv.service_uuids),
            "manufacturer_data": {
                str(k): _hex(bytes(v)) for k, v in adv.manufacturer_data.items()
            },
            "service_data": {k: _hex(bytes(v)) for k, v in adv.service_data.items()},
        }

    scanner = BleakScanner(detection_callback=detection)
    await scanner.start()
    await asyncio.sleep(seconds)
    await scanner.stop()

    rows = sorted(seen.values(), key=lambda r: (r["rssi"] or -999), reverse=True)
    print(f"Found {len(rows)} devices (strongest signal first):\n")
    for r in rows:
        print(f"  {r['name'] or '(no name)':<28} {r['address']}  rssi={r['rssi']}")
        if r["service_uuids"]:
            print(f"      services: {', '.join(r['service_uuids'])}")
        if r["manufacturer_data"]:
            print(f"      mfr_data: {r['manufacturer_data']}")
        if r["service_data"]:
            print(f"      svc_data: {r['service_data']}")

    out = CAPTURE_DIR / f"scan-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nSaved: {out}")
    print("\nLook for a name like 'Cloud', 'RO', or an unfamiliar device that")
    print("appears/disappears when you power-cycle the unit. Then run:")
    print("  python tools/recon.py dump <address-or-name>")


async def _resolve(identifier: str):
    print(f"Resolving '{identifier}' ...")
    devices = await BleakScanner.discover(timeout=8.0)
    for d in devices:
        if identifier.lower() in (d.address or "").lower() or (
            d.name and identifier.lower() in d.name.lower()
        ):
            print(f"  -> {d.name} ({d.address})")
            return d
    return None


async def cmd_dump(identifier: str, listen_seconds: float) -> None:
    device = await _resolve(identifier)
    if device is None:
        print(f"Could not find a device matching '{identifier}'. Run `scan` first.")
        return

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    gatt_path = CAPTURE_DIR / f"gatt-{stamp}.json"
    notif_path = CAPTURE_DIR / f"notifications-{stamp}.log"
    notif_log = notif_path.open("w")

    def log_notif(char, data: bytearray):
        line = f"{_ts()}  {char.uuid}  len={len(data):<3} {_hex(bytes(data))}  | {_ascii(bytes(data))}"
        print("NOTIFY " + line)
        notif_log.write(line + "\n")
        notif_log.flush()

    print(f"\nConnecting to {device.address} ...")
    async with BleakClient(device) as client:
        print("Connected. Enumerating GATT ...\n")
        gatt = []
        notify_chars = []
        for service in client.services:
            print(f"[service] {service.uuid}  {service.description}")
            svc = {"uuid": service.uuid, "description": service.description, "chars": []}
            for char in service.characteristics:
                props = ",".join(char.properties)
                value_hex = ""
                if "read" in char.properties:
                    try:
                        val = await client.read_gatt_char(char)
                        value_hex = _hex(bytes(val))
                    except Exception as e:  # noqa: BLE001
                        value_hex = f"<read error: {e}>"
                print(f"    [char] {char.uuid}  ({props})")
                if value_hex:
                    print(f"           value: {value_hex}  | {_ascii(bytes.fromhex(value_hex.replace(' ','')))}" if all(c in '0123456789abcdef ' for c in value_hex) else f"           value: {value_hex}")
                svc["chars"].append(
                    {"uuid": char.uuid, "properties": list(char.properties), "value": value_hex}
                )
                if "notify" in char.properties or "indicate" in char.properties:
                    notify_chars.append(char)
            gatt.append(svc)

        gatt_path.write_text(json.dumps(gatt, indent=2))
        print(f"\nSaved GATT table: {gatt_path}")

        if not notify_chars:
            print("\nNo notify/indicate characteristics. Data is likely read-only or in advertisements.")
            notif_log.close()
            return

        print(f"\nSubscribing to {len(notify_chars)} notify/indicate characteristics.")
        print(f"Listening {listen_seconds:.0f}s — interact with the unit now")
        print("(dispense water, check filter, etc.) to trigger updates.\n")
        for char in notify_chars:
            try:
                await client.start_notify(char, log_notif)
            except Exception as e:  # noqa: BLE001
                print(f"  could not subscribe to {char.uuid}: {e}")

        await asyncio.sleep(listen_seconds)

        for char in notify_chars:
            try:
                await client.stop_notify(char)
            except Exception:  # noqa: BLE001
                pass

    notif_log.close()
    print(f"\nDone. Notifications logged to: {notif_path}")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "scan":
        seconds = float(args[1]) if len(args) > 1 else 12.0
        asyncio.run(cmd_scan(seconds))
    elif cmd == "dump":
        if len(args) < 2:
            print("Usage: python tools/recon.py dump <address-or-name> [listen_seconds]")
            return
        listen = float(args[2]) if len(args) > 2 else 60.0
        asyncio.run(cmd_dump(args[1], listen))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
