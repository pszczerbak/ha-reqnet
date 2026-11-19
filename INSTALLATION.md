# Installation — REQNET for Home Assistant

[← Back to README](README.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)

This guide covers **HACS installation**, **manual installation**, **initial configuration**, and **updating an existing installation**. REQNET is an unofficial, local-first integration.

> **Release status:** Version 0.3.0 has passed static checks, but its updated broker setup flow has not yet been validated on every supported Home Assistant installation. Keep a working way to control your ventilation unit during testing.

## Requirements

- Home Assistant **2026.11 or newer** (the version declared in this repository's `hacs.json` is 2026.11.0).
- The official **MQTT** integration installed and connected to a working broker (such as Mosquitto).
- A REQNET ventilation unit reachable by Home Assistant over the local network at its hostname or IP address (local REST API, HTTP port 80).
- The REQNET Wi-Fi module's MAC address.
- **REQNET must connect to the same MQTT broker used by Home Assistant.** Its firmware calls this the *additional MQTT broker*. You can configure this on the device using the REQNET wizard, or skip that step if it is already configured.

HACS is optional. No vendor cloud account is required.

## Option A — Install with HACS

1. Open **HACS** in Home Assistant.
2. Open the HACS **⋮ (three-dot) menu → Custom repositories** (the exact menu location may vary between HACS versions).
3. Enter this repository URL: **https://github.com/pszczerbak/ha-reqnet**.
4. Select **Integration** as the repository type and add it.
5. Find **REQNET** in HACS, open it, and select **Download** / **Install**.
6. Restart **Home Assistant Core** after HACS has installed the files.
7. Open **Settings → Devices & services → Add integration**, search for **REQNET**, and proceed with [First-time setup](#first-time-setup).

**Note:** Adding a repository to HACS does not create the REQNET device in Home Assistant. Step 7 is required. HACS installation has not yet been tested across all HACS versions; if this route fails, use the manual method below.

## Option B — Install manually (no HACS)

1. Download the repository as a ZIP using **Code → Download ZIP** on GitHub, or clone it locally.
2. Extract the downloaded archive.
3. Copy the **whole** `custom_components/reqnet` directory into the Home Assistant configuration directory so the resulting paths are:

   ```text
   /config/custom_components/reqnet/__init__.py
   /config/custom_components/reqnet/manifest.json
   /config/custom_components/reqnet/config_flow.py
   /config/custom_components/reqnet/translations/en.json
   /config/custom_components/reqnet/translations/pl.json
   ```

   Create `/config/custom_components/` if necessary. Do **not** copy the entire repository into that folder; copy only the `reqnet` component directory.
4. Restart **Home Assistant Core**.
5. Open **Settings → Devices & services → Add integration**, search for **REQNET**, then proceed with [First-time setup](#first-time-setup).

## First-time setup

1. Make sure **Settings → Devices & services → MQTT** is already set up and connected to your broker. This integration reuses Home Assistant's existing MQTT connection; it does **not** create a new MQTT broker.
2. Add **REQNET** under **Settings → Devices & services → Add integration**.
3. Enter the REQNET device's **local hostname/IP** and **Wi-Fi MAC address**. Use the values from **your own device**; no device-specific values are prefilled.
4. Choose one of the following:
   - **Broker already configured (recommended when MQTT telemetry is already arriving):** leave the additional-broker configuration option unchecked. No change is made to the REQNET broker settings.
   - **Configure additional MQTT broker on REQNET:** select the configuration option and enter a broker hostname/IP reachable **from the REQNET device**, broker port (typically `1883`), username and password, as applicable. Explicitly acknowledge the HTTP security warning in the wizard.
5. Finish setup and open the **REQNET** device in Home Assistant. Confirm that readings update and the bypass/ventilation mode matches the actual device before testing any controls.

### Important: broker configuration security

REQNET documents `ChangeAdditionalBrokerConfiguration` using **unencrypted HTTP GET**, with broker credentials inside URL query parameters. These values can be exposed to anyone observing the local HTTP traffic and may appear in network logs or proxies. Use this option **only on a trusted network**, or configure the broker through a more secure vendor-supported method if one is available. The integration does not persist the supplied broker password in its Home Assistant configuration entry.

**Do not submit empty broker settings in order to “skip” setup.** The vendor documents an all-empty broker configuration as a method to disable the additional MQTT connection. Use the explicit **already configured / skip** option instead.

If Home Assistant connects to MQTT but REQNET telemetry does not arrive, verify the **device-side additional broker** is configured correctly. A connected MQTT integration alone is not sufficient.

## Upgrade an existing installation

1. Keep your current REQNET integration entry and entity registry. **Do not delete and re-add the integration** merely to update its files.
2. Back up only the current `/config/custom_components/reqnet` code folder before replacing it. Keep the backup until the upgrade is verified.
3. Update through HACS if installed through HACS; otherwise replace the contents of `/config/custom_components/reqnet` with the latest repository's `custom_components/reqnet` files.
4. Restart **Home Assistant Core**.
5. Check that the REQNET device loads, readings update, bypass mode is shown correctly, and existing automations still work.
6. After successful verification, remove temporary upgrade backups. Keep any permanent recovery backups.

**Existing MQTT YAML sensors and REST commands are not removed automatically.** If migrating from an older hand-written REQNET configuration, update automations, dashboards and other entity references before removing the legacy configuration. Do not remove the separate, shared Home Assistant MQTT integration.

## Troubleshooting

- **REQNET does not appear in Add integration:** verify `/config/custom_components/reqnet/manifest.json` exists, then restart Core. Check Home Assistant logs for errors loading custom integration `reqnet`.
- **No MQTT data:** confirm the MQTT integration is connected and that REQNET publishes to the **same** broker.
- **Cannot connect to the REQNET device:** confirm the device hostname/IP is reachable from the HA host and the local REST API is available; do not expose port 80 to the public internet.
- **Controls do not update immediately:** REQNET telemetry can lag command acknowledgements by a few seconds. Verify the real device state rather than resending commands blindly.
- **Some diagnostic values show Unknown:** the firmware may omit fields; the integration intentionally does not invent missing data.

For more detail, see [troubleshooting](docs/TROUBLESHOOTING.md) and [protocol notes](docs/PROTOCOL.md).

---

Maintained by **Przemysław Szczerbak ([@pszczerbak](https://github.com/pszczerbak))**. Distributed under [Apache License 2.0](LICENSE); see [NOTICE](NOTICE) for attribution.
