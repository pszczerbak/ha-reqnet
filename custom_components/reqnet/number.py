# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""REQNET airing duration as a local command parameter."""
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.restore_state import RestoreEntity
from .entity import ReqnetEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ReqnetAiringDuration(entry.runtime_data)])


class ReqnetAiringDuration(ReqnetEntity, NumberEntity, RestoreEntity):
    _attr_native_min_value = 5
    _attr_native_max_value = 90
    _attr_native_step = 5
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator):
        super().__init__(coordinator, "airing_duration_request", "number")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                requested = int(float(last.state))
                if 5 <= requested <= 90 and requested % 5 == 0:
                    self.coordinator.airing_duration = requested
            except ValueError:
                pass

    @property
    def native_value(self):
        return self.coordinator.airing_duration

    async def async_set_native_value(self, value):
        self.coordinator.airing_duration = int(value)
        self.async_write_ha_state()
