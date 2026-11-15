# -*- coding: utf-8 -*-
"""PRD-465/T3 测试（trend #2247 的 T3 环节）：mba skill 发现层 发现回路闸门。
运行：python3 -m pytest tests/unit/test_prd465_t3_discovery_gate.py -q
覆盖（T1 §6.2–§6.3，T3 issue 正文）：推荐可溯源（matched/reason/
trace 与首位候选一致）/人工复核（接受生效、否决须写原因、只可复核
一次、无候选不可复核）/入账闸门（溯源断裂拒入账、复核记录不一致拒
入账）/否决纠正重推（排除被否决 skill、次位顶上、全部否决则空推）/
全链路跑通/AST 零网络。零网络；全合成占位。T2 模块未动。
"""
import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(MOD_DIR))

from skill_discovery import (  # noqa: E402
    DiscoveryError, load_index, recommend,
)
from skill_discovery_gate import (  # noqa: E402
    ERROR_CODES, GatedDiscoveryLedger, recommend_corrected,
    review_recommendation, verify_trace,
)

# 与 T2 测试同一套合成索引夹具（独立复制，T3 测试自包含）。
REGISTRY = {
    "schema": "judge-pack-registry/v1",
    "packs": [
        {"name": "mba-brand", "skills": [
            {"name": "arnault",
             "triggers": "\"用 Bernard Arnault 视角\", "
                         "\"LVMH / Arnault 会怎么看\"",
             "x-positioning": "品牌组合经营（占位）",
             "x-perspective_ref": "perspectives/arnault-perspective/"},
            {"name": "jobs",
             "triggers": "「用乔布斯视角」「Jobs 会怎么看」",
             "x-positioning": "产品与发布（占位）",
             "x-perspective_ref": "perspectives/jobs-perspective/"},
        ]},
    ],
}

ARNAULT_SKILL = """---
name: arnault-perspective
description: |
  奢侈品品牌组合经营视角：看 Maison 长期价值、desirability。

  Use as: 品牌定位审计评委。

  Explicit triggers: “用 Bernard Arnault 视角”、“奢侈品定位”。
---

# 视角（占位）
"""

JOBS_SKILL = """---
name: jobs-perspective
description: |
  产品发布视角：看产品定义与发布节奏。

  Use as: 产品评审评委。
---

# 视角（占位）
"""

SHOPPER_SKILL = """---
name: first-glance-shopper-perspective
description: |
  模拟消费者人设（合成角色，非真实人物）——货架 3 秒扫描型直觉快判视角。

  Use as: 消费者视角评委。

  Explicit triggers: “用普通消费者视角看”、“第一印象怎么样”、“会不会买”。
---

# 视角（占位）
"""

METRIC_SKILL = """---
name: metric-brand-auditor
description: |
  品牌指标审计：用量化指标盘点品牌资产。

  Explicit triggers: “品牌指标怎么样”、“量化盘点”。
---

# 指标（占位）
"""


def build_root(tmp: Path) -> Path:
    (tmp / "registry.json").write_text(
        json.dumps(REGISTRY, ensure_ascii=False), encoding="utf-8")
    for name, text in (("arnault-perspective", ARNAULT_SKILL),
                       ("jobs-perspective", JOBS_SKILL),
                       ("first-glance-shopper-perspective", SHOPPER_SKILL)):
        d = tmp / "perspectives" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8")
    (tmp / "plugins" / "mba-brand-audit").mkdir(parents=True)
    (tmp / "plugins" / "mba-brand-audit" / "manifest.json").write_text(
        json.dumps({"name": "mba-brand-audit", "version": "0.1.0",
                    "description": "品牌资产盘点与竞争定位审计"},
                   ensure_ascii=False), encoding="utf-8")
    (tmp / "plugins" / "mba-copy-review").mkdir(parents=True)
    (tmp / "plugins" / "mba-copy-review" / "manifest.json").write_text(
        json.dumps({"name": "mba-copy-review", "version": "0.1.0",
                    "description": "文案评审",
                    "keywords": ["文案", "广告语"]},
                   ensure_ascii=False), encoding="utf-8")
    (tmp / "metric-brand-auditor").mkdir(parents=True)
    (tmp / "metric-brand-auditor" / "SKILL.md").write_text(
        METRIC_SKILL, encoding="utf-8")
    return tmp


def index_for(td):
    return load_index(build_root(Path(td)))


def rec_for(td, text, request_id="r-001"):
    return recommend(index_for(td), text, request_id=request_id)


