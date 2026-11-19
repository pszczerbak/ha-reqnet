# Security and privacy

This integration communicates locally with your REQNET controller and the MQTT broker already configured in Home Assistant.

## Plaintext broker provisioning

REQNET's documented `ChangeAdditionalBrokerConfiguration` REST endpoint accepts MQTT credentials as HTTP GET query parameters. HTTPS support is not documented. As a result, the password may be exposed to devices with access to the LAN, network captures, reverse proxies, or logs generated outside Home Assistant. **Only use optional provisioning on a trusted network.** An explicit checkbox is required in the setup wizard.

The integration does not store broker username/password in its Home Assistant config entry or options. Device IP and Wi-Fi MAC are stored in the config entry because they are needed to address the device. Users should keep `.storage` private.

## Reporting vulnerabilities

Do not publish secrets, complete request URLs, private IP/MAC addresses, SSIDs, token values or your Home Assistant configuration files in public GitHub issues. Contact the maintainer privately via their GitHub profile if you have a suspected security issue.

## Operational safety

Device state is checked after control commands. The integration never intentionally clears errors, resets filter counters or changes advanced controller settings without a reviewed user action. MQTT command retain flag must remain false.
