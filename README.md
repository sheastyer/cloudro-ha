# Cloud RO Water — Home Assistant integration

Local Home Assistant integration for [Cloud RO](https://www.cloudwaterfilters.com/)
reverse-osmosis water systems. Talks to the unit directly over Bluetooth LE — **no
cloud, no account, no authentication** — and surfaces:

- **TDS at every stage**: inlet (tap), post-RO (after membrane), remineralized (what you drink)
- **Tank fill %** and raw stored-water level
- **Lifetime dispensed water**
- **Battery** level and voltage
- **Tank pressure**, water-flow status, and a problem indicator (device error code)

The Bluetooth protocol was reverse-engineered from the Cloud Water Filters app and
verified against real hardware — see [`PROTOCOL.md`](PROTOCOL.md).

## Layout

| Path | What |
|---|---|
| `custom_components/cloudro/` | The Home Assistant integration |
| `cloudro-ble/` | Standalone BLE protocol library (no HA dependency) |
| `tools/` | BLE recon / verification scripts used during development |
| `PROTOCOL.md` | The reverse-engineered protocol spec |

## Install (HACS custom repository)

1. HACS → Integrations → ⋯ → Custom repositories → add this repo as an *Integration*.
2. Install **Cloud RO Water**, restart Home Assistant.
3. Your unit is auto-discovered over Bluetooth — confirm the prompt under
   Settings → Devices & Services.

> Requires a Bluetooth adapter within range of the unit. On Home Assistant OS this
> is the built-in/USB Bluetooth or a [Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html).

## Develop

```bash
# protocol library + unit tests (no hardware needed)
python -m venv .venv && .venv/bin/pip install -e './cloudro-ble[test]'
.venv/bin/pytest cloudro-ble/tests

# live BLE recon against a real unit (close the phone app first)
.venv/bin/python tools/verify_cloud.py
```

## Status

Working against firmware V1.05. Tank-volume gallons calibration and filter/
remineralizer life are TODO (see PROTOCOL.md open questions).
