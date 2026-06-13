"""Config flow for the Cloud RO Water integration."""

from __future__ import annotations

from typing import Any

from .cloudro_ble import is_cloud_ro
import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, MODEL


class CloudROConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cloud RO."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._discoveries: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a unit discovered automatically over Bluetooth."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {"name": self._title(discovery_info)}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup of a discovered unit."""
        assert self._discovery is not None
        if user_input is not None:
            return self._create_entry(self._discovery)

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._title(self._discovery)},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup by picking from discovered units."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self._create_entry(self._discoveries[address])

        current = self._async_current_ids()
        for info in async_discovered_service_info(self.hass, connectable=True):
            if (
                info.address not in current
                and info.address not in self._discoveries
                and is_cloud_ro(info.service_uuids)
            ):
                self._discoveries[info.address] = info

        if not self._discoveries:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: self._title(info)
                            for address, info in self._discoveries.items()
                        }
                    )
                }
            ),
        )

    def _create_entry(self, info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        return self.async_create_entry(title=self._title(info), data={})

    @staticmethod
    def _title(info: BluetoothServiceInfoBleak) -> str:
        return info.name or f"{MODEL} {info.address}"
