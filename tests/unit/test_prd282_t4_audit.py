# -*- coding: utf-8 -*-
"""PRD-282/T4 自测（trend #1414）：口径变更审计断言——三类记录可审计导出。

运行：.venv/bin/python -m pytest tests/unit/test_prd282_t4_audit.py -q

覆盖：
  三类事件（config_changed / rolled_back / recalc_done）全链产出且全可导出
  JSONL 复算记录与 events 交叉对账（指纹一致：记录的新旧指纹都能在事件账本
    里找到出处，且逐条对应到具体事件）
  事件字段齐全（每条有 at；带指纹的事件指纹为 16 位十六进制且非空）
  全链演练（change → recalc → rollback）三类齐、时序正确、还原口径=改前口径
  确定性（同输入全链重放：事件导出逐字段全等、JSONL 落档字节全等）
  机读可解析（events + recalcs 整体 JSON 往返全等，逐行可 json.loads）
  导出独立性 + append-only（导出是深拷贝，外部改写不伤账本；续记按序读回）

虚构纪律：评委包口径、样例品牌、分数全虚构；diff 由 T2 recalc_diff 以注入的
假 score_fn 产出（不真调 LLM）；零网络；不含真实主机名、IP、账号、密钥。
"""
import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from judge_config_snapshot import (  # noqa: E402
    EVENT_CONFIG_CHANGED,
    EVENT_RECALC_DONE,
    EVENT_ROLLED_BACK,
    config_fingerprint,
    current_config,
    export_events,
    recalc_diff,
    reset_state,
    restore,
    take_snapshot,
)
from recalc_record import (  # noqa: E402
    RECALC_RECORD_SCHEMA,
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
# 全链固定时刻（确定性：所有时刻显式注入，不掺当前时钟）
CHANGE_AT_A = "2026-10-29T09:00:00+08:00"
CHANGE_AT_B = "2026-10-29T10:00:00+08:00"
RECALC_AT = "2026-10-29T11:00:00+08:00"
ROLLBACK_AT = "2026-10-29T12:00:00+08:00"

FP_HEX = re.compile(r"^[0-9a-f]{16}$")


def _run_full_chain(audit_path):
    """全链演练：变更（留两版快照）→ 复算（JSONL 落档）→ 回滚（回 v1）。

    所有时刻显式注入；返回链上全部产物供各断言取用。
    """
    reset_state()
    old_cfg, new_cfg = _old_config(), _new_config()
    snap_old = take_snapshot(old_cfg, CHANGE_AT_A)   # 变更挂点 1：v1 留快照
    snap_new = take_snapshot(new_cfg, CHANGE_AT_B)   # 变更挂点 2：v2 成为现行
    diff = recalc_diff(old_cfg, new_cfg, SAMPLES, _fake_score_fn, at=RECALC_AT)
    record = write_recalc_record(diff, config_fingerprint(old_cfg),
                                 config_fingerprint(new_cfg), RECALC_AT)
    append_recalc(record, audit_path)                # 复算记录 JSONL 落档
    restored = restore(snap_old, at=ROLLBACK_AT)     # 一键回滚到 v1
    return {
        "snap_old": snap_old, "snap_new": snap_new, "diff": diff,
        "record": record, "restored": restored,
        "old_fp": config_fingerprint(old_cfg),
        "new_fp": config_fingerprint(new_cfg),
    }


def _events_of_type(events, event_type):
    return [e for e in events if e["event"] == event_type]


def _reconcile(events, recalcs):
    """交叉对账：每条复算记录的新旧指纹都必须在事件账本里有出处。

    返回不一致清单（空 = 对账通过）；出处集 = config_changed.fingerprint ∪
    rolled_back.to_fingerprint（recalc_done 事件本身不带指纹，指纹出处走
    JSONL 记录，与账本事件互为对账两翼）。
    """
    ledger_fps = set()
    for e in events:
        for key in ("fingerprint", "to_fingerprint"):
            if isinstance(e.get(key), str):
                ledger_fps.add(e[key])
    mismatches = []
    for i, rec in enumerate(recalcs):
        for side in ("old_fingerprint", "new_fingerprint"):
            fp = rec.get(side)
            if fp not in ledger_fps:
                mismatches.append("recalcs[%d].%s=%r 在事件账本中无出处" % (i, side, fp))
    return mismatches


class TestAuditExport(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.audit_path = str(Path(self._tmp.name) / "audit.jsonl")

    # T4-1 三类事件全可导出
    def test_01_three_event_types_all_exportable(self):
        _run_full_chain(self.audit_path)
        events = export_events()
        kinds = [e["event"] for e in events]
        for event_type in (EVENT_CONFIG_CHANGED, EVENT_ROLLED_BACK, EVENT_RECALC_DONE):
            self.assertIn(event_type, kinds, "三类事件缺一不可导出")
        self.assertEqual(
            kinds,
            [EVENT_CONFIG_CHANGED, EVENT_CONFIG_CHANGED,
             EVENT_RECALC_DONE, EVENT_ROLLED_BACK],
            "导出顺序 = 全链发生顺序（append-only 只增不减）",
        )
        self.assertEqual(len(events), len(set(id(e) for e in events)))
        # 导出可序列化（可审计导出的最低门槛在 T4-6 机读专项里加严）

    # T4-2 JSONL 复算记录与 events 交叉对账（指纹一致）
    def test_02_jsonl_recalc_cross_reconcile_fingerprints(self):
        chain = _run_full_chain(self.audit_path)
        events = export_events()
        recalcs = read_recalcs(self.audit_path)
        self.assertEqual(len(recalcs), 1, "全链恰落一条复算记录")
        self.assertEqual(recalcs[0]["schema"], RECALC_RECORD_SCHEMA)

        # 通用对账：记录指纹 ⊆ 事件账本指纹出处集
        self.assertEqual(_reconcile(events, recalcs), [], "交叉对账零缺口")

        # 逐条对账：指纹一一对应到具体事件
        changed = _events_of_type(events, EVENT_CONFIG_CHANGED)
        rolled = _events_of_type(events, EVENT_ROLLED_BACK)
        self.assertEqual(len(changed), 2)
        self.assertEqual(len(rolled), 1)
        self.assertEqual(recalcs[0]["old_fingerprint"],
                         changed[0]["fingerprint"],
                         "记录旧口径指纹 = 第一次变更事件的指纹（v1）")
        self.assertEqual(recalcs[0]["new_fingerprint"],
                         changed[1]["fingerprint"],
                         "记录新口径指纹 = 第二次变更事件的指纹（v2）")
        self.assertEqual(recalcs[0]["old_fingerprint"],
                         chain["old_fp"])
        self.assertEqual(recalcs[0]["new_fingerprint"], chain["new_fp"])
        self.assertEqual(rolled[0]["to_fingerprint"],
                         recalcs[0]["old_fingerprint"],
                         "回滚事件指纹 = 复算记录旧口径指纹（回到 v1）")
        # 记录与事件两翼的时刻同源可查（同一 RECALC_AT 互相引证）
        self.assertEqual(recalcs[0]["at"], RECALC_AT)
        self.assertEqual(_events_of_type(events, EVENT_RECALC_DONE)[0]["at"],
                         RECALC_AT)

    # T4-3 事件字段齐全（at / fingerprint）
    def test_03_event_fields_complete(self):
        _run_full_chain(self.audit_path)
        events = export_events()
        self.assertTrue(events)
        for e in events:
            self.assertIsInstance(e.get("at"), str)
            self.assertTrue(e["at"], "每条事件都带非空 at")
            for key, value in e.items():
                self.assertIsNotNone(value, "事件字段不留空：%s/%s" % (e["event"], key))
        for e in _events_of_type(events, EVENT_CONFIG_CHANGED):
            self.assertRegex(e["fingerprint"], FP_HEX, "变更事件指纹 16 位十六进制")
            self.assertEqual(e["schema"], "judge-config-snapshot-v1")
        for e in _events_of_type(events, EVENT_ROLLED_BACK):
            self.assertRegex(e["to_fingerprint"], FP_HEX, "回滚事件指纹 16 位十六进制")
            self.assertEqual(e["snapshot_taken_at"], CHANGE_AT_A,
                             "回滚事件可追到快照挂点时刻")
        for e in _events_of_type(events, EVENT_RECALC_DONE):
            self.assertEqual(e["n"], len(SAMPLES))
            self.assertIsInstance(e["max_abs_delta"], float)
        # JSONL 记录同样字段齐全
        for rec in read_recalcs(self.audit_path):
            for key in ("schema", "old_fingerprint", "new_fingerprint",
                        "n", "max_abs_delta", "diffs", "at"):
                self.assertIn(key, rec, "记录缺字段：%s" % key)
            self.assertRegex(rec["old_fingerprint"], FP_HEX)
            self.assertRegex(rec["new_fingerprint"], FP_HEX)
            self.assertTrue(rec["at"])

    # T4-4 全链演练三类齐（change → recalc → rollback）
    def test_04_full_chain_rehearsal_all_three_types(self):
        chain = _run_full_chain(self.audit_path)
        events = export_events()
        kinds = [e["event"] for e in events]
        self.assertEqual(sorted(set(kinds)),
                         sorted({EVENT_CONFIG_CHANGED, EVENT_ROLLED_BACK,
                                 EVENT_RECALC_DONE}),
                         "全链演练后三类记录齐")
        self.assertLess(kinds.index(EVENT_RECALC_DONE),
                        kinds.index(EVENT_ROLLED_BACK),
                        "时序：复算先于回滚（对账链可读）")
        # 还原口径 = 改前口径（v1），指纹闭环
        self.assertEqual(current_config(), _old_config())
        self.assertEqual(config_fingerprint(chain["restored"]), chain["old_fp"])
        # 回滚可再回滚的语义不被 T4 破坏：单槽快照仍在
        self.assertIsNotNone(chain["snap_old"])
        # 复算记录落档且可读回
        self.assertEqual(len(read_recalcs(self.audit_path)), 1)

    # T4-5 确定性：同输入全链重放逐字节全等
    def test_05_deterministic(self):
        _run_full_chain(self.audit_path)
        events_first = export_events()
        bytes_first = Path(self.audit_path).read_bytes()

        other_path = str(Path(self._tmp.name) / "audit-replay.jsonl")
        _run_full_chain(other_path)
        events_second = export_events()
        bytes_second = Path(other_path).read_bytes()

        self.assertEqual(events_first, events_second,
                         "同输入重放：事件导出逐字段全等")
        self.assertEqual(bytes_first, bytes_second,
                         "同输入重放：JSONL 落档字节全等")

    # T4-6 机读可解析
    def test_06_machine_readable(self):
        _run_full_chain(self.audit_path)
        events = export_events()
        recalcs = read_recalcs(self.audit_path)
        # 审计导出整体（两翼合包）JSON 往返全等
        bundle = {"schema": "prd-282-audit-export-v1",
                  "events": events, "recalcs": recalcs}
        text = json.dumps(bundle, ensure_ascii=False, sort_keys=True)
        self.assertEqual(json.loads(text), bundle)
        # 逐事件、逐行独立可解析
        for e in events:
            self.assertEqual(json.loads(json.dumps(e, ensure_ascii=False)), e)
        for line in Path(self.audit_path).read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)   # 任一行非合法 JSON 即此处抛错
            self.assertEqual(rec["schema"], RECALC_RECORD_SCHEMA)
        # 指纹字段机读形态统一（16 位十六进制字符串）
        for fp in (bundle["recalcs"][0]["old_fingerprint"],
                   bundle["recalcs"][0]["new_fingerprint"]):
            self.assertRegex(fp, FP_HEX)

    # T4-7 导出独立性 + append-only 续记按序
    def test_07_export_isolation_and_append_only(self):
        _run_full_chain(self.audit_path)
        snapshot_export = copy.deepcopy(export_events())
        exported = export_events()
        exported[0]["event"] = "tampered"          # 外部改写导出件
        exported.pop()
        self.assertEqual(export_events(), snapshot_export,
                         "导出是深拷贝：改写导出件不伤账本")
        recalcs_exported = read_recalcs(self.audit_path)
        recalcs_exported[0]["n"] = -1              # 同理：记录导出件可改不伤档
        self.assertEqual(read_recalcs(self.audit_path)[0]["n"], len(SAMPLES))

        # append-only 续记：再复算一次并落档，读回按序、只增不减
        diff2 = recalc_diff(_new_config(), _old_config(), SAMPLES[:1],
                            _fake_score_fn, at="2026-10-29T13:00:00+08:00")
        append_recalc(write_recalc_record(
            diff2, config_fingerprint(_new_config()),
            config_fingerprint(_old_config()), "2026-10-29T13:00:00+08:00"),
            self.audit_path)
        records = read_recalcs(self.audit_path)
        self.assertEqual(len(records), 2, "续记只增不减")
        self.assertEqual([r["at"] for r in records],
                         [RECALC_AT, "2026-10-29T13:00:00+08:00"],
                         "按 append 顺序读回")
        self.assertEqual(_reconcile(export_events(), records), [],
                         "续记后交叉对账仍零缺口")


if __name__ == "__main__":
    unittest.main()
