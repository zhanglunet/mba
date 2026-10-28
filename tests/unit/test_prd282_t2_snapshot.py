# -*- coding: utf-8 -*-
"""PRD-282/T2 自测（trend #1412）：评委包配置快照最小实现。

运行：.venv/bin/python -m pytest tests/unit/test_prd282_t2_snapshot.py -q

覆盖：
  快照字段齐全（schema/config/fingerprint/taken_at）
  快照 config 为深拷贝（原口径与快照互不影响）
  指纹确定性（同口径同指纹、异口径异指纹、可复算）
  还原回滚（还原后口径与指纹一致）
  指纹篡改抛错（FingerprintMismatchError，fail-close）
  recalc_diff 双口径差异计算正确
  recalc_diff 零差异场景（max_abs_delta == 0）
  审计事件三类齐全且可 JSON 序列化
  单槽语义（新快照覆盖旧槽，槽内只有最近一份）

虚构纪律：评委包口径、样例品牌、分数全虚构；score_fn 由测试注入假函数，
不真调 LLM；零网络；不含真实主机名、IP、账号、密钥。
"""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from judge_config_snapshot import (  # noqa: E402
    FingerprintMismatchError,
    SNAPSHOT_SCHEMA,
    config_fingerprint,
    current_config,
    export_events,
    latest_snapshot,
    recalc_diff,
    reset_state,
    restore,
    take_snapshot,
)


def _fake_score_fn(sample, config):
    """注入的假评分函数（不真调 LLM）：分数只由虚构口径版本决定。"""
    return config["rubric"].get(sample, 0.0)


def _old_config():
    return {
        "pack": "example-brand-panel",
        "rubric_version": "v1",
        "rubric": {"示例品牌甲": 3.0, "示例品牌乙": 4.0, "示例品牌丙": 2.5},
        "weights": {"trust": 0.4, "value": 0.6},
    }


def _new_config():
    cfg = _old_config()
    cfg["rubric_version"] = "v2"
    cfg["rubric"] = {"示例品牌甲": 4.0, "示例品牌乙": 4.0, "示例品牌丙": 2.0}
    return cfg


SAMPLES = ["示例品牌甲", "示例品牌乙", "示例品牌丙"]


