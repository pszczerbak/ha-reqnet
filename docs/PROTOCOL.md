# REQNET protocol notes

These notes document observations and vendor-described fields used in this integration. They are not a substitute for the manufacturer's documentation.

## Network and MQTT

- The REQNET device must be configured with an **additional MQTT broker**, pointing to the same broker already configured under Home Assistant's MQTT integration.
- MQTT topics are prefixed with the REQNET Wi-Fi MAC address, e.g. `<MAC>/CurrentWorkParametersResult`.
- REQNET also exposes local HTTP endpoints such as `http://<DEVICE_HOST>/API/RunFunction?name=CurrentWorkParameters`.
- Control messages must **not** be retained. Broker PUBACK alone does not mean a device executed a command.
- A retained `StatusDeviceResult` is useful as metadata, not proof of current connectivity.

## Device MQTT commands

| Function | Topic suffix | Payload | Expected application response |
| --- | --- | --- | --- |
| Bypass | `SetByPassMode` | `{"mode":0}` closed / `{"mode":1}` open / `{"mode":2}` auto | `SetByPassModeResult` |
| Automatic ventilation | `AutomaticMode` | Empty (zero bytes) | `AutomaticModeResult` |
| Manual ventilation | `ManualMode` | `{"airflowvalue":300,"valueofairextraction":300}` (example) | `ManualModeResult` |
| Start airing | `TurnOnAiring` | `{"time":5}` (example) | `TurnOnAiringResult` |
| Stop airing | `TurnOffAiring` | Empty (zero bytes) | `TurnOffAiringResult` |
| Set additional broker | `ChangeAdditionalBrokerConfiguration` | JSON with broker address, port, username and password | `ChangeAdditionalBrokerConfigurationResult` |

The additional broker command can also be sent through the documented REST API. This integration's setup wizard uses the vendor's REST GET request, after an explicit security acknowledgement.

## CurrentWorkParameters indexing

**Important:** The vendor documentation numbers `CurrentWorkParameters.Values` starting at **1**; Python lists start at **0**. The indices below are Python zero-based indices.

| Python index | Meaning |
| --- | --- |
| `1` | Maximum supply airflow, m³/h |
| `3`, `4` | Measured supply/extract airflow, m³/h |
| `5`, `6` | Manual setpoints, supply/extract, m³/h |
| `7`, `8` | Humidity (%) and CO₂ (ppm) |
| `10` | Operating mode: `8` manual, `9` intelligent/automatic, `4` airing |
| `11`, `12` | Remaining function time, minutes and seconds |
| `39` | Bypass: 0 manual closed, 1 manual open, 2 automatic closed, 3 automatic open |
| `40` | Active error code (zero = none reported) |
| `41` | Current informational/notification code (27 = filter replacement reminder) |
| `55`–`58` | Intake, exhaust, supply, extract temperatures, °C |
| `63`, `64` | Supply/extract duct resistance, Pa |
| `65`, `66` | Supply/extract fan output, percent |
| `75`, `76` | Supply/extract pressure; units not confirmed by provided documentation |
| `81`, `82` | Supply/extract fan power, W |
| `83` | Days until filter replacement |

A reading of `2` or `3` both corresponds to bypass **automatic** control mode; the damper-open sensor reports whether the actual readback corresponds to an open damper (`1` or `3`). A firmware sample occasionally briefly reports `0` for a previously active informational code; debounce is used before clearing a positive notification.

## GetWorkParameters indexing

Unlike the previous array, the vendor **documents this array from 0**. Examples:

| Python index | Meaning |
| --- | --- |
| `0` | CO₂ threshold setting (vendor states 500–900 ppm) |
| `15` | Humidity automation enable flag |
| `16`–`18` | Humidity sensitivity, averaging interval, hysteresis |
| `39` | Anti-condensation mode enable flag |
| `40` | Comfort temperature |
| `41` | Configured maximum airflow |
| `42` | Days before filter replacement to notify |
| `43` | Filter replacement interval in days |

Advanced device settings are intentionally read-only. Some observed firmware values differ from the ranges/descriptions in the generic API documentation; users should verify model-specific behaviour before implementing writes.

## Temperatures

`GetTemperatures` (REST) has named fields `Intake`, `Launcher`, `Supply`, and `Extract` (temperatures on intake, exhaust, supply and extract ducts). Optional `HeaterCooler`, `GWC`, `Room`, and `Additional` sensors have associated active/present flags; a numeric `0.0` alone does not establish physical presence.

The observed MQTT topic `CurrentTemperaturesResult` uses `IntakeTemp`, `LauncherTemp`, `SupplyTemp`, `ExtractTemp`, `Humidity`, and `CO2Concentration`.

## Alerts and the error log

- `Values[40]`: active device error code.
- `Values[41]`: current informational notification code. `27` has been observed for filter replacement reminders.
- `GetTheListOfMessages` supplies up to 15 error-log entries; vendor example `{"GetTheListOfMessagesResult":true,"Bytes":8,"Rows":1,"0":[14,16,7,11,3,20]}` encodes error code, hour, minute, day, month, year.
- Some devices return only `{"GetTheListOfMessagesResult":true}`. This does not prove the log has zero entries.
- `ReplaceFilters` resets the filter counter and must not be called as a passive diagnostic operation.
- `SetFiltersParameters` changes service-reminder parameters and may alter the filter timer; it is not exposed as a writable entity.
