# -*- coding: utf-8 -*-
"""PRD-261/T4 自测（trend #1308）：服务端权限双路——渲染过滤 + 服务端独立校验。

运行：python3 -m pytest tests/unit/test_board_authz.py -q

覆盖（PRD-261 红线「权限在服务端校验；隐藏控件≠有权」+ T4 验收「越权操作被拒，有测试」）：
  无权用户渲染过滤动作组件（evidence-link/table-view 从树中剔除，日志留痕）
  有权用户渲染保留动作组件
  直接调 authorize_action 无权抛 PermissionError（双路断言核心：渲染滤掉≠授权，服务端独立拒）
  有权调用 authorize_action 通过（返回端点名）
  未知组件动作默认拒（清单外组件/映射外动作）
  权限按组件类型判定（同类型实例同权限；跨类型不互认）
  双路一致性：同一会话下渲染过滤与 authorize_action 判定一致
  过滤不改输入树；深层 children 递归过滤

虚构纪律：评审数据全虚构；不含真实主机名、账号、密钥。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from board_authz import (  # noqa: E402
    ACTION_ENDPOINTS, authorize_action, filter_by_session, perm_key,
)

PERM_EVIDENCE = perm_key("evidence-link", "open_evidence")      # evidence-link:open_evidence
PERM_TABLE = perm_key("table-view", "export_rows")              # table-view:export_rows

EVIDENCE_NODE = {"component": "evidence-link",
                 "props": {"ref": "findings-001", "label": "示例证据"}}
TABLE_NODE = {"component": "table-view",
              "props": {"columns": ["项", "值"], "rows": [["示例", "1"]], "max_rows": 10}}
NOTE_NODE = {"component": "note", "props": {"body": "示例备注", "tone": "neutral"}}
VERDICT_NODE = {"component": "verdict-card",
                "props": {"verdict": "hold", "confidence": 60, "rationale_ref": "findings-002"}}

TREE = {"component": "panel", "props": {"title": "示例评审看板", "level": "summary",
                                        "children": [VERDICT_NODE, EVIDENCE_NODE, TABLE_NODE, NOTE_NODE]}}


def components_of(tree):
    """按序收集树中所有组件名（含根）。"""
    out = [tree["component"]]
    for child in (tree.get("props", {}) or {}).get("children", []) or []:
        if isinstance(child, dict):
            out.extend(components_of(child))
    return out


class TestRenderPath(unittest.TestCase):
    def test_render_filters_unauthorized_action_components(self):
        """无权用户渲染：动作组件从树中过滤，非动作组件保留，日志机读留痕。"""
        clean, log = filter_by_session(TREE, session_perms=set())
        self.assertEqual(components_of(clean),
                         ["panel", "verdict-card", "note"])  # 两个动作组件被剔除
        self.assertIn({"action": "filtered_no_perm", "component": "evidence-link",
                       "permission": PERM_EVIDENCE, "where": "root"}, log)
        self.assertIn({"action": "filtered_no_perm", "component": "table-view",
                       "permission": PERM_TABLE, "where": "root"}, log)

    def test_render_retains_authorized_action_components(self):
        """有权用户渲染：动作组件保留，零过滤日志。"""
        clean, log = filter_by_session(TREE, session_perms={PERM_EVIDENCE, PERM_TABLE})
        self.assertEqual(components_of(clean),
                         ["panel", "verdict-card", "evidence-link", "table-view", "note"])
        self.assertEqual(log, [])

    def test_filter_does_not_mutate_input_tree(self):
        """过滤不改输入树：原树仍是完整四子节点（渲染层无副作用）。"""
        import copy
        snapshot = copy.deepcopy(TREE)
        filter_by_session(TREE, session_perms=set())
        self.assertEqual(TREE, snapshot)

    def test_filter_recurses_into_nested_children(self):
        """深层 children 递归过滤：panel>panel 里的无权动作组件同样被剔除。"""
        nested = {"component": "panel", "props": {"title": "外层", "children": [
            {"component": "panel", "props": {"title": "内层", "children": [EVIDENCE_NODE, NOTE_NODE]}},
        ]}}
        clean, log = filter_by_session(nested, session_perms=set())
        inner = clean["props"]["children"][0]
        self.assertEqual([c["component"] for c in inner["props"]["children"]], ["note"])
        self.assertEqual(len(log), 1)


class TestServerPath(unittest.TestCase):
    def test_authorize_denies_without_perm_dual_path(self):
        """双路断言核心：渲染路已滤掉的组件，服务端直调 authorize_action 无权照样抛 PermissionError。

        前端隐藏≠有权——绕过渲染过滤直接打端点，服务端独立校验仍然拒绝。
        """
        # 渲染路：无权会话看不到 evidence-link
        clean, _ = filter_by_session(TREE, session_perms=set())
        self.assertNotIn("evidence-link", components_of(clean))
        # 服务端路：同一无权会话直接请求端点 → 独立拒绝
        with self.assertRaises(PermissionError):
            authorize_action("evidence-link", "open_evidence", set())

    def test_authorize_allows_with_perm(self):
        """有权调用通过：返回放行的端点名，供服务端路由。"""
        self.assertEqual(authorize_action("evidence-link", "open_evidence", {PERM_EVIDENCE}),
                         "open_evidence")
        self.assertEqual(authorize_action("table-view", "export_rows", {PERM_TABLE}),
                         "export_rows")

    def test_unknown_component_or_action_default_deny(self):
        """未知组件动作默认拒：清单外组件、映射外动作、None 会话全拒。"""
        for component, action, perms in [
            ("free-html", "render_html", {PERM_EVIDENCE, PERM_TABLE}),  # 清单外组件
            ("evidence-link", "delete_all", {PERM_EVIDENCE}),           # 映射外动作
            ("evidence-link", "open_evidence", None),                   # 无会话权限
        ]:
            with self.assertRaises(PermissionError, msg=f"{component}.{action} 应默认拒"):
                authorize_action(component, action, perms)

    def test_permission_judged_by_component_type(self):
        """权限按组件类型判定：同类型两个实例同权限；跨类型不互认（有 evidence 权 ≠ 有 table 权）。"""
        perms = {PERM_EVIDENCE}
        # 同类型另一实例（不同 ref/label）同权限通过
        other_instance = {"component": "evidence-link", "props": {"ref": "findings-009"}}
        endpoint = ACTION_ENDPOINTS[other_instance["component"]]
        self.assertEqual(authorize_action(other_instance["component"], endpoint, perms),
                         "open_evidence")
        # 跨类型不互认：evidence 权限不含 table-view
        with self.assertRaises(PermissionError):
            authorize_action("table-view", "export_rows", perms)

    def test_dual_paths_agree_on_same_session(self):
        """双路一致性：同一会话下，渲染过滤判定与 authorize_action 判定逐组件一致。"""
        for perms in (set(), {PERM_EVIDENCE}, {PERM_EVIDENCE, PERM_TABLE}):
            clean, _ = filter_by_session(TREE, perms)
            rendered = set(components_of(clean))
            for component, endpoint in ACTION_ENDPOINTS.items():
                rendered_keeps = component in rendered
                try:
                    authorize_action(component, endpoint, perms)
                    server_allows = True
                except PermissionError:
                    server_allows = False
                self.assertEqual(rendered_keeps, server_allows,
                                 f"{component} 渲染路/服务端路判定不一致（perms={perms}）")


if __name__ == "__main__":
    unittest.main()
