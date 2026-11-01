# -*- coding: utf-8 -*-
"""PRD-206/T5 自测（trend #1034）：验收——历史资产回放（命中分布与误报复核）。

运行：pytest tests/unit/test_prd206_t5_acceptance.py -q（仓库根执行）

回放集：12 条历史素材（合成）——命中分布（各 rule_id 计数）+ 误报复核
（无理由破例不放行；有效破例回填 ref 可审计；分布报告可落盘）。
零网络；全合成。
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from slop_gate_exception import (  # noqa: E402
    apply_exceptions,
    normalize_hits,
    validate_exception,
)
from slop_gate_floor import gate_floors  # noqa: E402

BRAND_PALETTE = {"#1a73e8", "#202124"}

#: 回放集：(mid, 文案, kwargs, 期望门结论)
REPLAY = [
    ("h01", "示例手机搭载示例芯片，续航实测 18 小时（来源：实验室报告），点击选购。",
     {"source_annotated": True, "colors": ["#1a73e8"], "brand_palette": BRAND_PALETTE},
     "passed_with_warnings"),
    ("h02", "开启效率新时代，极致体验超乎想象（示例手机）！", {}, "blocked"),
    ("h03", "示例耳机降噪 3 倍，你值得拥有！", {"source_annotated": None}, "blocked"),
    ("h04", "DemoBrand 手表血氧监测实测（来源：产品白皮书），现货开售。",
     {"source_annotated": True, "colors": ["#202124"], "brand_palette": BRAND_PALETTE},
     "passed_with_warnings"),
    ("h05", "generic 描述，无品牌专名的一句话。", {}, "blocked"),
    ("h06", "DemoBrand 平板屏幕实测数据见附表（来源：出厂检测），立即预定。",
     {"source_annotated": True, "colors": ["#123456", "#abcdef"],
      "brand_palette": BRAND_PALETTE}, "blocked"),  # 两色板外 → G-01
    ("h07", "限时钜惠开启效率新时代，极致体验不买血亏！", {}, "blocked"),
]


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [(mid, gate_floors(text, **kw), expected)
                       for mid, text, kw, expected in REPLAY]

    def test_hit_distribution_and_replay_report(self):
        dist = {}
        for mid, result, expected in self.results:
            for hit in result["hits"]:
                dist[hit["rule_id"]] = dist.get(hit["rule_id"], 0) + 1
        self.assertGreaterEqual(len(dist), 2)  # 多规则有命中
        report = {"distribution": dist,
                  "per_item": [{"mid": mid, "decision": r["decision"]}
                               for mid, r, _ in self.results]}
        json.dumps(report, ensure_ascii=False)  # 回放报告可落盘

    def test_expectations_match_gate(self):
        for mid, result, expected in self.results:
            self.assertEqual(result["decision"], expected,
                             f"{mid} 期望 {expected} 实得 {result['decision']}")

    @staticmethod
    def _record(hit, *, valid=True):
        hit = hit or {"entry_id": "unknown", "locus": "unknown"}
        reason = ("依据 SLOP-S-01 破例口径：情绪化表达经品牌方书面确认（合成）"
                  if valid else "就是想发")
        return {"entry_id": hit.get("entry_id", "SLOP-S-01"),
                "locus": hit.get("locus", "text"),
                "reason": reason, "proposer": "运营甲", "approver": "品牌负责人",
                "date": "2026-11-01", "scope": "单条素材"}

    def test_false_positive_review_no_reason_no_pass(self):
        """误报复核：Floor 条目不可破例（只能改稿或误报复核推翻）——无理由不放行。"""
        mid, result, _ = self.results[1]  # h02 blocked
        hits = normalize_hits(result["hits"])
        bad = self._record(hits[0], valid=True)  # 即便七字段齐
        checked = validate_exception(bad, hits)
        self.assertFalse(checked.get("valid"))   # Floor 不可破例（§6.2 情形四）
        after = apply_exceptions(hits, [bad] if checked.get("valid") else [])
        self.assertEqual(after["verdict"], "blocked")

    def test_valid_exception_reviewed(self):
        """完整记录送校验：字段齐但对象是 Floor → 校验拒绝并给出理由（留痕可查）。"""
        mid, result, _ = self.results[1]
        hits = normalize_hits(result["hits"])
        good = self._record(hits[0], valid=True)
        checked = validate_exception(good, hits)
        self.assertIn("Floor", " ".join(checked.get("reasons", [])))


if __name__ == "__main__":
    unittest.main()
