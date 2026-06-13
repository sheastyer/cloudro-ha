"""Pure decoders for Cloud RO BLE payloads.

These functions take raw characteristic bytes and return dataclasses. They have no
I/O and no Bluetooth dependency, so they are unit-tested against captured fixtures.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .const import MEASURED_DATA_LEN


@dataclass(slots=True)
class MeasuredData:
    """Decoded MEASURED_DATA (characteristic 0x1404) — the live metrics.

    See PROTOCOL.md for byte layout. TDS values are ppm, battery_life is percent,
    battery_voltage is millivolts. stored_water / max_tank_volume_life are raw units
    (~248 = full); use tank_fill_percent for a friendly value.
    """

    inlet_tds: int
    post_ro_tds: int
    remin_tds: int
    stored_water: int
    total_dispensed_water: int
    battery_life: int
    battery_voltage_mv: int
    tank_pressure: int
    max_tank_pressure_life: int
    max_tank_volume_life: int
    max_tank_pressure_month: int
    max_tank_volume_month: int
    latch: int
    flow: int
    valve: int
    error_code: int
    timestamp: int

    @property
    def tank_fill_percent(self) -> float | None:
        """Tank fill as a percentage of the lifetime max observed volume."""
        if not self.max_tank_volume_life:
            return None
        return round(self.stored_water / self.max_tank_volume_life * 100, 1)

    @property
    def battery_voltage(self) -> float:
        """Battery voltage in volts."""
        return round(self.battery_voltage_mv / 1000, 3)

    @property
    def ok(self) -> bool:
        """True when the device reports no error."""
        return self.error_code == 0


def parse_measured_data(data: bytes) -> MeasuredData:
    """Decode a 34-byte MEASURED_DATA payload (little-endian)."""
    if len(data) < MEASURED_DATA_LEN:
        raise ValueError(
            f"MEASURED_DATA too short: {len(data)} bytes (need {MEASURED_DATA_LEN})"
        )
    (
        inlet_tds,
        post_ro_tds,
        remin_tds,
        stored_water,
        total_dispensed_water,
        battery_life,
        battery_voltage_mv,
        tank_pressure,
        max_tank_pressure_life,
        max_tank_volume_life,
        max_tank_pressure_month,
        max_tank_volume_month,
    ) = struct.unpack_from("<HHHHIHHHHHHH", data, 0)
    latch, flow, valve, error_code = struct.unpack_from("<BBBB", data, 26)
    (timestamp,) = struct.unpack_from("<I", data, 30)
    return MeasuredData(
        inlet_tds=inlet_tds,
        post_ro_tds=post_ro_tds,
        remin_tds=remin_tds,
        stored_water=stored_water,
        total_dispensed_water=total_dispensed_water,
        battery_life=battery_life,
        battery_voltage_mv=battery_voltage_mv,
        tank_pressure=tank_pressure,
        max_tank_pressure_life=max_tank_pressure_life,
        max_tank_volume_life=max_tank_volume_life,
        max_tank_pressure_month=max_tank_pressure_month,
        max_tank_volume_month=max_tank_volume_month,
        latch=latch,
        flow=flow,
        valve=valve,
        error_code=error_code,
        timestamp=timestamp,
    )


@dataclass(slots=True)
class HistoricalTDS:
    """A historical TDS record (characteristic 0x1407)."""

    timestamp: int
    inlet_tds: int
    post_ro_tds: int
    remin_tds: int


def parse_historical_tds(data: bytes) -> HistoricalTDS:
    """Decode the leading 10 bytes of a HISTORICAL_TDS payload."""
    if len(data) < 10:
        raise ValueError(f"HISTORICAL_TDS too short: {len(data)} bytes")
    timestamp, inlet, post_ro, remin = struct.unpack_from("<IHHH", data, 0)
    return HistoricalTDS(
        timestamp=timestamp, inlet_tds=inlet, post_ro_tds=post_ro, remin_tds=remin
    )


@dataclass(slots=True)
class ConsumedWater:
    """Monthly water-consumption histogram (characteristic 0x1406)."""

    months: list[int] = field(default_factory=list)  # Jan..Dec, raw units
    overflow: int = 0

    @property
    def total(self) -> int:
        return sum(self.months) + self.overflow


def parse_consumed_water(data: bytes) -> ConsumedWater:
    """Decode the leading monthly histogram (12 x uint16, then optional uint32 overflow).

    The device appends recent per-day records after the histogram; we only read the
    leading 24 (or 28) bytes.
    """
    if len(data) < 24:
        raise ValueError(f"CONSUMED_WATER too short: {len(data)} bytes")
    months = list(struct.unpack_from("<12H", data, 0))
    overflow = 0
    if len(data) >= 28:
        (overflow,) = struct.unpack_from("<I", data, 24)
    return ConsumedWater(months=months, overflow=overflow)
