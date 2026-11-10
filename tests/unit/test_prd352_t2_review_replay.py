# -*- coding: utf-8 -*-
"""PRD-352/T2 测试（trend #1631 的 T2 环节）：评审结论重放包。

运行：.venv/bin/python -m pytest tests/unit/test_prd352_t2_review_replay.py -q

覆盖（T1 §3.1/§3.2/§4 + R1–R4）：三件套构建（评审缺字段/空入参
PACK_INCOMPLETE）；重放三步（同快照同评委包 REPLAY_OK/作品快照或评委包版本
漂移 INPUT_DRIFT 拒绝防新快照冒充当时/决策漂移 MISMATCH 首分歧条显形——含
分数漂移路径）；R2 零改分（AST 零评分写导入+重放只比对）；R4 账本
append-only；与 PRD-338 slides 串联（评审批次结论记录作快照来源）。零网络；
全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from review_replay import (  # noqa: E402
    ERROR_CODES,
    ReplayLedger,
    make_pack,
    replay,
)

NOW = "2026-11-11T09:00:00Z"
WORKS = [{"work_id": 42, "work_title": "作品42（占位）",
          "snapshot_digest": "sha16:w42（占位）"}]
REVIEWS = [{"work_id": 42, "score": "88（原样）", "why": "论证扎实（占位）"}]


def score_fn(work_snapshots):
    return [dict(r) for r in REVIEWS]


class TestPackBuild(unittest.TestCase):
    def test_pack_three_parts_complete(self):
        pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        self.assertEqual(pack["schema"], "review-replay-pack/v1")
        fp = pack["input_fingerprint"]
        self.assertTrue(fp["work_snapshots_digest"].startswith("sha16:"))
        self.assertEqual(fp["judgepack_version"], "v1")
        self.assertEqual(pack["output"]["scores"], ["88（原样）"])   # R4 原样

    def test_incomplete_refused(self):
        bad = dict(REVIEWS[0])
        del bad["why"]
        self.assertEqual(make_pack([bad], WORKS,
                                   judgepack_version="v1")["refused"],
                         "PACK_INCOMPLETE")
        self.assertEqual(make_pack([], WORKS,
                                   judgepack_version="v1")["refused"],
                         "PACK_INCOMPLETE")
        self.assertEqual(make_pack(REVIEWS, WORKS,
                                   judgepack_version="")["refused"],
                         "PACK_INCOMPLETE")


class TestReplay(unittest.TestCase):
    def _pack(self):
        return make_pack(REVIEWS, WORKS, judgepack_version="v1")

    def test_same_snapshots_replay_ok(self):
        out = replay(self._pack(), WORKS, score_fn, judgepack_version="v1")
        self.assertEqual(out["verdict"], "REPLAY_OK")

    def test_input_drift_refused(self):
        """指纹复核：作品/评委包漂移 → INPUT_DRIFT 拒绝（防新快照冒充）。"""
        mutated = [dict(WORKS[0], snapshot_digest="sha16:changed（占位）")]
        out = replay(self._pack(), mutated, score_fn, judgepack_version="v1")
        self.assertEqual(out["refused"], "REPLAY_INPUT_DRIFT")
        out2 = replay(self._pack(), WORKS, score_fn, judgepack_version="v2")
        self.assertEqual(out2["refused"], "REPLAY_INPUT_DRIFT")

    def test_mismatch_first_divergence_visible(self):
        """R3：评分漂移 → MISMATCH 首分歧条显形，零静默换新评分。"""
        drift_fn = lambda ws: [dict(REVIEWS[0], score="92（漂移）")]
        out = replay(self._pack(), WORKS, drift_fn, judgepack_version="v1")
        self.assertEqual(out["verdict"], "REPLAY_MISMATCH")
        self.assertEqual(out["evidence"]["first_divergence_index"], 0)
        self.assertEqual(out["evidence"]["got"]["score"], "92（漂移）")
        out2 = replay(self._pack(), WORKS, lambda ws: [],
                      judgepack_version="v1")
        self.assertEqual(out2["verdict"], "REPLAY_MISMATCH")
        self.assertEqual(out2["evidence"]["got"], None)

    def test_incomplete_pack_refused(self):
        out = replay({"schema": "review-replay-pack/v1"}, WORKS, score_fn,
                     judgepack_version="v1")
        self.assertEqual(out["refused"], "PACK_INCOMPLETE")


class TestLedgerAndRedline(unittest.TestCase):
    def test_ledger_append_only(self):
        led = ReplayLedger()
        pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        led.record(pack, {"verdict": "REPLAY_OK", "evidence": None}, at=NOW)
        before = [dict(x) for x in led.entries]
        led.record(pack, {"refused": "REPLAY_INPUT_DRIFT", "evidence": None},
                   at=NOW)
        self.assertEqual(led.entries[0], before[0])
        self.assertEqual(len(led.entries), 2)

    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"REPLAY_INPUT_DRIFT", "REPLAY_MISMATCH",
                          "PACK_INCOMPLETE"})

    def test_ast_zero_score_write_zero_network(self):
        """R2 AST：零改分——零评分写导入零网络零子进程。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess",
                  "score_write", "scoring"}
        tree = ast.parse((REPO / "scripts" / "review_replay.py").read_text(
            encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                self.assertNotIn(mod, banned)


if __name__ == "__main__":
    unittest.main()
