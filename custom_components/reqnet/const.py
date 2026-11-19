# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""REQNET protocol identifiers and verified control values."""

DOMAIN = "reqnet"
CONF_MAC = "mac"
CONF_CONFIGURE_BROKER = "configure_broker"
CONF_BROKER_ADDRESS = "broker_address"
CONF_BROKER_PORT = "broker_port"
CONF_BROKER_USER = "broker_user"
CONF_BROKER_PASSWORD = "broker_password"
CONF_INSECURE_HTTP_ACK = "acknowledge_insecure_http"

# Vendor CurrentWorkParameters.Values is documented 1-based.
# These are zero-based Python array indices.
MODE_TO_NUMBER = {"automatic": 9, "manual": 8, "airing": 4}
NUMBER_TO_MODE = {value: key for key, value in MODE_TO_NUMBER.items()}
BYPASS_TO_NUMBER = {"closed": 0, "open": 1, "auto": 2}
NUMBER_TO_BYPASS = {0: "closed", 1: "open", 2: "auto", 3: "auto"}
# 2 = automatic with damper closed; 3 = automatic with damper open.
# SetByPassMode command for automatic is always {"mode":2}.
