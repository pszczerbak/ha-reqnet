# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""REQNET command buttons; filter reset is deliberately not exposed."""
from homeassistant.components.button import ButtonEntity
from .entity import ReqnetEntity


async def async_setup_entry(hass, entry, async_add_entities):
    co = entry.runtime_data
    async_add_entities([
        ReqnetButton(co, "airing_start", "async_start_airing"),
        ReqnetButton(co, "airing_stop", "async_stop_airing"),
        ReqnetButton(co, "apply_manual_airflow", "async_set_manual"),
    ])


class ReqnetButton(ReqnetEntity, ButtonEntity):
    def __init__(self, coordinator, key, action):
        super().__init__(coordinator, key, "button")
        self._action = action

    async def async_press(self):
        await getattr(self.coordinator, self._action)()
