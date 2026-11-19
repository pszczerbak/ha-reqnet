# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""Local-first REQNET integration using HA's existing MQTT connection."""
from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import ReqnetCoordinator

PLATFORMS = (
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Load config entry."""
    if not await mqtt.async_wait_for_mqtt_client(hass):
        raise ConfigEntryNotReady("MQTT client unavailable")
    coordinator = ReqnetCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_start_mqtt()
    entry.runtime_data = coordinator
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await coordinator.async_stop_mqtt()
        raise


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unload entities before dropping subscriptions."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
    await entry.runtime_data.async_stop_mqtt()
