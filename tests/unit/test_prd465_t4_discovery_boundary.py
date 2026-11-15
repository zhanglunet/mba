# -*- coding: utf-8 -*-
"""PRD-465/T4 测试（trend #2248 的 T4 环节）：mba skill 发现层 划界断言。
运行：python3 -m pytest tests/unit/test_prd465_t4_discovery_boundary.py -q
覆盖（T1 §3–§4 + R1/R2，T4 issue 正文）：发现层不碰评审流程与分数、
不绕过 skill 自己的标准安装链路：越界字段显形拒绝 / 入账划界拒洗账 /
推荐输出形态断言 / 索引源只读（全流程前后源文件一字不差）/ 纠正重推
全程在界内 / AST 零网络。零网络；全合成占位。T2/T3 模块未动。
"""
import ast
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
    GatedDiscoveryLedger, recommend_corrected, review_recommendation,
)
from skill_discovery_boundary import (  # noqa: E402
    ERROR_CODES, BoundaryDiscoveryLedger, assert_no_install,
    assert_no_review_writes, recommendation_shape_check, scope_check,
    snapshot_sources, sources_unchanged,
)

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
    (tmp / "perspectives" / "arnault-perspective").mkdir(parents=True)
    (tmp / "perspectives" / "arnault-perspective" / "SKILL.md").write_text(
        ARNAULT_SKILL, encoding="utf-8")
    (tmp / "perspectives" / "jobs-perspective").mkdir(parents=True)
    (tmp / "perspectives" / "jobs-perspective" / "SKILL.md").write_text(
        JOBS_SKILL, encoding="utf-8")
    (tmp / "perspectives" / "first-glance-shopper-perspective").mkdir(
        parents=True)
    (tmp / "perspectives" / "first-glance-shopper-perspective"
     / "SKILL.md").write_text(SHOPPER_SKILL, encoding="utf-8")
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
    (tmp / ".claude-plugin").mkdir(parents=True)
    (tmp / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "bogus-marketplace-only-skill"}]},
                   ensure_ascii=False), encoding="utf-8")
    return tmp


def fresh_rec(td, text="第一印象怎么样", request_id="r-001"):
    index = load_index(build_root(Path(td)))
    return index, recommend(index, text, request_id=request_id)


