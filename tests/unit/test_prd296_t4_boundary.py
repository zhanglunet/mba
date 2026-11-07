# -*- coding: utf-8 -*-
"""PRD-296/T4 测试（trend #1484）：与 PRD-233/262/282 划界断言——评审寻址。

运行：.venv/bin/python -m pytest tests/unit/test_prd296_t4_boundary.py -q

覆盖（T1 设计 §2，验收「划界断言通过」）：
  ① 模块隔离双向（work_ref/ref_gates 零导入安检/快照/编排面；既有 judge
    面模块零导入引用面——存在者扫描）；② PRD-233 行为不变（登记册条目
    deepcopy 钉值零改动）；③ PRD-282 行为不变（ref_gates 零 config_snapshot
    导入 AST——口径变更仍走快照）；④ 本条是评审寻址（零安检/零口径修改
    调用，撤回作品寻址显形不拦截）。
零网络；全合成占位。
"""
import ast
import copy
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from work_ref import resolve  # noqa: E402

PACKS = [{"name": "brand-pack（占位）", "members": ["评委A（占位）"]}]
WORKS = [{"work_id": 42, "status": "在库（占位）"},
         {"work_id": 43, "status": "已撤回（占位）"}]


class 模块隔离Tests(unittest.TestCase):
    def test_ref_side_never_imports_gate_snapshot_orchestration(self):
        banned = {"config_snapshot", "judge_pack_gate", "judge_orchestration",
                  "judge_pack_whitelist"}
        for name in ("work_ref.py", "ref_gates.py"):
            tree = ast.parse((REPO / "scripts" / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module.split(".")[0]]
                for mod in mods:
                    self.assertNotIn(mod, banned, f"{name} 导入了 {mod}")

    def test_existing_judge_modules_never_import_ref(self):
        engine_files = [p for p in ("judge_registry.py", "judge_orchestration.py",
                                    "config_snapshot.py", "judge_pack_gate.py")
                        if (REPO / "scripts" / p).is_file()]
        for name in engine_files:
            src = (REPO / "scripts" / name).read_text(encoding="utf-8")
            for token in ("work_ref", "ref_gates"):
                self.assertNotIn(token, src, f"{name} 导入了引用面 {token}")
        self.assertTrue(engine_files)


class PRD233行为不变Tests(unittest.TestCase):
    def test_registry_untouched_by_resolve(self):
        """登记册 deepcopy 钉值：引用解析并入零扰动。"""
        before = copy.deepcopy(PACKS)
        resolve("@brand-pack（占位）", PACKS, WORKS)
        self.assertEqual(PACKS, before)


class PRD282行为不变Tests(unittest.TestCase):
    def test_ref_gates_no_snapshot_import(self):
        """口径变更走快照：引用账本零快照写导入（AST，T3 断言复核）。"""
        tree = ast.parse((REPO / "scripts" / "ref_gates.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            self.assertNotIn("config_snapshot", mods)


class 评审寻址Tests(unittest.TestCase):
    def test_revoked_work_addressable_visible(self):
        """撤回作品照常寻址、状态显形——业务拦截不在寻址层（T1 §4.2）。"""
        out = resolve("@作品43", PACKS, WORKS)
        self.assertEqual(out["resolution"]["status"], "resolved")
        self.assertEqual(out["meta_summary"]["work_status"], "已撤回（占位）")

    def test_zero_security_check_calls(self):
        """零安检调用（安检在进池时已完成，PRD-262）：ref 面零安检符号。"""
        for name in ("work_ref.py", "ref_gates.py"):
            blob = ast.dump(ast.parse((REPO / "scripts" / name)
                                      .read_text(encoding="utf-8")))
            for token in ("security_scan", "pack_gate", "quarantine"):
                self.assertNotIn(token, blob, f"{name} 含安检符号 {token}")


if __name__ == "__main__":
    unittest.main()
