# -*- coding: utf-8 -*-
"""PRD-352/T4 测试（trend #1631 的 T4 环节）：评审评分重放划界断言。

运行：uv run --with pytest python -m pytest tests/unit/test_prd352_t4_review_replay_boundary.py -q
（仓库根执行）

覆盖（T1 §0/§2，验收「划界断言通过」）：
  ① 模块隔离双向：review_replay/gates 零导入 judge_config_snapshot
    （PRD-282 评委包配置可逆）/meta_review 族（PRD-177 结论形态）+
    借鉴词零出现（AiSOC/OpenBot MIT 只借形态）；judge_config_snapshot
    零导入 review_replay*；
  ② 唯一耦合钉值：review_replay 静态导入全标准库——评分推导经 score_fn
    注入（零 import 耦合）；零网络零子进程零改分词面 AST（R2）；
  ③ R1 行为钉值：评审缺 work_id/score/why 任一或空 reviews →
    refused=PACK_INCOMPLETE；
  ④ R2 零改分行为钉值：score_fn 收到深拷贝（work_snapshots 零污染）+
    重放返回值零分数写载荷键（只比对）；
  ⑤ R3 零静默钉值：mismatch 键面封闭 {schema,refused,verdict,evidence,
    rerun_count}——零回退新评分载荷键；
  ⑥ R4：ReplayLedger 方法面封闭（零删除方法）；
  ⑦ §2 划界钉值：judge_config_snapshot 快照面（judge-config-snapshot-v1 +
    FingerprintMismatchError + 事件词表）符号不变——PRD-282 管配置可逆，
    本条管评分可重算，互不越界。
零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from judge_config_snapshot import (  # noqa: E402
    FingerprintMismatchError,
    SNAPSHOT_SCHEMA,
)
from review_replay import ReplayLedger, make_pack, replay  # noqa: E402

WORKS = [{"work_id": 42, "work_title": "作品42（占位）",
          "snapshot_digest": "sha16:w42（占位）"}]
REVIEWS = [{"work_id": 42, "score": "88（原样）", "why": "论证扎实（占位）"}]

REPLAY_MODULES = ["review_replay.py", "review_replay_gates.py"]


def score_fn(work_snapshots):
    return [dict(r) for r in REVIEWS]


def _imports_of(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return imported


class TestModuleIsolation(unittest.TestCase):
    def test_replay_never_imports_snapshot_or_meta_review(self):
        """重放面零触碰评委包配置快照/meta review 族（评分可重算不感知
        配置可逆与结论形态）。"""
        for mod in REPLAY_MODULES:
            imported = _imports_of(SCRIPTS / mod)
            for banned in ("judge_config_snapshot", "meta_review",
                           "ci_meta_review", "e2e_meta_review"):
                self.assertNotIn(banned, imported, f"{mod} 导入 {banned}")
            blob = ast.dump(ast.parse(
                (SCRIPTS / mod).read_text(encoding="utf-8")))
            for symbol in ("FingerprintMismatchError", "take_snapshot",
                           "rolled_back"):
                self.assertNotIn(symbol, blob, f"{mod} 引用 {symbol}")

    def test_snapshot_never_imports_replay(self):
        """快照面零导入重放（PRD-282 不感知本条——双向隔离）。"""
        imported = _imports_of(SCRIPTS / "judge_config_snapshot.py")
        for mod in ("review_replay", "review_replay_gates"):
            self.assertNotIn(mod, imported)

    def test_no_aisoc_openbot_symbols(self):
        """借鉴仓（AiSOC/OpenBot，MIT 实测）零符号——只借形态。"""
        for mod in REPLAY_MODULES:
            blob = ast.dump(ast.parse(
                (SCRIPTS / mod).read_text("utf-8"))).lower()
            for word in ("aisoc", "openbot"):
                self.assertNotIn(word, blob, f"{mod} 出现 {word}")

    def test_only_coupling_is_injected_score_fn(self):
        """§2 钉值：review_replay 静态导入全标准库——评分推导经 score_fn
        注入（零 import 耦合）。"""
        imported = _imports_of(SCRIPTS / "review_replay.py")
        self.assertLessEqual(imported,
                             {"__future__", "copy", "hashlib", "json",
                              "typing"})
        src = (SCRIPTS / "review_replay.py").read_text("utf-8")
        self.assertIn("score_fn", src)


class TestRedLinePins(unittest.TestCase):
    def test_r1_pack_incomplete_refusal_pinned(self):
        """R1 行为钉值：评审缺 score/why 任一或空 reviews →
        refused=PACK_INCOMPLETE。"""
        bad = dict(REVIEWS[0])
        del bad["score"]
        out = make_pack([bad], WORKS, judgepack_version="v1")
        self.assertEqual(out["refused"], "PACK_INCOMPLETE")
        out2 = make_pack([], WORKS, judgepack_version="v1")
        self.assertEqual(out2["refused"], "PACK_INCOMPLETE")

    def test_r2_zero_score_write_ast_and_deepcopy(self):
        """R2 AST+行为：零网络零子进程零改分词面；score_fn 收到深拷贝
        work_snapshots 零污染；重放返回值零分数写载荷键（只比对）。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess",
                  "judge_config_snapshot"}
        for mod in REPLAY_MODULES:
            imported = _imports_of(SCRIPTS / mod)
            self.assertFalse(imported & banned,
                             f"{mod} 导入 {imported & banned}")
            src = (SCRIPTS / mod).read_text(encoding="utf-8").lower()
            for word in ("set_score", "score_write", "update_score"):
                self.assertNotIn(word, src, f"{mod} 出现 {word}")
        pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")

        def mutating_fn(snapshots):
            snapshots[0]["work_title"] = "就地改写（占位）"
            return [dict(r) for r in REVIEWS]

        out = replay(pack, WORKS, mutating_fn, judgepack_version="v1")
        self.assertEqual(WORKS[0]["work_title"], "作品42（占位）",
                         "调用方快照零污染")
        for key in ("written_scores", "score_delta"):
            self.assertNotIn(key, out)

    def test_r3_mismatch_returns_closed_keys_no_new_score(self):
        """R3 零静默钉值：mismatch 键面封闭——零回退新评分载荷键。"""
        pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        out = replay(pack, WORKS,
                     lambda s: [dict(REVIEWS[0], score="1（改写）")],
                     judgepack_version="v1")
        self.assertEqual(out["verdict"], "REPLAY_MISMATCH")
        self.assertEqual(out["evidence"]["first_divergence_index"], 0)
        self.assertEqual(set(out), {"schema", "refused", "verdict",
                                    "evidence", "rerun_count"})

    def test_r4_ledger_method_surface_closed(self):
        """R4：ReplayLedger 方法面封闭——零删除方法。"""
        led = ReplayLedger()
        methods = {n for n in dir(led) if not n.startswith("_")}
        self.assertLessEqual(methods, {"record", "entries"}, methods)
        pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        led.record(pack, {"verdict": "REPLAY_OK", "evidence": None},
                   at="2026-11-11T09:00:00Z")
        self.assertEqual(len(led.entries), 1)


class TestDemarcationPins(unittest.TestCase):
    def test_judge_config_snapshot_surface_unchanged(self):
        """§2 划界钉值：judge_config_snapshot 快照面（judge-config-snapshot-v1
        + FingerprintMismatchError + 事件词表）符号不变——PRD-282 管配置
        可逆，本条管评分可重算，互不越界。"""
        import judge_config_snapshot as jcs
        self.assertEqual(SNAPSHOT_SCHEMA, "judge-config-snapshot-v1")
        for name in ("FingerprintMismatchError", "EVENT_CONFIG_CHANGED",
                     "EVENT_ROLLED_BACK", "EVENT_RECALC_DONE"):
            self.assertTrue(hasattr(jcs, name), name)
        self.assertFalse(hasattr(jcs, "replay"), "快照面不应出现重放符号")


if __name__ == "__main__":
    unittest.main()
