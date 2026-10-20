#!/usr/bin/env python3
"""生成式 UI 中间表示（IR）层（PRD-098/T3 第二批 M1 第 0+1 步，issue #272）。

设计稿：issue #272 的 M1 设计（JSON 载体 / props 按值内嵌 / children v1
只定义不启用 / unknown 不产 IR，用户 2026-10-20 定版）。

职责：把现状 `genui_charts.render(intent, deck)` 内部的"意图→组件映射 +
deck 切片"知识独立成一份自包含的 JSON 文档（IR），生成方与渲染方只认 IR：

    route() ──▶ intent ──compose(intent, deck)──▶ IR 文档 ──render_ir(doc)──▶ HTML

IR 文档信封：{ir, intent, router_spec, deck_schema, root}
  ir          本模块 IR_VERSION：产出方↔渲染方协议版本
  intent      溯源元数据（渲染分发不依赖它，只看节点 type）
  router_spec ask_router.ROUTER_SPEC_VERSION：产出方规范版本戳
  deck_schema build_deck_json.DECK_SCHEMA_VERSION：数据格式版本戳
  root        组件节点 {type, props, children}；v1 恒为单节点

节点 type 白名单 = genui_charts.COMPONENTS 注册表的 key（白名单即安全
边界）；props 字段口径直接沿用注册表，不另立第二份 schema。props 只允许
纯 JSON 数据，不允许函数/表达式/HTML 字符串。

降级双保险（文案与现状 genui_charts 逐字一致，黄金快照锁死）：
  1. binder 层（数据段级）：compose() 切段时，段为 null/非预期类型直接
     产 missing_card 节点，text 用现状对应文案；
  2. 渲染器层（字段级）：render_ir() 入口校验（版本主号、type 白名单、
     注册表 required props 的粗类型）不过 → 按组件语境降级 missing_card；
     各渲染器原有的防御式取值与降级逻辑原样保留。

unknown 意图不产 IR：compose() 返回 None，调用方沿用既有 fallback
（genui_charts.render 垫片落到"未知意图"卡）。

版本演进（与 ROUTER_SPEC_VERSION 规则同构）：不兼容变更（删/改信封必填
字段、改节点结构、删组件、改 props 既有字段语义）递增 IR 主版本，渲染器
只接受同主版本；兼容变更（新增可选 props/组件/信封可选字段）递增次
版本，渲染器必须忽略不认识的可选字段。

纯标准库。JS 双实现（ask.html 内 composeIR/renderIR）为迁移第 2 步，
本步只落 Python 侧。
"""

import importlib
import importlib.util
import os
import sys

# IR 协议版本（PRD-098/T3 M1 第 0 步规格冻结）：信封字段、节点结构、
# 组件名集合与 props 口径的版本。与 ROUTER_SPEC_VERSION（产出方语义）、
# DECK_SCHEMA_VERSION（数据格式）组成三戳配对矩阵，compose() 盖进信封。
IR_VERSION = "1.0.0"
SUPPORTED_IR_MAJOR = 1

_INTENTS = ("total", "compare", "radar", "delta",
            "volume", "sentiment", "events", "rivals")

# render_ir 校验失败时按组件语境的降级文案（与 genui_charts 各渲染器
# 现状文案逐字一致）：数据段语境 → 对应段的暂缺文案。
_FALLBACK_TEXT = {
    "metric_card": "健康度数据暂缺",
    "bar": "健康度数据暂缺",
    "radar": "健康度数据暂缺",
    "line": "舆情数据暂缺",
    "stacked_bar": "舆情数据暂缺",
    "events": "暂无事件数据",
    "missing_card": "数据暂缺",
}

_sibling_cache = {}


