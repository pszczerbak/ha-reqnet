# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""Setup flow and optional on-device additional MQTT broker provisioning.

Credentials are submitted only once via the vendor's documented local HTTP GET
endpoint, and are NEVER saved in a Home Assistant config entry. The endpoint is
unencrypted; the user must explicitly acknowledge the transport risk.
"""
from __future__ import annotations

import asyncio
import re

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .const import (
    CONF_BROKER_ADDRESS,
    CONF_BROKER_PASSWORD,
    CONF_BROKER_PORT,
    CONF_BROKER_USER,
    CONF_CONFIGURE_BROKER,
    CONF_INSECURE_HTTP_ACK,
    CONF_MAC,
    DOMAIN,
)

MAC_RE = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
HOST_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$")


def _safe_host(host: str) -> bool:
    """Accept local IPv4/DNS names, never a URL, path or injected query."""
    return bool(HOST_RE.fullmatch(host)) and ".." not in host


async def _get_json(hass, host, params):
    """Issue a local vendor GET request; never log sensitive query parameters."""
    session = async_get_clientsession(hass)
    url = f"http://{host}/API/RunFunction"
    try:
        async with asyncio.timeout(10):
            async with session.get(url, params=params, allow_redirects=False) as response:
                # Do not include response.url or exceptions in log output.
                if response.status != 200:
                    raise ConnectionError("REQNET returned an unexpected HTTP status")
                data = await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, OSError) as exc:
        raise ConnectionError("REQNET did not complete the local HTTP request") from None
    if not isinstance(data, dict):
        raise ValueError("Unexpected device response")
    return data


async def _provision_broker(hass, host, user_input):
    """Configure REQNET's additional broker using the documented local API.

    WARNING: the device only documents a plaintext HTTP GET API. Its URL
    includes credentials; this must be used only on a trusted local network.
    """
    params = {
        "name": "ChangeAdditionalBrokerConfiguration",
        "MQTT_ADDITIONAL_BROKER_ADDRESS": user_input[CONF_BROKER_ADDRESS].strip(),
        "MQTT_ADDITIONAL_BROKER_PORT": user_input[CONF_BROKER_PORT],
        "MQTT_ADDITIONAL_BROKER_USER": user_input.get(CONF_BROKER_USER, ""),
        "MQTT_ADDITIONAL_BROKER_PASSWORD": user_input.get(CONF_BROKER_PASSWORD, ""),
    }
    try:
        data = await _get_json(hass, host, params)
    finally:
        # Never save credentials to a config entry, file, or logger.
        params.clear()
    return data.get("ChangeAdditionalBrokerConfigurationResult") is True


def _broker_schema(values=None):
    values = values or {}
    return vol.Schema({
        vol.Required(CONF_BROKER_ADDRESS, default=values.get(CONF_BROKER_ADDRESS, "")): str,
        vol.Required(CONF_BROKER_PORT, default=values.get(CONF_BROKER_PORT, 1883)):
            vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(CONF_BROKER_USER, default=values.get(CONF_BROKER_USER, "")): str,
        vol.Optional(CONF_BROKER_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_INSECURE_HTTP_ACK, default=False): bool,
    })


class ReqnetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a REQNET ventilation unit."""

    VERSION = 1

    def __init__(self):
        self._device = None

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            mac = user_input[CONF_MAC].upper().strip()
            if not _safe_host(host):
                errors[CONF_HOST] = "invalid_host"
            if not MAC_RE.fullmatch(mac):
                errors[CONF_MAC] = "invalid_mac"
            if not errors:
                try:
                    result = await _get_json(self.hass, host, {"name": "CurrentWorkParameters"})
                    if result.get("CurrentWorkParametersResult") is not True or not isinstance(result.get("Values"), list):
                        errors["base"] = "invalid_response"
                except (ConnectionError, ValueError):
                    errors["base"] = "cannot_connect"
                if not errors:
                    await self.async_set_unique_id(mac.replace(":", "").lower())
                    self._abort_if_unique_id_configured()
                    self._device = {CONF_HOST: host, CONF_MAC: mac}
                    if user_input.get(CONF_CONFIGURE_BROKER, False):
                        return await self.async_step_broker()
                    return self.async_create_entry(title="REQNET", data=self._device)

        schema = vol.Schema({
            vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): str,
            vol.Required(CONF_MAC, default=(user_input or {}).get(CONF_MAC, "")): str,
            vol.Required(CONF_CONFIGURE_BROKER, default=(user_input or {}).get(CONF_CONFIGURE_BROKER, False)): bool,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_broker(self, user_input=None):
        errors = {}
        if user_input is not None:
            address = user_input[CONF_BROKER_ADDRESS].strip()
            if not _safe_host(address):
                errors[CONF_BROKER_ADDRESS] = "invalid_host"
            elif not user_input[CONF_INSECURE_HTTP_ACK]:
                errors[CONF_INSECURE_HTTP_ACK] = "http_ack_required"
            else:
                try:
                    if not await _provision_broker(self.hass, self._device[CONF_HOST], user_input):
                        errors["base"] = "broker_rejected"
                except (ConnectionError, ValueError):
                    errors["base"] = "broker_failed"
                if not errors:
                    return self.async_create_entry(title="REQNET", data=self._device)
        return self.async_show_form(step_id="broker", data_schema=_broker_schema(), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return ReqnetOptionsFlow()


class ReqnetOptionsFlow(config_entries.OptionsFlow):
    """Allow optional broker provisioning after an integration is already added."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            if user_input[CONF_CONFIGURE_BROKER]:
                return await self.async_step_broker()
            return self.async_create_entry(title="", data=self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_CONFIGURE_BROKER, default=False): bool}),
        )

    async def async_step_broker(self, user_input=None):
        errors = {}
        if user_input is not None:
            address = user_input[CONF_BROKER_ADDRESS].strip()
            if not _safe_host(address):
                errors[CONF_BROKER_ADDRESS] = "invalid_host"
            elif not user_input[CONF_INSECURE_HTTP_ACK]:
                errors[CONF_INSECURE_HTTP_ACK] = "http_ack_required"
            else:
                try:
                    if not await _provision_broker(self.hass, self.config_entry.data[CONF_HOST], user_input):
                        errors["base"] = "broker_rejected"
                except (ConnectionError, ValueError):
                    errors["base"] = "broker_failed"
                if not errors:
                    # No password (or username) is persisted in options.
                    return self.async_create_entry(title="", data=self.config_entry.options)
        return self.async_show_form(step_id="broker", data_schema=_broker_schema(), errors=errors)