class TestVerifyTrace(unittest.TestCase):
    def test_normal_recommendation_traces(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "用普通消费者视角看，这个品牌第一印象怎么样")
            trace = verify_trace(rec)
            self.assertTrue(trace["ok"], trace["problems"])
            self.assertEqual(trace["problems"], [])
            self.assertEqual(rec["recommendation"]["trace"],
                             rec["candidates"][0]["reason"])

    def test_candidate_without_matched_fails(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            rec["candidates"][0]["matched"] = []
            trace = verify_trace(rec)
            self.assertFalse(trace["ok"])
            self.assertTrue(any("matched" in p for p in trace["problems"]))

    def test_candidate_without_reason_fails(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            rec["candidates"][0]["reason"] = "   "
            trace = verify_trace(rec)
            self.assertFalse(trace["ok"])
            self.assertTrue(any("reason" in p for p in trace["problems"]))

    def test_trace_mismatched_top_candidate_fails(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            rec["recommendation"]["trace"] = "无中生有的理由（占位）"
            trace = verify_trace(rec)
            self.assertFalse(trace["ok"])
            self.assertTrue(any("trace" in p for p in trace["problems"]))

    def test_recommendation_skill_mismatched_top_fails(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            rec["recommendation"]["skill"] = "jobs-perspective"
            trace = verify_trace(rec)
            self.assertFalse(trace["ok"])

    def test_score_out_of_range_fails(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            rec["candidates"][0]["score"] = 1.5
            trace = verify_trace(rec)
            self.assertFalse(trace["ok"])

    def test_empty_recommendation_traces(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "zzzqqq 未知词（占位）")
            self.assertEqual(rec["candidates"], [])
            self.assertTrue(verify_trace(rec)["ok"])


class TestReview(unittest.TestCase):
    def test_accept_marks_effective(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            out = review_recommendation(rec, verdict="accepted",
                                        reviewer="reviewer（占位）",
                                        note="推得对（占位）")
            self.assertEqual(out["review"]["verdict"], "accepted")
            self.assertTrue(out["recommendation"]["effective"])
            self.assertEqual(out["recommendation"]["trace"],
                             rec["recommendation"]["trace"])  # 溯源保留
            self.assertEqual(out["candidates"], rec["candidates"])

    def test_reject_requires_note(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            out = review_recommendation(rec, verdict="rejected",
                                        reviewer="reviewer（占位）",
                                        note="   ")
            self.assertEqual(out["refused"], "DISCOVERY_INVALID_REVIEW")

    def test_reject_requires_reviewer(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            out = review_recommendation(rec, verdict="rejected",
                                        reviewer="  ",
                                        note="推错了（占位）")
            self.assertEqual(out["refused"], "DISCOVERY_INVALID_REVIEW")

    def test_reject_marks_ineffective_keeps_trace(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            out = review_recommendation(rec, verdict="rejected",
                                        reviewer="reviewer（占位）",
                                        note="推错了：要的是指标不是直觉（占位）")
            self.assertEqual(out["review"]["verdict"], "rejected")
            self.assertFalse(out["recommendation"]["effective"])
            self.assertEqual(out["review"]["note"],
                             "推错了：要的是指标不是直觉（占位）")
            self.assertEqual(out["recommendation"]["trace"],
                             rec["recommendation"]["trace"])

    def test_double_review_refused(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            once = review_recommendation(rec, verdict="accepted",
                                         reviewer="reviewer（占位）")
            out = review_recommendation(once, verdict="rejected",
                                        reviewer="reviewer（占位）",
                                        note="改主意（占位）")
            self.assertEqual(out["refused"], "DISCOVERY_INVALID_REVIEW")

    def test_review_empty_recommendation_refused(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "zzzqqq 未知词（占位）")
            out = review_recommendation(rec, verdict="accepted",
                                        reviewer="reviewer（占位）")
            self.assertEqual(out["refused"], "DISCOVERY_INVALID_REVIEW")

    def test_bad_verdict_refused(self):
        with tempfile.TemporaryDirectory() as td:
            rec = rec_for(td, "第一印象怎么样")
            out = review_recommendation(rec, verdict="maybe",
                                        reviewer="reviewer（占位）")
            self.assertEqual(out["refused"], "DISCOVERY_INVALID_REVIEW")


class TestGatedLedger(unittest.TestCase):
    def test_broken_trace_refused_at_record(self):
        with tempfile.TemporaryDirectory() as td:
            led = GatedDiscoveryLedger(None)
            rec = rec_for(td, "第一印象怎么样")
            rec["candidates"][0]["reason"] = ""
            with self.assertRaisesRegex(DiscoveryError,
                                        "DISCOVERY_TRACE_MISMATCH"):
                led.record(rec)
            self.assertEqual(led.entries(), [])

    def test_accepted_without_reviewer_refused(self):
        with tempfile.TemporaryDirectory() as td:
            led = GatedDiscoveryLedger(None)
            rec = rec_for(td, "第一印象怎么样")
            rec = review_recommendation(rec, verdict="accepted",
                                        reviewer="reviewer（占位）")
            rec["review"]["reviewer"] = ""
            with self.assertRaisesRegex(DiscoveryError,
                                        "DISCOVERY_INCOMPLETE"):
                led.record(rec)

    def test_rejected_without_note_refused(self):
        with tempfile.TemporaryDirectory() as td:
            led = GatedDiscoveryLedger(None)
            rec = rec_for(td, "第一印象怎么样")
            rec = review_recommendation(rec, verdict="rejected",
                                        reviewer="reviewer（占位）",
                                        note="推错了（占位）")
            rec["review"]["note"] = ""
            with self.assertRaisesRegex(DiscoveryError,
                                        "DISCOVERY_INCOMPLETE"):
                led.record(rec)

    def test_rejected_still_effective_refused(self):
        with tempfile.TemporaryDirectory() as td:
            led = GatedDiscoveryLedger(None)
            rec = rec_for(td, "第一印象怎么样")
            rec = review_recommendation(rec, verdict="rejected",
                                        reviewer="reviewer（占位）",
                                        note="推错了（占位）")
            rec["recommendation"]["effective"] = True
            with self.assertRaisesRegex(DiscoveryError,
                                        "DISCOVERY_INCOMPLETE"):
                led.record(rec)

    def test_rejected_record_stores_correction(self):
        with tempfile.TemporaryDirectory() as td:
            led = GatedDiscoveryLedger(None)
            rec = rec_for(td, "第一印象怎么样")
            rec = review_recommendation(rec, verdict="rejected",
                                        reviewer="reviewer（占位）",
                                        note="推错了（占位）")
            led.record(rec)
            self.assertEqual(
                led.corrections_for("第一印象怎么样"),
                {"first-glance-shopper-perspective": "推错了（占位）"})


class TestRecommendCorrected(unittest.TestCase):
    def _rejected_ledger(self, index, text):
        led = GatedDiscoveryLedger(None)
        rec = recommend(index, text, request_id="r-001")
        rec = review_recommendation(rec, verdict="rejected",
                                    reviewer="reviewer（占位）",
                                    note="推错了（占位）")
        led.record(rec)
        return led, rec

    def test_rejected_skill_excluded_next_tops(self):
        with tempfile.TemporaryDirectory() as td:
            index = index_for(td)
            text = "用普通消费者视角看，这个品牌第一印象怎么样"
            led, first = self._rejected_ledger(index, text)
            second = recommend_corrected(index, text, led,
                                         request_id="r-002",
                                         supersedes="r-001")
            skills = [c["skill"] for c in second["candidates"]]
            self.assertNotIn("first-glance-shopper-perspective", skills)
            self.assertEqual(second["request"]["supersedes"], "r-001")
            self.assertTrue(verify_trace(second)["ok"])
            if second["candidates"]:
                self.assertEqual(second["recommendation"]["skill"],
                                 second["candidates"][0]["skill"])

    def test_no_correction_same_as_t2(self):
        with tempfile.TemporaryDirectory() as td:
            index = index_for(td)
            led = GatedDiscoveryLedger(None)
            text = "第一印象怎么样"
            out = recommend_corrected(index, text, led, request_id="r-009")
            plain = recommend(index, text, request_id="r-009")
            self.assertEqual(out, plain)

    def test_all_candidates_rejected_empty(self):
        with tempfile.TemporaryDirectory() as td:
            index = index_for(td)
            text = "品牌指标怎么样"
            led = GatedDiscoveryLedger(None)
            # 逐个否决全部候选：每轮重推、否决当轮首位
            rid = 1
            for _ in range(5):
                cur = recommend_corrected(index, text, led,
                                          request_id=f"r-{rid:03d}",
                                          supersedes=f"r-{rid-1:03d}")
                if not cur["candidates"]:
                    break
                reviewed = review_recommendation(
                    cur, verdict="rejected", reviewer="reviewer（占位）",
                    note="推错了（占位）")
                led.record(reviewed)
                rid += 1
            final = recommend_corrected(index, text, led,
                                        request_id="r-final")
            self.assertEqual(final["candidates"], [])
            self.assertIsNone(final["recommendation"])
            self.assertTrue(verify_trace(final)["ok"])

    def test_full_loop_reject_then_accept(self):
        with tempfile.TemporaryDirectory() as td:
            index = index_for(td)
            text = "用普通消费者视角看，这个品牌第一印象怎么样"
            led = GatedDiscoveryLedger(None)
            first = recommend(index, text, request_id="r-001")
            led.record(first)
            rejected = review_recommendation(
                first, verdict="rejected", reviewer="reviewer（占位）",
                note="推错了（占位）")
            led.record(rejected)
            second = recommend_corrected(index, text, led,
                                         request_id="r-002",
                                         supersedes="r-001")
            accepted = review_recommendation(
                second, verdict="accepted", reviewer="reviewer（占位）",
                note="这次对了（占位）")
            led.record(accepted)
            self.assertEqual(len(led.entries()), 3)
            self.assertTrue(accepted["recommendation"]["effective"])
            self.assertNotEqual(
                first["recommendation"]["skill"],
                accepted["recommendation"]["skill"])


class TestRedline(unittest.TestCase):
    def test_ast_zero_network_zero_subprocess(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        src = MOD_DIR / "skill_discovery_gate.py"
        tree = ast.parse(Path(src).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & banned, imported & banned)

    def test_vocabs_closed(self):
        self.assertIn("DISCOVERY_TRACE_MISMATCH", set(ERROR_CODES))
        self.assertIn("DISCOVERY_INVALID_REVIEW", set(ERROR_CODES))


if __name__ == "__main__":
    unittest.main()
