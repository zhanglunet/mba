#!/usr/bin/env python3
"""生成式 UI 图表组件（PRD-081/T3，trend #408）。

把 T2 路由出的意图渲染成自包含 HTML 片段（纯前端），供 T4 的 ask.html 插入结果区。

设计依据：docs/plans/2026-10-19-genui-matrix.md
- §2.1 意图明细表：8 意图 → 6 渲染器（delta 复用条形图 + 正负着色）
- §2.4 null 降级：缺数据 → 灰色"数据暂缺"卡，不抛异常、不画空图
- §四第3条风格：chart.js@4.4.4 CDN、--paper #faf8f3、--accent #c1440e、
  --missing-bg #f0ede7、serif 字体栈（与 dashboard.html 同套）

接口：
    render(intent, deck) -> str
        intent: 意图 ID（total/compare/radar/delta/volume/sentiment/events/rivals）
        deck:   data/deck.json 载入后的 dict（本函数按意图自己取段）
        返回:   自包含 HTML 片段（<div> + <canvas> + <script>；
                chart.js 由宿主页面用 CHART_JS_CDN 引入）

T4 接线说明：
    片段经 innerHTML 插入后，里面的 <script> 不会自动执行——宿主需把插入节点中
    的 script 标签取出重建（标准做法），再挂到 DOM。canvas id 全局唯一，
    同一页可插多个片段。

XSS：所有文本经 esc() 转义（与 dashboard.html 的 esc 同算法）；
     图表数据经 json.dumps 嵌入，并做 </ 转义防 script 突破；
     事件链接只允许 http(s)，其余一律按纯文本渲染。

纯标准库。用法：
    python3 scripts/genui_charts.py --demo        # /tmp/genui_demo.html 预览（含自测）
    python3 scripts/genui_charts.py --self-test   # 只跑断言
"""

import argparse
import html
import json
import re
import sys

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"

# 多系列调色板（PRD-099/T3 第二批，规范 §3/§8 第 4 项定版）：
# 由 7 色收敛为 series-1..5。保留：1=#c1440e(accent 本尊) 2=#1a4a7a(蓝)
# 3=#1a7a4a(正向绿) 4=#7c3aed(紫) 5=#d97706(预警橙)；
# 砍除 #0e7c86(青)/#a31e5b(品红)——现渲染器最多 5 个系列（5 lens），
# 索引 5/6 本就不可达；未来系列数 >5 时按 i%5 回绕映射到保留色。
PALETTE = ["#c1440e", "#1a4a7a", "#1a7a4a", "#7c3aed", "#d97706"]
ACCENT = "#c1440e"
ACCENT_SOFT = "rgba(193,68,14,0.10)"
POSITIVE = "#1a7a4a"
NEGATIVE = "#b3261e"
NEUTRAL = "#b9b2a6"

