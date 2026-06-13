"""Bluetooth LE protocol library for Cloud RO water filtration systems."""

from __future__ import annotations

from .const import CLOUD_SERVICE_UUID, char_uuid
from .device import CloudRODevice, CloudROState, is_cloud_ro
from .parser import (
    ConsumedWater,
    HistoricalTDS,
    MeasuredData,
    parse_consumed_water,
    parse_historical_tds,
    parse_measured_data,
)

__version__ = "0.1.3"

__all__ = [
    "CLOUD_SERVICE_UUID",
    "char_uuid",
    "CloudRODevice",
    "CloudROState",
    "is_cloud_ro",
    "MeasuredData",
    "HistoricalTDS",
    "ConsumedWater",
    "parse_measured_data",
    "parse_historical_tds",
    "parse_consumed_water",
]
