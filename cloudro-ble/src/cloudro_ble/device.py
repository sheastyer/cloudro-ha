"""Connect to a Cloud RO unit over BLE and read its current state.

No authentication or pairing is required. The device pushes MEASURED_DATA ~1×/second
while connected; for a poll-style update we connect, read MEASURED_DATA once, read a
few slow-changing characteristics, and return. The caller manages the BLEDevice
(in Home Assistant, via the shared scanner).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bleak import BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import (
    CLOUD_SERVICE_UUID,
    MAG_INSTALL_DATE,
    MEASURED_DATA,
    VERSION,
    char_uuid,
)
from .parser import MeasuredData, parse_measured_data

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CloudROState:
    """Snapshot of everything read from the unit in one update."""

    address: str
    name: str | None
    measured: MeasuredData
    firmware: str | None = None
    mag_install_date: int | None = None


class CloudRODevice:
    """Reads state from a single Cloud RO unit."""

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        """Update the BLEDevice (its address/handle can change between advertisements)."""
        self._ble_device = ble_device

    async def update(self) -> CloudROState:
        """Connect, read the current state, and disconnect.

        A device reboot or firmware update can leave Home Assistant with a stale
        cached GATT table whose characteristics no longer match the unit, so a read
        fails with "characteristic ... was not found" on every retry. When that
        happens we drop the cache and reconnect once to force a fresh discovery.
        """
        client = await self._connect()
        try:
            try:
                return await self._read_state(client)
            except BleakError as err:
                if not _is_char_not_found(err):
                    raise
                _LOGGER.debug(
                    "Cloud RO %s: %s; clearing GATT cache and reconnecting",
                    self._ble_device.address,
                    err,
                )
                await client.clear_cache()
                await client.disconnect()
                client = await self._connect()
                return await self._read_state(client)
        finally:
            await client.disconnect()

    async def _connect(self) -> BleakClientWithServiceCache:
        return await establish_connection(
            BleakClientWithServiceCache,
            self._ble_device,
            self._ble_device.address,
        )

    async def _read_state(self, client: BleakClientWithServiceCache) -> CloudROState:
        measured_raw = bytes(await client.read_gatt_char(char_uuid(MEASURED_DATA)))
        firmware = await self._read_str(client, VERSION)
        # Logged to help diagnose units with different firmware; see Compatibility
        # in the README.
        _LOGGER.debug(
            "Cloud RO %s firmware=%s MEASURED_DATA raw: %s",
            self._ble_device.address,
            firmware,
            measured_raw.hex(),
        )
        measured = parse_measured_data(measured_raw)

        mag_install = await self._read_u32(client, MAG_INSTALL_DATE)

        return CloudROState(
            address=self._ble_device.address,
            name=self._ble_device.name,
            measured=measured,
            firmware=firmware,
            mag_install_date=mag_install,
        )

    @staticmethod
    async def _read_str(client: BleakClientWithServiceCache, code: int) -> str | None:
        try:
            raw = bytes(await client.read_gatt_char(char_uuid(code)))
            return raw.split(b"\x00")[0].decode("ascii", "replace") or None
        except Exception as err:  # noqa: BLE001 - best-effort optional read
            _LOGGER.debug("Could not read 0x%04x: %s", code, err)
            return None

    @staticmethod
    async def _read_u32(client: BleakClientWithServiceCache, code: int) -> int | None:
        try:
            raw = bytes(await client.read_gatt_char(char_uuid(code)))
            return int.from_bytes(raw[:4], "little") if len(raw) >= 4 else None
        except Exception as err:  # noqa: BLE001 - best-effort optional read
            _LOGGER.debug("Could not read 0x%04x: %s", code, err)
            return None


def _is_char_not_found(err: BleakError) -> bool:
    """True if a BleakError reports a missing characteristic (stale GATT cache)."""
    return "was not found" in str(err)


def is_cloud_ro(service_uuids: list[str]) -> bool:
    """True if an advertisement's service UUIDs indicate a Cloud RO unit."""
    return CLOUD_SERVICE_UUID in [u.lower() for u in service_uuids]