# ---------------------------------------------------------------- 组件目录
# PRD-098/T3 第一批（C2 组件定义契约）：7 个渲染单元的声明式元数据。
# 只做登记（name/description/props 字段表），不参与渲染逻辑；
# 供将来接入 LLM 生成 UI 时作为组件签名来源（对应 T1 拆解的
# defineComponent 概念），字段口径与各渲染器 docstring 及实际取值一致。
COMPONENTS = {
    "metric_card": {
        "renderer": "render_metric_card",
        "intents": ("total",),
        "description": "大数字卡：总分/满分 + 归一化分 + 版本·日期。",
        "props": {
            "health": {
                "type": "dict", "required": True,
                "fields": {
                    "score_total": "number，必填；为 None 时降级为暂缺卡",
                    "score_max": "number，可选，缺省 250",
                    "score_normalized": "number，可选；归一化分（/10）",
                    "report_version": "string，可选；报告版本号",
                    "report_date": "string，可选；报告日期",
                },
            },
        },
    },
    "bar": {
        "renderer": "render_bar",
        "intents": ("compare", "delta"),
        "description": "横向条形图：compare 按分值排序展示 5 lens；"
                       "delta 复用本渲染器，按 delta 正负着色。",
        "props": {
            "lenses": {
                "type": "list[dict]", "required": True,
                "fields": {
                    "key": "string，维度英文 key",
                    "name_cn": "string，维度中文名（缺省回退 key）",
                    "mean": "number，delta=False 时必填；维度均值",
                    "delta": "string，delta=True 时使用；"
                             "取值 ↔ / ↑n / ↓n（parse_delta 解析）",
                },
            },
            "title": "string，可选，缺省 “维度对比”",
            "delta": "bool，可选，缺省 False；True 时按 delta 取值并着色",
        },
    },
    "radar": {
        "renderer": "render_radar",
        "intents": ("radar",),
        "description": "5 轴雷达图：各维度均值整体画像。",
        "props": {
            "lenses": {
                "type": "list[dict]", "required": True,
                "fields": {
                    "key": "string，维度英文 key",
                    "name_cn": "string，维度中文名（缺省回退 key）",
                    "mean": "number，必填；维度均值（0-10）",
                },
            },
            "title": "string，可选，缺省 “维度雷达”",
        },
    },
    "line": {
        "renderer": "render_line",
        "intents": ("volume",),
        "description": "折线图：近 7 天每日声量走势。",
        "props": {
            "daily": {
                "type": "list[dict]", "required": True,
                "fields": {
                    "date": "string，日期",
                    "count": "number，当日声量计数",
                },
            },
            "title": "string，可选，缺省 “近 7 天声量”",
        },
    },
    "stacked_bar": {
        "renderer": "render_stacked_bar",
        "intents": ("sentiment",),
        "description": "100% 堆叠条形图：近 7 天正面/中性/负面声量求和占比。"
                       "PRD-099/T3 第二批按规范 §2.4 定版替代原 doughnut。",
        "props": {
            "daily": {
                "type": "list[dict]", "required": True,
                "fields": {
                    "positive": "number，当日正面声量",
                    "neutral": "number，当日中性声量",
                    "negative": "number，当日负面声量",
                },
            },
            "title": "string，可选，缺省 “正负面占比”",
        },
    },
    "events": {
        "renderer": "render_events",
        "intents": ("events", "rivals"),
        "description": "事件列表：标题（可链接）+ 情感徽章 + 时间/摘要；"
                       "rivals 复用本渲染器并显示品牌名。",
        "props": {
            "events": {
                "type": "list[dict]", "required": True,
                "fields": {
                    "title": "string，事件标题（缺省 “（无标题）”）",
                    "url": "string，可选；仅 http(s) 渲染为链接，其余纯文本",
                    "brand": "string，可选；show_brand=True 时显示",
                    "sentiment": "string，可选；positive/negative/neutral，"
                                 "命中才显示情感徽章",
                    "at": "string，可选；事件时间",
                    "summary": "string，可选；事件摘要",
                },
            },
            "title": "string，可选，缺省 “热点事件”",
            "subtitle": "string，可选，缺省 None（不显示副标题）",
            "show_brand": "bool，可选，缺省 False",
        },
    },
    "missing_card": {
        "renderer": "missing_card",
        "intents": (),
        "description": "null 降级卡：数据缺失/意图未知时渲染的灰色暂缺卡，"
                       "所有渲染器的降级路径。",
        "props": {
            "text": "string，可选，缺省 “数据暂缺”",
        },
    },
}

_uid_counter = [0]


def _uid(prefix="genui-canvas"):
    _uid_counter[0] += 1
    return "%s-%d" % (prefix, _uid_counter[0])


def esc(s):
    """HTML 转义（与 dashboard.html 的 esc 同算法）。"""
    return html.escape("" if s is None else str(s), quote=True)


def missing_card(text="数据暂缺"):
    """null 降级：灰色数据暂缺卡（复用 --missing-bg 口径）。"""
    return '<div class="genui-missing">%s</div>' % esc(text)