class TestScopeCheckClean(unittest.TestCase):
    def test_recommend_output_in_scope(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            scope = scope_check(rec)
            self.assertTrue(scope["in_scope"])
            self.assertEqual(scope["violations"], [])

    def test_reviewed_records_in_scope(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            accepted = review_recommendation(
                rec, verdict="accepted", reviewer="reviewer（占位）")
            self.assertTrue(scope_check(accepted)["in_scope"])
        with tempfile.TemporaryDirectory() as td:
            _, rec2 = fresh_rec(td, request_id="r-002")
            rejected = review_recommendation(
                rec2, verdict="rejected", reviewer="reviewer（占位）",
                note="推错可纠（占位）")
            self.assertTrue(scope_check(rejected)["in_scope"])

    def test_own_fields_not_flagged(self):
        # 发现层自有字段含 score/review 字样，不得误伤：候选 score 是发现
        # 置信分，review.verdict 是发现复核结论，均在界内。
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            self.assertTrue(scope_check(rec)["in_scope"])
            self.assertTrue(0 <= rec["candidates"][0]["score"] <= 1)
            self.assertEqual(rec["review"]["verdict"], "pending")


class TestBoundaryR1Review(unittest.TestCase):
    def test_findings_field_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            rec["findings"] = [{"note": "评审发现（占位）"}]
            violations = assert_no_review_writes(rec)
            self.assertEqual(len(violations), 1)
            self.assertIn("R1", violations[0])

    def test_each_r1_field_flagged(self):
        for field in ("findings", "review_score", "audit_score",
                      "judge_score", "judge_verdict", "verdict_score",
                      "rating", "scorecard", "brand_audit_report",
                      "review_report"):
            with tempfile.TemporaryDirectory() as td:
                _, rec = fresh_rec(td)
                rec["review"] = dict(rec["review"], **{field: "占位"})
                self.assertTrue(assert_no_review_writes(rec), field)
                self.assertFalse(assert_no_install(rec), field)

    def test_nested_r1_field_in_recommendation_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            rec["recommendation"] = dict(rec["recommendation"],
                                         review_score=0.9)
            self.assertTrue(assert_no_review_writes(rec))

    def test_extra_top_level_key_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            rec["audit_report"] = "占位"
            scope = scope_check(rec)
            self.assertFalse(scope["in_scope"])
            self.assertTrue(any("顶层字段" in v for v in scope["violations"]))


class TestBoundaryR2Install(unittest.TestCase):
    def test_install_field_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            rec["recommendation"] = dict(rec["recommendation"],
                                         install_path="/tmp/x")
            violations = assert_no_install(rec)
            self.assertEqual(len(violations), 1)
            self.assertIn("R2", violations[0])

    def test_each_r2_field_flagged(self):
        for field in ("install", "installed", "install_path",
                      "install_command", "install_action", "install_status",
                      "installed_version", "registry_write",
                      "marketplace_write"):
            with tempfile.TemporaryDirectory() as td:
                _, rec = fresh_rec(td)
                rec[field] = "占位"
                self.assertTrue(assert_no_install(rec), field)
                self.assertFalse(assert_no_review_writes(rec), field)

    def test_registry_write_in_request_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            rec["request"] = dict(rec["request"], registry_write=True)
            self.assertTrue(assert_no_install(rec))


class TestBoundaryLedger(unittest.TestCase):
    def test_out_of_scope_record_refused(self):
        led = BoundaryDiscoveryLedger(None)
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            rec["findings"] = [{"note": "评审发现（占位）"}]
            with self.assertRaisesRegex(DiscoveryError,
                                        "DISCOVERY_OUT_OF_SCOPE"):
                led.record(rec)
            self.assertEqual(led.entries(), [])
            self.assertEqual(led.corrections_for("第一印象怎么样"), {})

    def test_both_domains_refused_at_ledger(self):
        for field in ("review_score", "install_path"):
            led = BoundaryDiscoveryLedger(None)
            with tempfile.TemporaryDirectory() as td:
                _, rec = fresh_rec(td)
                rec[field] = "占位"
                with self.assertRaisesRegex(DiscoveryError,
                                            "DISCOVERY_OUT_OF_SCOPE"):
                    led.record(rec)
                self.assertEqual(led.entries(), [])

    def test_clean_records_pass_through_with_corrections(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "boundary" / "log.jsonl"
            led = BoundaryDiscoveryLedger(path)
            _, rec = fresh_rec(td)
            led.record(rec)
            rejected = review_recommendation(
                rec, verdict="rejected", reviewer="reviewer（占位）",
                note="推错可纠（占位）")
            led.record(rejected)
            self.assertEqual(len(led.entries()), 2)
            self.assertEqual(
                led.excluded_for("第一印象怎么样"),
                ["first-glance-shopper-perspective"])
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)


class TestRecommendationShape(unittest.TestCase):
    def test_recommend_output_shape_ok(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            check = recommendation_shape_check(rec)
            self.assertTrue(check["ok"])
            self.assertEqual(check["violations"], [])
            self.assertEqual(set(rec.keys()),
                             {"schema", "request", "candidates",
                              "recommendation", "review"})
            self.assertEqual(set(rec["candidates"][0].keys()),
                             {"skill", "score", "matched", "reason"})
            self.assertEqual(set(rec["recommendation"].keys()),
                             {"skill", "trace"})

    def test_extra_candidate_key_fails_shape(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            rec["candidates"][0]["install_command"] = "占位"
            self.assertFalse(recommendation_shape_check(rec)["ok"])

    def test_extra_top_level_key_fails_shape(self):
        with tempfile.TemporaryDirectory() as td:
            _, rec = fresh_rec(td)
            rec["scorecard"] = {}
            self.assertFalse(recommendation_shape_check(rec)["ok"])


class TestIndexReadOnly(unittest.TestCase):
    def test_full_flow_leaves_sources_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            root = build_root(Path(td))
            before = snapshot_sources(root)
            self.assertGreater(len(before), 0)
            index = load_index(root)
            rec = recommend(index, "第一印象怎么样", request_id="r-001")
            led = BoundaryDiscoveryLedger(None)
            led.record(rec)
            reviewed = review_recommendation(
                rec, verdict="rejected", reviewer="reviewer（占位）",
                note="推错可纠（占位）")
            led.record(reviewed)
            corrected = recommend_corrected(index, "第一印象怎么样", led,
                                            request_id="r-002",
                                            supersedes="r-001")
            led.record(corrected)
            self.assertTrue(scope_check(corrected)["in_scope"])
            after = sources_unchanged(root, before)
            self.assertTrue(after["unchanged"])
            self.assertEqual(after["changed"], [])

    def test_tampered_source_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = build_root(Path(td))
            before = snapshot_sources(root)
            (root / "registry.json").write_text(
                json.dumps({"schema": "judge-pack-registry/v1",
                            "packs": []}, ensure_ascii=False),
                encoding="utf-8")
            after = sources_unchanged(root, before)
            self.assertFalse(after["unchanged"])
            self.assertEqual(after["changed"], ["registry.json"])

    def test_corrected_recommendation_stays_in_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = build_root(Path(td))
            index = load_index(root)
            led = GatedDiscoveryLedger(None)
            rec = recommend(index, "第一印象怎么样", request_id="r-001")
            led.record(review_recommendation(
                rec, verdict="rejected", reviewer="reviewer（占位）",
                note="推错可纠（占位）"))
            corrected = recommend_corrected(index, "第一印象怎么样", led,
                                            request_id="r-002",
                                            supersedes="r-001")
            self.assertTrue(scope_check(corrected)["in_scope"])
            self.assertEqual(corrected["request"]["supersedes"], "r-001")
            self.assertNotEqual(
                corrected["recommendation"]["skill"],
                "first-glance-shopper-perspective")


class TestRedline(unittest.TestCase):
    def test_ast_zero_network_zero_subprocess(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        src = MOD_DIR / "skill_discovery_boundary.py"
        tree = ast.parse(Path(src).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & banned, imported & banned)

    def test_vocabs_closed(self):
        self.assertIn("DISCOVERY_OUT_OF_SCOPE", set(ERROR_CODES))
        self.assertEqual(set(ERROR_CODES),
                         {"DISCOVERY_INCOMPLETE",
                          "DISCOVERY_SCORE_MISMATCH",
                          "DISCOVERY_TRACE_MISMATCH",
                          "DISCOVERY_INVALID_REVIEW",
                          "DISCOVERY_OUT_OF_SCOPE"})


if __name__ == "__main__":
    unittest.main()
