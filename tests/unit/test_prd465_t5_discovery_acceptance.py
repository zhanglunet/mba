# -*- coding: utf-8 -*-
"""PRD-465/T5 测试（trend #2249 的 T5 环节）：mba skill 发现层 验收试运行。
运行：python3 -m pytest tests/unit/test_prd465_t5_discovery_acceptance.py -q
验收（T5 issue 正文「真实需求描述 → 推荐 → 人工复核，全链跑通」）：
  接入点全链演练：需求描述 → 推荐（可溯源）→ 人工否决首位（推错可纠）
  → 纠正重推（次位顶上，supersedes 链路在位）→ 人工接受 → 入账 →
  形态与划界断言全过 → 索引源一字未动；两遍逐字节一致（确定性可复现）；
  真实 registry 冒烟：main 上真实 registry.json 建索引 43 条，真实触发
  句式命中首位 arnault-perspective；
  失败演练：无匹配空推荐 / 溯源断了不入账 / 全部否决返回空推荐 /
  R1/R2 越界显形拒绝 / 索引源被改显形 / 重复复核拒绝；
  链复跑：T2/T3/T4 测试子进程 exit 0；文档无密钥：T1 设计文档拼接
  needle 扫描 + 占位符纪律。零网络；全合成占位（真实 registry 只读
  冒烟）。T2/T3/T4 模块未动；不碰评审流程与分数（R1）。
"""
import ast
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
MOD_DIR = Path(__file__).resolve().parents[2] / "scripts"
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MOD_DIR))

from skill_discovery import (  # noqa: E402
    DiscoveryError, load_index, recommend,
)
from skill_discovery_gate import (  # noqa: E402
    GatedDiscoveryLedger,
    recommend_corrected,
    review_recommendation,
    verify_trace,
)
from skill_discovery_boundary import (  # noqa: E402
    BoundaryDiscoveryLedger,
    assert_no_install,
    assert_no_review_writes,
    recommendation_shape_check,
    scope_check,
    snapshot_sources,
    sources_unchanged,
)

NOW = "2026-11-16T09:00:00Z"
TEXT = "用普通消费者视角看，这个品牌第一印象怎么样"
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

LONG_SKILL = """---
name: long-desc-perspective
description: |
  %s
---

# 视角（占位）
""" % ("超长描述词（占位）" * 200)

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
    (tmp / "perspectives" / "long-desc-perspective").mkdir(parents=True)
    (tmp / "perspectives" / "long-desc-perspective" / "SKILL.md").write_text(
        LONG_SKILL, encoding="utf-8")
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


def full_chain():
    """接入点全链：需求 → 推荐 → 否决首位 → 纠正重推 → 接受 → 入账 →
    形态与划界全过 → 索引源一字未动。"""
    with tempfile.TemporaryDirectory() as td:
        root = build_root(Path(td))
        before = snapshot_sources(root)
        index = load_index(root)
        led = BoundaryDiscoveryLedger(None)
        first = recommend(index, TEXT, request_id="r-001")
        led.record(first)
        rejected = review_recommendation(
            first, verdict="rejected", reviewer="reviewer（占位）",
            note="推错了（占位）")
        led.record(rejected)
        second = recommend_corrected(index, TEXT, led, request_id="r-002",
                                     supersedes="r-001")
        accepted = review_recommendation(
            second, verdict="accepted", reviewer="reviewer（占位）",
            note="这次对了（占位）")
        led.record(accepted)
        after = sources_unchanged(root, before)
        return {"index_counts": index["counts"], "index_total": index["total"],
                "first": first, "rejected": rejected, "second": second,
                "accepted": accepted, "entries": led.entries(),
                "corrections": led.corrections_for(TEXT),
                "first_trace": verify_trace(first),
                "second_trace": verify_trace(second),
                "second_shape": recommendation_shape_check(second),
                "second_scope": scope_check(second),
                "sources": after}


