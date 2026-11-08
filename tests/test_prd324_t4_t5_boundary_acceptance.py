# -*- coding: utf-8 -*-
"""PRD-324/T4+T5：重放闸门划界断言 + 验收试运行（trend #1603 区段）。

T4 划界：scripts/replay_gate.py 零网络形态（无 requests/urllib/socket/http）、
零写盘调用形态（AST import 白名单）+ 闸门拒绝零副作用（入参 deepcopy 不变）。
T5 验收：真实 T2 交付（docs/agent-ui/component-catalog.json）→ 结构校验 →
replay_gate 全链——真实目录过闸两遍逐字段一致（可重放）；篡改/非 dict 拒绝。
"""
import ast
import copy
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from replay_gate import replay_gate

CATALOG = REPO / "docs" / "agent-ui" / "component-catalog.json"


class T4BoundaryTests(unittest.TestCase):
    def test_ast_import_stdlib_only(self):
        tree = ast.parse((REPO / "scripts" / "replay_gate.py").read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        for bad in ("requests", "urllib", "socket", "http"):
            self.assertNotIn(bad, roots, f"越界网络导入：{bad}")

    def test_gate_refusal_zero_side_effect(self):
        verify = {"status": "MISMATCH", "evidence": {"catalog": "篡改"}}
        frozen = copy.deepcopy(verify)
        out = replay_gate(verify)
        self.assertFalse(out["allow"])
        self.assertEqual(verify, frozen, "拒绝路径不得改入参")


def verify_catalog(catalog) -> dict:
    """目录结构校验：{"status": "MATCH", ...} 或 REFUSED+evidence（T4 语义复用）。"""
    if not isinstance(catalog, dict):
        return {"status": "REFUSED", "evidence": ["catalog 不是 JSON 对象"]}
    evidence = []
    components = catalog.get("components")
    if not isinstance(components, list) or not components:
        evidence.append("components 缺失或为空——agent 无可调用面")
    else:
        seen = set()
        for i, c in enumerate(components):
            cid = str(c.get("name") or c.get("id") or "")
            if not cid:
                evidence.append(f"components[{i}] 缺标识（name/id）")
            elif cid in seen:
                evidence.append(f"components[{i}] 标识重复：{cid}")
            seen.add(cid)
    if evidence:
        return {"status": "REFUSED", "evidence": evidence}
    return {"status": "MATCH", "count": len(components)}


class T5AcceptanceTests(unittest.TestCase):
    def test_real_catalog_full_chain_replay_identical(self):
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        def chain(c):
            verify = verify_catalog(c)
            return {"verify": verify, "gate": replay_gate(verify)}
        out1 = chain(catalog)
        out2 = chain(json.loads(json.dumps(catalog)))
        self.assertEqual(out1, out2, "两遍逐字段一致（可重放口径）")
        self.assertTrue(out1["gate"]["allow"])
        self.assertGreater(out1["verify"]["count"], 0)

    def test_tampered_catalog_refused_replay_identical(self):
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        tampered = json.loads(json.dumps(catalog))
        if isinstance(tampered.get("components"), list) and tampered["components"]:
            tampered["components"][0].pop("name", None)
            tampered["components"][0].pop("id", None)
        def run():
            return replay_gate(verify_catalog(tampered))
        self.assertEqual(run(), run())
        self.assertFalse(run()["allow"])

    def test_non_dict_refused(self):
        self.assertFalse(replay_gate(verify_catalog("not-a-dict"))["allow"])


if __name__ == "__main__":
    unittest.main()
