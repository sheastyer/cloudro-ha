"""Constants for the Cloud RO BLE protocol.

The device exposes its data over a custom GATT service with no authentication or
pairing. See PROTOCOL.md for the full specification.
"""

from __future__ import annotations

# Primary GATT service advertised by the unit; also used as the scan filter.
CLOUD_SERVICE_UUID = "5e3c1400-0929-41b6-89ea-502be1edf8b0"

# Firmware-update service (ignored by this library).
DFU_SERVICE_UUID = "8ec91400-f315-4f60-9fb8-838830daea50"

# Characteristic UUIDs are 5e3c14XX-... where XX is the hex "code" below.
_UUID_SUFFIX = "-0929-41b6-89ea-502be1edf8b0"


def char_uuid(code: int) -> str:
    """Return the full characteristic UUID for a Cloud characteristic code."""
    return f"5e3c{code:04x}{_UUID_SUFFIX}"


# Characteristic codes (the low 16 bits of the UUID).
VERSION = 0x1401
DATETIME = 0x1402
MAG_INSTALL_DATE = 0x1403
MEASURED_DATA = 0x1404
NICKNAME = 0x1405
CONSUMED_WATER = 0x1406
HISTORICAL_TDS = 0x1407
COMMAND = 0x1410
RESPONSE = 0x1411
RAW_DATA = 0x1420

# ASCII commands written to the COMMAND characteristic (optional; not needed for reads).
CMD_TDS_HISTORY = "TDSHISTORY"

# MEASURED_DATA payload is 34 bytes, little-endian.
MEASURED_DATA_LEN = 34

# The device pushes MEASURED_DATA roughly once per second while connected.
NOTIFY_INTERVAL_S = 1
