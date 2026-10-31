#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-261/T4（trend #1308）：服务端权限双路——渲染过滤 + 服务端独立校验（隐藏控件≠有权）。

按 PRD-261 红线「权限在服务端校验；隐藏控件≠有权」实现：
  渲染路 filter_by_session：用户无权的动作类组件（evidence-link/table-view）从组件树中
    过滤（含其子树）——前端看不到即点不到（纵深防御第一层，不是授权依据）；
  服务端路 authorize_action：与渲染无关的独立校验——直接按 (component, action) 查会话权限，
    无权 raise PermissionError。前端隐藏/绕过渲染过滤直接打端点，照样被拒。

双路断言核心：同一权限模型下「渲染过滤 ≠ 授权」——渲染层滤掉的同时，服务端直调
authorize_action 对无权会话仍然抛错；两路各自独立成立，任一单独失效不构成放行。

权限模型（最小封闭）：
  ACTION_ENDPOINTS：动作类组件 → 服务端端点封闭映射；其余组件无服务端动作；
  session_perms：形如 "component:action" 的授权条目集合（perm_key 规范化）；
  权限按组件类型判定（同类型实例同权限，不看实例 id）；
  未知组件 / 未知动作 / 会话无条目 → 一律默认拒（deny by default）。

零网络；示例数据全虚构；不含真实主机名、账号、密钥。

运行自测：python3 -m pytest tests/unit/test_board_authz.py -q
"""
from __future__ import annotations

import copy
from typing import Any, Iterable

# 动作类组件 → 服务端端点（封闭清单；清单外组件不构成服务端动作，直接默认拒）
ACTION_ENDPOINTS: dict[str, str] = {
    "evidence-link": "open_evidence",
    "table-view": "export_rows",
}


def perm_key(component: str, action: str) -> str:
    """权限条目规范化形态：component:action。"""
    return f"{component}:{action}"


def _as_perm_set(session_perms: Iterable[str] | None) -> set[str]:
    """会话权限归一化为条目集合（None → 空集 = 全拒）。"""
    if session_perms is None:
        return set()
    return {str(p).strip() for p in session_perms if str(p).strip()}


def authorize_action(component: str, action: str, session_perms: Iterable[str] | None) -> str:
    """服务端独立校验（与渲染无关）：直接查权限，无权 raise PermissionError。

    参数：
      component：组件类型名（如 evidence-link）；
      action：请求的服务端动作/端点名（如 open_evidence）；
      session_perms：会话授权条目集合（"component:action" 形态）。

    默认拒（任一不满足即抛 PermissionError）：
      - component 不在 ACTION_ENDPOINTS（未知组件动作）；
      - action 与该组件映射端点不符；
      - 会话权限不含 component:action。
    通过返回放行的端点名（供服务端路由）。权限按组件类型判定，不看实例 id。
    """
    endpoint = ACTION_ENDPOINTS.get(component)
    if endpoint is None:
        raise PermissionError(f"未知动作组件 {component!r}：默认拒")
    if action != endpoint:
        raise PermissionError(f"组件 {component!r} 不提供动作 {action!r}：默认拒")
    key = perm_key(component, action)
    if key not in _as_perm_set(session_perms):
        raise PermissionError(f"会话无权限 {key}：拒绝执行")
    return endpoint


def filter_by_session(
    tree: dict[str, Any], session_perms: Iterable[str] | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """渲染路过滤：无权动作组件从树中剔除（含其子树）。返回（净树, 过滤日志）。

    - 只动 ACTION_ENDPOINTS 内的动作类组件；其余组件（含未知组件，交网关校验层）原样保留；
    - 不改输入树（深拷贝后过滤）；
    - 过滤日志机读：{action: filtered_no_perm, component, permission, where}；
    - 根节点若为无权动作组件（非 panel 的异常输入），替换为 warning note，不透出原节点。
    """
    perms = _as_perm_set(session_perms)
    log: list[dict[str, Any]] = []
    filtered = _filter_node(copy.deepcopy(tree), perms, log, where="root")
    if filtered is None:
        return _warning_note("根组件因无权限被过滤"), log
    return filtered, log


def _filter_node(
    node: Any, perms: set[str], log: list[dict[str, Any]], where: str = "children"
) -> Any:
    if not isinstance(node, dict):
        return node
    name = node.get("component")
    endpoint = ACTION_ENDPOINTS.get(name) if isinstance(name, str) else None
    if endpoint is not None:
        key = perm_key(name, endpoint)
        if key not in perms:
            log.append({"action": "filtered_no_perm", "component": name,
                        "permission": key, "where": where})
            return None
    props = node.get("props")
    if isinstance(props, dict):
        children = props.get("children")
        if isinstance(children, list):
            kept: list[Any] = []
            for child in children:
                cleaned = _filter_node(child, perms, log, where=where)
                if cleaned is not None:
                    kept.append(cleaned)
            props["children"] = kept
    return node


def _warning_note(body: str) -> dict[str, Any]:
    return {"component": "note", "props": {"body": body[:300], "tone": "warning"}}
