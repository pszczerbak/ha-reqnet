"""Offline regression tests for balanced manual requests using actual source methods."""
import ast
import asyncio
from datetime import timedelta
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "reqnet"


class HomeAssistantError(Exception):
    pass


class UpdateFailed(Exception):
    pass


class CoordinatorBase:
    def __init__(self, *args, **kwargs):
        pass

    def async_set_updated_data(self, data):
        self.data = data


class EntityBase:
    def __init__(self, coordinator, *args):
        self.coordinator = coordinator

    async def async_added_to_hass(self):
        pass

    async def async_get_last_state(self):
        return getattr(self, "previous", None)

    def async_write_ha_state(self):
        pass


class SelectBase:
    @property
    def options(self):
        return self._attr_options


class RestoreBase:
    pass


def load_class(filename, name, env, base=None):
    cls = next(n for n in ast.parse((COMPONENT / filename).read_text(encoding="utf-8")).body
               if isinstance(n, ast.ClassDef) and n.name == name)
    if base:
        cls.bases = [ast.Name(id=base, ctx=ast.Load())]
    module = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
    exec(compile(module, filename, "exec"), env)
    return env[name]


class ManualAirflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = dict(CoordinatorBase=CoordinatorBase, ReqnetEntity=EntityBase,
                   SelectEntity=SelectBase, RestoreEntity=RestoreBase,
                   HomeAssistantError=HomeAssistantError, UpdateFailed=UpdateFailed,
                   json=json, math=math, asyncio=asyncio, timedelta=timedelta,
                   _LOGGER=None, monotonic=lambda: 1000.0, callback=lambda f: f,
                   CONF_HOST="host", persistent_notification=SimpleNamespace(
                       async_create=lambda *a, **kw: None))
        exec(compile((COMPONENT / "const.py").read_text(encoding="utf-8"), "const.py", "exec"), env)
        coordinator = load_class("coordinator.py", "ReqnetCoordinator", env, "CoordinatorBase")
        selector = load_class("select.py", "ReqnetManualProfile", env)
        self.events = []
        self.commands = []
        self.limits = {"work": 550, "settings": 550}
        hass = SimpleNamespace(config=SimpleNamespace(language="en"),
                               bus=SimpleNamespace(async_fire=lambda *a: self.events.append(a)))
        self.c = coordinator(hass, SimpleNamespace(data={"host": "example.invalid", "mac": "synthetic"}))
        self.s = selector(self.c)
        self.c._read_rest = self.read_rest
        self.c.async_command = self.command

    @staticmethod
    def work(value=300, limit=550):
        values = [0] * 84
        values[1], values[5], values[6], values[10] = limit, value, value, 8
        return {"CurrentWorkParametersResult": True, "Values": values}

    async def read_rest(self, name):
        if name == "CurrentWorkParameters":
            return self.work(limit=self.limits["work"])
        if name == "GetWorkParameters":
            values = [0] * 44
            values[41] = self.limits["settings"]
            return {"GetWorkParametersResult": True, "Values": values}
        raise AssertionError(name)

    async def command(self, name, payload, target):
        self.commands.append((name, json.loads(payload), target))

    async def test_all_profiles(self):
        self.assertEqual(self.s.options, [f"{v} / {v}" for v in range(100, 551, 50)])
        for value in range(100, 551, 50):
            with self.subTest(value=value):
                option = f"{value} / {value}"
                before = len(self.commands)
                await self.s.async_select_option(option)
                self.assertEqual(len(self.commands), before)
                self.c._update_work(self.work())
                self.assertEqual(self.s.current_option, option)
                await self.c.async_set_manual()
                self.assertEqual(len(self.commands), before + 1)
                name, payload, target = self.commands[-1]
                self.assertEqual(name, "ManualMode")
                self.assertEqual(payload, {"airflowvalue": value, "valueofairextraction": value})
                self.assertTrue(target(self.work(value)["Values"]))
                for index, wrong in ((5, value + 1), (6, value + 1), (10, 9)):
                    sample = self.work(value)["Values"]
                    sample[index] = wrong
                    self.assertFalse(target(sample))
                self.c.manual_profile = None
                self.c._update_work(self.work(value))
                self.assertEqual(self.c.manual_profile, option)
                self.c.manual_profile = None
                self.s.previous = SimpleNamespace(state=option)
                await self.s.async_added_to_hass()
                self.assertEqual(self.s.current_option, option)
        self.assertEqual(self.events, [])

    async def test_invalid_profiles(self):
        for value in (None, True, False, 300, 300.0, [], {}, "50 / 50", "600 / 600",
                      "325 / 325", "100 / 350", "300.0 / 300.0", "invalid"):
            with self.subTest(value=value):
                with self.assertRaises(HomeAssistantError):
                    await self.s.async_select_option(value)
                self.c.manual_profile = value
                with self.assertRaises(HomeAssistantError):
                    await self.c.async_set_manual()
        self.assertEqual(self.commands, [])

    async def test_reported_target_validation(self):
        for value in (None, True, 325, 600, 300.5, "300"):
            with self.subTest(value=value):
                self.c.manual_profile = None
                self.c._update_work(self.work(value))
                self.assertIsNone(self.c.manual_profile)
        sample = self.work()
        sample["Values"][6] = 350
        self.c._update_work(sample)
        self.assertIsNone(self.c.manual_profile)

    async def test_limits_and_rest_failure(self):
        self.c.manual_profile = "550 / 550"
        for field in self.limits:
            for value in (500, None, True, "550", -1, 0, float("nan")):
                with self.subTest(field=field, value=value):
                    self.limits[field] = value
                    with self.assertRaises(HomeAssistantError):
                        await self.c.async_set_manual()
            self.limits[field] = 550

        async def failed_read(name):
            raise UpdateFailed("Synthetic REST failure")

        self.c._read_rest = failed_read
        with self.assertRaises(HomeAssistantError):
            await self.c.async_set_manual()
        self.assertEqual(self.commands, [])