def parse_delta(s):
    """T1 §2.1：delta 字符串 → 数值。"↔"→0，"↑n"→+n，"↓n"→-n。"""
    if s is None:
        return 0.0
    s = str(s).strip()
    if s in ("", "↔", "-"):
        return 0.0
    m = re.match(r"^[↑+]\s*([\d.]+)", s)
    if m:
        return float(m.group(1))
    m = re.match(r"^[↓\-\u2212]\s*([\d.]+)", s)
    if m:
        return -float(m.group(1))
    try:
        return float(s)
    except ValueError:
        return 0.0


def _chart_js(cid, ctype, labels, datasets, options):
    config = {"type": ctype,
              "data": {"labels": labels, "datasets": datasets},
              "options": options}
    payload = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
    js = ("(function(){"
          "var el=document.getElementById(" + json.dumps(cid) + ");"
          'if(!el||typeof Chart==="undefined"){return;}'
          "new Chart(el.getContext('2d')," + payload + ");"
          "})();")
    return "<script>" + js + "</script>"


def _canvas_card(title, cid, script):
    return (
        '<div class="genui-card">'
        '<div class="genui-title">%s</div>'
        '<div class="genui-chart-box"><canvas id="%s"></canvas></div>'
        "%s"
        "</div>"
    ) % (esc(title), esc(cid), script)


_BASE_OPTIONS = {"responsive": True, "maintainAspectRatio": False,
                 "plugins": {"legend": {"display": False}}}


def _valid_lenses(lenses):
    return isinstance(lenses, list) and len(lenses) > 0


def render_metric_card(health):
    """`total` 意图：大数字卡（总分/250 + 归一化/10 + 版本·日期）。"""
    if not isinstance(health, dict) or health.get("score_total") is None:
        return missing_card("健康度数据暂缺")
    total = health.get("score_total")
    smax = health.get("score_max", 250)
    norm = health.get("score_normalized")
    ver = health.get("report_version")
    date = health.get("report_date")
    bits = []
    if norm is not None:
        bits.append("归一化 %s/10" % esc(norm))
    if ver:
        bits.append("v%s" % esc(ver))
    if date:
        bits.append(esc(date))
    sub = ('<div class="genui-metric-sub">%s</div>' % " · ".join(bits)) if bits else ""
    return (
        '<div class="genui-card genui-metric">'
        '<div class="genui-metric-total">%s<span class="genui-metric-max">/%s</span></div>'
        "%s"
        "</div>"
    ) % (esc(total), esc(smax), sub)


def render_bar(lenses, title="维度对比", delta=False):
    """`compare` 意图：5 lens 横向条形（按分值排序）。
    `delta` 意图复用本渲染器：delta=True 时解析 delta 字符串并 ↑绿/↓红/↔灰着色。"""
    if not _valid_lenses(lenses):
        return missing_card("健康度数据暂缺")
    rows = []
    for l in lenses:
        if not isinstance(l, dict):
            continue
        name = l.get("name_cn") or l.get("key") or "?"
        if delta:
            val = parse_delta(l.get("delta"))
        else:
            try:
                val = float(l.get("mean"))
            except (TypeError, ValueError):
                continue
        rows.append((name, val))
    if not rows:
        return missing_card("健康度数据暂缺")
    if not delta:
        rows.sort(key=lambda r: r[1], reverse=True)
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    if delta:
        colors = [POSITIVE if v > 0 else (NEGATIVE if v < 0 else NEUTRAL)
                  for v in values]
    else:
        colors = [PALETTE[i % len(PALETTE)] for i in range(len(values))]
    cid = _uid()
    datasets = [{"data": values, "backgroundColor": colors,
                 "borderColor": colors, "borderWidth": 1}]
    options = dict(_BASE_OPTIONS)
    options["indexAxis"] = "y"
    options["scales"] = {"x": {"beginAtZero": True}}
    return _canvas_card(title, cid,
                        _chart_js(cid, "bar", labels, datasets, options))