class TestFullChainDrill(unittest.TestCase):
    def test_chain_twice_byte_identical(self):
        runs = [full_chain(), full_chain()]
        self.assertEqual(json.dumps(runs[0], sort_keys=True),
                         json.dumps(runs[1], sort_keys=True))
        run = runs[0]
        self.assertEqual(run["index_total"], 7)
        self.assertEqual(run["first"]["recommendation"]["skill"],
                         "first-glance-shopper-perspective")
        self.assertTrue(run["first_trace"]["ok"])
        self.assertFalse(run["rejected"]["recommendation"]["effective"])
        self.assertEqual(run["second"]["request"]["supersedes"], "r-001")
        self.assertNotEqual(run["first"]["recommendation"]["skill"],
                            run["accepted"]["recommendation"]["skill"])
        self.assertTrue(run["accepted"]["recommendation"]["effective"])
        self.assertTrue(run["second_trace"]["ok"])
        self.assertTrue(run["second_shape"]["ok"])
        self.assertTrue(run["second_scope"]["in_scope"])
        self.assertEqual(len(run["entries"]), 3)
        self.assertIn("first-glance-shopper-perspective",
                      run["corrections"])
        self.assertTrue(run["sources"]["unchanged"])
        self.assertEqual(run["sources"]["changed"], [])

    def test_real_registry_smoke(self):
        """真实 registry 冒烟：main 上真实 registry.json 建索引 43 条，
        真实触发句式命中首位 arnault-perspective（只读，不改源）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copyfile(REPO_ROOT / "registry.json",
                            root / "registry.json")
            index = load_index(root)
            self.assertTrue(index["registry_loaded"])
            self.assertEqual(index["total"], 43)
            self.assertEqual(index["counts"]["perspective"], 43)
            out = recommend(index, "用 Bernard Arnault 视角看 LVMH",
                            request_id="r-real")
            self.assertTrue(out["candidates"])
            self.assertEqual(out["recommendation"]["skill"],
                             "arnault-perspective")
            self.assertTrue(verify_trace(out)["ok"])
            self.assertTrue(recommendation_shape_check(out)["ok"])
            self.assertTrue(scope_check(out)["in_scope"])


class TestFailureDrills(unittest.TestCase):
    def test_no_match_empty_recommendation(self):
        """无匹配：空候选、空推荐，溯源仍成立，无可复核。"""
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            out = recommend(index, "zzzqqq 未知词（占位）",
                            request_id="r-empty")
            self.assertEqual(out["candidates"], [])
            self.assertIsNone(out["recommendation"])
            self.assertTrue(verify_trace(out)["ok"])
            refused = review_recommendation(
                out, verdict="accepted", reviewer="reviewer（占位）")
            self.assertEqual(refused["refused"], "DISCOVERY_INVALID_REVIEW")

    def test_broken_trace_refused_at_record(self):
        """溯源断了不入账：推荐 skill 被改成非首位候选，入账拒绝。"""
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            rec = recommend(index, TEXT, request_id="r-001")
            bad = copy.deepcopy(rec)
            bad["recommendation"]["skill"] = "jobs-perspective"
            self.assertFalse(verify_trace(bad)["ok"])
            led = BoundaryDiscoveryLedger(None)
            with self.assertRaises(DiscoveryError):
                led.record(bad)
            self.assertEqual(led.entries(), [])

    def test_all_candidates_rejected_empty(self):
        """全部候选都被否决则返回空推荐（不硬推）。"""
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            led = GatedDiscoveryLedger(None)
            rid = 1
            for _ in range(5):
                cur = recommend_corrected(index, "品牌指标怎么样", led,
                                          request_id=f"r-{rid:03d}",
                                          supersedes=f"r-{rid-1:03d}")
                if not cur["candidates"]:
                    break
                reviewed = review_recommendation(
                    cur, verdict="rejected", reviewer="reviewer（占位）",
                    note="推错了（占位）")
                led.record(reviewed)
                rid += 1
            final = recommend_corrected(index, "品牌指标怎么样", led,
                                        request_id="r-final")
            self.assertEqual(final["candidates"], [])
            self.assertIsNone(final["recommendation"])
            self.assertTrue(verify_trace(final)["ok"])

    def test_review_redlines_explicit(self):
        """R1/R2 越界显形：评审写字段与安装字段一律进 violation，洗不进账。"""
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            rec = recommend(index, TEXT, request_id="r-001")
            bad_r1 = copy.deepcopy(rec)
            bad_r1["review_score"] = 9.9
            self.assertFalse(scope_check(bad_r1)["in_scope"])
            self.assertTrue(assert_no_review_writes(bad_r1))
            bad_r2 = copy.deepcopy(rec)
            bad_r2["candidates"][0]["install_path"] = "/tmp/x"
            self.assertFalse(scope_check(bad_r2)["in_scope"])
            self.assertTrue(assert_no_install(bad_r2))
            led = BoundaryDiscoveryLedger(None)
            with self.assertRaises(DiscoveryError):
                led.record(bad_r1)
            with self.assertRaises(DiscoveryError):
                led.record(bad_r2)

    def test_sources_tamper_detected(self):
        """索引源被改显形：registry.json 改一个字节即进 changed 清单。"""
        with tempfile.TemporaryDirectory() as td:
            root = build_root(Path(td))
            before = snapshot_sources(root)
            self.assertTrue(sources_unchanged(root, before)["unchanged"])
            (root / "registry.json").write_text(
                json.dumps({"packs": []}), encoding="utf-8")
            after = sources_unchanged(root, before)
            self.assertFalse(after["unchanged"])
            self.assertEqual(after["changed"], ["registry.json"])

    def test_double_review_refused(self):
        """重复复核拒绝：一条推荐只可复核一次。"""
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            rec = recommend(index, TEXT, request_id="r-001")
            once = review_recommendation(
                rec, verdict="accepted", reviewer="reviewer（占位）")
            again = review_recommendation(
                once, verdict="rejected", reviewer="reviewer（占位）",
                note="改主意（占位）")
            self.assertEqual(again["refused"], "DISCOVERY_INVALID_REVIEW")


class TestChainRerun(unittest.TestCase):
    def test_t2_t3_t4_rerun_green(self):
        """链复跑：T2/T3/T4 测试子进程复跑 exit 0（链上仍绿实测）。"""
        for name in ("test_prd465_t2_skill_discovery.py",
                     "test_prd465_t3_discovery_gate.py",
                     "test_prd465_t4_discovery_boundary.py"):
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(TESTS_DIR / name)],
                capture_output=True, timeout=300)
            self.assertEqual(proc.returncode, 0,
                             f"{name} 复跑失败：{proc.stdout[-400:]}")


class TestDocNoSecrets(unittest.TestCase):
    def test_t1_design_doc_no_secrets(self):
        """文档无密钥：T1 设计文档拼接 needle 扫描 + 占位符纪律。"""
        doc = next(REPO_ROOT.glob("docs/plans/2026-11-15-prd-465-*.md"))
        text = doc.read_text(encoding="utf-8").lower()
        for needle in ("sk-" + "live", "passw" + "ord", "api_k" + "ey"):
            self.assertNotIn(needle, text, f"设计文档出现密钥词 {needle}")
        self.assertIn("占位", text)

    def test_ast_zero_network_in_modules(self):
        """T2/T3/T4 模块零网络零子进程（AST 断言）。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        for name in ("skill_discovery.py", "skill_discovery_gate.py",
                     "skill_discovery_boundary.py"):
            tree = ast.parse((MOD_DIR / name).read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(imported & banned, f"{name}: {imported & banned}")


if __name__ == "__main__":
    unittest.main()
