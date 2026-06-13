"""CloudRODevice.update() recovers from a stale GATT service cache.

A device reboot or firmware update can leave Home Assistant with a cached GATT
table that no longer contains MEASURED_DATA, so every read fails with
"characteristic ... was not found". update() should clear the cache and reconnect
once to force a fresh discovery rather than failing forever.
"""

import logging
from unittest.mock import AsyncMock, patch

import pytest
from bleak import BleakError
from bleak.exc import BleakCharacteristicNotFoundError

from custom_components.cloudro.cloudro_ble.const import MEASURED_DATA, char_uuid
from custom_components.cloudro.cloudro_ble.device import CloudRODevice

MODULE = "custom_components.cloudro.cloudro_ble.device"

# A valid 34-byte MEASURED_DATA frame (InletTDS=120 in the first uint16 LE).
FIXTURE = bytes.fromhex(
    (
        "78 00 03 00 12 00 f3 00 20 da 00 00 64 00 87 12 2d 00 30 00"
        "f8 00 2f 00 f6 00 00 00 01 00 bd 7d 2d 6a"
    ).replace(" ", "")
)


def _fake_device() -> AsyncMock:
    dev = AsyncMock()
    dev.address = "AA:BB:CC:DD:EE:FF"
    dev.name = "Cloud RO"
    return dev


def _ok_client() -> AsyncMock:
    client = AsyncMock()
    client.read_gatt_char = AsyncMock(return_value=bytearray(FIXTURE))
    return client


def _stale_client() -> AsyncMock:
    """A client whose cached GATT table is missing MEASURED_DATA."""
    client = AsyncMock()
    not_found = BleakCharacteristicNotFoundError(char_uuid(MEASURED_DATA))
    client.read_gatt_char = AsyncMock(side_effect=not_found)
    client.clear_cache = AsyncMock(return_value=True)
    return client


async def test_update_clears_cache_and_retries_on_missing_characteristic(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stale, good = _stale_client(), _ok_client()
    with (
        caplog.at_level(logging.WARNING, logger=MODULE),
        patch(f"{MODULE}.establish_connection", side_effect=[stale, good]) as connect,
    ):
        state = await CloudRODevice(_fake_device()).update()

    # Recovered: parsed the frame read after the reconnect.
    assert state.measured.inlet_tds == 120
    assert state.measured_raw == FIXTURE
    # Dropped the stale cache, reconnected a second time, and cleaned up both clients.
    stale.clear_cache.assert_awaited_once()
    assert connect.call_count == 2
    stale.disconnect.assert_awaited()
    good.disconnect.assert_awaited()
    # The recovery is visible at WARNING without enabling debug.
    assert any(
        r.levelno == logging.WARNING and "clearing GATT cache" in r.message
        for r in caplog.records
    )


async def test_update_warns_with_raw_frame_on_parse_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # A too-short MEASURED_DATA frame makes parse_measured_data raise ValueError.
    short = bytes.fromhex("deadbeef")
    client = AsyncMock()
    client.read_gatt_char = AsyncMock(return_value=bytearray(short))
    with (
        caplog.at_level(logging.WARNING, logger=MODULE),
        patch(f"{MODULE}.establish_connection", side_effect=[client]),
    ):
        with pytest.raises(ValueError):
            await CloudRODevice(_fake_device()).update()

    # The raw bytes are captured at WARNING so a layout change is diagnosable
    # without debug logging having been enabled beforehand.
    assert any(
        r.levelno == logging.WARNING and short.hex() in r.message
        for r in caplog.records
    )
    client.disconnect.assert_awaited()


async def test_firmware_logged_once_at_info(caplog: pytest.LogCaptureFixture) -> None:
    device = CloudRODevice(_fake_device())
    with (
        caplog.at_level(logging.INFO, logger=MODULE),
        patch(f"{MODULE}.establish_connection", return_value=_ok_client()),
    ):
        await device.update()
        await device.update()  # same firmware on the second poll

    firmware_lines = [r for r in caplog.records if "firmware is" in r.message]
    assert len(firmware_lines) == 1
    assert firmware_lines[0].levelno == logging.INFO


async def test_update_does_not_retry_other_errors() -> None:
    client = AsyncMock()
    client.read_gatt_char = AsyncMock(side_effect=BleakError("disconnected"))
    with patch(f"{MODULE}.establish_connection", side_effect=[client]) as connect:
        with pytest.raises(BleakError, match="disconnected"):
            await CloudRODevice(_fake_device()).update()

    client.clear_cache.assert_not_called()
    assert connect.call_count == 1
    client.disconnect.assert_awaited()
