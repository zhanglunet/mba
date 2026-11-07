# -*- coding: utf-8 -*-
"""PRD-310/T2 评审结论重放包·replay-pack/v1 最小实现测试（trend #1562）。

覆盖（T1 设计 §1/§3/§4）：schema 组装与字段纪律（缺字段报错不猜、错误码封闭）、
fpv1 指纹稳定性、append-only 账本、verify_panel_replay 二值结论（同登记册同选择
重放必 MATCH / 换登记册或换作品快照显形 REPLAY_INPUT_MISMATCH / 重放面零写盘
不改评审记录）、与 assemble_panel 编排出口的端到端装订（真实登记册全量组装）。
评分属 LLM 面不入重放面（口径走快照红线，模块 docstring 诚实声明）。
全部占位合成零网络。
"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from judge_orchestration import assemble_panel, load_registry  # noqa: E402
import replay_pack as rp  # noqa: E402

WORK_SNAPSHOT = {"work_id": "synthetic-001", "title": "作品（占位）",
                 "body": "这是一份占位作品正文，用于组装与重放测试。"}


class SchemaAssemblyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()
        cls.assembly = assemble_panel(cls.registry, [], consumer=True)
        cls.pack = rp.pack_from_panel_assembly(
            cls.registry, WORK_SNAPSHOT, [], True, cls.assembly)

    def test_pack_shape_and_registry_fingerprint(self):
        self.assertEqual(self.pack["schema_version"], "replay-pack/v1")
        self.assertEqual(self.pack["action"], "panel_assembly")
        self.assertEqual(self.pack["input"]["inputs"]["work_snapshot_fingerprint"],
                         rp.fingerprint(WORK_SNAPSHOT))
        self.assertEqual(self.pack["input"]["inputs"]["registry_fingerprint"],
                         rp.fingerprint(self.registry))
        self.assertEqual(self.pack["decision"]["rules_version"],
                         str(self.registry.get("schema") or "mba-judge-registry/v1"))

    def test_output_view_records_full_panel(self):
        view = rp.output_view_of_panel_assembly(self.assembly)
        self.assertEqual(view["result"]["panel_order"],
                         self.assembly["panel_order"])
        self.assertEqual(len(view["result"]["judge_slugs"]),
                         self.assembly["totals"]["judges"])
        self.assertEqual(view["key_numbers"]["judges"],
                         self.assembly["totals"]["judges"])

    def test_fingerprint_stability_and_sensitivity(self):
        p1 = rp.pack_from_panel_assembly(self.registry, WORK_SNAPSHOT, [], True,
                                         self.assembly)
        p2 = rp.pack_from_panel_assembly(self.registry, WORK_SNAPSHOT, [], True,
                                         self.assembly)
        self.assertEqual(p1["input"]["snapshot_fingerprint"],
                         p2["input"]["snapshot_fingerprint"])
        drifted_work = dict(WORK_SNAPSHOT, body="被改过的作品正文。")
        p3 = rp.pack_from_panel_assembly(self.registry, drifted_work, [], True,
                                         self.assembly)
        self.assertNotEqual(p3["input"]["inputs"]["work_snapshot_fingerprint"],
                            p1["input"]["inputs"]["work_snapshot_fingerprint"])


class FieldDisciplineTests(unittest.TestCase):

    def test_closed_error_vocabulary(self):
        good = dict(action="panel_assembly", inputs={"k": "v"},
                    decision={"chosen": "c", "why": "w", "rules_version": "v1"},
                    output={"result": "r", "key_numbers": {"n": 1}},
                    replay_command="rerun: x")
        with self.assertRaises(rp.ReplayPackError) as ei:
            rp.build_replay_pack(**{**good, "inputs": {}})
        self.assertEqual(ei.exception.code, "REPLAY_INPUT_REQUIRED")
        for drop in ("chosen", "why", "rules_version"):
            decision = {k: v for k, v in good["decision"].items() if k != drop}
            with self.assertRaises(rp.ReplayPackError) as ed:
                rp.build_replay_pack(**{**good, "decision": decision})
            self.assertEqual(ed.exception.code, "REPLAY_DECISION_FIELDS_REQUIRED")
        with self.assertRaises(ValueError):
            rp.ReplayPackError("NOT_IN_TABLE", "x")
        self.assertEqual(len(set(rp.ERROR_CODES)), len(rp.ERROR_CODES))


class LedgerTests(unittest.TestCase):

    def test_append_only_and_cold_start(self):
        pack = rp.pack_from_panel_assembly(load_registry(), WORK_SNAPSHOT, [],
                                           True, assemble_panel(load_registry(),
                                                                [], consumer=True))
        with tempfile.TemporaryDirectory() as tmp:
            ledger = rp.ReplayLedger(Path(tmp) / "ledger.jsonl")
            self.assertEqual(ledger.read_all(), [])
            ledger.append(pack)
            before = ledger.bytes_now()
            ledger.append(pack)
            packs = ledger.read_all()
            self.assertEqual(len(packs), 2)
            self.assertEqual(packs[0], pack)
            self.assertGreater(len(ledger.bytes_now()), len(before))


class VerifyReplayTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()
        cls.assembly = assemble_panel(cls.registry, [], consumer=True)
        cls.pack = rp.pack_from_panel_assembly(
            cls.registry, WORK_SNAPSHOT, [], True, cls.assembly)

    def test_same_inputs_replay_to_match_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = rp.ReplayLedger(Path(tmp) / "ledger.jsonl")
            ledger.append(self.pack)
            before = ledger.bytes_now()
            result = rp.verify_panel_replay(self.pack, self.registry,
                                            WORK_SNAPSHOT, assemble_panel)
            self.assertEqual(result["status"], rp.REPLAY_MATCH)
            self.assertIsNone(result["evidence"])
            self.assertEqual(ledger.bytes_now(), before)  # 重放面只读

    def test_drifted_registry_is_input_mismatch(self):
        drifted = copy.deepcopy(self.registry)
        if drifted.get("packs"):
            drifted["packs"][0]["name"] = drifted["packs"][0]["name"] + "-drifted"
        result = rp.verify_panel_replay(self.pack, drifted, WORK_SNAPSHOT,
                                        assemble_panel)
        self.assertEqual(result["status"], rp.REPLAY_MISMATCH)
        self.assertEqual(result["evidence"]["reason"], "REPLAY_INPUT_MISMATCH")
        self.assertEqual(result["evidence"]["field"], "registry_fingerprint")

    def test_drifted_work_snapshot_is_input_mismatch(self):
        drifted = dict(WORK_SNAPSHOT, body="另一份作品。")
        result = rp.verify_panel_replay(self.pack, self.registry, drifted,
                                        assemble_panel)
        self.assertEqual(result["status"], rp.REPLAY_MISMATCH)
        self.assertEqual(result["evidence"]["field"], "work_snapshot_fingerprint")

    def test_ledger_roundtrip_replay_still_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = rp.ReplayLedger(Path(tmp) / "ledger.jsonl")
            ledger.append(self.pack)
            reloaded = rp.ReplayLedger(Path(tmp) / "ledger.jsonl").read_all()[0]
            result = rp.verify_panel_replay(reloaded, self.registry,
                                            WORK_SNAPSHOT, assemble_panel)
            self.assertEqual(result["status"], rp.REPLAY_MATCH)


if __name__ == "__main__":
    unittest.main()
