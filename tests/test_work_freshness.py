"""Offline regression tests for REQNET work sample handling.

Execute the actual coordinator methods with an isolated clock and HA stubs.
No network, broker, credentials or Home Assistant installation is needed.
"""
import ast
import asyncio
from datetime import timedelta
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/reqnet/coordinator.py"


class CoordinatorBase:
    def __init__(self, hass, *args, **kwargs):
        self.hass = hass

    def async_set_updated_data(self, data):
        self.data = data


class WorkFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.clock = 1000.0
        self.events = []
        cls = next(node for node in ast.parse(SOURCE.read_text(encoding="utf-8")).body
                   if isinstance(node, ast.ClassDef) and node.name == "ReqnetCoordinator")
        names = {"__init__", "_validated_code", "work_fresh", "connected", "alert_code",
                 "error_code", "_update_work", "_update_temps", "_on_message"}
        methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)
                   and node.name in names]
        self.assertEqual(names, {node.name for node in methods})
        module = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(
            name="Coordinator", bases=[ast.Name(id="CoordinatorBase", ctx=ast.Load())],
            keywords=[], body=methods, decorator_list=[])], type_ignores=[]))
        env = dict(CoordinatorBase=CoordinatorBase, math=math, json=json, asyncio=asyncio,
                   timedelta=timedelta, _LOGGER=None, CONF_HOST="host", CONF_MAC="mac",
                   monotonic=lambda: self.clock, callback=lambda fn: fn,
                   persistent_notification=SimpleNamespace(async_create=lambda *a, **kw: None))
        exec(compile(SOURCE.with_name("const.py").read_text(encoding="utf-8"), "const.py", "exec"), env)
        exec(compile(module, str(SOURCE), "exec"), env)
        hass = SimpleNamespace(config=SimpleNamespace(language="en"), bus=SimpleNamespace(
            async_fire=lambda name, data: self.events.append((name, dict(data)))))
        entry = SimpleNamespace(data={"host": "example.invalid", "mac": "synthetic"})
        self.c = env["Coordinator"](hass, entry)

    @staticmethod
    def work(error=0, alert=0):
        values = [0] * 84
        values[10] = 9
        values[40:42] = [error, alert]
        return {"CurrentWorkParametersResult": True, "Values": values}

    def message(self, suffix, payload, retain=False):
        self.c._on_message(SimpleNamespace(topic=self.c.prefix + suffix,
                                          payload=json.dumps(payload), retain=retain))

    def recovery_events(self):
        return [name for name, data in self.events if data.get("code") == 0]

    def test_initial_state_and_code_types(self):
        self.assertFalse(self.c.work_fresh)
        self.assertIsNone(self.c.error_code)
        self.assertIsNone(self.c.alert_code)
        for value in (None, True, False, -1, -0.5, 0.5, 27.9, float("nan"),
                      float("inf"), "0", "", [], {}):
            with self.subTest(value=value):
                self.assertIsNone(self.c._validated_code(value))
        for value in (0, 27, 27.0):
            self.assertEqual(self.c._validated_code(value), int(value))

    def test_hold_invalid_samples_and_explicit_recovery(self):
        c = self.c
        c._update_work(self.work(7, 27))
        self.assertEqual((c.error_code, c.alert_code), (7, 27))
        self.clock += 20
        c._update_work(self.work(0, 0))
        self.assertEqual((c.error_code, c.alert_code), (7, 27))
        self.clock += 50
        c._update_work(self.work(None, -1))
        self.assertEqual((c.error_code, c.alert_code), (None, None))
        self.assertEqual(self.recovery_events(), [])
        c._update_work(self.work(0, 27))
        self.assertEqual((c.error_code, c.alert_code), (0, 27))
        self.assertEqual(self.recovery_events(), ["reqnet_error_changed"])
        self.clock += 61
        c._update_work(self.work(0, 0))
        c._update_work(self.work(0, 0))
        self.assertEqual((c.error_code, c.alert_code), (0, 0))
        self.assertEqual(self.recovery_events(), ["reqnet_error_changed", "reqnet_alert_changed"])

    def test_temperature_does_not_refresh_work(self):
        c = self.c
        c._update_work(self.work(7, 27))
        last_work = c._last_work_success
        self.clock += 90
        self.assertTrue(c._update_temps({"Intake": 10}))
        self.assertTrue(c.connected)
        self.assertFalse(c.work_fresh)
        self.assertEqual(c._last_work_success, last_work)
        self.assertEqual((c.error_code, c.alert_code), (None, None))
        self.assertEqual(self.recovery_events(), [])

    def test_retained_samples_are_ignored(self):
        c = self.c
        c._update_work(self.work(7, 27))
        last_work = c._last_work_success
        original_events = list(self.events)
        self.clock += 91
        for payload in (self.work(0, 0), self.work(9, 27)):
            self.message("CurrentWorkParametersResult", payload, retain=True)
        self.message("CurrentTemperaturesResult", {"CurrentTemperaturesResult": True, "Intake": 10}, retain=True)
        self.assertEqual(c._last_work_success, last_work)
        self.assertFalse(c.work_fresh)
        self.assertFalse(c.connected)
        self.assertEqual(self.events, original_events)
        self.assertEqual((c.error_code, c.alert_code), (None, None))
        self.message("CurrentWorkParametersResult", self.work(0, 0))
        self.assertTrue(c.work_fresh)
        self.assertEqual((c.error_code, c.alert_code), (0, 0))
        self.assertEqual(self.recovery_events(), ["reqnet_error_changed", "reqnet_alert_changed"])

    def test_invalid_envelope_and_per_code_validity(self):
        c = self.c
        c._update_work(self.work(0, 0))
        last_work = c._last_work_success
        for payload in ({"CurrentWorkParametersResult": True, "Values": [0] * 10},
                        {**self.work(), "CurrentWorkParametersResult": False}, None):
            self.assertFalse(c._update_work(payload))
            self.assertEqual((c.error_code, c.alert_code), (None, None))
            self.assertEqual(c._last_work_success, last_work)
        c._update_work(self.work(0, None))
        self.assertEqual((c.error_code, c.alert_code), (0, None))
        c._update_work(self.work(None, 27))
        self.assertEqual((c.error_code, c.alert_code), (None, 27))
        self.message("CurrentWorkParametersResult", {**self.work(), "CurrentWorkParametersResult": False})
        self.assertEqual((c.error_code, c.alert_code), (None, None))
        self.assertEqual(self.recovery_events(), [])


if __name__ == "__main__":
    unittest.main()
