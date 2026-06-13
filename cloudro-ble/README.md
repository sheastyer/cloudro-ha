# cloudro-ble

Bluetooth LE protocol library for [Cloud RO](https://www.cloudwaterfilters.com/)
water filtration systems. Reads live metrics (TDS at each filtration stage, tank
volume, battery, dispensed water, status flags) directly over BLE — **local, no
cloud, no authentication required**.

This library powers the Home Assistant `cloudro` integration but has no Home
Assistant dependency.

## Status

Reverse-engineered from the Cloud Water Filters app v1.6.0 and verified against a
real unit (firmware V1.05). See [`../PROTOCOL.md`](../PROTOCOL.md) for the full spec.

## Usage

```python
from bleak import BleakScanner
from cloudro_ble import CloudRODevice, is_cloud_ro

device = await BleakScanner.find_device_by_filter(
    lambda d, adv: is_cloud_ro(adv.service_uuids)
)
state = await CloudRODevice(device).update()
print(state.measured.inlet_tds, state.measured.tank_fill_percent)
```

## Develop

```bash
pip install -e '.[test]'
pytest
```
