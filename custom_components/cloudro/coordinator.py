"""DataUpdateCoordinator for the Cloud RO integration."""

from __future__ import annotations

import logging

from .cloudro_ble import CloudRODevice, CloudROState

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type CloudROConfigEntry = ConfigEntry[CloudRODataUpdateCoordinator]


class CloudRODataUpdateCoordinator(DataUpdateCoordinator[CloudROState]):
    """Polls a Cloud RO unit over BLE using the shared Home Assistant scanner."""

    config_entry: CloudROConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: CloudROConfigEntry, address: str
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{address}",
            update_interval=UPDATE_INTERVAL,
        )
        self.address = address
        self._device: CloudRODevice | None = None

    async def _async_update_data(self) -> CloudROState:
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise UpdateFailed(f"Cloud RO {self.address} not in Bluetooth range")

        if self._device is None:
            self._device = CloudRODevice(ble_device)
        else:
            self._device.set_ble_device(ble_device)

        try:
            return await self._device.update()
        except Exception as err:  # noqa: BLE001 - surface all BLE errors as UpdateFailed
            raise UpdateFailed(f"Error reading Cloud RO {self.address}: {err}") from err
