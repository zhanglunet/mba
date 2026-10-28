#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-261/T2+T3（trend #1306/#1307）：生成式评审看板——组件库 + 提示词生成 + 组件树解析/网关校验/流式纠错。

按 PRD-261/T1 设计（docs/plans/2026-10-28-prd-261-openui-review-board.md）实现：
  T2：review-widget-v1 八组件封闭清单（逐组件 schema：属性/类型/枚举/上限）；
      提示词由组件库模板化生成（组件库变提示词变，不手写漂移）；
      parse_component_tree：模型输出（JSON 字符串）→ 组件树对象（第一层校验：JSON 合法/根为 panel/深度上限）；
      网关校验 validate_tree：非法属性丢弃、未知组件替换 note(warning)、必填缺失拒绝节点、
      校验日志（机读，可回放）；
  T3：流式纠错 streaming_validate——逐 chunk（子树 JSON 片段）到达即校验，非法子树调 redo_fn
      请求模型重出（每 chunk ≤2 次），超限整块替换 warning note；深度超限直接走既有丢弃路径；
      redo 计数入校验日志。服务端权限双路属 T4。

零网络；模型侧由调用方注入（redo_fn/测试 fixture——不真调 LLM）。
示例评审数据全虚构；不含真实主机名、账号、密钥。
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

SCHEMA = "review-widget-v1"
VERSION = "0.1.0"
MAX_DEPTH = 6

# ── 组件库（封闭清单；属性表即 schema） ──

WIDGETS: dict[str, dict[str, Any]] = {
    "panel": {
        "required": ["title"],
        "props": {
            "title": {"type": "str", "max_len": 60},
            "level": {"type": "enum", "values": ["summary", "detail"]},
            "children": {"type": "children"},
        },
    },
    "verdict-card": {
        "required": ["verdict"],
        "props": {
            "verdict": {"type": "enum", "values": ["recommend", "hold", "reject"]},
            "confidence": {"type": "int", "min": 0, "max": 100},
            "rationale_ref": {"type": "str", "max_len": 120},
        },
    },
    "metric-row": {
        "required": ["label", "value"],
        "props": {
            "label": {"type": "str", "max_len": 40},
            "value": {"type": "str", "max_len": 40},
            "unit": {"type": "str", "max_len": 10},
            "trend": {"type": "enum", "values": ["up", "down", "flat"]},
        },
    },
    "table-view": {
        "required": ["columns"],
        "props": {
            "columns": {"type": "list"},
            "rows": {"type": "list"},
            "max_rows": {"type": "int", "min": 1, "max": 100},
        },
    },
    "evidence-link": {
        "required": ["ref"],
        "props": {"ref": {"type": "str", "max_len": 80}, "label": {"type": "str", "max_len": 60}},
    },
    "checklist": {
        "required": ["items"],
        "props": {
            "items": {"type": "list"},
        },
    },
    "note": {
        "required": ["body"],
        "props": {
            "body": {"type": "str", "max_len": 300},
            "tone": {"type": "enum", "values": ["neutral", "warning"]},
        },
    },
    "reference-list": {
        "required": ["refs"],
        "props": {"refs": {"type": "list"}},
    },
}

WIDGET_NAMES = tuple(WIDGETS)


# ── 提示词生成（模板化；组件库变提示词变） ──

def build_system_prompt() -> str:
    lines = [
        f"你是评审看板渲染器。只输出一个组件树 JSON（根为 panel），组件只能是以下 {len(WIDGETS)} 种，"
        "属性以组件库为准，不得发明属性或组件；不得输出 HTML。",
    ]
    for name, spec in WIDGETS.items():
        props = ", ".join(sorted(spec["props"]))
        required = ",".join(spec["required"])
        lines.append(f"- {name}（必填: {required}；属性: {props}）")
    lines.append(f"树深度 ≤ {MAX_DEPTH}。")
    return f"[review-widget {VERSION}]\n" + "\n".join(lines)


