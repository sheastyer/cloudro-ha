"""Config-flow tests for the Cloud RO integration."""

from types import SimpleNamespace
from unittest.mock import patch

from custom_components.cloudro.cloudro_ble import CLOUD_SERVICE_UUID

from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.cloudro.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:FF"


def _service_info(name: str = "AJ551-CLOUDRO") -> SimpleNamespace:
    """A stand-in for BluetoothServiceInfoBleak (flow only uses these attrs)."""
    return SimpleNamespace(
        address=ADDRESS, name=name, service_uuids=[CLOUD_SERVICE_UUID]
    )


async def test_bluetooth_discovery_flow(hass: HomeAssistant) -> None:
    """A unit advertised over Bluetooth is offered for setup and creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "AJ551-CLOUDRO"
    assert result["result"].unique_id == ADDRESS


async def test_user_flow(hass: HomeAssistant) -> None:
    """The manual flow lists discovered units and creates an entry."""
    with patch(
        "custom_components.cloudro.config_flow.async_discovered_service_info",
        return_value=[_service_info()],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"address": ADDRESS}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == ADDRESS


async def test_user_flow_no_devices(hass: HomeAssistant) -> None:
    """The manual flow aborts when nothing is in range."""
    with patch(
        "custom_components.cloudro.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"
