"""End-to-end setup test: real parser output flows through to HA entity states."""

from unittest.mock import AsyncMock, patch

import pytest
from custom_components.cloudro.cloudro_ble import CloudROState, parse_measured_data
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.cloudro.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:FF"

# Sample MEASURED_DATA frame.
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
    )


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    hass.config.units = US_CUSTOMARY_SYSTEM  # show dispensed water in gallons
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


async def test_entities_reflect_decoded_values(hass: HomeAssistant) -> None:
    await _setup(hass)
    ent_reg = er.async_get(hass)

    def state_of(platform: str, key: str) -> str:
        entity_id = ent_reg.async_get_entity_id(platform, DOMAIN, f"{ADDRESS}_{key}")
        assert entity_id, f"missing entity {key}"
        return hass.states.get(entity_id).state

    assert state_of("sensor", "inlet_tds") == "120"
    assert state_of("sensor", "post_ro_tds") == "3"
    assert state_of("sensor", "remin_tds") == "18"
    assert float(state_of("sensor", "tank_fill")) == 98.0
    assert float(state_of("sensor", "total_dispensed")) == pytest.approx(436.2, abs=0.1)
    assert state_of("sensor", "battery") == "100"
    assert state_of("sensor", "replacement_status") == "ok"
    assert state_of("binary_sensor", "problem") == "off"
    assert state_of("binary_sensor", "flow") == "off"


async def test_device_registry(hass: HomeAssistant) -> None:
    await _setup(hass)
    from homeassistant.helpers import device_registry as dr

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(identifiers={(DOMAIN, ADDRESS)})
    assert device is not None
    assert device.manufacturer == "Cloud Water Filters"
    assert device.model == "Cloud RO"
    assert device.sw_version == "V1.05"
