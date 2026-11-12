# -*- coding: utf-8 -*-
"""PRD-380/T3 测试（trend #1884 的 T3 环节）：评审结论验证台闸门。

运行：uv run --with pytest python -m pytest tests/unit/test_prd380_t3_review_verify_bench_gates.py -q
（仓库根执行）

覆盖（T1 §5 + R1/R3/R4）：append_only_gate（无基线形态过/mark_baseline 后
追加 pass/删除或首条改写 LEDGER_DRIFT 显形/非账本对象显形）；verdict_gate
（一致 pass/双向不一致 BENCH_REPRO_MISMATCH/缺件词表外 BENCH_INCOMPLETE
显形）；stale_gate（指纹一致 pass/不符 BENCH_STALE 显形）；gate_summary
一票否决；与 T2 串联（真实 verify_score+ReviewBenchLedger 产物过闸全
pass）；ERROR_CODES 随模块导出；AST 零 LLM 零网络零改分词面+闸门只读。
零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from review_verify_bench import ReviewBenchLedger, verify_score  # noqa: E402
from review_verify_bench_gates import (  # noqa: E402
    ERROR_CODES,
    append_only_gate,
    gate_summary,
    mark_baseline,
    stale_gate,
    verdict_gate,
)

NOW = "2026-11-13T09:00:00Z"
WORKS = [{"work_id": 42, "work_title": "作品42（占位）",
          "snapshot_digest": "sha16:w42（占位）"}]
REVIEW = {"review_id": "r-001", "work_id": 42, "kind": "low_confidence_score",
          "source_ref": "review-replay-pack/v1（占位）", "score": "88（原样）"}


def recheck_fn(work_snapshots):
    return [{"work_id": w["work_id"], "score": "88（原样）"}
            for w in work_snapshots]


def _ledger():
    led = ReviewBenchLedger(None)
    led.record(verify_score(REVIEW, WORKS, recheck_fn, at=NOW), at=NOW)
    led.record(verify_score(dict(REVIEW, review_id="r-002"), WORKS,
                            recheck_fn, at=NOW), at=NOW)
    return led


class TestAppendOnlyGate(unittest.TestCase):
    def test_no_baseline_form_check_passes(self):
        self.assertEqual(append_only_gate(_ledger())["gate"], "pass")

    def test_mark_baseline_then_append_passes(self):
        led = _ledger()
        mark_baseline(led)
        led.record(verify_score(dict(REVIEW, review_id="r-003"), WORKS,
                                recheck_fn, at=NOW), at=NOW)
        self.assertEqual(append_only_gate(led)["gate"], "pass")

    def test_deletion_detected(self):
        led = _ledger()
        mark_baseline(led)
        led._records.pop()
        self.assertEqual(append_only_gate(led)["gate"], "LEDGER_DRIFT")

    def test_first_record_rewrite_detected(self):
        led = _ledger()
        mark_baseline(led)
        led._records[0]["verdict"] = "UNVERIFIED"
        self.assertEqual(append_only_gate(led)["gate"], "LEDGER_DRIFT")

    def test_non_ledger_object_visible(self):
        self.assertEqual(append_only_gate(object())["gate"], "LEDGER_DRIFT")


class TestVerdictGate(unittest.TestCase):
    def test_consistent_record_passes(self):
        rec = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        self.assertEqual(verdict_gate(rec)["gate"], "pass")

    def test_verified_but_score_mismatch(self):
        rec = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        rec["reproduce"]["score_match"] = False
        self.assertEqual(verdict_gate(rec)["gate"], "BENCH_REPRO_MISMATCH")

    def test_unverified_but_match_mismatch(self):
        rec = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        rec["verdict"] = "UNVERIFIED"   # 词表内但与 score_match=true 不一致
        self.assertEqual(verdict_gate(rec)["gate"], "BENCH_REPRO_MISMATCH")

    def test_vocab_out_and_missing_visible(self):
        rec = dict(verify_score(REVIEW, WORKS, recheck_fn, at=NOW),
                   verdict="MAYBE（占位）")
        self.assertEqual(verdict_gate(rec)["gate"], "BENCH_INCOMPLETE")
        out = verdict_gate({"review_id": "x"})
        self.assertEqual(out["gate"], "BENCH_INCOMPLETE")
        self.assertTrue(any("缺" in r for r in out["reasons"]))


class TestStaleGate(unittest.TestCase):
    def test_matching_fingerprint_passes(self):
        rec = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        self.assertEqual(stale_gate(rec, WORKS)["gate"], "pass")

    def test_stale_fingerprint_visible(self):
        rec = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        out = stale_gate(rec, [{"work_id": 99, "snapshot_digest":
                                "sha16:other（占位）"}])
        self.assertEqual(out["gate"], "BENCH_STALE")


class TestSummaryAndChain(unittest.TestCase):
    def test_summary_one_block_votes_all(self):
        led = _ledger()
        led.record(verify_score(dict(REVIEW, review_id="r-003"), WORKS,
                                recheck_fn, at=NOW), at=NOW)
        rec = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        rec["reproduce"]["score_match"] = False
        out = gate_summary([append_only_gate(led), verdict_gate(rec)])
        self.assertEqual(out["gate"], "block")
        self.assertEqual(out["gates_checked"], 2)

    def test_chain_with_real_t2_products(self):
        """与 T2 串联：真实 verify_score+ReviewBenchLedger 产物过闸全
        pass。"""
        led = _ledger()
        mark_baseline(led)
        rec = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        results = [append_only_gate(led), verdict_gate(rec),
                   stale_gate(rec, WORKS)]
        self.assertTrue(all(r["gate"] == "pass" for r in results))
        self.assertEqual(gate_summary(results)["gate"], "pass")

    def test_error_codes_closed_and_exported(self):
        import review_verify_bench_gates as g
        self.assertEqual(set(g.ERROR_CODES),
                         {"LEDGER_DRIFT", "BENCH_INCOMPLETE",
                          "BENCH_REPRO_MISMATCH", "BENCH_STALE"})


class TestRedline(unittest.TestCase):
    def test_ast_zero_llm_zero_network_zero_score_write_readonly(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess",
                  "openai", "anthropic", "judge_config_snapshot"}
        src = REPO / "scripts" / "review_verify_bench_gates.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & banned, imported & banned)
        text = src.read_text(encoding="utf-8")
        for call in (".record(", ".append("):
            self.assertNotIn(call, text, f"闸门出现账本写调用 {call}")
        names = {n.id.lower() for n in ast.walk(tree)
                 if isinstance(n, ast.Name)}
        for word in ("set_score", "score_write"):
            self.assertNotIn(word, names, f"出现改分词面 {word}")


if __name__ == "__main__":
    unittest.main()
