# Cloud RO BLE protocol

Reverse-engineered from `com.cloudwaterfilters` v1.6.0 (React Native bundle,
`assets/index.android.bundle`, plain minified JS — BLE module fully readable) and
live BLE recon from macOS. **No authentication / pairing / handshake** — the device
exposes its data over a custom GATT service to any central that connects.

## Device

- Advertised name: `AJ551-CL` (the app scans **by service UUID**, then maps name→serial)
- Advertises service `5E3C1400-0929-41B6-89EA-502BE1EDF8B0` in its adv packet
- App library: `react-native-ble-manager`
- NOTE: the earlier `112637_533C` / `4772911e-...` device was a **red herring**
  (a different product — returned "Insufficient Authentication"; not Cloud).

## GATT layout

Primary service **`5E3C1400-0929-41B6-89EA-502BE1EDF8B0`** (`CLOUD_SERVICE`).
DFU/firmware service `8EC91400-F315-4F60-9FB8-838830DAEA50` (ignore).

Characteristic UUIDs are `5E3C14XX-0929-41B6-89EA-502BE1EDF8B0`, where `XX` is the
hex code below. (App builds them as `"5E3C"+code.toString(16)+"-0929-41B6-89EA-502BE1EDF8B0"`.)

| Code (dec / hex) | Name | UUID `5E3C14XX` | Access | Payload |
|---|---|---|---|---|
| 5121 / 0x1401 | VERSION | `5E3C1401` | read/notify | string |
| 5122 / 0x1402 | DATETIME | `5E3C1402` | read/notify/write | uint32 LE unix time |
| 5123 / 0x1403 | MAG_INSTALL_DATE | `5E3C1403` | read/notify | uint32 LE unix time (remineralizer install) |
| 5124 / 0x1404 | **MEASURED_DATA** | `5E3C1404` | read/notify | 34-byte struct (below) |
| 5125 / 0x1405 | NICKNAME | `5E3C1405` | read/notify/write | string (app skips parsing) |
| 5126 / 0x1406 | CONSUMED_WATER | `5E3C1406` | read/notify | monthly histogram (below) |
| 5127 / 0x1407 | HISTORICAL_TDS | `5E3C1407` | read/notify | TDS record (below) |
| 5136 / 0x1410 | COMMAND | `5E3C1410` | write | ASCII command (e.g. `TDSHISTORY`) |
| 5137 / 0x1411 | RESPONSE | `5E3C1411` | read/notify | string command response |
| 5152 / 0x1420 | RAW_DATA | `5E3C1420` | — | raw |

The app routes incoming data by `code = parseInt(uuid.substr(4,4), 16)`.

## MEASURED_DATA (`5E3C1404`) — 34 bytes, little-endian — THE LIVE METRICS

| Field | Offset | Type | Meaning / notes (units TBD by live test) |
|---|---|---|---|
| InletTDS | 0 | uint16 | tap water TDS (ppm) |
| PostROTDS | 2 | uint16 | TDS after RO membrane (ppm) |
| ReminTDS | 4 | uint16 | TDS after remineralization = final drinking water (ppm) |
| **StoredWater** | 6 | uint16 | current tank volume (raw units — scale to gal via Max*Volume or live test) |
| TotalDispensedWater | 8 | uint32 | lifetime dispensed |
| BatteryLife | 12 | uint16 | battery (% or raw) |
| BatteryVoltage | 14 | uint16 | mV (likely) |
| TankPressure | 16 | uint16 | current tank pressure |
| MaxTankPressureLife | 18 | uint16 | |
| MaxTankVolumeLife | 20 | uint16 | full-tank reference → use for tank % |
| MaxTankPressureMonth | 22 | uint16 | |
| MaxTankVolumeMonth | 24 | uint16 | |
| Latch | 26 | uint8 | status flag |
| Flow | 27 | uint8 | flow state flag |
| Valve | 28 | uint8 | valve state flag |
| ErrorCode | 29 | uint8 | 0 = OK |
| TS | 30 | uint32 | sample unix timestamp |

