# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""REQNET ventilation and bypass selectors."""
from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.restore_state import RestoreEntity
from .entity import ReqnetEntity
from .const import NUMBER_TO_MODE, NUMBER_TO_BYPASS, BYPASS_TO_NUMBER


async def async_setup_entry(hass, entry, async_add_entities):
    co = entry.runtime_data
    async_add_entities([ReqnetVentilationMode(co), ReqnetBypassMode(co), ReqnetManualProfile(co)])


class ReqnetVentilationMode(ReqnetEntity, SelectEntity):
    _attr_options = ["automatic", "manual", "airing"]

    def __init__(self, coordinator):
        super().__init__(coordinator, "ventilation_mode", "select")

    @property
    def current_option(self):
        values = self.coordinator.data.get("work")
        return NUMBER_TO_MODE.get(values[10]) if values else None

    async def async_select_option(self, option):
        if option == "automatic":
            await self.coordinator.async_set_automatic()
        elif option == "manual":
            await self.coordinator.async_set_manual()
        elif option == "airing":
            await self.coordinator.async_start_airing()
        else:
            raise HomeAssistantError("Unknown ventilation mode")


class ReqnetBypassMode(ReqnetEntity, SelectEntity):
    _attr_options = ["closed", "open", "auto"]

    def __init__(self, coordinator):
        super().__init__(coordinator, "bypass_mode", "select")

    @property
    def current_option(self):
        values = self.coordinator.data.get("work")
        return NUMBER_TO_BYPASS.get(values[39]) if values else None

    async def async_select_option(self, option):
        if option not in BYPASS_TO_NUMBER:
            raise HomeAssistantError("Unknown bypass mode")
        await self.coordinator.async_set_bypass(BYPASS_TO_NUMBER[option])


class ReqnetManualProfile(ReqnetEntity, SelectEntity, RestoreEntity):
    """Only tested balanced profiles; never misrepresent actual airflow target."""
    _attr_options = ["300 / 300", "550 / 550"]

    def __init__(self, coordinator):
        super().__init__(coordinator, "manual_airflow_request", "select")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        if self.coordinator.manual_profile is None and previous is not None and previous.state in self.options:
            self.coordinator.manual_profile = previous.state
            self.async_write_ha_state()

    @property
    def current_option(self):
        return self.coordinator.manual_profile

    async def async_select_option(self, option):
        if option not in self.options:
            raise HomeAssistantError("Unsupported manual airflow profile")
        # Only selects a command preset. Use Apply button or Manual mode to send.
        self.coordinator.manual_profile = option
        self.coordinator.async_set_updated_data(self.coordinator.data.copy())