# ── 解析（第一层校验） ──

def parse_component_tree(model_output: str) -> dict[str, Any]:
    """模型输出（JSON 字符串）→ 树对象；非法 JSON/根错误/超深抛 TreeSyntaxError。"""
    try:
        tree = json.loads(model_output)
    except json.JSONDecodeError as exc:
        raise TreeSyntaxError(f"JSON 解析失败: {exc}") from exc
    if not isinstance(tree, dict) or tree.get("component") != "panel":
        raise TreeSyntaxError("根必须为 panel")
    _check_depth(tree, 1)
    return tree


class TreeSyntaxError(ValueError):
    pass


def _check_depth(node: dict[str, Any], depth: int) -> None:
    if depth > MAX_DEPTH:
        raise TreeSyntaxError(f"树深度超过 {MAX_DEPTH}")
    for child in (node.get("props", {}) or {}).get("children", []) or []:
        if isinstance(child, dict):
            _check_depth(child, depth + 1)


# ── 网关校验（非法属性丢弃/未知组件替换/必填拒绝；日志机读） ──

def validate_tree(tree: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """返回 (净树, 校验日志)。"""
    log: list[dict[str, Any]] = []
    clean = _validate_node(tree, 1, log)
    return clean, log


def _validate_node(node: dict[str, Any], depth: int, log: list[dict[str, Any]]) -> dict[str, Any]:
    name = node.get("component")
    if depth > MAX_DEPTH:
        log.append({"action": "dropped", "where": f"depth>{MAX_DEPTH}", "component": name})
        return _warning_note("结构超深被丢弃")
    if name not in WIDGETS:
        log.append({"action": "replaced_warning", "component": name})
        return _warning_note(f"未知组件 {name!r} 未通过校验")
    spec = WIDGETS[name]
    props_in = node.get("props", {}) or {}
    clean_props: dict[str, Any] = {}
    for key, val in props_in.items():
        rule = spec["props"].get(key)
        if rule is None:
            log.append({"action": "dropped_prop", "component": name, "prop": key})
            continue
        if rule["type"] == "children":
            # children 逐个降级校验（不因单个子节点非法而丢弃整棵）
            kids = []
            for child in val or []:
                if isinstance(child, dict):
                    kids.append(_validate_node(child, depth + 1, log))
            clean_props[key] = kids
            continue
        problem = _prop_problem(key, val, rule)
        if problem:
            log.append({"action": "dropped_prop", "component": name, "prop": key, "reason": problem})
            continue
        clean_props[key] = val
    missing = [r for r in spec["required"] if r not in clean_props]
    if missing:
        log.append({"action": "node_rejected", "component": name, "missing": missing})
        return _warning_note(f"组件 {name} 缺必填 {','.join(missing)} 被拒")
    clean: dict[str, Any] = {"component": name, "props": clean_props}
    return clean


def _warning_note(body: str) -> dict[str, Any]:
    return {"component": "note", "props": {"body": body[:300], "tone": "warning"}}


def _prop_problem(key: str, val: Any, rule: dict[str, Any]) -> str | None:
    t = rule["type"]
    if t == "children":
        if not isinstance(val, list):
            return "children 应为数组"
        return None
    if t == "str":
        if not isinstance(val, str):
            return f"{key} 应为字符串"
        if len(val) > rule.get("max_len", 10**6):
            return f"{key} 超长（>{rule.get('max_len')}）"
        return None
    if t == "enum":
        if val not in rule["values"]:
            return f"{key}={val!r} 不在 {rule['values']}"
        return None
    if t == "int":
        if not isinstance(val, int) or isinstance(val, bool):
            return f"{key} 应为整数"
        if "min" in rule and val < rule["min"]:
            return f"{key} < {rule['min']}"
        if "max" in rule and val > rule["max"]:
            return f"{key} > {rule['max']}"
        return None
    if t == "list":
        if not isinstance(val, list):
            return f"{key} 应为数组"
        return None
    return f"未知属性类型 {t}"


def sanitize_text(text: str) -> str:
    """文本属性统一净化：去 HTML 标签形态（防注入面）。"""
    return re.sub(r"<[^>]{1,80}>", "", text)


# ── 流式纠错（T3：逐 chunk 校验，非法重出 ≤2 次，超限整块 warning note） ──

def _coerce_chunk(raw: Any) -> dict[str, Any]:
    """chunk 归一化：JSON 字符串 → dict；解析失败/非对象回落为非法标记（交回网关判非法）。"""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {"component": "__parse_error__"}
    return raw if isinstance(raw, dict) else {"component": "__parse_error__"}


def _chunk_problems(chunk: dict[str, Any]) -> list[dict[str, Any]]:
    """用既有网关校验探测 chunk 合法性：校验日志非空即有非法处（属性/组件/必填/深度）。"""
    _, issues = validate_tree(chunk)
    return issues


def _max_depth(node: Any) -> int:
    if not isinstance(node, dict):
        return 0
    children = (node.get("props", {}) or {}).get("children", []) or []
    deepest = 0
    for child in children:
        deepest = max(deepest, _max_depth(child))
    return 1 + deepest


def streaming_validate(
    chunks: list[Any],
    redo_fn: Callable[[Any], Any] | None,
    max_redo: int = 2,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """逐 chunk（子树 JSON 片段：dict 或 JSON 字符串）到达即校验的流式纠错。

    - 合法 chunk 原样放行（零纠错，不触发 redo）；
    - 非法 chunk 调 redo_fn(chunk) 请求模型重出该子树，每个 chunk 重出 ≤ max_redo 次；
    - 超限仍非法 → 整块替换为 note(tone: warning)，非法内容零透传；
    - chunk 深度超过 MAX_DEPTH → 不重出，直接走既有网关丢弃路径（确定性错误，重出无益）；
    - 校验日志机读：每条含 chunk_index；纠错相关条目含 redo 计数（attempt/redo_count）。

    返回（放行 chunk 列表, 校验日志）。redo_fn 由调用方注入（模型重出，测试用 fixture 不真调 LLM）。
    """
    out: list[dict[str, Any]] = []
    log: list[dict[str, Any]] = []
    for index, raw in enumerate(chunks):
        current = _coerce_chunk(raw)
        redo_count = 0
        if _max_depth(current) > MAX_DEPTH:
            # 深度超限：既有丢弃路径（同 _validate_node 的 dropped 口径），不重出
            log.append({"action": "dropped", "where": f"depth>{MAX_DEPTH}",
                        "component": current.get("component"),
                        "chunk_index": index, "redo_count": redo_count})
            out.append(_warning_note(f"流式片段 #{index} 结构超深被丢弃"))
            continue
        while True:
            problems = _chunk_problems(current)
            if not problems:
                if redo_count:
                    log.append({"action": "chunk_fixed_after_redo", "chunk_index": index,
                                "redo_count": redo_count})
                out.append(current)
                break
            if redo_count >= max_redo:
                log.append({"action": "chunk_replaced_warning", "chunk_index": index,
                            "redo_count": redo_count, "reason": problems})
                out.append(_warning_note(f"流式片段 #{index} 重出 {redo_count} 次仍非法，整块替换"))
                break
            if redo_fn is None:
                log.append({"action": "chunk_replaced_warning", "chunk_index": index,
                            "redo_count": redo_count, "reason": problems, "no_redo_fn": True})
                out.append(_warning_note(f"流式片段 #{index} 非法且无纠错通道，整块替换"))
                break
            redo_count += 1
            log.append({"action": "redo_requested", "chunk_index": index,
                        "attempt": redo_count, "reason": problems})
            current = _coerce_chunk(redo_fn(raw))
    return out, log
