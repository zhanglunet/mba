# -*- coding: utf-8 -*-
"""PRD-380/T4 测试（trend #1884 的 T4 环节）：评审结论验证台划界断言。

运行：uv run --with pytest python -m pytest tests/unit/test_prd380_t4_review_verify_bench_boundary.py -q
（仓库根执行）

覆盖（T1 §0/§3，验收「划界断言通过」）：
  ① 模块隔离双向：review_verify_bench/gates 零导入 verify_inbox（366
    收件箱——下游零感知）/review_replay（352 重放——被消费零 import，
    经 recheck_fn 注入重跑）/judge_config_snapshot（282 配置可逆）/
    slides_gate（338 转换闸门）+ 借鉴词零出现（codex/security-audit，仅
    代码标识符扫描 docstring 提及不算）；
  ② 零外部仓内耦合钉值：bench 静态导入全标准库（gates 只 import 同链
    snapshots_fingerprint）；零 LLM 零网络零子进程零改分词面 AST（R2，
    不碰分数红线不变）；
  ③ R2 零新增评分 AST+行为：bench 零评分推导词面（make_pack/
    work_snapshots_digest 不在标识符面）——复算只经注入 fn；同一输入
    verify_score 两遍逐字节一致（确定性复现）；
  ④ R1 拦截行为钉值：UNVERIFIED 不进 verified 分组（不进复核收件箱）；
  ⑤ R3 八件套封闭钉值：缺件 BENCH_INCOMPLETE+verdict 词表封闭+快照指纹
    与 352 work_snapshots_digest 同族口径钉值；
  ⑥ R4：ReviewBenchLedger 公开方法面封闭+reverify BENCH_STALE；
  ⑦ §3 划界钉值：review_replay 面（make_pack/replay）与 verify_inbox 面
    （ITEM_KINDS 词表）符号不变——重算归重放、验证台零新增评分，互不
    越界。
零网络；全合成占位。
"""
import ast
import sys
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
from verify_inbox import ITEM_KINDS  # noqa: E402

NOW = "2026-11-13T09:00:00Z"
WORKS = [{"work_id": 42, "work_title": "作品42（占位）",
          "snapshot_digest": "sha16:w42（占位）"}]
REVIEW = {"review_id": "r-001", "work_id": 42, "kind": "low_confidence_score",
          "source_ref": "review-replay-pack/v1（占位）", "score": "88（原样）"}

BENCH_MODULES = ["review_verify_bench.py", "review_verify_bench_gates.py"]


def recheck_fn(work_snapshots):
    return [{"work_id": w["work_id"], "score": "88（原样）"}
            for w in work_snapshots]


