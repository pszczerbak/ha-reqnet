"""Offline checks of packaging, translation parity and privacy invariants."""

import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "reqnet"


def leaf_strings(data, prefix=""):
    if not isinstance(data, dict):
        return {prefix}
    out = set()
    for name, value in data.items():
        out.update(leaf_strings(value, f"{prefix}/{name}"))
    return out


class RepositoryContract(unittest.TestCase):
    def test_manifest_and_version(self):
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("reqnet", manifest["domain"])
        self.assertEqual("0.3.1", manifest["version"])
        self.assertTrue(manifest["config_flow"])
        self.assertIn("mqtt", manifest["dependencies"])
        self.assertIn("@pszczerbak", manifest["codeowners"])

    def test_translation_key_parity(self):
        en = json.loads((COMPONENT / "translations/en.json").read_text(encoding="utf-8"))
        pl = json.loads((COMPONENT / "translations/pl.json").read_text(encoding="utf-8"))
        source = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
        self.assertEqual(source, en)
        self.assertEqual(leaf_strings(en), leaf_strings(pl))
        self.assertIn("options", en)
        self.assertIn("broker", en["config"]["step"])

    def test_no_private_defaults_in_source(self):
        for path in COMPONENT.rglob("*"):
            if path.is_file() and path.suffix in (".py", ".json"):
                content = path.read_text(encoding="utf-8")
                self.assertNotRegex(content, r"(?<!\w)192\.168\.\d{1,3}\.\d{1,3}(?!\w)", str(path))
                self.assertNotRegex(content, r"(?i)(?<![0-9a-f])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![0-9a-f])", str(path))

    def test_protocol_mapping(self):
        spec = importlib.util.spec_from_file_location("reqnet_constants", COMPONENT / "const.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.NUMBER_TO_BYPASS[2], "auto")
        self.assertEqual(module.NUMBER_TO_BYPASS[3], "auto")
        self.assertEqual(module.BYPASS_TO_NUMBER["auto"], 2)
        self.assertEqual(module.NUMBER_TO_MODE[8], "manual")
        self.assertEqual(module.NUMBER_TO_MODE[9], "automatic")

    def test_copyright_headers(self):
        for path in COMPONENT.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Copyright 2026 Przemysław Szczerbak", text.splitlines()[0])
            self.assertIn("SPDX-License-Identifier: Apache-2.0", text.splitlines()[1])


if __name__ == "__main__":
    unittest.main()
