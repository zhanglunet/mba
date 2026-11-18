# -*- coding: utf-8 -*-
"""PRD-485/T4 测试（trend #2348 的 T4 环节）：技能评估划界断言。
运行：uv run --with pytest python -m pytest tests/unit/test_prd485_t4_boundary.py -q
按 PRD 任务拆分 T4 行：评估与独立验收测试/验证台/评审流水线/监督回路的边界
断言——评估不越界审产物、不审过程：
  - 评估双模块（T2 评估 + T3 闸门）对邻居模块（评审流水线/协同会话/监督台/
    下游载体）零导入（AST）；
  - 借鉴仓（NVIDIA/SkillEvaluator Apache-2.0、Claude-BugHunter MIT、
    stitch-skills Apache-2.0）零符号（仅代码标识符扫描）；
  - 下游载体词零标识符（评估只在技能层面，产物/过程通道零触碰）；
  - 红线钉值：疑似重叠拦下不自动合并/未知技能显形拒绝/闸门账本 append-only
    （深拷贝隔离）/闸门只读报告不重跑评估/无发布路径；
  - 词表封闭 + AST 零网络零子进程。
只断言，不改任何生产代码。零网络；全合成占位。
"""
import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(MOD_DIR))
MODULE_DIR = MOD_DIR
MODULES = ["skill_evaluation.py", "skill_evaluation_gate.py"]
NEIGHBOR_STEMS = ["review_collab_session", "review_review_pipeline", "review_supervision_bench"]
CARRIER_WORDS = ["review_collab_session", "review_review_pipeline", "review_supervision_bench"]

from skill_evaluation import SCHEMA  # noqa: E402
from skill_evaluation_gate import (  # noqa: E402
    BEHAVIOR_PASS, BLOCK_REASON_CODES, GateError, SkillEvaluationLedger,
    check_gate)

NOW = "2026-11-17T10:00:00Z"
BY = "reviewer（占位）"



OK_ROW = ("skill-a", "静态完整", "过关")


def make_report(specs):
    skills = []
    for sid, static, behavior in specs:
        skills.append({"name": sid, "path": f"skills/{sid}/SKILL.md",
                       "checks": {}, "missing": [],
                       "static_verdict": static,
                       "behavior_verdict": behavior,
                       "behavior_reason": "合成占位"})
    return {"schema": SCHEMA, "skill_count": len(skills),
            "static_complete": 0, "static_gap": 0,
            "overlap_candidates": [], "skills": skills}


def codes(verdict):
    return [r["code"] for r in verdict["reasons"]]


class TestGatePins(unittest.TestCase):
    def test_redline_overlap_blocked_even_if_passing(self):
        """红线：疑似重叠拦下不自动合并——行为过关也拦（确认由人做）。"""
        report = make_report([OK_ROW])
        report["overlap_candidates"] = [
            {"a": "skills/skill-a/SKILL.md", "b": "skills/x/SKILL.md",
             "similarity": 0.9}]
        d = check_gate(report, "skill-a")
        self.assertFalse(d["allowed"])
        self.assertIn("SUSPECTED_OVERLAP", codes(d))

    def test_redline_unknown_skill_explicit(self):
        """红线：未知技能显形拒绝（不静默放行）。"""
        with self.assertRaisesRegex(GateError, "UNKNOWN_SKILL"):
            check_gate(make_report([OK_ROW]), "ghost")

    def test_redline_ledger_append_only_deep_copy(self):
        """红线：闸门账本 append-only——entries 深拷贝，改返回不污染账本。"""
        led = SkillEvaluationLedger(None)
        led.record({"prd": 485}, {"kind": "gate_passed", "skill_id": "s",
                                    "by": BY, "at": NOW})
        snapshot = led.entries()
        snapshot[0]["kind"] = "改（占位）"
        self.assertEqual(led.entries()[0]["kind"], "gate_passed")

    def test_redline_gate_reads_not_reruns(self):
        """红线：闸门只读报告不重跑评估——check_gate 纯函数零副作用。"""
        report = make_report([OK_ROW])
        before = copy.deepcopy(report)
        check_gate(report, "skill-a")
        self.assertEqual(json.dumps(report, sort_keys=True),
                         json.dumps(before, sort_keys=True))

    def test_vocab_closed(self):
        """词表封闭：行为词表与拦因词表只能取设计稿封闭集合。"""
        self.assertEqual(BEHAVIOR_PASS, "过关")
        self.assertEqual(set(BLOCK_REASON_CODES),
                         {"BAD_REPORT", "UNKNOWN_SKILL", "REMEDIATE",
                          "INSUFFICIENT_EVIDENCE", "SUSPECTED_OVERLAP"})

class TestBoundary(unittest.TestCase):
    def test_eval_modules_zero_neighbor_imports(self):
        """评估双模块对邻居（评审流水线/协同会话/监督台/下游载体）零导入。"""
        for mod in MODULES:
            src = (MODULE_DIR / mod).read_text(encoding="utf-8")
            imported = set()
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            for stem in NEIGHBOR_STEMS:
                self.assertNotIn(stem, imported, f"{mod} 导入邻居 {stem}")

    def test_downstream_carrier_zero_identifiers(self):
        """下游载体词零标识符（产物通道/过程通道不在评估模块里）。"""
        for mod in MODULES:
            src = (MODULE_DIR / mod).read_text(encoding="utf-8")
            tree = ast.parse(src)
            names = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    names.add(node.name.lower())
                elif isinstance(node, ast.arg):
                    names.add(node.arg.lower())
                elif isinstance(node, ast.Name):
                    names.add(node.id.lower())
                elif isinstance(node, ast.Attribute):
                    names.add(node.attr.lower())
            for word in CARRIER_WORDS:
                self.assertNotIn(word, names,
                                 f"{mod} 标识符出现下游载体词 {word}")

    def test_borrowed_zero_symbols(self):
        """借鉴仓零符号（SkillEvaluator/BugHunter/stitch-skills，仅标识符）。"""
        for mod in MODULES:
            src = (MODULE_DIR / mod).read_text(encoding="utf-8")
            tree = ast.parse(src)
            names = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    names.add(node.name.lower())
                elif isinstance(node, ast.Name):
                    names.add(node.id.lower())
                elif isinstance(node, ast.Attribute):
                    names.add(node.attr.lower())
            for word in ("skillevaluator", "bughunter", "stitch_skills"):
                self.assertNotIn(word, names,
                                 f"{mod} 标识符出现借鉴词 {word}")

    def test_no_publish_path(self):
        """评估不碰发布/删除：评估双模块无发布路径符号。"""
        for mod in MODULES:
            src = (MODULE_DIR / mod).read_text(encoding="utf-8")
            tree = ast.parse(src)
            names = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    names.add(node.name.lower())
                elif isinstance(node, ast.Name):
                    names.add(node.id.lower())
            for word in ("publish", "delete_skill", "remove_skill",
                         "merge_skill"):
                self.assertNotIn(word, names, f"{mod} 出现 {word}")

    def test_ast_zero_network(self):
        """AST 零网络零子进程（评估双模块）。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        for mod in MODULES:
            src = (MODULE_DIR / mod).read_text(encoding="utf-8")
            imported = set()
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(imported & banned,
                             f"{mod} 导入 {imported & banned}")


if __name__ == "__main__":
    unittest.main()
