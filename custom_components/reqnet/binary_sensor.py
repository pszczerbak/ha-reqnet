# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""REQNET filter alarm and online status."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from .entity import ReqnetEntity


async def async_setup_entry(hass, entry, async_add_entities):
    co = entry.runtime_data
    async_add_entities([ReqnetFilterAlert(co), ReqnetConnectivity(co), ReqnetBypassOpen(co), ReqnetErrorActive(co)])


class ReqnetFilterAlert(ReqnetEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator):
        super().__init__(coordinator, "filter_replacement_required", "binary_sensor")

    @property
    def is_on(self):
        code = self.coordinator.alert_code
        return None if code is None else code == 27


class ReqnetConnectivity(ReqnetEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "connected", "binary_sensor")

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        return self.coordinator.connected


class ReqnetBypassOpen(ReqnetEntity, BinarySensorEntity):
    """Actual damper state independent of manual/automatic control mode."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "bypass_open", "binary_sensor")

    @property
    def is_on(self):
        values = self.coordinator.data.get("work")
        if not values:
            return None
        return values[39] in (1, 3) if values[39] in (0, 1, 2, 3) else None


class ReqnetErrorActive(ReqnetEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "error_active", "binary_sensor")

    @property
    def is_on(self):
        code = self.coordinator.error_code
        return None if code is None else code > 0