Tank % (for a friendly entity) ≈ `StoredWater / MaxTankVolumeLife * 100` (verify live).

## CONSUMED_WATER (`5E3C1406`) — monthly histogram

12 × uint16 LE at offsets 0,2,…,22 = Jan…Dec consumption; then `Overflow = uint32 LE`
at offset 24 (optional). Units = same as dispensed water.

## HISTORICAL_TDS (`5E3C1407`) — TDS snapshot record

`TS = uint32LE(0)`, `InletTDS = uint16LE(4)`, `PostROTDS = uint16LE(6)`,
`ReminTDS = uint16LE(8)`.

## Connection flow (what the library must do)

1. **Scan** filtering on service UUID `5E3C1400-...` → finds `AJ551-CL`.
2. **Connect** (plain connect, no bonding).
3. **retrieveServices** for the Cloud service.
4. **Subscribe (notify)** to every read+notify characteristic — the device PUSHES
   `MEASURED_DATA` periodically, so this can behave as local-push once connected.
5. **Eager-read** VERSION, MAG_INSTALL_DATE, CONSUMED_WATER, HISTORICAL_TDS,
   MEASURED_DATA.
6. Parse per tables above.

Optional writes (not needed for read-only metrics):
- `COMMAND` (`5E3C1410`) ASCII `TDSHISTORY` → triggers a historical-TDS notify.
- `DATETIME` (`5E3C1402`) ← uint32 unix time (the app syncs the clock on connect).

## Filter status

There is no direct "filter life %" characteristic. The app derives filter/remineralizer
status from `MAG_INSTALL_DATE` + consumed/dispensed water vs rated life. We can surface
the raw inputs first, and replicate the % calc later once we see the app's formula
(in another bundle module — TODO if wanted).

## LIVE-CONFIRMED (2026-06-13, device `AJ551-CL`, no pairing)

Decoder verified against the real unit — all fields physically sensible:

```
VERSION          = "V1.05"
MAG_INSTALL_DATE = 1995-08-21  (looks unset/default — confirm vs app)
MEASURED_DATA: InletTDS=120 PostROTDS=3 ReminTDS=18 (ppm)
               StoredWater=243 MaxTankVolumeLife=248  -> ~98% full
               TotalDispensedWater=55840  BatteryLife=100(%)  BatteryVoltage=4743(mV=4.74V)
               TankPressure=45 MaxTankPressureLife=48
               Latch=0 Flow=0 Valve=1 ErrorCode=0  TS=now ✓
```

Confirmed units:
- TDS fields: **ppm**.
- BatteryLife: **percent** (0–100).
- BatteryVoltage: **millivolts** (4743 = 4.74 V).
- StoredWater / MaxTankVolume*: **raw units (~248 = full)**, NOT gallons. Surface as
  **tank fill %** = StoredWater / MaxTankVolumeLife × 100. (To also show gallons, calibrate
  raw→gal once against the app, e.g. full ≈ 2.8 gal usable.)
- TankPressure: raw units (~45–48 range); unit unknown (psi-ish?). Surface raw.

Behavior:
- **MEASURED_DATA notifies ~1×/second** while connected (true push). Integration should
  connect, subscribe, and throttle updates (e.g. accept ≤ every 30–60 s) to avoid spamming HA.
- CONSUMED_WATER read returns the 12-month histogram followed by appended recent
  per-day records (TS+TDS quadruplets); parse the leading 24–28 bytes for monthly totals.

## Open calibration questions (compare against the app UI)

- Tank volume in **gallons**: what does the app show now vs StoredWater≈243/248? → raw→gal factor.
- **Filter / remineralizer status**: how the app presents it, and whether it maps to
  MAG_INSTALL_DATE (which read as 1995 = likely unset) or to dispensed-water thresholds.
- TankPressure units (psi?).

## Captures / sources

- `apk/base_extracted/assets/index.android.bundle` — app JS (BLE module decoded)
- `apk/ble_module.js`, `apk/ble_module2.js` — beautified BLE module excerpts
- `captures/` — scan + GATT dumps
