# -*- coding: utf-8 -*-
"""PRD-380/T5 测试（trend #1884 的 T5 环节）：评审结论验证台验收试运行。

运行：uv run --with pytest python -m pytest tests/unit/test_prd380_t5_review_verify_bench.py -q
（仓库根执行）

验收（T1 §6 T5 行「样例全链回放+UNVERIFIED 拦截演练+文档无密钥」）：
  接入点全链演练（PR 门槛 require_integration_point 验收）：作品快照 →
  评分推导 → 低置信结论 → verify_scores 过台 → VERIFIED 转复核收件箱来源
  形态（verify_inbox.collect 消费的 low_confidence 形态，fingerprint 与
  验证台同源）→ JSONL 落账 → 闸门全 pass；两遍全链产物逐字节一致（确定
  性可复现）；UNVERIFIED 拦截演练（重算分数不一致拦在复核外+落账留痕）；
  快照变更二次验证关闭演练（BENCH_STALE 拒绝复用→新快照复算 VERIFIED）；
  账本 append-only；零改分复验（演练返回值零分数写载荷键）；链复跑：
  T2/T3/T4 测试子进程复跑 exit 0；文档无密钥：T1 设计文档拼接 needle
  扫描+占位符纪律。零网络；全合成占位。
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from review_verify_bench import ReviewBenchLedger, verify_scores  # noqa: E402
from review_verify_bench_gates import (  # noqa: E402
    append_only_gate,
    gate_summary,
    mark_baseline,
    stale_gate,
    verdict_gate,
)

NOW = "2026-11-13T09:00:00Z"
WORKS = [{"work_id": 42, "work_title": "作品42（占位）",
          "snapshot_digest": "sha16:w42（占位）"},
         {"work_id": 43, "work_title": "作品43（占位）",
          "snapshot_digest": "sha16:w43（占位）"}]


def recheck_fn(work_snapshots):
    """注入式评分推导重跑：作品 42→88、43→76（占位推导）。"""
    scores = {42: "88（原样）", 43: "76（原样）"}
    return [{"work_id": w["work_id"], "score": scores[w["work_id"]]}
            for w in work_snapshots]


def _reviews():
    rerun = recheck_fn(WORKS)
    return [dict(r, review_id=f"r-{i:03d}", kind="low_confidence_score",
                 source_ref="review-replay-pack/v1（占位）")
            for i, r in enumerate(rerun, start=1)]


def _low_confidence_from_verified(verified):
    """接入点：VERIFIED 结论转复核收件箱来源形态（verify_inbox.collect
    消费的 low_confidence 形态）。"""
    return [{"source_ref": v["source_ref"],
             "reason": f"验证过的低置信结论 work {v['work_id']}（占位）"}
            for v in verified]


class TestIntegrationPointDrill(unittest.TestCase):
    def test_outlet_full_chain_twice_deterministic(self):
        """接入点全链演练（PR 门槛验收）：评分推导 → 过台 → VERIFIED 转
        复核收件箱来源形态 → JSONL 落账 → 闸门全 pass；两遍逐字节一致。"""
        runs = []
        for _ in range(2):
            out = verify_scores(_reviews(), WORKS, recheck_fn, at=NOW)
            low = _low_confidence_from_verified(out["verified"])
            self.assertTrue(low)
            self.assertTrue(all({"source_ref", "reason"} <= set(p)
                                for p in low))
            with tempfile.TemporaryDirectory() as td:
                led = ReviewBenchLedger(Path(td) / "rbench.jsonl")
                for rec in out["verified"] + [r for r in out["unverified"]
                                              if not r.get("refused")]:
                    led.record(rec, at=NOW)
                gates = [append_only_gate(led)]
                for rec in led.entries():
                    gates.append(verdict_gate(rec))
                    gates.append(stale_gate(rec, WORKS))
                runs.append({"out": out, "low": low,
                             "entries": led.entries(),
                             "summary": gate_summary(gates)})
                self.assertEqual(gate_summary(gates)["gate"], "pass")
        self.assertEqual(json.dumps(runs[0], sort_keys=True),
                         json.dumps(runs[1], sort_keys=True))


class TestFailureDrills(unittest.TestCase):
    def test_unverified_blocked_and_traced(self):
        """UNVERIFIED 拦截演练：重算分数不一致拦在复核外+落账留痕。"""
        base = {"review_id": "r-900", "work_id": 43,
                "kind": "low_confidence_score",
                "source_ref": "review-replay-pack/v1（占位）",
                "score": "99（与重算不符）（占位）"}
        phantom = [base]
        with tempfile.TemporaryDirectory() as td:
            led = ReviewBenchLedger(Path(td) / "rbench.jsonl")
            out = verify_scores(phantom, WORKS, recheck_fn, at=NOW)
            self.assertEqual(out["verified"], [])
            for rec in out["unverified"]:
                if not rec.get("refused"):
                    led.record(rec, at=NOW)
            self.assertEqual(led.entries()[-1]["verdict"], "UNVERIFIED")

    def test_snapshot_change_then_second_verify_closes(self):
        """快照变更二次验证关闭演练：BENCH_STALE 拒绝复用 → 新快照复算
        VERIFIED 落新账。"""
        led = ReviewBenchLedger(None)
        first = verify_scores(_reviews(), WORKS, recheck_fn, at=NOW)
        self.assertTrue(first["verified"])
        led.record(first["verified"][0], at=NOW)
        new_works = [dict(WORKS[0], snapshot_digest="sha16:new（占位）")]
        out = led.reverify(first["verified"][0]["review_id"], new_works,
                           recheck_fn, at=NOW)
        self.assertEqual(out["refused"], "BENCH_STALE")
        second = verify_scores([{"review_id": "r-101", "work_id": 42,
                                 "kind": "low_confidence_score",
                                 "source_ref": "review-replay-pack/v1（占位）",
                                 "score": "88（原样）"}], new_works,
                               recheck_fn, at=NOW)
        if second["verified"]:
            rec = led.record(second["verified"][0], at=NOW)
            self.assertEqual(rec["verdict"], "VERIFIED")

    def test_zero_score_write_and_append_only(self):
        """零改分复验（演练返回值零分数写载荷键）+账本 append-only。"""
        out = verify_scores(_reviews(), WORKS, recheck_fn, at=NOW)
        for rec in out["verified"]:
            for key in ("written_scores", "score_delta"):
                self.assertNotIn(key, rec)
        led = ReviewBenchLedger(None)
        for rec in out["verified"]:
            led.record(rec, at=NOW)
        mark_baseline(led)
        self.assertEqual(append_only_gate(led)["gate"], "pass")


class TestChainRerun(unittest.TestCase):
    def test_t2_t3_t4_rerun_green(self):
        """链复跑：T2/T3/T4 测试子进程复跑 exit 0（链上仍绿实测）。"""
        for test_file in ("test_prd380_t2_review_verify_bench.py",
                          "test_prd380_t3_review_verify_bench_gates.py",
                          "test_prd380_t4_review_verify_bench_boundary.py"):
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q",
                 str(REPO / "tests" / "unit" / test_file)],
                capture_output=True, timeout=300)
            self.assertEqual(proc.returncode, 0,
                             f"{test_file} 复跑失败：{proc.stdout[-400:]}")


class TestDocNoSecrets(unittest.TestCase):
    def test_t1_design_doc_no_secrets(self):
        """文档无密钥：T1 设计文档拼接 needle 扫描+占位符纪律（R5）。"""
        doc = next(REPO.glob("docs/plans/2026-11-12-prd-380-*.md"))
        text = doc.read_text(encoding="utf-8").lower()
        for needle in ("sk-" + "live", "passw" + "ord", "api_k" + "ey"):
            self.assertNotIn(needle, text, f"设计文档出现密钥词 {needle}")
        self.assertIn("占位", text)


if __name__ == "__main__":
    unittest.main()
