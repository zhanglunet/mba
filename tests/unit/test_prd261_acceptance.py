# -*- coding: utf-8 -*-
"""PRD-261/T5 验收试运行（trend #1309）：样例评审看板端到端。

运行：python3 -m pytest tests/unit/test_prd261_acceptance.py -q

验收标准（issue #1309）：无自由 HTML 直出；权限服务端生效；无密钥。
PRD 红线：非法属性丢弃；权限在服务端校验；不以自由 HTML 作为上线输出。

覆盖（端到端验收，不重复 T2–T4 单元路径，只验整体合同）：
  样例评审数据端到端出板（parse→validate→权限过滤→净板）
  注入非法属性 + 未知组件被拦（校验日志断言，注入物零透传）
  无自由 HTML 直出：净板全文本无标签形态；组件库封闭清单无 html/raw-html 组件
  服务端权限双路（渲染过滤 + authorize_action 直调 403 语义；绕过渲染直打端点仍拒）
  流式纠错 redo ≤ 2（超限整块替换 warning，非法内容零透传）
  校验日志机读（逐条 dict/action 字段/可 JSON 回放/动作词表封闭）
  密钥扫描（实现 + 测试 + 验收记录零命中）
  确定性（同输入两次出板逐字节一致；系统提示词两次一致）
  零网络（实现模块无网络导入；socket 封禁下端到端照常出板）

虚构纪律：评审数据全虚构（示例产品/示例指标）；不含真实主机名、账号、密钥。
"""
import copy
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from board_authz import ACTION_ENDPOINTS, authorize_action, filter_by_session, perm_key  # noqa: E402
from review_widget_board import (  # noqa: E402
    WIDGET_NAMES, build_system_prompt, parse_component_tree,
    streaming_validate, validate_tree,
)

# ── 样例评审数据（全虚构：示例产品「示例笔记应用」的一轮虚构评审） ──
SAMPLE_MODEL_OUTPUT = json.dumps({
    "component": "panel",
    "props": {
        "title": "示例笔记应用 · 评审看板",
        "level": "summary",
        "children": [
            {"component": "verdict-card",
             "props": {"verdict": "hold", "confidence": 62, "rationale_ref": "F-DEMO-001"}},
            {"component": "metric-row",
             "props": {"label": "示例周活跃", "value": "1200", "unit": "人", "trend": "up"}},
            {"component": "evidence-link",
             "props": {"ref": "F-DEMO-002", "label": "示例证据链接"}},
            {"component": "table-view",
             "props": {"columns": ["维度", "评分"], "rows": [["示例留存", "3.8"]], "max_rows": 10}},
            {"component": "note",
             "props": {"body": "示例备注：证据待补", "tone": "neutral"}},
        ],
    },
}, ensure_ascii=False)

PERM_EVIDENCE = perm_key("evidence-link", "open_evidence")
PERM_TABLE = perm_key("table-view", "export_rows")

TAG_SHAPE = re.compile(r"<[a-zA-Z/!][^>]{0,80}>")
SECRET_SHAPES = [
    re.compile("AKIA[A-Z0-9]{16}"),
    re.compile("ghp_[A-Za-z0-9]{20,}"),
    re.compile("sk" + "-[A-Za-z0-9]{20,}"),          # 拼接避免本文件自命中
    re.compile("xox[baprs]" + "-[A-Za-z0-9]{10,}"),
    re.compile("BEGIN (RSA |EC )?PRIVATE KEY"),
    re.compile("(?i)(password|passwd|api[_-]?key|secret)\\s*[:=]\\s*['\"][^'\"]{8,}['\"]"),
]
SCAN_TARGETS = [
    REPO / "scripts" / "review_widget_board.py",
    REPO / "scripts" / "board_authz.py",
    REPO / "tests" / "unit" / "test_prd261_acceptance.py",
    REPO / "docs" / "devlog" / "2026-10-28-prd-261-t5-acceptance.md",
]
NETWORK_MODULES = {"socket", "ssl", "urllib", "urllib.request", "http", "http.client",
                   "requests", "httpx", "aiohttp", "ftplib", "smtplib", "telnetlib"}


def _string_leaves(node):
    """递归收集树中全部字符串叶子（属性值/列表元素）。"""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, val in node.items():
            yield from _string_leaves(key)
            yield from _string_leaves(val)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _string_leaves(item)


