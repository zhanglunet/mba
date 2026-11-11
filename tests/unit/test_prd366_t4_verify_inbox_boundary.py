# -*- coding: utf-8 -*-
"""PRD-366/T4 测试（trend #1645 的 T4 环节）：复核收件箱划界断言。

运行：uv run --with pytest python -m pytest tests/unit/test_prd366_t4_verify_inbox_boundary.py -q
（仓库根执行）

覆盖（T1 §0/§2，验收「划界断言通过」）：
  ① 模块隔离双向：verify_inbox/verify_inbox_gates 零导入 slides_gate
    （PRD-338 转换+双机判——闸门继续各拦各的零 import）/slides（转换
    内核）/judge_config_snapshot（PRD-282 配置可逆）/review_replay*
    （PRD-352 重放——快照同源模块隔离）+ 借鉴词零出现（plannotator/
    t3code 只借控制面形态）；slides_gate 零导入 verify_inbox*（仅代码
    标识符扫描，docstring 提及不算）；
  ② 零网络零子进程零分数写/撤回/转换词面 AST（R1）；
  ③ R1 零自动执行 AST+行为：approve 携带 closed 词表动作载荷
    （withdraw/rescore/reconvert）→ INBOX_AUTO_EXEC_ATTEMPT 显形拒绝；
    裁决返回值零分数写/撤回触发/转换重跑载荷键；
  ④ R2 只读汇聚行为钉值：collect 注入式四源齐收（low_confidence_score/
    withdraw_confirm/slides_gate_review/external_ref_review 词表封闭），
    零内核调用面；
  ⑤ R3 每项带证据钉值：复核项缺 reason（必填）→ INBOX_ITEM_INCOMPLETE
    显形拒绝入箱+fingerprint 与 PRD-352 同族（sha16 口径）；
  ⑥ R4：InboxLedger 方法面封闭（零删除方法）+reject 留痕钉值；
  ⑦ §2 划界钉值：slides_gate 面（校验码词表）源码 AST 符号不变——
    闸门拒绝归 338、收件箱零自动，互不越界。
零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_inbox import (  # noqa: E402
    InboxError,
    InboxLedger,
    ITEM_KINDS,
    collect,
)

NOW = "2026-11-11T09:00:00Z"
FP = "sha16:work42（占位）"
LOW = [{"source_ref": "review-replay-pack/v1（占位）",
        "reason": "低置信评分项（占位）"}]
WITHDRAW = [{"source_ref": "withdraw-motion#42（占位）",
             "reason": "撤回动议（占位）"}]
SLIDES = [{"check": "page_mapping", "reason": "SLIDES_PAGE_MISMATCH 复核（占位）"}]
EXTERNAL = [{"source_ref": "verify-gate/v1（占位）",
             "reason": "外链检出处置（占位）"}]

INBOX_MODULES = ["verify_inbox.py", "verify_inbox_gates.py"]


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
    def test_inbox_never_imports_gate_snapshot_or_replay(self):
        """收件箱面零触碰转换闸门/转换内核/评委包快照/重放（只读消费=
        注入式；闸门继续各拦各的）。"""
        for mod in INBOX_MODULES:
            imported = _imports_of(SCRIPTS / mod)
            for banned in ("slides_gate", "slides", "judge_config_snapshot",
                           "review_replay", "review_replay_gates"):
                self.assertNotIn(banned, imported, f"{mod} 导入 {banned}")
            names = _code_names(SCRIPTS / mod)
            for symbol in ("SLIDES_PAGE_MISMATCH", "take_snapshot",
                           "make_pack"):
                self.assertNotIn(symbol, names, f"{mod} 引用 {symbol}")

    def test_slides_gate_never_imports_inbox(self):
        """转换闸门面零导入收件箱（PRD-338 不感知本条——双向隔离）。"""
        imported = _imports_of(SCRIPTS / "slides_gate.py")
        for mod in ("verify_inbox", "verify_inbox_gates"):
            self.assertNotIn(mod, imported)

    def test_no_plannotator_t3code_symbols(self):
        """借鉴仓（plannotator Apache-2.0/t3code MIT 实测）零符号——只借
        控制面形态。"""
        for mod in INBOX_MODULES:
            blob = ast.dump(ast.parse(
                (SCRIPTS / mod).read_text("utf-8"))).lower()
            for word in ("plannotator", "t3code"):
                self.assertNotIn(word, blob, f"{mod} 出现 {word}")


class TestRedLinePins(unittest.TestCase):
    def test_r1_zero_action_ast_and_payload_rejected(self):
        """R1 AST+行为：收件箱两模块零网络零子进程；分数写/撤回/转换词面
        零出现；approve 携带 closed 词表载荷（withdraw/rescore）→
        INBOX_AUTO_EXEC_ATTEMPT 显形拒绝；裁决返回值零动作触发载荷键。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        for mod in INBOX_MODULES:
            imported = _imports_of(SCRIPTS / mod)
            self.assertFalse(imported & banned,
                             f"{mod} 导入 {imported & banned}")
            names = {n.lower() for n in _code_names(SCRIPTS / mod)}
            for word in ("do_withdraw", "rescore_now", "reconvert_now"):
                self.assertNotIn(word, names, f"{mod} 出现 {word}")
        items = collect(low_confidence=LOW, withdraw_confirms=WITHDRAW,
                        slides_gate_reviews=SLIDES,
                        external_ref_reviews=EXTERNAL, fingerprint=FP,
                        at=NOW)
        led = InboxLedger()
        led.add(items)
        iid = items[0]["item_id"]
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.approve(iid, by="复核人（占位）", at=NOW,
                        payload={"withdraw": True})
        out = led.approve(iid, by="复核人（占位）", at=NOW)
        for key in ("withdrawn", "rescored", "reconverted"):
            self.assertNotIn(key, out)

    def test_r2_collect_injected_four_sources(self):
        """R2 只读汇聚行为钉值：collect 注入式四源齐收（词表封闭），零
        内核调用面。"""
        items = collect(low_confidence=LOW, withdraw_confirms=WITHDRAW,
                        slides_gate_reviews=SLIDES,
                        external_ref_reviews=EXTERNAL, fingerprint=FP,
                        at=NOW)
        self.assertEqual([it["kind"] for it in items],
                         ["low_confidence_score", "withdraw_confirm",
                          "slides_gate_review", "external_ref_review"])
        self.assertEqual(set(ITEM_KINDS),
                         {"low_confidence_score", "withdraw_confirm",
                          "slides_gate_review", "external_ref_review"})

    def test_r3_incomplete_refused_and_fingerprint_family(self):
        """R3 行为钉值：复核项缺 reason（必填）→ INBOX_ITEM_INCOMPLETE
        显形拒绝入箱；fingerprint 与 PRD-352 重放包同族（sha16: 口径）。"""
        bad = dict(WITHDRAW[0])
        del bad["reason"]   # withdraw_confirms 的 reason 必填（无回退默认）
        with self.assertRaisesRegex(InboxError, "INBOX_ITEM_INCOMPLETE"):
            collect(withdraw_confirms=[bad], fingerprint=FP, at=NOW)
        items = collect(low_confidence=LOW, fingerprint=FP, at=NOW)
        self.assertEqual(items[0]["work_snapshot_digest"], FP)
        self.assertTrue(FP.startswith("sha16:"))

    def test_r4_ledger_surface_closed_and_reject_trace(self):
        """R4：InboxLedger 方法面封闭（零删除方法）+reject 留痕钉值。"""
        led = InboxLedger()
        methods = {n for n in dir(led) if not n.startswith("_")}
        self.assertLessEqual(methods, {"add", "approve", "reject", "view",
                                       "events"}, methods)
        items = collect(low_confidence=LOW, fingerprint=FP, at=NOW)
        led.add(items)
        iid = items[0]["item_id"]
        out = led.reject(iid, by="复核人（占位）", at=NOW,
                         reason="不复核（占位）")
        self.assertEqual(out["reject_reason"], "不复核（占位）")
        self.assertEqual(len(led.events), 2)   # add + rejected（只增）


class TestDemarcationPins(unittest.TestCase):
    def test_slides_gate_surface_unchanged(self):
        """§2 划界钉值：slides_gate 面（SLIDES_PAGE_MISMATCH/
        EXTERNAL_REF_FOUND 校验码词表）源码 AST 符号不变——闸门拒绝归
        338、收件箱零自动，互不越界。"""
        src = (SCRIPTS / "slides_gate.py").read_text(encoding="utf-8")
        for code in ("SLIDES_PAGE_MISMATCH", "EXTERNAL_REF_FOUND"):
            self.assertIn(code, src, f"校验码 {code} 漂移")
        self.assertNotIn("collect_inbox", src,
                         "闸门面不应出现收件箱符号")


if __name__ == "__main__":
    unittest.main()
