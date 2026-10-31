# -*- coding: utf-8 -*-
"""PRD-282/T5 验收试运行（trend #1414）：评委包配置快照全流程演练 + 复算对照 + 文档无密钥。

全链：T1 #1411（设计）→ T2 #1412（judge_config_snapshot.py 快照/还原/审计）→
T3 #1413（recalc_record.py 复算记录落档）→ T4 #1414（审计断言）→ 本验收。

红线：口径变更可回滚；复算记录留痕；零网络；示例全虚构。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from judge_config_snapshot import (  # noqa: E402
    take_snapshot, restore, recalc_diff, export_events,
)
from recalc_record import write_recalc_record, append_recalc, read_recalcs  # noqa: E402

OLD_CONFIG = {"packs": ["示例评委A", "示例评委B"], "rubric_version": "r1",
               "weights": {"创新": 0.4, "可行": 0.6}}
NEW_CONFIG = {"packs": ["示例评委A", "示例评委C"], "rubric_version": "r2",
               "weights": {"创新": 0.5, "可行": 0.5}}
SAMPLES = ["示例项目1", "示例项目2", "示例项目3"]


def fake_score(sample, config):
    """注入式假评分：权重差 → 分差（不真调 LLM）。"""
    base = 80
    delta = int(abs(config["weights"]["创新"] - 0.4) * 100) * len(sample)
    return base + delta


class TestAcceptance(unittest.TestCase):
    def test_a1_full_flow_snapshot_change_recalc_rollback(self):
        """全流程演练：快照→改口径→复算对照→差异落档→回滚。"""
        snap = take_snapshot(OLD_CONFIG, "2026-10-30T10:00:00Z")
        diff = recalc_diff(OLD_CONFIG, NEW_CONFIG, SAMPLES, fake_score)
        record = write_recalc_record(diff, snap["fingerprint"], "new-fp-placeholder0",
                                      "2026-10-30T10:05:00Z")
        self.assertEqual(record["schema"], "recalc-record-v1")
        restored = restore(snap)
        self.assertEqual(restored["rubric_version"], "r1")

    def test_a2_recalc_diff_detects_drift(self):
        """复算对照：口径漂移可量化（max_abs_delta>0 且差异逐样例在场）。"""
        diff = recalc_diff(OLD_CONFIG, NEW_CONFIG, SAMPLES, fake_score)
        self.assertGreater(diff["max_abs_delta"], 0)
        self.assertEqual(diff["n"], len(SAMPLES))
        self.assertEqual(len(diff["diffs"]), len(SAMPLES))

    def test_a3_recalc_record_persisted_and_readable(self):
        diff = recalc_diff(OLD_CONFIG, NEW_CONFIG, SAMPLES, fake_score)
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "recalc.jsonl"
            record = write_recalc_record(diff, "old-fp", "new-fp", "2026-10-30T10:05:00Z")
            append_recalc(record, str(audit))
            loaded = read_recalcs(str(audit))
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["schema"], "recalc-record-v1")

    def test_a4_rollback_restores_exact_config(self):
        snap = take_snapshot(OLD_CONFIG, "2026-10-30T10:00:00Z")
        restored = restore(snap)
        self.assertEqual(restored["weights"], OLD_CONFIG["weights"])
        self.assertEqual(restored["packs"], OLD_CONFIG["packs"])

    def test_a5_three_audit_event_types(self):
        snap = take_snapshot(OLD_CONFIG, "2026-10-30T10:00:00Z")
        restore(snap)
        diff = recalc_diff(OLD_CONFIG, NEW_CONFIG, SAMPLES, fake_score)
        recalc_diff(OLD_CONFIG, NEW_CONFIG, SAMPLES, fake_score)
        events = export_events()
        kinds = {e.get("event") for e in events}
        self.assertIn("config_changed", kinds)  # T2 事件形态
        self.assertIn("rolled_back", kinds)
        self.assertIn("recalc_done", kinds)

    def test_a6_tamper_detected(self):
        snap = take_snapshot(OLD_CONFIG, "2026-10-30T10:00:00Z")
        tampered = json.loads(json.dumps(snap))
        tampered["config"]["rubric_version"] = "r99"
        with self.assertRaises(Exception):
            restore(tampered)

    def test_a7_no_network(self):
        src = (Path(__file__).resolve().parents[2] / "scripts" /
               "judge_config_snapshot.py").read_text(encoding="utf-8")
        for banned in ("requests", "urllib", "socket", "http.client", "fetch("):
            self.assertNotIn(banned, src)

    def test_a8_secrets_scan(self):
        surfaces = [
            Path(__file__).resolve().parents[2] / "scripts" / "judge_config_snapshot.py",
            Path(__file__).resolve().parents[2] / "scripts" / "recalc_record.py",
            Path(__file__),
        ]
        needle = "sk-" + "placeholder0123456789"
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(needle, text)
            self.assertNotIn("AK" + "IA", text)


if __name__ == "__main__":
    unittest.main()
