# Cloud RO Water — Home Assistant integration

Local Home Assistant integration for [Cloud RO](https://www.cloudwaterfilters.com/)
reverse-osmosis water systems. Talks to the unit directly over Bluetooth LE — **no
cloud, no account, no authentication** — and surfaces:

- **TDS at every stage**: inlet (tap), post-RO (after the membrane), remineralized (drinking water)
- **Tank fill %**
- **Total dispensed water** (gallons)
- **Filter & battery status** (good / replace soon / replace)
- **Battery** level and voltage
- **Water-flow** and **problem** indicators, plus tank pressure

## Install (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/sheastyer/cloudro-ha`
   as an *Integration*.
2. Install **Cloud RO Water** and restart Home Assistant.
3. The unit is auto-discovered over Bluetooth — confirm the prompt under
   **Settings → Devices & Services**.

Requires a Bluetooth adapter within range of the unit. On Home Assistant OS this is
the built-in/USB Bluetooth or an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html).

## Layout

| Path | What |
|---|---|
| `custom_components/cloudro/` | The Home Assistant integration |
| `cloudro-ble/` | Standalone BLE protocol library (no Home Assistant dependency) |
| `PROTOCOL.md` | The BLE protocol specification |

## Develop

```bash
python -m venv .venv && .venv/bin/pip install -e './cloudro-ble[test]'
.venv/bin/pytest cloudro-ble/tests
```

## License

MIT
