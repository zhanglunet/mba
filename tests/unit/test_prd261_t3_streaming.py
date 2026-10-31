# -*- coding: utf-8 -*-
"""PRD-261/T3 自测（trend #1307）：网关校验与流式纠错。

运行：python3 -m pytest tests/unit/test_prd261_t3_streaming.py -q

覆盖（T1 §3.3 流式纠错 + §5 T3 验收「非法属性被丢弃/纠正，有测试」）：
  全合法 chunks 零纠错（redo 不触发）
  单非法 chunk 重出一次成功（redo 计数 1 入日志）
  两次重出仍非法 → 整块替换 warning note（redo 计数 2 入日志）
  校验日志机读：chunk_index/attempt/redo_count 可回放
  干净树（panel 全树）不触发 redo
  深度超限走既有丢弃路径（dropped，不重出）
  JSON 字符串 chunk 同样支持（dict/str 两形态）

虚构纪律：评审数据全虚构；非法内容用 <script> 形态断言零透传；不含真实主机名、账号、密钥。
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from review_widget_board import (  # noqa: E402
    MAX_DEPTH, streaming_validate,
)

LEGAL_VERDICT = {"component": "verdict-card",
                 "props": {"verdict": "hold", "confidence": 60, "rationale_ref": "findings-002"}}
LEGAL_METRIC = {"component": "metric-row",
                "props": {"label": "示例缺陷数", "value": "3", "unit": "个", "trend": "down"}}
LEGAL_NOTE = {"component": "note", "props": {"body": "示例备注", "tone": "neutral"}}
ILLEGAL_UNKNOWN = {"component": "free_html", "props": {"html": "<script>alert(1)</script>"}}


class TestStreaming(unittest.TestCase):
    def test_all_legal_chunks_zero_correction(self):
        """全合法 chunks：零纠错，redo 不触发，chunk 原样放行。"""
        def redo_fail(_raw):
            raise AssertionError("合法 chunk 不应触发 redo")

        chunks = [LEGAL_VERDICT, LEGAL_METRIC, LEGAL_NOTE]
        out, log = streaming_validate(chunks, redo_fail)
        self.assertEqual(out, chunks)
        self.assertEqual(log, [])

    def test_single_illegal_redo_once_success(self):
        """单非法 chunk：重出一次成功，redo 计数 1 入日志，放行的是重出结果。"""
        calls = []

        def redo_once(_raw):
            calls.append(_raw)
            return LEGAL_NOTE

        out, log = streaming_validate([LEGAL_VERDICT, ILLEGAL_UNKNOWN], redo_once)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], ILLEGAL_UNKNOWN)  # redo_fn 收到原 chunk
        self.assertEqual(out[0], LEGAL_VERDICT)
        self.assertEqual(out[1], LEGAL_NOTE)  # 重出后的合法片段被放行
        self.assertTrue(any(e["action"] == "redo_requested" and e["attempt"] == 1 for e in log))
        self.assertTrue(any(e["action"] == "chunk_fixed_after_redo" and e["redo_count"] == 1
                            and e["chunk_index"] == 1 for e in log))

    def test_redo_exhausted_whole_chunk_warning(self):
        """两次重出仍非法：整块替换 warning note，redo 恰好 2 次，计数入日志。"""
        calls = []

        def redo_always_bad(_raw):
            calls.append(_raw)
            return dict(ILLEGAL_UNKNOWN)  # 每次重出仍非法

        out, log = streaming_validate([ILLEGAL_UNKNOWN], redo_always_bad)
        self.assertEqual(len(calls), 2)  # ≤ max_redo
        self.assertEqual(out[0]["component"], "note")
        self.assertEqual(out[0]["props"]["tone"], "warning")
        self.assertNotIn("<script>", json.dumps(out, ensure_ascii=False))  # 非法内容零透传
        entry = next(e for e in log if e["action"] == "chunk_replaced_warning")
        self.assertEqual(entry["redo_count"], 2)
        self.assertEqual(entry["chunk_index"], 0)

    def test_log_machine_readable_replay(self):
        """校验日志机读可回放：每条含 chunk_index；纠错条目含 attempt/redo_count。"""
        def redo_once(_raw):
            return LEGAL_METRIC

        _, log = streaming_validate([ILLEGAL_UNKNOWN, LEGAL_NOTE], redo_once)
        self.assertTrue(log)  # 有纠错动作
        for entry in log:
            self.assertIn("chunk_index", entry)
            self.assertIn("action", entry)
        # 回放：chunk 0 先 redo_requested(attempt=1)，后 chunk_fixed_after_redo(redo_count=1)
        self.assertEqual(log[0]["action"], "redo_requested")
        self.assertEqual(log[0]["attempt"], 1)
        self.assertEqual(log[1]["action"], "chunk_fixed_after_redo")
        self.assertEqual(log[1]["redo_count"], 1)

    def test_clean_tree_no_redo(self):
        """干净 panel 全树（含 children）：不触发 redo，原样放行零日志。"""
        def redo_fail(_raw):
            raise AssertionError("干净树不应触发 redo")

        tree = {"component": "panel", "props": {
            "title": "示例评审看板", "level": "summary",
            "children": [LEGAL_VERDICT, LEGAL_METRIC, LEGAL_NOTE]}}
        out, log = streaming_validate([tree], redo_fail)
        self.assertEqual(out, [tree])
        self.assertEqual(log, [])

    def test_depth_over_limit_dropped_existing_path(self):
        """深度超限 chunk：走既有丢弃路径（dropped/depth>6），不重出，替换 warning note。"""
        calls = []

        def redo_fail(_raw):
            calls.append(_raw)
            return LEGAL_NOTE

        deep = {"component": "panel", "props": {"title": "示例"}}
        node = deep
        for _ in range(MAX_DEPTH + 2):
            node["props"]["children"] = [{"component": "panel", "props": {}}]
            node = node["props"]["children"][0]
        out, log = streaming_validate([LEGAL_NOTE, deep], redo_fail)
        self.assertEqual(calls, [])  # 深度超限确定性错误，不重出
        dropped = next(e for e in log if e["action"] == "dropped")
        self.assertEqual(dropped["where"], f"depth>{MAX_DEPTH}")
        self.assertEqual(dropped["chunk_index"], 1)
        self.assertEqual(out[1]["component"], "note")
        self.assertEqual(out[1]["props"]["tone"], "warning")

    def test_json_string_chunks_supported(self):
        """chunk 为 JSON 字符串同样支持：合法串放行，非法串触发重出。"""
        def redo_once(_raw):
            return json.dumps(LEGAL_NOTE, ensure_ascii=False)  # 模型重出也是字符串

        out, log = streaming_validate(
            [json.dumps(LEGAL_VERDICT, ensure_ascii=False), "not json"], redo_once)
        self.assertEqual(out[0], LEGAL_VERDICT)  # 合法字符串解析后原样放行
        self.assertEqual(out[1], LEGAL_NOTE)  # 重出成功
        self.assertTrue(any(e["action"] == "chunk_fixed_after_redo" for e in log))

    def test_no_redo_fn_illegal_replaced(self):
        """无纠错通道（redo_fn=None）：非法 chunk 直接整块替换 warning note，不抛异常。"""
        out, log = streaming_validate([ILLEGAL_UNKNOWN], None)
        self.assertEqual(out[0]["component"], "note")
        self.assertEqual(out[0]["props"]["tone"], "warning")
        entry = log[0]
        self.assertEqual(entry["action"], "chunk_replaced_warning")
        self.assertTrue(entry.get("no_redo_fn"))


if __name__ == "__main__":
    unittest.main()
