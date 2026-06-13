"""The diagnostics dump reflects the last reading and redacts the device address."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cloudro.cloudro_ble import CloudROState, parse_measured_data
from custom_components.cloudro.const import DOMAIN
from custom_components.cloudro.diagnostics import async_get_config_entry_diagnostics

ADDRESS = "AA:BB:CC:DD:EE:FF"
FIXTURE = bytes.fromhex(
    (
        "78 00 03 00 12 00 f3 00 20 da 00 00 64 00 87 12 2d 00 30 00"
        "f8 00 2f 00 f6 00 00 00 01 00 bd 7d 2d 6a"
    ).replace(" ", "")
)


def _state() -> CloudROState:
    return CloudROState(
        address=ADDRESS,
        name="Cloud RO",
        measured=parse_measured_data(FIXTURE),
        firmware="V1.05",
        mag_install_date=None,
        measured_raw=FIXTURE,
    )


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="Cloud RO")
    entry.add_to_hass(hass)
    fake_device = AsyncMock()
    fake_device.update = AsyncMock(return_value=_state())
    with (
        patch(
            "custom_components.cloudro.coordinator.bluetooth.async_ble_device_from_address",
            return_value=object(),
        ),
        patch(
            "custom_components.cloudro.coordinator.CloudRODevice",
            return_value=fake_device,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_diagnostics_dump(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["last_update_success"] is True
    state = diag["state"]
    assert state["firmware"] == "V1.05"
    assert state["measured_raw"] == FIXTURE.hex()
    assert state["measured"]["inlet_tds"] == 120
    # Derived properties are included alongside the raw fields.
    assert state["measured"]["tank_fill_percent"] == 98.0
    assert state["measured"]["replacement_status"] == "ok"

    # The BLE address / unique_id is redacted from the dump.
    assert state["address"] == REDACTED
    assert diag["entry"]["unique_id"] == REDACTED
    assert ADDRESS not in repr(diag)
