# Cloud RO BLE protocol

Cloud RO water systems expose their telemetry over a custom Bluetooth LE GATT
service. There is **no pairing, bonding, or authentication** — any central that
connects can read the data. This document specifies the service so the integration
(and the `cloudro-ble` library) can read it.

## Discovery

The unit advertises the primary service UUID below; clients scan for it.

| | |
|---|---|
| Primary service | `5e3c1400-0929-41b6-89ea-502be1edf8b0` |
| Firmware-update service (ignored) | `8ec91400-f315-4f60-9fb8-838830daea50` |

## Characteristics

Characteristic UUIDs follow the pattern `5e3c14XX-0929-41b6-89ea-502be1edf8b0`,
where `XX` is the hex code below. The integration routes incoming data by that code.

| Code | Name | UUID `5e3c14XX` | Access | Payload |
|---|---|---|---|---|
| `0x1401` | VERSION | `5e3c1401` | read / notify | string |
| `0x1402` | DATETIME | `5e3c1402` | read / notify / write | uint32 LE unix time |
| `0x1403` | MAG_INSTALL_DATE | `5e3c1403` | read / notify | uint32 LE unix time (remineralizer install) |
| `0x1404` | MEASURED_DATA | `5e3c1404` | read / notify | 34-byte struct (below) |
| `0x1405` | NICKNAME | `5e3c1405` | read / notify / write | string |
| `0x1406` | CONSUMED_WATER | `5e3c1406` | read / notify | monthly histogram (below) |
| `0x1407` | HISTORICAL_TDS | `5e3c1407` | read / notify | TDS record (below) |
| `0x1410` | COMMAND | `5e3c1410` | write | ASCII command |
| `0x1411` | RESPONSE | `5e3c1411` | read / notify | string |
| `0x1420` | RAW_DATA | `5e3c1420` | — | raw |

## MEASURED_DATA (`0x1404`) — 34 bytes, little-endian

The primary live telemetry. The device notifies it roughly once per second while
connected, so an integration can connect, subscribe, and throttle updates.

| Field | Offset | Type | Notes |
|---|---|---|---|
| InletTDS | 0 | uint16 | tap water TDS (ppm) |
| PostROTDS | 2 | uint16 | TDS after the RO membrane (ppm) |
| ReminTDS | 4 | uint16 | TDS after remineralization = drinking water (ppm) |
| StoredWater | 6 | uint16 | current tank level (raw units) |
| TotalDispensedWater | 8 | uint32 | lifetime dispensed, **fluid ounces** |
| BatteryLife | 12 | uint16 | percent (0–100) |
| BatteryVoltage | 14 | uint16 | millivolts |
| TankPressure | 16 | uint16 | raw units |
| MaxTankPressureLife | 18 | uint16 | |
| MaxTankVolumeLife | 20 | uint16 | full-tank reference for tank % |
| MaxTankPressureMonth | 22 | uint16 | |
| MaxTankVolumeMonth | 24 | uint16 | |
| Latch | 26 | uint8 | status flag |
| Flow | 27 | uint8 | non-zero while water is flowing |
| Valve | 28 | uint8 | valve state |
| ErrorCode | 29 | uint8 | 0 = OK |
| TS | 30 | uint32 | sample unix timestamp |

## CONSUMED_WATER (`0x1406`)

Monthly consumption histogram: 12 × uint16 LE at offsets 0,2,…,22 (Jan…Dec), then an
optional uint32 LE overflow at offset 24. Values are in fluid ounces. Recent per-day
records may be appended after the histogram.

## HISTORICAL_TDS (`0x1407`)

`TS = uint32 LE(0)`, `InletTDS = uint16 LE(4)`, `PostROTDS = uint16 LE(6)`,
`ReminTDS = uint16 LE(8)`.

## Connection flow

1. Scan, filtering on the primary service UUID.
2. Connect (no bonding) and retrieve services.
3. Subscribe to the read/notify characteristics; the device pushes `MEASURED_DATA`.
4. Optionally read `VERSION`, `MAG_INSTALL_DATE`, `CONSUMED_WATER`, `HISTORICAL_TDS`.

Optional writes (not required for telemetry):

- `COMMAND` (`0x1410`): ASCII `TDSHISTORY` requests a historical-TDS notification.
- `DATETIME` (`0x1402`): uint32 unix time to sync the device clock.

## Derived values

- **Dispensed water in gallons** = `TotalDispensedWater / 128` (the device counts
  fluid ounces).
- **Tank fill %** = `clamp(round(StoredWater / MaxTankVolumeLife × 100), 0, 100)`.
- **Filter / battery status** maps from `BatteryVoltage` (the remineralizer cartridge
  and battery are serviced together):
  - `≥ 4000 mV` → OK
  - `3900–3999 mV` → replace soon
  - `< 3900 mV` → replace

  A server-side replacement recommendation can also exist but is not exposed over BLE.

## Unconfirmed

- `TankPressure` units (exposed raw).
