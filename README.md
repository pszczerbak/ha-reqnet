# REQNET for Home Assistant

> **📦 [INSTALLATION GUIDE — HACS & manual setup](INSTALLATION.md)**  
> Step-by-step instructions, MQTT broker prerequisites, first-time configuration, upgrades and troubleshooting.  
> **[Open the installation instructions →](INSTALLATION.md)**


[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

A local-first, community-developed Home Assistant integration for compatible **REQNET ventilation/heat recovery units**. It reads data over **MQTT** and the device's **local REST API**, and offers confirmed MQTT control for supported operations. No vendor cloud account is required.

**Author:** Przemysław Szczerbak ([@pszczerbak](https://github.com/pszczerbak))  
**License:** [Apache License 2.0](LICENSE), with required author attribution in [NOTICE](NOTICE).  
**Languages:** English and Polish (the interface follows Home Assistant's language settings).

> **Community project:** Independent, unofficial integration. Test with your own hardware and keep a reliable way to control ventilation if Home Assistant is unavailable.

## Prerequisites

1. Home Assistant with its official **MQTT integration** connected to an MQTT broker (for example, Mosquitto).
2. A supported REQNET device reachable by Home Assistant over your local network (REST API, port 80).
3. The REQNET device must be configured to **publish to the same MQTT broker** that Home Assistant uses. The REQNET firmware calls this the **additional MQTT broker**.
4. The device's Wi-Fi MAC address and its local IP address or hostname.

**Important:** Connecting Home Assistant to a broker does **not** automatically configure the REQNET device to publish there. The integration's setup wizard can configure the additional broker for you, or you can skip that step if it is already configured.

## Installation

**Start here: [Step-by-step installation guide (HACS or manual)](INSTALLATION.md).** It includes the required device-side MQTT broker setup, configuration and upgrade steps.

### HACS (custom repository)

If HACS is installed, add this repository URL as a **custom integration repository** in HACS, install **REQNET**, restart Home Assistant Core, and complete the setup wizard as described below. HACS installation has not yet been validated on all HA versions; manual installation is a supported alternative.

### Manual installation

1. Copy this repository's `custom_components/reqnet` directory to Home Assistant at `/config/custom_components/reqnet`.
2. Restart **Home Assistant Core**.
3. Go to **Settings → Devices & services → Add integration → REQNET**.
4. Provide your device hostname/IP address and Wi-Fi MAC address. No personal IP or MAC values are built into this project.
5. Select one of the broker options below, then complete the setup.

**Upgrading an existing installation:** Replace only the integration's code files, keep the existing config entry and entity registry, and restart Home Assistant Core. Existing entity `unique_id` values are not intentionally changed in this release. Back up the existing integration code before the update; remove the temporary backup after verifying the new version.

### MQTT broker setup choices

**Option A — Broker already configured (default):** Leave **Configure additional MQTT broker on REQNET** unchecked. REQNET must already connect to the MQTT broker configured in HA. The integration will not change the REQNET device's broker configuration.

**Option B — Configure broker on REQNET:** Check the option, then enter:

| Field | Example | Notes |
| --- | --- | --- |
| Broker address | `mqtt.example.test` | Broker reachable *from the REQNET device* (hostname or IPv4) |
| Port | `1883` | Standard unencrypted MQTT port; choose the port of your existing broker |
| Username | `reqnet-client` | Account configured on your broker (if required) |
| Password | *(enter securely in the form)* | Not persisted in the integration config entry |

A separate checkbox explicitly acknowledges the HTTP security limitation below. The device should then publish its usual `MAC_Address/...Result` topics to this broker. HA still needs its own MQTT integration configured.

**Existing installations:** Open **Settings → Devices & services → REQNET → Configure**, choose to provision the broker, and provide the fields above. You can also skip/exit without changing the broker.

**Security warning:** The device's documented `ChangeAdditionalBrokerConfiguration` API uses **plain HTTP GET** with MQTT credentials in the query string. Those credentials can be visible on the LAN and in HTTP/network logs outside Home Assistant. Only use the setup option on a trusted network; prefer configuring the REQNET broker via a secure vendor method if available. The integration does **not** save the broker password in its config entry or options and does not print the request URL, but it cannot make the vendor's plaintext transport secure. Never publish screenshots or logs containing broker passwords.

> Do not submit empty broker address/user/password fields just to “clear” configuration: the vendor documents empty values as a way to **disable** the additional broker connection. The wizard requires a nonempty broker address.

## Features

| Category | Entities/behaviour |
| --- | --- |
| Ventilation | Automatic/manual mode, controlled airing, balanced manual airflow requests (100–550 m³/h in 50 m³/h steps) |
| Bypass | Closed, open and automatic modes; separate **actual damper-open** binary sensor. Vendor readback `2` = automatic/closed, `3` = automatic/open |
| Temperatures | Intake, exhaust, supply and extract |
| Air quality | Humidity and CO₂ |
| Fans | Supply/extract airflow, power, output, duct resistance and diagnostic pressure values |
| Filters | Days remaining, alert (notification code 27), warning lead time and replacement interval readings |
| Messages | Active error code, current notification code, last recorded error and message-log count when provided by the firmware |
| Connectivity | Online-state estimate based on fresh local telemetry/REST, not on retained MQTT status alone |

The integration uses the device's actual state to confirm commands. It sends commands with MQTT `retain=false` and does not assume success solely because a broker acknowledged publication.

### Naming and translations

Entity IDs follow `<domain>.<device>_<function>[_detail]`, for example:

- `select.reqnet_ventilation_mode`
- `select.reqnet_bypass_mode`
- `binary_sensor.reqnet_bypass_open`
- `sensor.reqnet_supply_temperature`
- `sensor.reqnet_filter_days_remaining`

Internal option keys remain in English. Display names and selectable states are translated into **English and Polish** according to the active Home Assistant language. HA may append a suffix when the suggested entity ID is already in use; existing user-edited entity IDs remain under the entity registry's control.

## Known limitations

- Manual airflow requests offer ten balanced profiles from **100 to 550 m³/h**, in 50 m³/h steps, bounded by the device's reported and configured limits. Selecting a profile does not send a device command; Apply or Manual mode sends it and verifies the applied targets via REST. Requested, applied and measured airflow are distinct. The new 250/250 profile was confirmed on a physical unit; all ten were tested offline and as local HA selections. Support may vary by model.
- Airing duration in this integration is offered as a local request parameter (5–90 minutes in 5-minute steps); remaining time comes from the device.
- The filter replacement counter-reset command is **not** exposed yet. Changing advanced controller settings and clearing error history are intentionally not implemented.
- A successful `GetTheListOfMessagesResult` with no `Rows` does **not** prove that the log is empty. Related sensors may report *unknown* instead of misleading zeroes.
- Notification **27** means filter replacement; codes other than those verified are not guessed.
- The 13 `DeviceStatus` fields are not mapped to arbitrary devices solely from numeric values.
- The device provides the separate `CurrentTemperaturesResult` MQTT topic even though official REST documentation names `GetTemperatures`.
- The additional MQTT broker wizard requires a working local REST connection. It does not create an MQTT broker or configure Home Assistant's MQTT integration.

See [protocol notes](docs/PROTOCOL.md) and [troubleshooting](docs/TROUBLESHOOTING.md).

## Support and contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before filing an issue or pull request. Please redact IP addresses, MAC addresses, SSIDs, access tokens and MQTT passwords from logs and screenshots. Do not share a Home Assistant `.storage` directory.

## Attribution and license

Copyright © 2026 **Przemysław Szczerbak (@pszczerbak)**.

Distributed under the **Apache License 2.0**. If you redistribute the source or a modified copy, preserve the license, applicable copyright notices, and attribution in [`NOTICE`](NOTICE) as required by the license. This license permits private use without requiring a visible credit on every dashboard or installation; it does **not** require every individual user to publicly name the author. The project is not an official REQNET product.
