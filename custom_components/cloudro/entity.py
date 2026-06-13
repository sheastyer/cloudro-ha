"""Base entity for the Cloud RO integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import CloudRODataUpdateCoordinator


class CloudROEntity(CoordinatorEntity[CloudRODataUpdateCoordinator]):
    """Base entity that ties all platforms to one Cloud RO device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CloudRODataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        address = coordinator.address
        state = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={(CONNECTION_BLUETOOTH, address)},
            name=state.name or f"{MODEL} {address}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=state.firmware,
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None
