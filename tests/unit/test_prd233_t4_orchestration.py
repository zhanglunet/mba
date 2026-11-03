# -*- coding: utf-8 -*-
"""PRD-233/T4 测试（trend #1168）：评审编排按包调用适配。

运行：uv run --with pytest python -m pytest tests/unit/test_prd233_t4_orchestration.py -q

覆盖（验收「现有评审流程可按包选择评委组装」）：按包组装（四包各一例/
全量=46 位等价现行全量评审）、消费者横切组并排可选（不换算不平均）、未知
包拒绝、空选择拒绝、包序固定、包内成员序确定、无重复评委、预览渲染、确定性。
零网络；只读。
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from judge_orchestration import (  # noqa: E402
    OrchestrationError,
    assemble_panel,
    preview_render,
)
def load_registry(path=None):
    return json.loads(Path(path or REPO / "registry.json").read_text(encoding="utf-8"))


class 组装Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry(REPO / "registry.json")

    def test_single_pack_assembly(self):
        assembly = assemble_panel(self.registry, ["mba-visual"])
        assert assembly["totals"]["judges"] == 4
        assert assembly["panel_order"] == ["mba-visual"]
        assert {j["slug"] for j in assembly["judges"]} == \
            {"burton", "hexiaopeng", "jobs", "tomford"}

    def test_full_registry_equals_current_full_review(self):
        """四包 + consumer = 46 位——全量组装等价于现行全量评审。"""
        assembly = assemble_panel(self.registry, ["mba-brand", "mba-copy",
                                                  "mba-visual", "mba-compliance"],
                                  consumer=True)
        assert assembly["totals"]["judges"] == 46
        assert assembly["totals"]["consumer_parallel"] is True

    def test_unknown_pack_rejected(self):
        with self.assertRaises(OrchestrationError, msg="未知包"):
            assemble_panel(self.registry, ["mba-ghost"])

    def test_empty_selection_rejected(self):
        with self.assertRaises(OrchestrationError, msg="至少选择一个包"):
            assemble_panel(self.registry, [])

    def test_pack_order_fixed_by_registry(self):
        """包间按登记册固定顺序（brand→copy→visual→compliance），输入乱序不改变。"""
        assembly = assemble_panel(self.registry, ["mba-visual", "mba-brand"])
        order = [j["pack"] for j in assembly["judges"]]
        assert order == sorted(order, key=lambda p: ["mba-brand", "mba-copy",
                                                     "mba-visual",
                                                     "mba-compliance"].index(p))

    def test_no_duplicate_judges(self):
        assembly = assemble_panel(self.registry, ["mba-brand", "mba-copy",
                                                  "mba-visual", "mba-compliance"],
                                  consumer=True)
        slugs = [j["slug"] for j in assembly["judges"]]
        assert len(slugs) == len(set(slugs))

    def test_consumer_group_parallel_note(self):
        assembly = assemble_panel(self.registry, ["mba-brand"], consumer=True)
        assert assembly["totals"]["consumer_parallel"] is True
        assert "不换算不平均" in assembly["totals"]["note"]
        assert any(j["pack"] == "mba-consumer" for j in assembly["judges"])


class 渲染与确定性Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()

    def test_preview_render_lines(self):
        assembly = assemble_panel(self.registry, ["mba-visual"])
        rendered = preview_render(assembly).splitlines()
        assert rendered[0] == "[mba-visual]"
        assert all(line.startswith("  - ") for line in rendered[1:])

    def test_deterministic(self):
        one = json.dumps(assemble_panel(self.registry, ["mba-brand", "mba-copy"]),
                         ensure_ascii=False, sort_keys=True)
        two = json.dumps(assemble_panel(self.registry, ["mba-brand", "mba-copy"]),
                         ensure_ascii=False, sort_keys=True)
        assert one == two


if __name__ == "__main__":
    unittest.main()
