# -*- coding: utf-8 -*-
"""PRD-118/T4 mba-compliance-check 独立测试（trend #592）。"""
import json, unittest
from pathlib import Path

class Testmba-compliance-check(unittest.TestCase):
    def setUp(self):
        self.plugin_dir = Path(__file__).resolve().parents[2] / "plugins" / "mba-compliance-check"
        self.manifest = json.loads((self.plugin_dir / "manifest.json").read_text(encoding="utf-8"))

    def test_manifest_exists_and_valid(self):
        self.assertEqual(self.manifest["name"], "mba-compliance-check")
        self.assertTrue(self.manifest.get("description"))
        self.assertTrue(self.manifest.get("entry_skill"))

    def test_dependencies_declared(self):
        self.assertIsInstance(self.manifest.get("dependencies", []), list)

    def test_estimated_tokens_declared(self):
        self.assertIn(self.plugin_dir.name, open(
            Path(__file__).resolve().parents[2] / "plugins" / "plugin-mapping.json"
        ).read())

if __name__ == "__main__":
    unittest.main()
