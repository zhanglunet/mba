# -*- coding: utf-8 -*-
"""PRD-233/T5 测试：验收试运行——按登记册独立组装一次完整评审（trend #1169）。

运行：.venv/bin/python -m pytest tests/unit/test_prd233_t5_assembly.py -q

验收标准（trend #1169）：**试运行通过，组装路径无死角**。

以真实登记册（registry.json 4 专家包 43 评委 + 消费者横切组 3 位）把组装
路径全部走一遍（无死角）：
  ① 全量组装（4 包）=43 位，等价现行全量评审；② 单包组装×4（每包独立
  可用）；③ 子集组装（brand+copy 仅并集成员）；④ 消费者横切组并排
  （consumer=True 附加 3 位，信号分开呈现不换算不平均）；⑤ 仅消费者组
  （packs=[]+consumer）；⑥ 拒绝路径（未知包/空选择）；⑦ preview 渲染
  全量名单无遗漏；⑧ 同配置重装确定性（发言序不变）。
零网络；全合成占位。
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from judge_orchestration import (  # noqa: E402
    OrchestrationError,
    assemble_panel,
    load_registry,
    preview_render,
)

REGISTRY = load_registry(Path(REPO) / "registry.json")
ALL_PACKS = [p["name"] for p in REGISTRY["packs"]]
CROSSCUT = [s["name"] for s in (REGISTRY.get("x-crosscut") or {}).get("skills", [])]


def registry_count(pack_name):
    for pack in REGISTRY["packs"]:
        if pack["name"] == pack_name:
            return len(pack["skills"])
    return 0


class 组装路径Tests(unittest.TestCase):
    def test_full_assembly_equals_all_packs(self):
        """① 全量组装：4 包全员 43 位（等价现行全量评审，无死角基线）。"""
        assembly = assemble_panel(REGISTRY, ALL_PACKS)
        self.assertEqual(assembly["totals"]["judges"], 43)
        self.assertEqual(assembly["totals"]["packs"], 4)
        self.assertEqual(assembly["panel_order"], ALL_PACKS)
        self.assertFalse(assembly["totals"]["consumer_parallel"])

    def test_each_pack_assembles_alone(self):
        """② 单包组装×4：每包独立可用，人数与登记册逐包一致。"""
        for pack_name in ALL_PACKS:
            assembly = assemble_panel(REGISTRY, [pack_name])
            self.assertEqual(assembly["totals"]["judges"], registry_count(pack_name),
                             pack_name)
            self.assertEqual({j["pack"] for j in assembly["judges"]}, {pack_name})

    def test_subset_assembly_is_exact_union(self):
        """③ 子集组装：brand+copy 仅并集成员，其余包零混入。"""
        assembly = assemble_panel(REGISTRY, ["mba-brand", "mba-copy"])
        self.assertEqual(assembly["totals"]["judges"],
                         registry_count("mba-brand") + registry_count("mba-copy"))
        self.assertEqual({j["pack"] for j in assembly["judges"]},
                         {"mba-brand", "mba-copy"})

    def test_consumer_crosscut_parallel(self):
        """④ 消费者横切组并排：附加 3 位、信号分开呈现（不换算不平均）。"""
        assembly = assemble_panel(REGISTRY, ALL_PACKS, consumer=True)
        self.assertEqual(assembly["totals"]["judges"], 43 + len(CROSSCUT))
        consumer_judges = [j for j in assembly["judges"]
                           if j["pack"] == "mba-consumer"]
        self.assertEqual({j["slug"] for j in consumer_judges}, set(CROSSCUT))
        self.assertTrue(assembly["totals"]["consumer_parallel"])
        self.assertIn("不换算不平均", assembly["totals"]["note"])

    def test_consumer_only_assembly(self):
        """⑤ 仅消费者组：packs=[]+consumer=True → 横切组 3 位独立成团。"""
        assembly = assemble_panel(REGISTRY, [], consumer=True)
        self.assertEqual(assembly["totals"]["judges"], len(CROSSCUT))
        self.assertEqual(assembly["panel_order"], ["mba-consumer"])

    def test_rejected_paths(self):
        """⑥ 拒绝路径：未知包、空选择均拒绝（组装不静默糊弄）。"""
        with self.assertRaises(OrchestrationError):
            assemble_panel(REGISTRY, ["mba-not-exist"])
        with self.assertRaises(OrchestrationError):
            assemble_panel(REGISTRY, [])

    def test_preview_renders_every_judge(self):
        """⑦ preview 渲染：全量名单逐位在渲染文本中出现（无遗漏）。"""
        assembly = assemble_panel(REGISTRY, ALL_PACKS, consumer=True)
        rendered = preview_render(assembly)
        for judge in assembly["judges"]:
            self.assertIn(judge["slug"], rendered, judge)

    def test_deterministic_panel_order(self):
        """⑧ 确定性：同配置两次组装发言序逐位一致。"""
        first = assemble_panel(REGISTRY, ALL_PACKS, consumer=True)
        second = assemble_panel(REGISTRY, ALL_PACKS, consumer=True)
        self.assertEqual(first["judges"], second["judges"])
        self.assertEqual(first["panel_order"], second["panel_order"])


if __name__ == "__main__":
    unittest.main()
