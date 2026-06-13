# Cloud RO Water — Home Assistant integration

> **Unofficial.** This is a community project and is not affiliated with, authorized
> by, or endorsed by Cloud Water Filters. "Cloud" and "Cloud RO" refer to the product
> for identification only.

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

## Compatibility

Developed and verified against firmware **V1.05**. The BLE protocol comes from the
Cloud app, which is shared across the product line, so other units running similar
firmware should work without changes — the device address, name, and tank-size
reference are all read at runtime, nothing is tied to one unit.

A different model or firmware revision *could* change the service UUID or the
measurement layout, which would make values read wrong or the device fail to be
discovered. If that happens, please [open an issue](https://github.com/sheastyer/cloudro-ha/issues)
with:

- your firmware version (shown on the device page in Home Assistant), and
- the raw measurement frame.

To capture the raw frame, enable debug logging and reload the integration:

```yaml
# configuration.yaml
logger:
  logs:
    custom_components.cloudro: debug
```

The log will contain a line like `MEASURED_DATA raw: 7800...` — include it in the issue.

## Example dashboard

[`examples/dashboard.yaml`](examples/dashboard.yaml) is a copy-paste starter view —
status tiles, TDS + tank-fill gauges, and a TDS history graph. It uses only built-in
cards (no extra frontend installs). Open a dashboard's **raw configuration editor**,
paste it, and replace the `cloud_ro` entity prefix with your device's prefix (shown
on the device page under Settings → Devices & Services).

## Layout

| Path | What |
|---|---|
| `custom_components/cloudro/` | The Home Assistant integration |
| `cloudro-ble/` | Standalone BLE protocol library (no Home Assistant dependency) |
| `examples/dashboard.yaml` | Starter Lovelace dashboard (built-in cards only) |
| `PROTOCOL.md` | The BLE protocol specification |

## Develop

```bash
python -m venv .venv && .venv/bin/pip install -e './cloudro-ble[test]'
.venv/bin/pytest cloudro-ble/tests
```

## License

MIT