def render_radar(lenses, title="维度雷达"):
    """`radar` 意图：5 轴雷达（画法同 dashboard.html）。"""
    if not _valid_lenses(lenses):
        return missing_card("健康度数据暂缺")
    labels, values = [], []
    for l in lenses:
        if not isinstance(l, dict):
            continue
        try:
            v = float(l.get("mean"))
        except (TypeError, ValueError):
            continue
        labels.append(l.get("name_cn") or l.get("key") or "?")
        values.append(v)
    if not labels:
        return missing_card("健康度数据暂缺")
    cid = _uid()
    datasets = [{"label": "维度均值", "data": values,
                 "borderColor": ACCENT, "backgroundColor": ACCENT_SOFT,
                 "borderWidth": 2, "pointRadius": 3,
                 "pointBackgroundColor":
                     [PALETTE[i % len(PALETTE)] for i in range(len(values))]}]
    options = dict(_BASE_OPTIONS)
    options["scales"] = {"r": {"min": 0, "max": 10,
                               "ticks": {"stepSize": 2}}}
    return _canvas_card(title, cid,
                        _chart_js(cid, "radar", labels, datasets, options))


def render_line(daily, title="近 7 天声量"):
    """`volume` 意图：daily_volume 按 date 的 count 折线。"""
    if not isinstance(daily, list) or not daily:
        return missing_card("舆情数据暂缺")
    labels, values = [], []
    for d in daily:
        if not isinstance(d, dict):
            continue
        try:
            v = float(d.get("count", 0))
        except (TypeError, ValueError):
            v = 0.0
        labels.append(d.get("date") or "")
        values.append(v)
    if not labels:
        return missing_card("舆情数据暂缺")
    cid = _uid()
    datasets = [{"label": "声量", "data": values,
                 "borderColor": ACCENT, "backgroundColor": ACCENT_SOFT,
                 "fill": True, "tension": 0.3,
                 "borderWidth": 2, "pointRadius": 2}]
    options = dict(_BASE_OPTIONS)
    options["scales"] = {"y": {"beginAtZero": True}}
    return _canvas_card(title, cid,
                        _chart_js(cid, "line", labels, datasets, options))


def render_stacked_bar(daily, title="正负面占比"):
    """`sentiment` 意图：近 7 天 positive/negative/neutral 求和 100% 堆叠条形。
    PRD-099/T3 第二批：按图表规范 §2.4/§8 第 3 项定版，以 100% 堆叠条形
    替代原 doughnut；数据口径不变（三类声量按 7 天求和）。"""
    if not isinstance(daily, list) or not daily:
        return missing_card("舆情数据暂缺")
    pos = neu = neg = 0.0
    for d in daily:
        if not isinstance(d, dict):
            continue
        for key, acc in (("positive", "pos"), ("neutral", "neu"),
                         ("negative", "neg")):
            try:
                v = float(d.get(key, 0) or 0)
            except (TypeError, ValueError):
                v = 0.0
            if acc == "pos":
                pos += v
            elif acc == "neu":
                neu += v
            else:
                neg += v
    total = pos + neu + neg
    if total <= 0:
        return missing_card("暂无声量数据")
    cid = _uid()
    datasets = [
        {"label": "正面", "data": [pos], "backgroundColor": POSITIVE,
         "borderColor": POSITIVE, "borderWidth": 1},
        {"label": "中性", "data": [neu], "backgroundColor": NEUTRAL,
         "borderColor": NEUTRAL, "borderWidth": 1},
        {"label": "负面", "data": [neg], "backgroundColor": NEGATIVE,
         "borderColor": NEGATIVE, "borderWidth": 1},
    ]
    options = dict(_BASE_OPTIONS)
    options["indexAxis"] = "y"
    options["scales"] = {"x": {"stacked": True, "min": 0, "max": total},
                         "y": {"stacked": True}}
    return _canvas_card(title, cid,
                        _chart_js(cid, "bar", [""], datasets, options))


_SENT_LABEL = {"positive": "正面", "negative": "负面", "neutral": "中性"}
_SENT_COLOR = {"positive": POSITIVE, "negative": NEGATIVE, "neutral": NEUTRAL}


