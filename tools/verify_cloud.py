#!/usr/bin/env python3
"""Connect to the Cloud RO unit and decode live MEASURED_DATA.

Confirms the protocol reverse-engineered from the app bundle (see PROTOCOL.md):
scans by the Cloud service UUID, connects (no auth), reads + subscribes to the
data characteristics, and decodes the 34-byte MEASURED_DATA struct.

Usage:
    python tools/verify_cloud.py [listen_seconds]

Keep the Cloud phone app CLOSED so it isn't holding the single BLE connection.
"""

import asyncio
import datetime as dt
import struct
import sys

from bleak import BleakClient, BleakScanner

CLOUD_SERVICE = "5e3c1400-0929-41b6-89ea-502be1edf8b0"


def uuid_for(code: int) -> str:
    return f"5e3c{code:04x}-0929-41b6-89ea-502be1edf8b0"


MEASURED_DATA = 0x1404
VERSION = 0x1401
MAG_INSTALL_DATE = 0x1403
CONSUMED_WATER = 0x1406
HISTORICAL_TDS = 0x1407


def decode_measured(b: bytes) -> dict:
    if len(b) < 34:
        return {"error": f"short payload ({len(b)} bytes)", "raw": b.hex(" ")}
    (inlet, postro, remin, stored, dispensed, batt_life, batt_v, tank_p,
     max_p_life, max_v_life, max_p_month, max_v_month) = struct.unpack_from("<HHHHIHHHHHHH", b, 0)
    latch, flow, valve, err = struct.unpack_from("<BBBB", b, 26)
    ts = struct.unpack_from("<I", b, 30)[0]
    pct = round(stored / max_v_life * 100, 1) if max_v_life else None
    return {
        "InletTDS": inlet, "PostROTDS": postro, "ReminTDS": remin,
        "StoredWater": stored, "MaxTankVolumeLife": max_v_life,
        "TankFillPct(est)": pct,
        "TotalDispensedWater": dispensed,
        "BatteryLife": batt_life, "BatteryVoltage": batt_v,
        "TankPressure": tank_p, "MaxTankPressureLife": max_p_life,
        "MaxTankVolumeMonth": max_v_month, "MaxTankPressureMonth": max_p_month,
        "Latch": latch, "Flow": flow, "Valve": valve, "ErrorCode": err,
        "TS": dt.datetime.fromtimestamp(ts).isoformat() if ts else 0,
        "raw": b[:34].hex(" "),
    }


def decode_string(b: bytes) -> str:
    return b.split(b"\x00")[0].decode("ascii", "replace")


async def main(listen_seconds: float) -> None:
    print(f"Scanning for Cloud service {CLOUD_SERVICE} ...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, adv: CLOUD_SERVICE in [u.lower() for u in adv.service_uuids],
        timeout=15.0,
    )
    if device is None:
        print("No Cloud device found. Is the unit powered and the phone app closed?")
        return
    print(f"Found: {device.name} ({device.address})\n")

    def on_notify(char, data: bytearray):
        code = int(str(char.uuid)[4:8], 16)
        b = bytes(data)
        if code == MEASURED_DATA:
            print(f"[NOTIFY MEASURED_DATA] {decode_measured(b)}")
        else:
            print(f"[NOTIFY 0x{code:04x}] len={len(b)} {b.hex(' ')}")

    async with BleakClient(device) as client:
        print("Connected (no pairing). Reading characteristics...\n")

        for code, label, decoder in [
            (VERSION, "VERSION", decode_string),
            (MAG_INSTALL_DATE, "MAG_INSTALL_DATE", lambda b: dt.datetime.fromtimestamp(struct.unpack("<I", b[:4])[0]).isoformat() if len(b) >= 4 else b.hex()),
            (MEASURED_DATA, "MEASURED_DATA", decode_measured),
            (CONSUMED_WATER, "CONSUMED_WATER", lambda b: b.hex(" ")),
            (HISTORICAL_TDS, "HISTORICAL_TDS", lambda b: b.hex(" ")),
        ]:
            try:
                val = await client.read_gatt_char(uuid_for(code))
                print(f"  {label} (0x{code:04x}): {decoder(bytes(val))}")
            except Exception as e:  # noqa: BLE001
                print(f"  {label} (0x{code:04x}): <read error: {e}>")

        print("\nSubscribing to notifications. Dispense water / interact to trigger updates.")
        print(f"Listening {listen_seconds:.0f}s ...\n")
        for service in client.services:
            for char in service.characteristics:
                if "notify" in char.properties:
                    try:
                        await client.start_notify(char, on_notify)
                    except Exception:  # noqa: BLE001
                        pass
        await asyncio.sleep(listen_seconds)

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main(float(sys.argv[1]) if len(sys.argv) > 1 else 45.0))
