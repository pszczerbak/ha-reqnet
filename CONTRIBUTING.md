# Contributing

Thanks for helping improve this REQNET community integration.

- Open an issue describing the specific REQNET model and Wi-Fi API firmware version, without sharing private IP/MAC/credentials.
- For bugs, provide Home Assistant version, integration version, relevant entity IDs, expected/actual state, and sanitized logs.
- Keep protocol changes grounded in REQNET documentation or on-device tests; do not guess payloads or status meanings.
- Add translations to `strings.json` (English), `translations/en.json`, and `translations/pl.json` together.
- Keep entity IDs stable and do not put IP/MAC addresses or credentials in source defaults, tests, README, or issue examples.
- Prefer local MQTT and REST; do not introduce cloud dependencies without an explicit architectural discussion.
- Do not automatically clear error logs or reset filter counters.
- Do not send MQTT commands with `retain=true`.
- Include a brief note in the changelog when behaviour or mappings change.

Copyright is retained by contributors for their respective contributions. By submitting a contribution, you agree it may be distributed under Apache-2.0 with the project while preserving required attribution notices.
