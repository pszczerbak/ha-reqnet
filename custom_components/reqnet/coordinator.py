# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""REQNET data collection and confirmed MQTT command handling."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import json
import logging
import math
from time import monotonic

import aiohttp
from homeassistant.components import mqtt, persistent_notification
from homeassistant.core import callback
from homeassistant.const import CONF_HOST
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_MAC, DOMAIN, MANUAL_AIRFLOW_VALUES, MANUAL_AIRFLOW_PROFILES

_LOGGER = logging.getLogger(__name__)


class ReqnetCoordinator(DataUpdateCoordinator[dict]):
    """Shared MQTT/REST state, refreshed and distributed to all entities."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name="REQNET",
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.mac = entry.data[CONF_MAC].upper()
        self.serial = self.mac.replace(":", "").lower()
        self.prefix = self.mac + "/"
        self.data = {"work": None, "temperatures": None, "messages": None, "status": None, "settings": None}
        self._mqtt_unsubscribers = []
        self._command_lock = asyncio.Lock()
        self._waiting_for = None
        self._message_counter = 0
        self._last_success = None
        self._last_work_success = None
        self._error_sample_valid = False
        self._alert_sample_valid = False
        self._positive_alert_code = None
        self._last_positive_alert = None
        self._announced_alert = None
        self._positive_error_code = None
        self._last_positive_error = None
        self._announced_error = None
        self.manual_profile = None
        self.airing_duration = 5

    @property
    def connected(self):
        return self._last_success is not None and (monotonic() - self._last_success) < 90


    @staticmethod
    def _validated_code(value):
        """Return a non-negative integral code or None."""
        if type(value) is int:
            return value if value >= 0 else None
        if type(value) is float:
            if math.isfinite(value) and value >= 0 and value.is_integer():
                return int(value)
        return None

    @property
    def work_fresh(self):
        """Only accepted work samples refresh this timestamp."""
        return (
            self._last_work_success is not None
            and monotonic() - self._last_work_success < 90
        )

    @property
    def alert_code(self):
        if not self.work_fresh or not self._alert_sample_valid:
            return None
        work = self.data.get("work")
        if work is None or len(work) <= 41:
            return None
        raw = self._validated_code(work[41])
        if raw is None:
            return None
        if raw > 0:
            return raw
        if self._positive_alert_code is not None and self._last_positive_alert is not None:
            if monotonic() - self._last_positive_alert < 60:
                return self._positive_alert_code
        return 0


    @property
    def error_code(self):
        """Return a validated error code from fresh work data."""
        if not self.work_fresh or not self._error_sample_valid:
            return None
        work = self.data.get("work")
        if work is None or len(work) <= 40:
            return None
        raw = self._validated_code(work[40])
        if raw is None:
            return None
        if raw > 0:
            return raw
        if self._positive_error_code is not None and self._last_positive_error is not None:
            if monotonic() - self._last_positive_error < 60:
                return self._positive_error_code
        return 0

    @property
    def device_info(self):
        status = self.data.get("status") or {}
        return {
            "identifiers": {(DOMAIN, self.serial)},
            "name": "REQNET",
            "manufacturer": "REQNET",
            "model": "Ventilation unit",
            "sw_version": str(status["RecuperatorSoftwareVersion"]) if status.get("RecuperatorSoftwareVersion") is not None else None,
            "connections": {("mac", self.mac)},
        }

    async def _read_rest(self, function):
        url = f"http://{self.host}/API/RunFunction"
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(8):
                async with session.get(url, params={"name": function}) as response:
                    response.raise_for_status()
                    obj = await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise UpdateFailed(f"REQNET REST {function}: {exc}") from exc
        if obj.get(function + "Result") is not True:
            raise UpdateFailed(f"REQNET REST {function} rejected request")
        return obj

    def _update_work(self, payload):
        if not isinstance(payload, dict) or payload.get("CurrentWorkParametersResult") is not True:
            self._error_sample_valid = False
            self._alert_sample_valid = False
            return False
        values = payload.get("Values")
        if not isinstance(values, list) or len(values) < 84:
            self._error_sample_valid = False
            self._alert_sample_valid = False
            return False
        self.data["work"] = values
        self._last_work_success = monotonic()
        self._error_sample_valid = self._validated_code(values[40]) is not None
        self._alert_sample_valid = self._validated_code(values[41]) is not None
        # CurrentWorkParameters is 1-based in the vendor documentation:
        # Python [5]/[6] are the applied manual supply/extract targets.
        # Initialize from the reported manual target only when no
        # requested profile exists. Never overwrite a pending selection.
        supply = self._validated_code(values[5])
        extract = self._validated_code(values[6])
        if (
            self.manual_profile is None
            and values[10] == 8
            and supply == extract
            and supply in MANUAL_AIRFLOW_VALUES
        ):
            self.manual_profile = f"{supply} / {supply}"
        # Error code [40] is distinct from informational message code [41].
        error = self._validated_code(values[40])
        if error is not None and error > 0:
            self._positive_error_code = int(error)
            self._last_positive_error = monotonic()
            if self._announced_error != int(error):
                self._announced_error = int(error)
                persistent_notification.async_create(
                    self.hass,
                    (f"Rekuperator zgłosił błąd o kodzie {int(error)}." if self.hass.config.language.startswith("pl") else f"REQNET reported error code {int(error)}."),
                    title="REQNET — błąd" if self.hass.config.language.startswith("pl") else "REQNET — error",
                    notification_id=f"reqnet_error_{self.serial}",
                )
                self.hass.bus.async_fire("reqnet_error_changed", {
                    "mac": self.mac, "code": int(error),
                })
        elif error == 0 and self._announced_error is not None and self._last_positive_error is not None:
            if monotonic() - self._last_positive_error >= 60:
                self._announced_error = None
                self.hass.bus.async_fire("reqnet_error_changed", {
                    "mac": self.mac, "code": 0,
                })
        code = self._validated_code(values[41])
        if code is not None and code > 0:
            self._positive_alert_code = int(code)
            self._last_positive_alert = monotonic()
            if self._announced_alert != int(code):
                self._announced_alert = int(code)
                description = (
                    ("Wymień filtry w urządzeniu na nowe." if self.hass.config.language.startswith("pl") else "Replace the air filters.")
                    if int(code) == 27 else
                    (f"REQNET zgłosił komunikat o kodzie {int(code)}." if self.hass.config.language.startswith("pl") else f"REQNET reported notification code {int(code)}.")
                )
                persistent_notification.async_create(
                    self.hass, description, title="REQNET — powiadomienie" if self.hass.config.language.startswith("pl") else "REQNET — notification",
                    notification_id=f"reqnet_alert_{self.serial}",
                )
                self.hass.bus.async_fire("reqnet_alert_changed", {
                    "mac": self.mac, "code": int(code), "description": description,
                })
        elif code == 0 and self._announced_alert is not None and self._last_positive_alert is not None:
            if monotonic() - self._last_positive_alert >= 60:
                self._announced_alert = None
                self.hass.bus.async_fire("reqnet_alert_changed", {
                    "mac": self.mac, "code": 0, "description": "No active notification",
                })
        self._last_success = monotonic()
        return True

    def _update_temps(self, payload):
        if not isinstance(payload, dict) or payload.get("GetTemperaturesResult") is False:
            return False
        if not any(k in payload for k in ("IntakeTemp", "Intake")):
            return False
        self.data["temperatures"] = payload
        self._last_success = monotonic()
        return True

    async def _async_update_data(self):
        # REST ensures a fresh state even when the device's MQTT stream pauses.
        try:
            work = await self._read_rest("CurrentWorkParameters")
            if not self._update_work(work):
                raise UpdateFailed("REQNET invalid work parameters array")
        except UpdateFailed:
            if self.data["work"] is None or not self.work_fresh:
                raise
            _LOGGER.warning("REQNET REST poll failed; retaining fresh MQTT state")

        self._message_counter += 1
        if self.data["temperatures"] is None or self._message_counter % 2 == 1:
            try:
                temps = await self._read_rest("GetTemperatures")
                self._update_temps(temps)
            except UpdateFailed as exc:
                _LOGGER.debug("REQNET temperatures polling failed: %s", exc)

        # Advanced settings are read only. They are a distinct zero-based table.
        if self.data["settings"] is None or self._message_counter % 20 == 1:
            try:
                settings = await self._read_rest("GetWorkParameters")
                if isinstance(settings.get("Values"), list) and len(settings["Values"]) >= 44:
                    self.data["settings"] = settings["Values"]
            except UpdateFailed as exc:
                _LOGGER.debug("REQNET advanced settings poll failed: %s", exc)

        if self.data["messages"] is None or self._message_counter % 4 == 1:
            try:
                log = await self._read_rest("GetTheListOfMessages")
                self.data["messages"] = log
            except UpdateFailed as exc:
                _LOGGER.debug("REQNET message log polling failed: %s", exc)

        return self.data.copy()

    async def async_start_mqtt(self):
        topics = (
            "CurrentWorkParametersResult", "CurrentTemperaturesResult",
            "GetTheListOfMessagesResult", "StatusDeviceResult",
            "AutomaticModeResult", "ManualModeResult", "SetByPassModeResult",
            "TurnOnAiringResult", "TurnOffAiringResult", "ReplaceFiltersResult",
        )
        for suffix in topics:
            unsub = await mqtt.async_subscribe(self.hass, self.prefix + suffix, self._on_message, qos=0)
            self._mqtt_unsubscribers.append(unsub)

    async def async_stop_mqtt(self):
        for unsub in self._mqtt_unsubscribers:
            unsub()
        self._mqtt_unsubscribers.clear()

    @callback
    def _on_message(self, message):
        try:
            payload = json.loads(message.payload)
            if not isinstance(payload, dict):
                return
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError):
            return
        suffix = message.topic.removeprefix(self.prefix)
        changed = False
        if suffix == "CurrentWorkParametersResult":
            if message.retain:
                return
            changed = self._update_work(payload)
            if not changed:
                # Publish invalidation without refreshing work freshness.
                changed = True
        elif suffix == "CurrentTemperaturesResult" and payload.get("CurrentTemperaturesResult") is True:
            if message.retain:
                return
            changed = self._update_temps(payload)
        elif suffix == "GetTheListOfMessagesResult" and payload.get("GetTheListOfMessagesResult") is True:
            self.data["messages"] = payload
            changed = True
        elif suffix == "StatusDeviceResult" and payload.get("StatusDeviceResult") is True:
            self.data["status"] = payload
            # Retained MQTT status is metadata, not proof of connectivity.
            changed = True
        else:
            pending = self._waiting_for
            if pending is not None and not message.retain and suffix == pending[0] + "Result":
                future = pending[1]
                if not future.done():
                    future.set_result(payload)
        if changed:
            self.async_set_updated_data(self.data.copy())

    async def async_command(self, name, payload, target):
        """Publish once without retain, wait for application ACK and real REST state."""
        async with self._command_lock:
            fut = self.hass.loop.create_future()
            self._waiting_for = (name, fut)
            try:
                await mqtt.async_publish(
                    self.hass, self.prefix + name, payload, qos=1, retain=False
                )
                result = await asyncio.wait_for(fut, timeout=12)
            except asyncio.TimeoutError as exc:
                raise HomeAssistantError(
                    f"REQNET: no application acknowledgment for {name}; check physical state before retrying"
                ) from exc
            finally:
                self._waiting_for = None
            if result.get(name + "Result") is not True:
                raise HomeAssistantError(f"REQNET rejected {name}: {result.get('Message', '')}")
            for _ in range(12):
                await asyncio.sleep(1)
                try:
                    work = await self._read_rest("CurrentWorkParameters")
                except UpdateFailed:
                    continue
                if self._update_work(work):
                    self.async_set_updated_data(self.data.copy())
                    if target(work["Values"]):
                        return
            raise HomeAssistantError(
                f"REQNET acknowledged {name} but expected state was not confirmed over REST"
            )

    async def async_set_bypass(self, mode):
        # Auto command is 2, but state 3 means Auto with the damper open.
        valid = (2, 3) if mode == 2 else (mode,)
        await self.async_command(
            "SetByPassMode", json.dumps({"mode": mode}), lambda v: v[39] in valid
        )

    async def async_set_automatic(self):
        await self.async_command("AutomaticMode", "", lambda v: v[10] == 9)

    async def async_set_manual(self):
        profile = self.manual_profile
        if type(profile) is not str or profile not in MANUAL_AIRFLOW_PROFILES:
            raise HomeAssistantError(
                "Select a validated manual airflow profile before changing mode"
            )
        val = MANUAL_AIRFLOW_PROFILES[profile]

        # Verify both current and configured airflow limits.
        try:
            work = await self._read_rest("CurrentWorkParameters")
            settings = await self._read_rest("GetWorkParameters")
        except UpdateFailed as exc:
            raise HomeAssistantError(
                "REQNET airflow limits could not be verified"
            ) from exc

        work_values = work.get("Values")
        setting_values = settings.get("Values")

        if (
            not isinstance(work_values, list)
            or len(work_values) < 84
            or not isinstance(setting_values, list)
            or len(setting_values) < 44
        ):
            raise HomeAssistantError("REQNET airflow limits are unavailable")

        limits = (
            self._validated_code(work_values[1]),
            self._validated_code(setting_values[41]),
        )

        if any(limit is None or limit <= 0 for limit in limits):
            raise HomeAssistantError("REQNET airflow limits are invalid")

        if val > min(limits):
            raise HomeAssistantError(
                "Requested airflow exceeds the configured device limit"
            )
        await self.async_command(
            "ManualMode", json.dumps({"airflowvalue": val, "valueofairextraction": val}, separators=(",", ":")),
            lambda v: v[10] == 8 and v[5] == val and v[6] == val
        )

    async def async_start_airing(self):
        await self.async_command(
            "TurnOnAiring", json.dumps({"time": self.airing_duration}, separators=(",", ":")),
            lambda v: v[10] == 4 and v[11] * 60 + v[12] > 0
        )

    async def async_stop_airing(self):
        await self.async_command("TurnOffAiring", "", lambda v: v[10] != 4 and v[11] == 0 and v[12] == 0)

    async def async_reset_filters(self):
        # Deliberately NOT exposed until a safe physical replacement workflow is established.
        raise HomeAssistantError("Filter reset requires a separately reviewed service workflow")
