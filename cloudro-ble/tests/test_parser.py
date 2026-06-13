"""Tests for the Cloud RO payload decoders, using sample device payloads."""

from __future__ import annotations

import pytest

from cloudro_ble import (
    parse_consumed_water,
    parse_historical_tds,
    parse_measured_data,
)

# Sample MEASURED_DATA frame.
MEASURED_FIXTURE = bytes.fromhex(
    "78 00 03 00 12 00 f3 00 20 da 00 00 64 00 87 12 2d 00 30 00"
    "f8 00 2f 00 f6 00 00 00 01 00 bd 7d 2d 6a".replace(" ", "")
)

# Sample CONSUMED_WATER read (leading monthly histogram + overflow).
CONSUMED_FIXTURE = bytes.fromhex(
    "fa 13 f4 13 68 16 be 15 55 1a ce 08 89 05 fb 12 11 12 d8 10"
    "dd 12 9d 14 02 00 00 00".replace(" ", "")
)


def test_parse_measured_data_matches_live_values():
    m = parse_measured_data(MEASURED_FIXTURE)
    assert m.inlet_tds == 120
    assert m.post_ro_tds == 3
    assert m.remin_tds == 18
    assert m.stored_water == 243
    assert m.max_tank_volume_life == 248
    assert m.total_dispensed_water == 55840
    assert m.battery_life == 100
    assert m.battery_voltage_mv == 4743
    assert m.tank_pressure == 45
    assert m.max_tank_pressure_life == 48
    assert m.latch == 0
    assert m.flow == 0
    assert m.valve == 1
    assert m.error_code == 0
    assert m.timestamp == 0x6A2D7DBD


def test_measured_data_derived_properties():
    m = parse_measured_data(MEASURED_FIXTURE)
    assert m.tank_fill_percent == pytest.approx(98.0, abs=0.1)
    assert m.battery_voltage == pytest.approx(4.743)
    assert m.total_dispensed_gallons == pytest.approx(436.2, abs=0.1)  # 55840 / 128
    assert m.replacement_status == "ok"  # 4743 mV >= 4000
    assert m.ok is True


@pytest.mark.parametrize(
    ("battery_mv", "expected"),
    [(4743, "ok"), (4000, "ok"), (3999, "replace_soon"), (3900, "replace_soon"), (3899, "replace")],
)
def test_replacement_status_thresholds(battery_mv, expected):
    m = parse_measured_data(MEASURED_FIXTURE)
    m.battery_voltage_mv = battery_mv
    assert m.replacement_status == expected


def test_parse_measured_data_rejects_short_payload():
    with pytest.raises(ValueError):
        parse_measured_data(MEASURED_FIXTURE[:20])


def test_tank_fill_percent_handles_zero_max():
    m = parse_measured_data(MEASURED_FIXTURE)
    m.max_tank_volume_life = 0
    assert m.tank_fill_percent is None


def test_parse_consumed_water():
    c = parse_consumed_water(CONSUMED_FIXTURE)
    assert len(c.months) == 12
    assert c.months[0] == 0x13FA  # Jan
    assert c.months[11] == 0x149D  # Dec
    assert c.overflow == 2
    assert c.total == sum(c.months) + 2


def test_parse_historical_tds():
    # TS=0x6A2D7DBD, inlet=120, post_ro=3, remin=18
    raw = bytes.fromhex("bd7d2d6a") + bytes.fromhex("7800") + bytes.fromhex("0300") + bytes.fromhex("1200")
    h = parse_historical_tds(raw)
    assert h.timestamp == 0x6A2D7DBD
    assert h.inlet_tds == 120
    assert h.post_ro_tds == 3
    assert h.remin_tds == 18
