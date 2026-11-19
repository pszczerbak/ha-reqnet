# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""Common REQNET entity identity and naming."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


class ReqnetEntity(CoordinatorEntity):
    """An entity under one REQNET device, with globally consistent IDs."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, key, platform):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = coordinator.device_info
        # For first registration HA treats this as integration-suggested ID.
        # Subsequent user changes are retained by HA's entity registry.
        self.entity_id = f"{platform}.{DOMAIN}_{key}"

    @property
    def available(self):
        return self.coordinator.connected