class TestSnapshot(unittest.TestCase):
    def setUp(self):
        reset_state()

    def test_01_snapshot_fields(self):
        snap = take_snapshot(_old_config(), "2026-10-29T09:00:00+08:00")
        self.assertEqual(snap["schema"], SNAPSHOT_SCHEMA)
        self.assertEqual(snap["config"], _old_config())
        self.assertEqual(snap["taken_at"], "2026-10-29T09:00:00+08:00")
        self.assertEqual(len(snap["fingerprint"]), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in snap["fingerprint"]))

    def test_02_snapshot_config_is_deep_copy(self):
        cfg = _old_config()
        snap = take_snapshot(cfg, "2026-10-29T09:00:00+08:00")
        cfg["rubric"]["示例品牌甲"] = 99.0          # 改原口径
        snap["config"]["rubric"]["示例品牌乙"] = 88.0  # 改快照
        self.assertEqual(snap["config"]["rubric"]["示例品牌甲"], 3.0)
        self.assertEqual(latest_snapshot()["config"]["rubric"]["示例品牌乙"], 4.0)
        self.assertNotIn(99.0, latest_snapshot()["config"]["rubric"].values())

    def test_03_fingerprint_deterministic(self):
        s1 = take_snapshot(_old_config(), "2026-10-29T09:00:00+08:00")
        s2 = take_snapshot(_old_config(), "2026-10-29T10:00:00+08:00")
        self.assertEqual(s1["fingerprint"], s2["fingerprint"])
        s3 = take_snapshot(_new_config(), "2026-10-29T11:00:00+08:00")
        self.assertNotEqual(s1["fingerprint"], s3["fingerprint"])
        # 指纹可复算：canonical json sha256 前 16 位
        canonical = json.dumps(_old_config(), sort_keys=True,
                               separators=(",", ":"), ensure_ascii=False)
        expect = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        self.assertEqual(s1["fingerprint"], expect)
        self.assertEqual(config_fingerprint(_old_config()), expect)

    def test_04_restore_roundtrip(self):
        snap = take_snapshot(_old_config(), "2026-10-29T09:00:00+08:00")
        take_snapshot(_new_config(), "2026-10-29T10:00:00+08:00")  # 口径变了
        self.assertEqual(current_config(), _new_config())
        restored = restore(snap, at="2026-10-29T14:30:00+08:00")
        self.assertEqual(restored, _old_config())
        self.assertEqual(current_config(), _old_config())
        self.assertEqual(config_fingerprint(current_config()), snap["fingerprint"])

    def test_05_tampered_fingerprint_raises(self):
        snap = take_snapshot(_old_config(), "2026-10-29T09:00:00+08:00")
        bad = copy.deepcopy(snap)
        bad["fingerprint"] = "0" * 16
        with self.assertRaises(FingerprintMismatchError):
            restore(bad)
        # 篡改 config 同样被检出
        bad2 = copy.deepcopy(snap)
        bad2["config"]["rubric_version"] = "tampered"
        with self.assertRaises(FingerprintMismatchError):
            restore(bad2)
        # 非法快照对象直接拒绝
        with self.assertRaises(FingerprintMismatchError):
            restore({"schema": "other", "config": {}})
        # fail-close：现行口径未被半还原
        self.assertEqual(current_config(), _old_config())

    def test_06_recalc_diff_computes_deltas(self):
        record = recalc_diff(_old_config(), _new_config(), SAMPLES,
                             _fake_score_fn, at="2026-10-29T15:00:00+08:00")
        self.assertEqual(record["n"], 3)
        by_sample = {d["sample"]: d for d in record["diffs"]}
        self.assertEqual(by_sample["示例品牌甲"]["old_score"], 3.0)
        self.assertEqual(by_sample["示例品牌甲"]["new_score"], 4.0)
        self.assertEqual(by_sample["示例品牌甲"]["delta"], 1.0)
        self.assertEqual(by_sample["示例品牌丙"]["delta"], -0.5)
        self.assertEqual(by_sample["示例品牌乙"]["delta"], 0.0)
        self.assertEqual(record["max_abs_delta"], 1.0)

    def test_07_recalc_diff_zero_difference(self):
        cfg = _old_config()
        record = recalc_diff(cfg, copy.deepcopy(cfg), SAMPLES, _fake_score_fn,
                             at="2026-10-29T15:00:00+08:00")
        self.assertEqual(record["n"], len(SAMPLES))
        self.assertTrue(all(d["delta"] == 0.0 for d in record["diffs"]))
        self.assertEqual(record["max_abs_delta"], 0.0)

    def test_08_events_kinds_and_serializable(self):
        snap = take_snapshot(_old_config(), "2026-10-29T09:00:00+08:00")
        recalc_diff(_old_config(), _new_config(), SAMPLES, _fake_score_fn,
                    at="2026-10-29T15:00:00+08:00")
        restore(snap, at="2026-10-29T16:00:00+08:00")
        events = export_events()
        kinds = [e["event"] for e in events]
        self.assertEqual(kinds, ["config_changed", "recalc_done", "rolled_back"])
        # 全部事件可 JSON 序列化（机读审计）
        for e in events:
            json.dumps(e, ensure_ascii=False)
        self.assertEqual(events[0]["fingerprint"], snap["fingerprint"])
        self.assertEqual(events[1]["n"], 3)

    def test_09_single_slot_overwrite(self):
        s1 = take_snapshot(_old_config(), "2026-10-29T09:00:00+08:00")
        s2 = take_snapshot(_new_config(), "2026-10-29T10:00:00+08:00")
        latest = latest_snapshot()
        self.assertEqual(latest["fingerprint"], s2["fingerprint"])
        self.assertNotEqual(latest["fingerprint"], s1["fingerprint"])
        self.assertEqual(latest["config"], _new_config())

    def test_10_restore_older_snapshot_after_slot_overwrite(self):
        s1 = take_snapshot(_old_config(), "2026-10-29T09:00:00+08:00")
        take_snapshot(_new_config(), "2026-10-29T10:00:00+08:00")
        restored = restore(s1, at="2026-10-29T17:00:00+08:00")
        self.assertEqual(restored, _old_config())
        self.assertEqual(config_fingerprint(current_config()), s1["fingerprint"])


if __name__ == "__main__":
    unittest.main()
