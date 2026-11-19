# Copyright 2026 Przemysław Szczerbak (@pszczerbak)
# SPDX-License-Identifier: Apache-2.0

"""REQNET telemetry and diagnostic sensors."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfPower, CONCENTRATION_PARTS_PER_MILLION, PERCENTAGE
from .entity import ReqnetEntity


# key, source, field, device_class, unit, state_class, category
SENSORS = [
    ("intake_temperature", "temperatures", "intake", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, None),
    ("exhaust_temperature", "temperatures", "launcher", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, None),
    ("supply_temperature", "temperatures", "supply", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, None),
    ("extract_temperature", "temperatures", "extract", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, None),
    ("humidity", "temperatures", "humidity", SensorDeviceClass.HUMIDITY, PERCENTAGE, SensorStateClass.MEASUREMENT, None),
    ("co2", "temperatures", "co2", SensorDeviceClass.CO2, CONCENTRATION_PARTS_PER_MILLION, SensorStateClass.MEASUREMENT, None),
    ("manual_supply_airflow_target", "work", 5, None, "m³/h", SensorStateClass.MEASUREMENT, None),
    ("manual_extract_airflow_target", "work", 6, None, "m³/h", SensorStateClass.MEASUREMENT, None),
    ("max_supply_airflow", "work", 1, None, "m³/h", None, EntityCategory.DIAGNOSTIC),
    ("supply_airflow", "work", 3, None, "m³/h", SensorStateClass.MEASUREMENT, None),
    ("extract_airflow", "work", 4, None, "m³/h", SensorStateClass.MEASUREMENT, None),
    ("supply_fan_power", "work", 81, SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT, None),
    ("extract_fan_power", "work", 82, SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT, None),
    ("airing_time_remaining", "work", "airing", None, None, None, None),
    ("filter_days_remaining", "work", 83, None, "d", None, None),
    ("supply_duct_resistance", "work", 63, None, "Pa", SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC),
    ("extract_duct_resistance", "work", 64, None, "Pa", SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC),
    ("supply_fan_output", "work", 65, None, PERCENTAGE, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC),
    ("extract_fan_output", "work", 66, None, PERCENTAGE, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC),
    ("supply_pressure", "work", 75, None, None, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC),
    ("extract_pressure", "work", 76, None, None, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC),
    ("error_code", "error", "code", None, None, None, EntityCategory.DIAGNOSTIC),
    ("filter_warning_days", "settings", 42, None, "d", None, EntityCategory.DIAGNOSTIC),
    ("filter_service_interval_days", "settings", 43, None, "d", None, EntityCategory.DIAGNOSTIC),
    ("alert_code", "alert", "code", None, None, None, EntityCategory.DIAGNOSTIC),
    ("active_alert", "alert", "text", None, None, None, None),
    ("error_count", "messages", "count", None, None, None, EntityCategory.DIAGNOSTIC),
    ("last_error", "messages", "last", None, None, None, EntityCategory.DIAGNOSTIC),
    ("wifi_signal_description", "status", "description", None, None, None, EntityCategory.DIAGNOSTIC),
]


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ReqnetSensor(entry.runtime_data, spec) for spec in SENSORS])


class ReqnetSensor(ReqnetEntity, SensorEntity):
    def __init__(self, coordinator, spec):
        key, self.source, self.field, dc, unit, state_class, category = spec
        super().__init__(coordinator, key, "sensor")
        self._attr_device_class = SensorDeviceClass.ENUM if key == "active_alert" else dc
        if key == "active_alert":
            self._attr_options = ["none", "filter_replacement", "other"]
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_entity_category = category

    @property
    def native_value(self):
        data = self.coordinator.data
        if self.source == "work":
            values = data.get("work")
            if values is None:
                return None
            if self.field == "airing":
                if values[10] != 4:
                    return "00:00"
                return f"{int(values[11]):02d}:{int(values[12]):02d}"
            return values[self.field]
        if self.source == "temperatures":
            values = data.get("temperatures")
            if values is None:
                return None
            aliases = {
                "intake": ("IntakeTemp", "Intake"),
                "launcher": ("LauncherTemp", "Launcher"),
                "supply": ("SupplyTemp", "Supply"),
                "extract": ("ExtractTemp", "Extract"),
                "humidity": ("Humidity",),
                "co2": ("CO2Concentration",),
            }
            for key in aliases[self.field]:
                if key in values:
                    try:
                        return float(values[key])
                    except (ValueError, TypeError):
                        return None
            return None
        if self.source == "settings":
            values = data.get("settings")
            return values[self.field] if values and len(values) > self.field else None
        if self.source == "error":
            return self.coordinator.error_code
        if self.source == "alert":
            code = self.coordinator.alert_code
            if self.field == "code":
                return code
            if code is None:
                return None
            return "none" if code == 0 else "filter_replacement" if code == 27 else "other"
        if self.source == "messages":
            log = data.get("messages")
            # An affirmative result WITHOUT Rows does not prove an empty log.
            if not isinstance(log, dict) or not isinstance(log.get("Rows"), int):
                return None
            if self.field == "count":
                return log["Rows"]
            rows = self._rows(log)
            if not rows:
                return None
            item = rows[0]
            return item[0] if item else None
        if self.source == "status":
            status = data.get("status") or {}
            return status.get("WifiSignalStrengthDescription")
        return None

    @staticmethod
    def _rows(log):
        count = max(0, min(15, log.get("Rows", 0)))
        return [log[str(i)] for i in range(count) if isinstance(log.get(str(i)), list)]

    @property
    def extra_state_attributes(self):
        if self.source == "alert" and self.field == "text":
            return {"code": self.coordinator.alert_code}
        if self.source != "messages" or self.field != "last":
            return None
        log = self.coordinator.data.get("messages")
        if not isinstance(log, dict):
            return None
        return {"entries": self._rows(log)[:15]} if "Rows" in log else None
