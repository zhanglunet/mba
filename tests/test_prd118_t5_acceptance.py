# -*- coding: utf-8 -*-
"""PRD-118/T5 验收试运行（trend #593）：本地 agent 安装调用全部插件。"""
import json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
REPO = Path(__file__).resolve().parents[2]

class AcceptanceTests(unittest.TestCase):
    def test_all_plugins_have_manifest_and_skill(self):
        mapping = json.loads((REPO / "plugins" / "plugin-mapping.json").read_text())
        self.assertGreaterEqual(len(mapping["plugins"]), 4)
        for p in mapping["plugins"]:
            d = REPO / "plugins" / p["plugin_id"]
            self.assertTrue((d / "manifest.json").exists(), f"{p['plugin_id']} 缺 manifest")
            self.assertTrue((d / "SKILL.md").exists(), f"{p['plugin_id']} 缺 SKILL.md")

    def test_plugin_manifests_parseable(self):
        for mf in (REPO / "plugins").glob("*/manifest.json"):
            data = json.loads(mf.read_text())
            self.assertTrue(data.get("name"))
            self.assertTrue(data.get("description"))

if __name__ == "__main__":
    unittest.main()