def _safe_url(url):
    """只允许 http(s) 链接，其余一律按纯文本渲染（防 javascript: 注入）。"""
    u = str(url or "").strip()
    if re.match(r"^https?://", u, re.IGNORECASE):
        return u
    return ""


def render_events(events, title="热点事件", subtitle=None, show_brand=False):
    """`events`/`rivals` 意图：事件列表（标题 + 摘要 + 情感 + 时间 + 来源链接）。"""
    if not isinstance(events, list) or not events:
        return missing_card("暂无事件数据")
    lis = []
    for e in events:
        if not isinstance(e, dict):
            continue
        t = esc(e.get("title") or "（无标题）")
        url = _safe_url(e.get("url"))
        if url:
            t_html = '<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(url), t)
        else:
            t_html = "<span>%s</span>" % t
        head = t_html
        if show_brand and e.get("brand"):
            head = "<b>%s</b> " % esc(e.get("brand")) + head
        sent = str(e.get("sentiment") or "").lower()
        badge = ""
        if sent in _SENT_LABEL:
            badge = (' <span class="genui-badge" style="background:%s">%s</span>'
                     % (_SENT_COLOR[sent], esc(_SENT_LABEL[sent])))
        meta_bits = []
        if e.get("at"):
            meta_bits.append(esc(e.get("at")))
        if e.get("summary"):
            meta_bits.append(esc(e.get("summary")))
        meta = ('<div class="genui-ev-meta">%s</div>' % " · ".join(meta_bits)) \
            if meta_bits else ""
        lis.append('<li class="genui-ev">%s%s%s</li>' % (head, badge, meta))
    if not lis:
        return missing_card("暂无事件数据")
    sub = ('<div class="genui-sub">%s</div>' % esc(subtitle)) if subtitle else ""
    return (
        '<div class="genui-card">'
        '<div class="genui-title">%s</div>'
        "%s"
        '<ul class="genui-evlist">%s</ul>'
        "</div>"
    ) % (esc(title), sub, "".join(lis))


def _lenses(deck):
    h = deck.get("health")
    return h.get("lenses") if isinstance(h, dict) else None


_genui_ir_mod = None


def _load_genui_ir():
    """加载同目录的 genui_ir 模块（兼容按路径加载本文件的环境）。

    注：本文件受 PRD-081 只读审计约束（不得 import os/subprocess 等），
    故同目录定位用 __file__ 字符串切分 + sys.path，不引入 os/pathlib。
    """
    global _genui_ir_mod
    if _genui_ir_mod is not None:
        return _genui_ir_mod
    mod = sys.modules.get("genui_ir")
    if mod is None:
        for m in list(sys.modules.values()):
            f = getattr(m, "__file__", None)
            if f and f.replace("\\", "/").rsplit("/", 1)[-1] \
                    == "genui_ir.py":
                mod = m
                break
    if mod is None:
        try:
            import genui_ir as mod
        except ImportError:
            here = __file__.replace("\\", "/").rsplit("/", 1)[0] \
                if "/" in __file__ else "."
            if here not in sys.path:
                sys.path.insert(0, here)
            import genui_ir as mod
    _genui_ir_mod = mod
    return mod


def render(intent, deck):
    """意图 → HTML 片段（含 §2.4 null 降级）。

    PRD-098/T3 M1 第 1 步：实现改为垫片——经 genui_ir.compose() 把
    意图 + deck 编译为 IR 文档，再由 genui_ir.render_ir() 按节点 type
    分发渲染；对外行为与 IR 化前逐字一致（黄金快照锁死）。unknown
    意图不产 IR（compose 返回 None），沿用"未知意图"降级；deck 非
    dict 时 compose 直接产 missing_card 文档（"数据暂缺"先行口径不变）。
    """
    ir = _load_genui_ir()
    doc = ir.compose(intent, deck)
    if doc is not None:
        return ir.render_ir(doc)
    if not isinstance(deck, dict):
        return missing_card()
    return missing_card("未知意图")


