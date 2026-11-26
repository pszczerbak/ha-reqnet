# Changelog

## 0.3.1 — 2026-11-26

- Validate error and alert codes independently; reject negative, fractional, non-finite, boolean and non-numeric values instead of interpreting them as cleared alarms.
- Track work-sample freshness separately from temperature connectivity, with a 90-second freshness window and the existing 60-second transient-zero hold.
- Ignore retained MQTT work and temperature samples; require valid work data for alarm state and recovery.
- Preserve entity identifiers, command handling and integration configuration.
- Add isolated offline regression tests for invalid codes, stale data, retained messages, recovery events and deduplication.

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
