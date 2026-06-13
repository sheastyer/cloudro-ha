"""End-to-end setup test: real parser output flows through to HA entity states."""

from unittest.mock import AsyncMock, patch

from custom_components.cloudro.cloudro_ble import CloudROState, parse_measured_data
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.cloudro.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:FF"

# Real MEASURED_DATA frame captured from device AJ551-CLOUDRO.
FIXTURE = bytes.fromhex(
    (
        "78 00 03 00 12 00 f3 00 20 da 00 00 64 00 87 12 2d 00 30 00"
        "f8 00 2f 00 f6 00 00 00 01 00 bd 7d 2d 6a"
    ).replace(" ", "")
)


def _state() -> CloudROState:
    return CloudROState(
        address=ADDRESS,
        name="AJ551-CLOUDRO",
        measured=parse_measured_data(FIXTURE),
        firmware="V1.05",
        mag_install_date=808990513,
    )


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="AJ551-CLOUDRO")
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
    assert state_of("sensor", "total_dispensed") == "55840"
    assert state_of("sensor", "battery") == "100"
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