# ---------------------------------------------------------------- 自测

def _demo_deck():
    lenses = [
        {"key": "origin", "name_cn": "本源", "mean": 8.6, "delta": "↔"},
        {"key": "category", "name_cn": "品类", "mean": 8.2, "delta": "↔"},
        {"key": "leverage", "name_cn": "杠杆", "mean": 7.8, "delta": "↔"},
        {"key": "identity", "name_cn": "身份", "mean": 8.0, "delta": "↔"},
        {"key": "signal", "name_cn": "信号", "mean": 9.0, "delta": "↑0.2"},
    ]
    daily = [{"date": "2026-10-%02d" % d, "count": 10 + d * 3,
              "positive": 5 + d, "neutral": 3, "negative": 2}
             for d in range(13, 20)]
    return {
        "brand": "deepseek",
        "health": {"score_total": 208, "score_max": 250,
                   "score_normalized": 8.32,
                   "report_version": "3", "report_date": "2026-07-20",
                   "lenses": lenses},
        "sentiment": {
            "daily_volume": daily,
            "top_events": [
                {"title": "DeepSeek 完成首轮融资",
                 "summary": "估值约 3500 亿元",
                 "sentiment": "positive",
                 "at": "2026-10-18", "url": "https://example.com/a"},
                {"title": "<script>alert(1)</script>注入测试",
                 "summary": "XSS 转义验证",
                 "sentiment": "neutral",
                 "at": "2026-10-17", "url": "javascript:alert(1)"},
            ],
        },
        "competitors": {
            "watch_list": ["openai", "anthropic"],
            "events": [
                {"brand": "OpenAI", "title": "发布新模型",
                 "at": "2026-10-18", "url": "https://example.com/b"},
            ],
        },
    }


def self_test():
    """断言：8 意图渲染 + null 降级 + XSS + delta 解析 + id 唯一。"""
    deck = _demo_deck()
    ok = []

    def check(name, cond):
        ok.append((name, bool(cond)))
        print("[%s] %s" % ("PASS" if cond else "FAIL", name))

    # 1. 8 意图全跑通
    outs = {}
    for intent in ("total", "compare", "radar", "delta", "volume",
                   "sentiment", "events", "rivals"):
        try:
            outs[intent] = render(intent, deck)
            check("render:" + intent, isinstance(outs[intent], str)
                  and len(outs[intent]) > 50)
        except Exception as e:  # noqa: BLE001
            check("render:" + intent + " (%s)" % e, False)
            outs[intent] = ""

    # 2. 输出形态标记
    check("metric card", "genui-metric-total" in outs["total"]
          and "208" in outs["total"])
    check("bar chart", '"bar"' in outs["compare"])
    check("radar chart", '"radar"' in outs["radar"])
    check("delta colors", '"bar"' in outs["delta"]
          and NEGATIVE not in outs["delta"]  # 本轮无负值
          and POSITIVE in outs["delta"])
    check("line chart", '"line"' in outs["volume"])
    check("stacked bar chart", '"bar"' in outs["sentiment"]
          and '"stacked": true' in outs["sentiment"]
          and '"doughnut"' not in outs["sentiment"])
    check("event list", "genui-evlist" in outs["events"]
          and "genui-evlist" in outs["rivals"])
    check("rivals watch_list", "openai" in outs["rivals"])

    # 3. null 降级（§2.4）
    check("null deck", "数据暂缺" in render("total", None))
    check("health null", "数据暂缺" in render("compare", {"health": None}))
    check("sentiment null", "数据暂缺" in render("volume", {"sentiment": None}))
    check("competitors null", "数据暂缺" in render("rivals", {"competitors": None}))
    check("empty lenses", "数据暂缺" in render_bar([]))
    check("unknown intent", "未知意图" in render("nope", deck))

    # 4. XSS
    check("xss escaped", "&lt;script&gt;" in outs["events"]
          and "<script>alert(1)</script>" not in outs["events"])
    check("js url dropped", "javascript:alert" not in outs["events"])

    # 5. delta 解析
    check("delta parse", parse_delta("↔") == 0.0
          and parse_delta("↑0.2") == 0.2
          and parse_delta("↓0.4") == -0.4
          and parse_delta(None) == 0.0)

    # 6. canvas id 唯一
    ids = re.findall(r'id="(genui-canvas-\d+)"', "".join(outs.values()))
    check("unique canvas ids", len(ids) == len(set(ids)) and len(ids) == 5)

    failed = [n for n, c in ok if not c]
    print("自测：%d/%d 通过" % (len(ok) - len(failed), len(ok)))
    return 1 if failed else 0