def _sibling(name):
    """加载同目录模块（genui_charts / ask_router / build_deck_json）。

    兼容三种加载环境：scripts/ 在 sys.path 时的普通 import、调用方用
    importlib 按路径加载（可能未注册进 sys.modules）、本模块被按路径
    加载。按 sys.modules 注册名 → 已加载模块的 __file__ → import →
    同目录文件路径 的顺序解析，尽量拿到已加载的同一份模块。
    """
    if name in _sibling_cache:
        return _sibling_cache[name]
    mod = sys.modules.get(name)
    if mod is None or not hasattr(mod, "__file__"):
        mod = None
        for m in list(sys.modules.values()):
            f = getattr(m, "__file__", None)
            if f and os.path.basename(f) == name + ".py":
                mod = m
                break
    if mod is None:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            here = os.path.dirname(os.path.abspath(__file__))
            spec = importlib.util.spec_from_file_location(
                name, os.path.join(here, name + ".py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
    _sibling_cache[name] = mod
    return mod


def _charts():
    return _sibling("genui_charts")


def _router_spec_version():
    try:
        return _sibling("ask_router").ROUTER_SPEC_VERSION
    except Exception:  # noqa: BLE001 —— 盖戳失败不阻断渲染，退回同批发布口径
        return "1.0.0"


def _deck_schema_version():
    try:
        return _sibling("build_deck_json").DECK_SCHEMA_VERSION
    except Exception:  # noqa: BLE001 —— 同上
        return "1.0.0"


def _node(type_, props):
    return {"type": type_, "props": props, "children": []}


def _missing_node(text):
    return _node("missing_card", {"text": text})


def _envelope(intent, root):
    return {
        "ir": IR_VERSION,
        "intent": intent,
        "router_spec": _router_spec_version(),
        "deck_schema": _deck_schema_version(),
        "root": root,
    }


def compose(intent, deck):
    """binder：意图 + deck → IR 文档（纯 JSON 可序列化）。

    intent 为 "unknown" 或不在 8 意图内 → 返回 None（不产 IR）。
    deck 非 dict → 产 missing_card 文档（与现状 render 的 deck 校验
    先行口径一致：任何意图先落"数据暂缺"）。其余按设计稿 §3.4 映射表
    切 deck、组 props、盖三戳；数据段为 null/非预期类型时在 binder 层
    直接降级为 missing_card 节点（文案与现状逐字一致）。
    """
    if not isinstance(deck, dict):
        return _envelope(intent, _missing_node("数据暂缺"))
    if intent not in _INTENTS:
        return None
    health = deck.get("health")
    sentiment = deck.get("sentiment")
    competitors = deck.get("competitors")

    if intent == "total":
        if isinstance(health, dict):
            root = _node("metric_card", {"health": health})
        else:
            root = _missing_node("健康度数据暂缺")
    elif intent in ("compare", "delta", "radar"):
        lenses = health.get("lenses") if isinstance(health, dict) else None
        if not isinstance(lenses, list):
            root = _missing_node("健康度数据暂缺")
        elif intent == "compare":
            root = _node("bar", {"lenses": lenses, "title": "维度对比",
                                 "delta": False})
        elif intent == "delta":
            root = _node("bar", {"lenses": lenses, "title": "版本变化",
                                 "delta": True})
        else:
            root = _node("radar", {"lenses": lenses, "title": "维度雷达"})
    elif intent in ("volume", "sentiment"):
        daily = (sentiment.get("daily_volume")
                 if isinstance(sentiment, dict) else None)
        if not isinstance(daily, list):
            root = _missing_node("舆情数据暂缺")
        elif intent == "volume":
            root = _node("line", {"daily": daily, "title": "近 7 天声量"})
        else:
            root = _node("stacked_bar", {"daily": daily,
                                         "title": "正负面占比"})
    elif intent == "events":
        evs = (sentiment.get("top_events")
               if isinstance(sentiment, dict) else None)
        if not isinstance(evs, list):
            root = _missing_node("暂无事件数据")
        else:
            root = _node("events", {"events": evs, "title": "热点事件"})
    else:  # rivals
        if not isinstance(competitors, dict):
            root = _missing_node("竞品数据暂缺")
        else:
            evs = competitors.get("events")
            if not isinstance(evs, list):
                root = _missing_node("暂无事件数据")
            else:
                wl = competitors.get("watch_list") or []
                sub = (("对标品牌：" + "、".join(str(w) for w in wl))
                       if wl else None)
                root = _node("events", {"events": evs, "title": "竞品动态",
                                        "subtitle": sub, "show_brand": True})
    return _envelope(intent, root)


def _type_ok(value, tname):
    """按注册表 type 字段做粗类型核对（细校验仍归各渲染器防御式取值）。"""
    if tname == "dict":
        return isinstance(value, dict)
    if tname.startswith("list"):
        return isinstance(value, list)
    if tname == "string":
        return isinstance(value, str)
    if tname == "bool":
        return isinstance(value, bool)
    if tname == "number":
        return isinstance(value, (int, float)) \
            and not isinstance(value, bool)
    return True


def _render_node(node):
    charts = _charts()
    if not isinstance(node, dict):
        return charts.missing_card()
    ntype = node.get("type")
    spec = charts.COMPONENTS.get(ntype) if isinstance(ntype, str) else None
    if spec is None:
        return charts.missing_card()
    props = node.get("props")
    if not isinstance(props, dict):
        props = {}
    for pname, pspec in spec.get("props", {}).items():
        if isinstance(pspec, dict) and pspec.get("required"):
            if pname not in props \
                    or not _type_ok(props[pname], pspec.get("type", "")):
                return charts.missing_card(
                    _FALLBACK_TEXT.get(ntype, "数据暂缺"))
    children = node.get("children")
    if isinstance(children, list):
        # v1 无容器组件：递归机制先行（校验链走通），子节点输出不拼装；
        # C4 注册容器组件后在此按组件契约拼装。
        for child in children:
            _render_node(child)
    return _dispatch(ntype, props, charts)


def _dispatch(ntype, props, charts):
    """按 type 分发到 genui_charts 渲染器（函数签名不动，props 摊平调用）。"""
    if ntype == "metric_card":
        return charts.render_metric_card(props.get("health"))
    if ntype == "bar":
        return charts.render_bar(props.get("lenses"),
                                 title=props.get("title", "维度对比"),
                                 delta=props.get("delta", False))
    if ntype == "radar":
        return charts.render_radar(props.get("lenses"),
                                   title=props.get("title", "维度雷达"))
    if ntype == "line":
        return charts.render_line(props.get("daily"),
                                  title=props.get("title", "近 7 天声量"))
    if ntype == "stacked_bar":
        return charts.render_stacked_bar(
            props.get("daily"), title=props.get("title", "正负面占比"))
    if ntype == "events":
        return charts.render_events(props.get("events"),
                                    title=props.get("title", "热点事件"),
                                    subtitle=props.get("subtitle"),
                                    show_brand=props.get("show_brand", False))
    if ntype == "missing_card":
        return charts.missing_card(props.get("text", "数据暂缺"))
    return charts.missing_card()


def render_ir(doc):
    """渲染器入口：IR 文档 → HTML 片段。

    入口校验（与 JS 侧第 2 步同口径）：doc 必须是 dict、ir 主版本受
    支持、root 为节点 dict；任一不过 → missing_card 降级，不抛异常、
    不渲染半成品。分发只看节点 type，不看 intent。
    """
    charts = _charts()
    if not isinstance(doc, dict):
        return charts.missing_card()
    irv = doc.get("ir")
    if not isinstance(irv, str):
        return charts.missing_card()
    try:
        major = int(irv.split(".")[0])
    except ValueError:
        return charts.missing_card()
    if major != SUPPORTED_IR_MAJOR:
        return charts.missing_card()
    root = doc.get("root")
    if not isinstance(root, dict):
        return charts.missing_card()
    return _render_node(root)
