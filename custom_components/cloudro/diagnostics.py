"""Diagnostics for the Cloud RO integration.

Lets a user download a snapshot of the last reading (parsed values, firmware, and
the raw MEASURED_DATA frame) from the integration page — no log access, no restart,
and no need to enable debug logging first.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import CloudROConfigEntry

# The device address is the entry's unique_id (a BLE MAC); redact it from the dump.
TO_REDACT = {"address", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CloudROConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    state = coordinator.data

    data: dict[str, Any] = {
        "entry": {"title": entry.title, "unique_id": entry.unique_id},
        "last_update_success": coordinator.last_update_success,
    }

    if state is not None:
        measured = state.measured
        data["state"] = {
            "address": state.address,
            "name": state.name,
            "firmware": state.firmware,
            "mag_install_date": state.mag_install_date,
            "measured_raw": state.measured_raw.hex() or None,
            "measured": {
                **asdict(measured),
                # Derived values (properties aren't picked up by asdict).
                "tank_fill_percent": measured.tank_fill_percent,
                "battery_voltage": measured.battery_voltage,
                "total_dispensed_gallons": measured.total_dispensed_gallons,
                "replacement_status": measured.replacement_status,
                "ok": measured.ok,
            },
        }

    return async_redact_data(data, TO_REDACT)
