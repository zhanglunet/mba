# -*- coding: utf-8 -*-
"""PRD-380/T2 测试（trend #1884 的 T2 环节）：评审结论验证台。

运行：uv run --with pytest python -m pytest tests/unit/test_prd380_t2_review_verify_bench.py -q
（仓库根执行）

覆盖（T1 §4 + R1~R4）：verify_score 八件套校验（缺一 BENCH_INCOMPLETE）；
真实评分推导串联（快照重跑重算分数比对 → VERIFIED；不一致 → UNVERIFIED
词表封闭）；verify_scores 复核收件箱来源包装（UNVERIFIED 拦下）；
ReviewBenchLedger JSONL 真实落库+八件套缺一/词表外/REPRO_MISMATCH 声称
拒绝；reverify 快照变更二次验证（指纹不符 BENCH_STALE 拒绝复用/一致正常
复验）；AST 零 LLM 零网络零子进程零改分词面+快照指纹与 352 work_
snapshots_digest 同族口径。零网络；全合成占位。
"""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from review_verify_bench import (  # noqa: E402
    BENCH_SCHEMA,
    ERROR_CODES,
    ReviewBenchError,
    ReviewBenchLedger,
    VERDICTS,
    snapshots_fingerprint,
    verify_score,
    verify_scores,
)

NOW = "2026-11-13T09:00:00Z"
WORKS = [{"work_id": 42, "work_title": "作品42（占位）",
          "snapshot_digest": "sha16:w42（占位）"}]
REVIEW = {"review_id": "r-001", "work_id": 42, "kind": "low_confidence_score",
          "source_ref": "review-replay-pack/v1（占位）", "score": "88（原样）"}


def recheck_fn(work_snapshots):
    """注入式评分推导重跑（复用 352 score_fn 形态）：作品 42 → 88（原样）。"""
    return [{"work_id": w["work_id"], "score": "88（原样）"}
            for w in work_snapshots]


class TestVerifyScore(unittest.TestCase):
    def test_verified_with_score_rerun(self):
        """真实评分推导串联：重算分数与结论一致 → VERIFIED；快照指纹与
        352 work_snapshots_digest 同族口径（sha16: 前缀确定性）。"""
        out = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        self.assertEqual(out["verdict"], "VERIFIED")
        self.assertEqual(out["schema"], BENCH_SCHEMA)
        fp = snapshots_fingerprint(WORKS)
        self.assertTrue(fp.startswith("sha16:"))
        self.assertEqual(out["snapshots_fingerprint"], fp)

    def test_unverified_when_score_differs(self):
        out = verify_score(dict(REVIEW, score="1（改写）"), WORKS,
                           recheck_fn, at=NOW)
        self.assertEqual(out["verdict"], "UNVERIFIED")
        self.assertFalse(out["reproduce"]["score_match"])

    def test_incomplete_refused(self):
        bad = dict(REVIEW)
        del bad["score"]
        out = verify_score(bad, WORKS, recheck_fn, at=NOW)
        self.assertEqual(out["refused"], "BENCH_INCOMPLETE")
        out2 = verify_score(REVIEW, WORKS, None, at=NOW)
        self.assertEqual(out2["refused"], "BENCH_INCOMPLETE")

    def test_verdict_vocab_closed(self):
        self.assertEqual(set(VERDICTS), {"VERIFIED", "UNVERIFIED"})


class TestVerifyScores(unittest.TestCase):
    def test_outlet_blocks_unverified(self):
        """复核收件箱来源包装：UNVERIFIED 拦下不进复核收件箱（R1）。"""
        reviews = [REVIEW, dict(REVIEW, review_id="r-002", work_id=99,
                                score="99（不在快照）（占位）")]
        out = verify_scores(reviews, WORKS, recheck_fn, at=NOW)
        self.assertEqual(len(out["verified"]), 1)
        self.assertEqual(out["unverified_count"], 1)
        self.assertEqual(out["unverified"][0]["review_id"], "r-002")


class TestReviewBenchLedger(unittest.TestCase):
    def test_jsonl_persistence_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rbench" / "ledger.jsonl"
            led = ReviewBenchLedger(path)
            led.record(verify_score(REVIEW, WORKS, recheck_fn, at=NOW),
                       at=NOW)
            led.record(verify_score(dict(REVIEW, review_id="r-002"), WORKS,
                                    recheck_fn, at=NOW), at=NOW)
            self.assertEqual(len(led.entries()), 2)
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["review_id"], "r-001")

    def test_record_refusals(self):
        led = ReviewBenchLedger(None)
        with self.assertRaisesRegex(ReviewBenchError, "BENCH_INCOMPLETE"):
            led.record({"schema": BENCH_SCHEMA}, at=NOW)
        with self.assertRaisesRegex(ReviewBenchError, "BENCH_REPRO_MISMATCH"):
            bad = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
            bad = dict(bad, verdict="VERIFIED",
                       reproduce={"score_match": False, "detail": "改（占位）"})
            led.record(bad, at=NOW)


class TestReverify(unittest.TestCase):
    def test_stale_refuses_reuse(self):
        """作品快照变更 → BENCH_STALE 拒绝复用旧 VERIFIED。"""
        led = ReviewBenchLedger(None)
        led.record(verify_score(REVIEW, WORKS, recheck_fn, at=NOW), at=NOW)
        new_works = [dict(WORKS[0], snapshot_digest="sha16:new（占位）")]
        out = led.reverify("r-001", new_works, recheck_fn, at=NOW)
        self.assertEqual(out["refused"], "BENCH_STALE")

    def test_same_snapshot_reverify_ok(self):
        led = ReviewBenchLedger(None)
        led.record(verify_score(REVIEW, WORKS, recheck_fn, at=NOW), at=NOW)
        out = led.reverify("r-001", WORKS, recheck_fn, at=NOW)
        self.assertEqual(out["verdict"], "VERIFIED")


class TestRedline(unittest.TestCase):
    def test_ast_zero_llm_zero_network_zero_score_write(self):
        """AST：零 LLM 零网络零子进程零改分词面（不碰分数红线不变）。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess",
                  "openai", "anthropic", "judge_config_snapshot"}
        src = REPO / "scripts" / "review_verify_bench.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & banned, imported & banned)
        names = {n.id.lower() for n in ast.walk(tree)
                 if isinstance(n, ast.Name)}
        names |= {n.attr.lower() for n in ast.walk(tree)
                  if isinstance(n, ast.Attribute)}
        for word in ("set_score", "score_write", "update_score"):
            self.assertNotIn(word, names, f"出现改分词面 {word}")

    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"BENCH_INCOMPLETE", "BENCH_REPRO_MISMATCH",
                          "BENCH_STALE"})


if __name__ == "__main__":
    unittest.main()