def _components_of(tree):
    out = [tree["component"]]
    for child in (tree.get("props", {}) or {}).get("children", []) or []:
        if isinstance(child, dict):
            out.extend(_components_of(child))
    return out


class TestEndToEnd(unittest.TestCase):
    def test_sample_board_end_to_end_render(self):
        """样例评审数据端到端出板：parse→validate→权限过滤，净板结构符合组件合同。"""
        tree = parse_component_tree(SAMPLE_MODEL_OUTPUT)
        clean, log = validate_tree(tree)
        self.assertEqual(log, [])                     # 样例数据全合法，零纠错
        board, filtered = filter_by_session(clean, {PERM_EVIDENCE, PERM_TABLE})
        self.assertEqual(filtered, [])
        self.assertEqual(_components_of(board),
                         ["panel", "verdict-card", "metric-row", "evidence-link",
                          "table-view", "note"])
        self.assertEqual(board["props"]["children"][0]["props"]["verdict"], "hold")

    def test_no_free_html_in_board_output(self):
        """无自由 HTML 直出：净板全部字符串叶子无标签形态；组件库为封闭清单且无 html 组件。"""
        tree = parse_component_tree(SAMPLE_MODEL_OUTPUT)
        clean, _ = validate_tree(tree)
        board, _ = filter_by_session(clean, None)
        for text in _string_leaves(board):
            self.assertIsNone(TAG_SHAPE.search(text), f"输出含 HTML 标签形态: {text!r}")
        for name in WIDGET_NAMES:
            self.assertFalse(re.search("html", name), f"组件库出现 HTML 直出组件: {name}")

    def test_injection_props_and_unknown_component_blocked(self):
        """注入非法属性 + 未知组件被拦：dropped_prop/replaced_warning 留痕，注入物零透传。"""
        hostile = {"component": "panel", "props": {"title": "示例注入板", "children": [
            {"component": "note",
             "props": {"body": "正文", "onclick": "alert(1)", "html": "<script>alert(1)</script>"}},
            {"component": "free-html", "props": {"html": "<img src=x onerror=alert(1)>"}},
        ]}}
        clean, log = validate_tree(hostile)
        dumped = json.dumps(clean, ensure_ascii=False)
        self.assertNotIn("<script>", dumped)
        self.assertNotIn("onerror", dumped)
        self.assertNotIn("onclick", dumped)
        self.assertIn({"action": "dropped_prop", "component": "note", "prop": "onclick"}, log)
        self.assertIn({"action": "dropped_prop", "component": "note", "prop": "html"}, log)
        self.assertTrue(any(e["action"] == "replaced_warning" and e["component"] == "free-html"
                            for e in log))
        for node in clean["props"]["children"]:
            self.assertIn(node["component"], WIDGET_NAMES)   # 出板只含封闭清单组件


class TestServerAuthz(unittest.TestCase):
    def test_server_authz_dual_path_403_semantics(self):
        """服务端权限双路：渲染过滤剔除无权动作组件；绕过渲染直调 authorize_action 仍拒（403 语义）。"""
        tree = parse_component_tree(SAMPLE_MODEL_OUTPUT)
        clean, _ = validate_tree(tree)
        no_perm_board, log = filter_by_session(clean, set())
        self.assertNotIn("evidence-link", _components_of(no_perm_board))
        self.assertNotIn("table-view", _components_of(no_perm_board))
        self.assertEqual(len(log), 2)
        # 绕过渲染过滤直接打端点：服务端独立校验，默认拒
        for component, endpoint in ACTION_ENDPOINTS.items():
            with self.assertRaises(PermissionError, msg=f"{component} 无权直调应拒"):
                authorize_action(component, endpoint, set())
        # 有权会话：两路一致放行
        perms = {PERM_EVIDENCE, PERM_TABLE}
        kept_board, kept_log = filter_by_session(clean, perms)
        self.assertEqual(kept_log, [])
        self.assertIn("evidence-link", _components_of(kept_board))
        self.assertEqual(authorize_action("evidence-link", "open_evidence", perms),
                         "open_evidence")
        # 权限按组件类型判定：跨类型不互认
        with self.assertRaises(PermissionError):
            authorize_action("table-view", "export_rows", {PERM_EVIDENCE})


