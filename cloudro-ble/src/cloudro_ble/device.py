"""Connect to a Cloud RO unit over BLE and read its current state.

No authentication or pairing is required. The device pushes MEASURED_DATA ~1×/second
while connected; for a poll-style update we connect, read MEASURED_DATA once, read a
few slow-changing characteristics, and return. The caller manages the BLEDevice
(in Home Assistant, via the shared scanner).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bleak.backends.device import BLEDevice
from bleak.exc import BleakCharacteristicNotFoundError
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
    # Raw MEASURED_DATA bytes, kept for diagnostics / protocol debugging.
    measured_raw: bytes = b""


class CloudRODevice:
    """Reads state from a single Cloud RO unit."""

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._last_firmware: str | None = None

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
            except BleakCharacteristicNotFoundError as err:
                # Rare and self-healing, but logged at WARNING (not DEBUG) so the
                # recovery is visible in normal logs without enabling debug.
                _LOGGER.warning(
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
        # Logged at DEBUG every poll; the firmware also surfaces once at INFO below.
        _LOGGER.debug(
            "Cloud RO %s firmware=%s MEASURED_DATA raw: %s",
            self._ble_device.address,
            firmware,
            measured_raw.hex(),
        )
        # Firmware is the key compatibility datum (see Compatibility in the README),
        # so log it once at INFO on first connect and whenever it changes — without
        # spamming a line every poll.
        if firmware != self._last_firmware:
            _LOGGER.info(
                "Cloud RO %s firmware is %s", self._ble_device.address, firmware
            )
            self._last_firmware = firmware

        try:
            measured = parse_measured_data(measured_raw)
        except ValueError as err:
            # Capture the raw frame at WARNING so a layout change (e.g. new firmware)
            # is diagnosable from a normal log, without needing debug enabled first.
            _LOGGER.warning(
                "Cloud RO %s: could not parse MEASURED_DATA (%s); raw: %s",
                self._ble_device.address,
                err,
                measured_raw.hex(),
            )
            raise

        mag_install = await self._read_u32(client, MAG_INSTALL_DATE)

        return CloudROState(
            address=self._ble_device.address,
            name=self._ble_device.name,
            measured=measured,
            firmware=firmware,
            mag_install_date=mag_install,
            measured_raw=measured_raw,
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


def is_cloud_ro(service_uuids: list[str]) -> bool:
    """True if an advertisement's service UUIDs indicate a Cloud RO unit."""
    return CLOUD_SERVICE_UUID in [u.lower() for u in service_uuids]
