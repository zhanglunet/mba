# -*- coding: utf-8 -*-
"""PRD-282/T3 自测（trend #1413）：复算记录正式化（recalc-record-v1）。

运行：.venv/bin/python -m pytest tests/unit/test_prd282_t3_record.py -q

覆盖：
  记录 schema 字段齐全（schema/old_fingerprint/new_fingerprint/n/max_abs_delta/diffs/at）
  与 T2 recalc_diff 衔接（真实 T2 产出固化为记录）
  append 落档可读（JSONL 追加 → read_recalcs 读回全等）
  read 全量按序（多条记录按 append 顺序返回）
  空审计空读（不存在路径 / 空文件 → []）
  diffs 截断至前 50 条（n 仍记全量样例数）
  确定性（同输入同记录、同记录同字节）
  fail-close（diff 结构非法 / 非 recalc-record-v1 拒落档 / 损坏行带行号抛错）
  深拷贝独立（写记录后改 diff 不影响已固化记录）

虚构纪律：评委包口径、样例品牌、分数全虚构；diff 由 T2 recalc_diff 以注入的
假 score_fn 产出（不真调 LLM）；零网络；不含真实主机名、IP、账号、密钥。
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from judge_config_snapshot import (  # noqa: E402
    config_fingerprint,
    recalc_diff,
)
from recalc_record import (  # noqa: E402
    DIFFS_LIMIT,
    RECALC_RECORD_SCHEMA,
    RecalcRecordError,
    append_recalc,
    read_recalcs,
    write_recalc_record,
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
OLD_AT = "2026-10-29T09:00:00+08:00"
RECALC_AT = "2026-10-29T15:00:00+08:00"


def _t2_diff():
    """T2 recalc_diff 真实产出（注入假 score_fn，不真调 LLM）。"""
    return recalc_diff(_old_config(), _new_config(), SAMPLES, _fake_score_fn,
                       at=RECALC_AT)


class TestRecalcRecord(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.audit_path = str(Path(self._tmp.name) / "audit.jsonl")

    # T3-1 记录 schema 字段齐全
    def test_01_record_schema_fields(self):
        diff = _t2_diff()
        old_fp = config_fingerprint(_old_config())
        new_fp = config_fingerprint(_new_config())
        record = write_recalc_record(diff, old_fp, new_fp, RECALC_AT)

        self.assertEqual(record["schema"], RECALC_RECORD_SCHEMA)
        self.assertEqual(record["old_fingerprint"], old_fp)
        self.assertEqual(record["new_fingerprint"], new_fp)
        self.assertEqual(record["n"], 3)
        self.assertEqual(record["max_abs_delta"], diff["max_abs_delta"])
        self.assertEqual(record["at"], RECALC_AT)
        # 字段集合钉死：不多不少
        self.assertEqual(
            sorted(record.keys()),
            ["at", "diffs", "max_abs_delta", "n",
             "new_fingerprint", "old_fingerprint", "schema"],
        )
        # diffs 与 T2 产出逐条一致
        self.assertEqual(record["diffs"], diff["diffs"])
        self.assertEqual(record["diffs"][0]["sample"], "示例品牌甲")
        self.assertEqual(record["diffs"][0]["delta"], 1.0)
        # 全部可 JSON 序列化
        self.assertEqual(json.loads(json.dumps(record, ensure_ascii=False)), record)

    # T3-2 append 落档可读
    def test_02_append_then_read_back(self):
        record = write_recalc_record(
            _t2_diff(), config_fingerprint(_old_config()),
            config_fingerprint(_new_config()), RECALC_AT)
        append_recalc(record, self.audit_path)

        self.assertTrue(Path(self.audit_path).exists())
        lines = Path(self.audit_path).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1, "一记录一行 JSONL")
        self.assertEqual(json.loads(lines[0]), record, "落档行与记录逐字段全等")
        self.assertEqual(read_recalcs(self.audit_path), [record], "读回全等")

    # T3-3 read 全量按序
    def test_03_read_full_in_order(self):
        for i, at in enumerate(["2026-10-29T15:00:00+08:00",
                                "2026-10-29T16:00:00+08:00",
                                "2026-10-29T17:00:00+08:00"], start=1):
            diff = recalc_diff(_old_config(), _new_config(),
                               SAMPLES[:i], _fake_score_fn, at=at)
            append_recalc(write_recalc_record(
                diff, config_fingerprint(_old_config()),
                config_fingerprint(_new_config()), at), self.audit_path)

        records = read_recalcs(self.audit_path)
        self.assertEqual(len(records), 3, "全量读回（append-only 只增不减）")
        self.assertEqual([r["at"] for r in records],
                         ["2026-10-29T15:00:00+08:00",
                          "2026-10-29T16:00:00+08:00",
                          "2026-10-29T17:00:00+08:00"], "按 append 顺序返回")
        self.assertEqual([r["n"] for r in records], [1, 2, 3])

    # T3-4 空审计空读
    def test_04_empty_audit_reads_empty(self):
        self.assertEqual(read_recalcs(self.audit_path), [], "不存在路径 → []")
        Path(self.audit_path).write_text("", encoding="utf-8")
        self.assertEqual(read_recalcs(self.audit_path), [], "空文件 → []")

    # T3-5 diffs 截断至前 50 条，n 仍记全量
    def test_05_diffs_truncated(self):
        total = DIFFS_LIMIT + 10  # 60 个虚构样例
        samples = ["虚构样例-%02d" % i for i in range(total)]
        old_cfg = {"pack": "example-brand-panel", "rubric_version": "v1",
                   "rubric": {s: 3.0 for s in samples}}
        new_cfg = {"pack": "example-brand-panel", "rubric_version": "v2",
                   "rubric": {s: 3.0 + (i % 7) * 0.5 for i, s in enumerate(samples)}}
        diff = recalc_diff(old_cfg, new_cfg, samples, _fake_score_fn, at=RECALC_AT)
        self.assertEqual(len(diff["diffs"]), total)

        record = write_recalc_record(
            diff, config_fingerprint(old_cfg), config_fingerprint(new_cfg), RECALC_AT)
        self.assertEqual(len(record["diffs"]), DIFFS_LIMIT, "截断至前 50 条")
        self.assertEqual(record["diffs"], diff["diffs"][:DIFFS_LIMIT], "保留前 50 条原样")
        self.assertEqual(record["n"], total, "n 仍记全量样例数，截断不丢总数")
        self.assertEqual(record["max_abs_delta"], diff["max_abs_delta"])
        # 恰好 50 条不截断
        exact = recalc_diff(old_cfg, new_cfg, samples[:DIFFS_LIMIT], _fake_score_fn, at=RECALC_AT)
        exact_record = write_recalc_record(
            exact, config_fingerprint(old_cfg), config_fingerprint(new_cfg), RECALC_AT)
        self.assertEqual(len(exact_record["diffs"]), DIFFS_LIMIT)

    # T3-6 确定性：同输入同记录、同记录同字节
    def test_06_deterministic(self):
        diff = _t2_diff()
        old_fp, new_fp = config_fingerprint(_old_config()), config_fingerprint(_new_config())
        r1 = write_recalc_record(diff, old_fp, new_fp, RECALC_AT)
        r2 = write_recalc_record(copy.deepcopy(diff), old_fp, new_fp, RECALC_AT)
        self.assertEqual(r1, r2, "同输入两次写记录逐字段全等")

        append_recalc(r1, self.audit_path)
        other_path = str(Path(self._tmp.name) / "audit-copy.jsonl")
        append_recalc(r2, other_path)
        self.assertEqual(
            Path(self.audit_path).read_bytes(), Path(other_path).read_bytes(),
            "同记录落档字节全等（键排序 + 紧凑分隔符 + ensure_ascii=False）",
        )

    # T3-7 fail-close：非法 diff / 非本 schema 拒落档 / 损坏行带行号抛错
    def test_07_fail_close(self):
        with self.assertRaises(RecalcRecordError):
            write_recalc_record(["not", "a", "dict"], "0" * 16, "1" * 16, RECALC_AT)
        with self.assertRaises(RecalcRecordError):
            write_recalc_record({"diffs": []}, "0" * 16, "1" * 16, RECALC_AT)  # 缺 n/max_abs_delta
        with self.assertRaises(RecalcRecordError):
            write_recalc_record({"diffs": "not-a-list", "n": 0, "max_abs_delta": 0.0},
                                "0" * 16, "1" * 16, RECALC_AT)
        with self.assertRaises(RecalcRecordError):
            write_recalc_record(_t2_diff(), "", "1" * 16, RECALC_AT)  # 空指纹拒收
        with self.assertRaises(RecalcRecordError):
            write_recalc_record(_t2_diff(), "0" * 16, "1" * 16, None)  # 缺 at 拒收

        record = write_recalc_record(
            _t2_diff(), config_fingerprint(_old_config()),
            config_fingerprint(_new_config()), RECALC_AT)
        with self.assertRaises(RecalcRecordError):
            append_recalc({"schema": "other-schema", "n": 1}, self.audit_path)
        self.assertFalse(Path(self.audit_path).exists(), "拒落档不写半截文件")

        append_recalc(record, self.audit_path)
        with open(self.audit_path, "a", encoding="utf-8") as fh:
            fh.write("{broken json\n")
        with self.assertRaises(RecalcRecordError) as ctx:
            read_recalcs(self.audit_path)
        self.assertIn("第 2 行", str(ctx.exception), "损坏行带行号，绝不静默跳过")

        with open(self.audit_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"schema": "rollback-record-v1", "at": RECALC_AT},
                                ensure_ascii=False) + "\n")
        with self.assertRaises(RecalcRecordError):
            read_recalcs(self.audit_path), "非本 schema 的行拒绝读回"

    # T3-8 深拷贝独立：写记录后改 diff 不影响已固化记录
    def test_08_deep_copy_independence(self):
        diff = _t2_diff()
        record = write_recalc_record(
            diff, config_fingerprint(_old_config()),
            config_fingerprint(_new_config()), RECALC_AT)
        snapshot = copy.deepcopy(record)
        diff["diffs"][0]["delta"] = 999.0
        diff["diffs"].append({"sample": "事后注入（虚构）", "old_score": 0.0,
                              "new_score": 0.0, "delta": 0.0})
        self.assertEqual(record, snapshot, "记录与调用方 diff 数据隔离")


if __name__ == "__main__":
    unittest.main()