class TestStreamingAndLog(unittest.TestCase):
    def test_streaming_redo_capped_at_two(self):
        """流式纠错 redo ≤ 2：重出两次仍非法 → 整块替换 warning，redo 计数留痕，非法内容零透传。"""
        illegal = {"component": "free-html", "props": {"html": "<script>x</script>"}}
        fixed = {"component": "note", "props": {"body": "重出后合法片段", "tone": "neutral"}}

        # 重出一次即合法
        out, log = streaming_validate([illegal], lambda _raw: fixed)
        self.assertEqual(out, [fixed])
        self.assertTrue(any(e["action"] == "chunk_fixed_after_redo" and e["redo_count"] == 1
                            for e in log))

        # 永远重出非法：每 chunk redo 恰 ≤2，超限整块替换 warning
        attempts = []

        def redo_always_illegal(raw):
            attempts.append(raw)
            return raw

        out, log = streaming_validate([illegal], redo_always_illegal)
        self.assertEqual(len(attempts), 2)                       # redo 次数封顶 2
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["component"], "note")
        self.assertEqual(out[0]["props"]["tone"], "warning")
        self.assertNotIn("<script>", json.dumps(out, ensure_ascii=False))
        redo_events = [e for e in log if e["action"] == "redo_requested"]
        self.assertEqual([e["attempt"] for e in redo_events], [1, 2])
        self.assertTrue(any(e["action"] == "chunk_replaced_warning" and e["redo_count"] == 2
                            for e in log))

    def test_validation_log_machine_readable(self):
        """校验日志机读：逐条 dict 且含 action 字段、动作词表封闭、整体可 JSON 回放。"""
        hostile = {"component": "panel", "props": {"title": "示例日志板", "children": [
            {"component": "no-such-widget", "props": {"x": 1}},
            {"component": "metric-row", "props": {"label": "示例", "value": "1", "trend": "斜的"}},
            {"component": "verdict-card", "props": {}},
        ]}}
        _, log = validate_tree(hostile)
        self.assertTrue(log)
        vocabulary = {"dropped", "replaced_warning", "dropped_prop", "node_rejected"}
        for entry in log:
            self.assertIsInstance(entry, dict)
            self.assertIsInstance(entry.get("action"), str)
            self.assertIn(entry["action"], vocabulary)
        replay = json.loads(json.dumps(log, ensure_ascii=False))     # 可回放
        self.assertEqual(replay, log)
        self.assertTrue(any(e["action"] == "node_rejected" and e["component"] == "verdict-card"
                            and "verdict" in e["missing"] for e in log))


class TestDiscipline(unittest.TestCase):
    def test_no_secrets_in_deliverables(self):
        """无密钥：实现 + 验收测试 + 验收记录对常见密钥形态扫描零命中。"""
        for path in SCAN_TARGETS:
            self.assertTrue(path.exists(), f"扫描目标缺失: {path}")
            text = path.read_text(encoding="utf-8")
            for shape in SECRET_SHAPES:
                hits = shape.findall(text)
                self.assertEqual(hits, [], f"{path.name} 命中密钥形态 {shape.pattern!r}: {hits}")

    def test_deterministic_pipeline(self):
        """确定性：同输入两次端到端出板逐字节一致；系统提示词两次一致；输入树不被改动。"""
        snapshot = copy.deepcopy(json.loads(SAMPLE_MODEL_OUTPUT))
        runs = []
        for _ in range(2):
            tree = parse_component_tree(SAMPLE_MODEL_OUTPUT)
            clean, log = validate_tree(tree)
            board, _ = filter_by_session(clean, {PERM_EVIDENCE})
            runs.append((json.dumps(board, sort_keys=True, ensure_ascii=False),
                         json.dumps(log, sort_keys=True, ensure_ascii=False)))
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(build_system_prompt(), build_system_prompt())
        self.assertEqual(json.loads(SAMPLE_MODEL_OUTPUT), snapshot)   # 输入零副作用

    def test_zero_network(self):
        """零网络：实现模块源码无网络库导入（AST 静态检查）；socket 封禁下端到端照常出板。"""
        import ast
        targets = [REPO / "scripts" / "review_widget_board.py",
                   REPO / "scripts" / "board_authz.py"]
        for path in targets:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(imported & NETWORK_MODULES,
                             f"{path.name} 导入网络模块: {imported & NETWORK_MODULES}")
        with mock.patch("socket.socket", side_effect=AssertionError("禁止网络")):
            parsed = parse_component_tree(SAMPLE_MODEL_OUTPUT)
            clean, _ = validate_tree(parsed)
            board, _ = filter_by_session(clean, None)
            self.assertEqual(board["component"], "panel")


if __name__ == "__main__":
    unittest.main()