def _imports_of(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return imported


def _code_names(path: Path) -> set:
    """仅代码标识符（ast.Name/Attribute）——docstring 提及不算引用。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


class TestModuleIsolation(unittest.TestCase):
    def test_bench_never_imports_inbox_replay_or_snapshot(self):
        """验证台面零触碰收件箱/重放/评委包快照/转换闸门（评分推导经注入
        重跑零 import；收件箱是下游零感知）。"""
        for mod in BENCH_MODULES:
            imported = _imports_of(REPO / "scripts" / mod)
            for banned in ("verify_inbox", "review_replay",
                           "review_replay_gates", "judge_config_snapshot",
                           "slides_gate"):
                self.assertNotIn(banned, imported, f"{mod} 导入 {banned}")
            names = _code_names(REPO / "scripts" / mod)
            for symbol in ("InboxLedger", "make_pack", "take_snapshot",
                           "SLIDES_PAGE_MISMATCH"):
                self.assertNotIn(symbol, names, f"{mod} 引用 {symbol}")

    def test_inbox_never_imports_bench(self):
        """收件箱面零导入验证台（366 不感知本条——双向隔离）。"""
        imported = _imports_of(REPO / "scripts" / "verify_inbox.py")
        for mod in ("review_verify_bench", "review_verify_bench_gates"):
            self.assertNotIn(mod, imported)

    def test_upstream_zero_symbols(self):
        """借鉴仓（codex-security Apache-2.0/security-audit-skill MIT 实测）
        零符号——只借控制面形态（仅代码标识符扫描）。"""
        for mod in BENCH_MODULES:
            names = {n.lower() for n in _code_names(REPO / "scripts" / mod)}
            for word in ("codex", "audit_skill"):
                self.assertNotIn(word, names, f"{mod} 出现 {word}")

    def test_zero_internal_coupling_and_redline_ast(self):
        """零外部仓内耦合钉值：bench 静态导入全标准库（gates 只 import 同链
        snapshots_fingerprint）；零 LLM 零网络零子进程零改分词面。"""
        imported = _imports_of(REPO / "scripts" / "review_verify_bench.py")
        self.assertLessEqual(imported - {"__future__", "copy", "hashlib",
                                         "json", "pathlib", "typing"},
                             set(), imported)
        gates_imported = _imports_of(
            REPO / "scripts" / "review_verify_bench_gates.py")
        self.assertLessEqual(gates_imported - {"__future__", "typing",
                                               "review_verify_bench"},
                             set())
        for mod in BENCH_MODULES:
            names = {n.lower() for n in _code_names(REPO / "scripts" / mod)}
            for word in ("set_score", "score_write", "update_score"):
                self.assertNotIn(word, names, f"{mod} 出现 {word}")


class TestRedLinePins(unittest.TestCase):
    def test_r2_no_new_score_ast_and_deterministic(self):
        """R2 AST+行为：bench 零评分推导词面（复算只经注入 fn）；同一输入
        verify_score 两遍逐字节一致（确定性复现）。"""
        for mod in BENCH_MODULES:
            names = {n.lower() for n in _code_names(REPO / "scripts" / mod)}
            for word in ("make_pack", "work_snapshots_digest", "replay"):
                self.assertNotIn(word, names, f"{mod} 出现 {word}")
        a = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        b = verify_score(REVIEW, WORKS, recheck_fn, at=NOW)
        self.assertEqual(a, b)

    def test_r1_unverified_blocked_at_outlet(self):
        """R1 拦截钉值：UNVERIFIED 不进 verified 分组（不进复核收件箱）。"""
        out = verify_scores([dict(REVIEW, score="1（改写）")], WORKS,
                            recheck_fn, at=NOW)
        self.assertEqual(out["verified"], [])
        self.assertEqual(out["unverified_count"], 1)

    def test_r3_eight_piece_closed_and_snapshots_fp_family(self):
        """R3 钉值：账目缺件 BENCH_INCOMPLETE；verdict 词表封闭；快照指纹
        与 352 work_snapshots_digest 同族口径（sha16: 前缀确定性）。"""
        led = ReviewBenchLedger(None)
        with self.assertRaisesRegex(ReviewBenchError, "BENCH_INCOMPLETE"):
            led.record({"schema": BENCH_SCHEMA}, at=NOW)
        self.assertEqual(set(VERDICTS), {"VERIFIED", "UNVERIFIED"})
        fp = snapshots_fingerprint(WORKS)
        self.assertTrue(fp.startswith("sha16:"))
        self.assertEqual(fp, snapshots_fingerprint(WORKS))

    def test_r4_ledger_surface_closed_and_stale(self):
        """R4：ReviewBenchLedger 公开方法面封闭（零删除方法）+reverify
        快照变更 BENCH_STALE 拒绝复用。"""
        led = ReviewBenchLedger(None)
        methods = {n for n in dir(led) if not n.startswith("_")}
        self.assertLessEqual(methods, {"record", "entries", "latest_for",
                                       "reverify"}, methods)
        led.record(verify_score(REVIEW, WORKS, recheck_fn, at=NOW), at=NOW)
        out = led.reverify("r-001", [{"work_id": 99}], recheck_fn, at=NOW)
        self.assertEqual(out["refused"], "BENCH_STALE")


class TestDemarcationPins(unittest.TestCase):
    def test_replay_and_inbox_surfaces_unchanged(self):
        """§3 划界钉值：review_replay 面（make_pack/replay）与 verify_inbox
        面（ITEM_KINDS 词表）符号不变——重算归重放、验证台零新增评分，
        互不越界。"""
        import review_replay as rr
        import verify_inbox as vi
        self.assertTrue(callable(rr.make_pack))
        self.assertTrue(callable(rr.replay))
        self.assertEqual(set(ITEM_KINDS),
                         {"low_confidence_score", "withdraw_confirm",
                          "slides_gate_review", "external_ref_review"})
        self.assertFalse(hasattr(rr, "verify_score"),
                         "重放面不应出现验证台符号")
        self.assertFalse(hasattr(vi, "reverify"),
                         "收件箱面不应出现复验符号")


if __name__ == "__main__":
    unittest.main()
