# Changelog

## 0.3.0 — 2026-11-19

- Added optional additional MQTT broker provisioning during initial setup and from integration options, with an explicit unencrypted HTTP warning.
- Added English (`en`) and Polish (`pl`) interface translations, including configuration steps and entity states.
- Removed device-specific IP, MAC, and firmware defaults, making the integration suitable for public redistribution.
- Added project documentation, author attribution and Apache-2.0 licensing.
- Preserved existing entity unique IDs and supported modes from 0.2.0.

## 0.2.0 — 2026-11-19

- Distinguished automatic bypass damper closed (`2`) vs open (`3`) and added damper-open readback.
- Added separate error code, notification code, filter service readings, and additional fan diagnostics.
- Corrected manual airflow targets to use the REQNET device's actual setpoint fields.

## 0.1.0 — 2026-11-19

- Initial local MQTT/REST REQNET integration for Home Assistant.
