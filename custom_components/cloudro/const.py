"""Constants for the Cloud RO integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "cloudro"

MANUFACTURER = "Cloud Water Filters"
MODEL = "Cloud RO"

# The unit pushes data ~1×/second while connected, but tank/TDS change slowly.
# Poll on a relaxed interval to keep the BLE connection brief and battery-friendly.
UPDATE_INTERVAL = timedelta(seconds=60)