DEMO_CSS = """
:root{--paper:#faf8f3;--ink:#111;--muted:#6b6760;--accent:#c1440e;--missing-bg:#f0ede7;}
body{background:var(--paper);color:var(--ink);
 font-family:ui-serif,"Noto Serif SC","Songti SC","Noto Serif",Georgia,serif;
 max-width:760px;margin:0 auto;padding:32px 20px;}
.genui-card{background:#fff;border:1px solid #e0ddd8;border-radius:8px;
 padding:16px 18px;margin:0 0 20px;}
.genui-title{font-size:14px;font-weight:700;margin-bottom:10px;}
.genui-chart-box{position:relative;height:260px;}
.genui-missing{background:var(--missing-bg);color:var(--muted);
 border-radius:8px;padding:28px;text-align:center;font-size:14px;}
.genui-metric-total{font-size:44px;font-weight:800;color:var(--accent);}
.genui-metric-max{font-size:20px;color:var(--muted);font-weight:400;}
.genui-metric-sub{font-size:13px;color:var(--muted);margin-top:6px;}
.genui-sub{font-size:12px;color:var(--muted);margin:-4px 0 10px;}
.genui-evlist{list-style:none;margin:0;padding:0;display:flex;
 flex-direction:column;gap:10px;}
.genui-ev{font-size:14px;line-height:1.6;border-bottom:1px solid #eee;padding-bottom:8px;}
.genui-ev a{color:var(--ink);}
.genui-ev-meta{font-size:12px;color:var(--muted);margin-top:2px;}
.genui-badge{font-size:11px;color:#fff;border-radius:4px;padding:1px 6px;}
h2{font-size:16px;margin:28px 0 12px;color:var(--accent);}
"""


def build_demo(path="/tmp/genui_demo.html"):
    deck = _demo_deck()
    parts = ['<h1>genui_charts.py 渲染器预览（假数据）</h1>']
    for intent, label in (("total", "total · 指标卡"),
                          ("compare", "compare · 条形图"),
                          ("radar", "radar · 雷达图"),
                          ("delta", "delta · delta 条形图"),
                          ("volume", "volume · 折线图"),
                          ("sentiment", "sentiment · 100% 堆叠条形图"),
                          ("events", "events · 事件列表（含 XSS 测试）"),
                          ("rivals", "rivals · 竞品事件列表")):
        parts.append("<h2>%s</h2>" % label + render(intent, deck))
    parts.append("<h2>null 降级</h2>" + render("volume", {"sentiment": None}))
    body = "\n".join(parts)
    page = ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<title>genui demo</title><style>" + DEMO_CSS + "</style>"
            '<script src="' + CHART_JS_CDN + '"></script>'
            "</head><body>" + body + "</body></html>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path


def main():
    ap = argparse.ArgumentParser(description="生成式 UI 图表组件（PRD-081/T3）")
    ap.add_argument("--demo", action="store_true",
                    help="先跑自测，再生成 /tmp/genui_demo.html 预览")
    ap.add_argument("--self-test", action="store_true", help="只跑自测断言")
    args = ap.parse_args()
    if args.self_test or args.demo:
        rc = self_test()
        if rc != 0:
            return rc
    if args.demo:
        p = build_demo()
        print("demo 已生成：" + p)
    if not (args.self_test or args.demo):
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
