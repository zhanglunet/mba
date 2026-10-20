#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-081/T5 端到端验收：生成式 UI 问答 demo。

覆盖（纯标准库）：
  1. 20 个黄金问题：路由意图正确 + 渲染输出含预期图表类型标记 + 数据正确
  2. 5 个 fallback 问题：全部走 unknown，输出含 T1 §3.2 固定逐字稿、无图表
  3. 只读审计：静态扫描（无文件写、无 POST、无 localStorage 写）+ 运行前后文件清单对比
  4. null 降级：sentiment/competitors 置 null 时显示降级卡片、不画空图、不崩
  5. 确定性：同一问题 3 遍结果一致
  6. 风格一致性：chart.js@4.4.4 + 指挥舱配色（#faf8f3/#c1440e）
  7. JS/Python 路由一致性：ask.html 内 route()（node 跑）vs scripts/ask_router.py

运行：python3 test_genui_e2e.py   （仓库根目录下）
退出码：0=全部通过，非 0=有失败。
"""
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("[%s] %s%s" % ("PASS" if cond else "FAIL", name,
                         (" -- " + detail) if detail and not cond else ""))


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


router = load_mod("ask_router", os.path.join(REPO, "scripts", "ask_router.py"))
charts = load_mod("genui_charts", os.path.join(REPO, "scripts", "genui_charts.py"))
route = router.route
render = charts.render


def make_deck(sentiment=True, competitors=True):
    deck = {
        "brand": "deepseek",
        "health": {
            "score_total": 208, "score_max": 250, "score_normalized": 8.32,
            "report_version": "3", "report_date": "2026-07-20",
            "lenses": [
                {"key": "origin", "name_cn": "本源", "mean": 8.6, "delta": "<->"},
                {"key": "category", "name_cn": "品类", "mean": 8.2, "delta": "<->"},
                {"key": "leverage", "name_cn": "杠杆", "mean": 7.8, "delta": "-0.3"},
                {"key": "identity", "name_cn": "人设", "mean": 8.0, "delta": "<->"},
                {"key": "signal", "name_cn": "信号", "mean": 9.0, "delta": "+0.2"},
            ],
        },
    }
    if sentiment:
        deck["sentiment"] = {
            "daily_volume": [
                {"date": "2026-10-%02d" % d, "count": 10 + d,
                 "positive": 5, "negative": 2, "neutral": 3}
                for d in range(11, 18)
            ],
            "top_events": [
                {"title": "融资落地", "summary": "完成首轮融资",
                 "sentiment": "pos", "at": "2026-10-18",
                 "url": "https://example.com/1"},
            ],
        }
    else:
        deck["sentiment"] = None
    if competitors:
        deck["competitors"] = {
            "watch_list": ["openai", "anthropic"],
            "events": [
                {"brand": "openai", "title": "发布新模型",
                 "at": "2026-10-17", "url": "https://example.com/2"},
            ],
        }
    else:
        deck["competitors"] = None
    return deck


# T1 §六 黄金问题集（20 个：8 意图 × 2–3 种问法）
GOLDEN = [
    ("综合评分多少？", "total"),
    ("deepseek 现在多少分？", "total"),
    ("归一化评分是多少？", "total"),
    ("哪个维度最弱？", "compare"),
    ("五个维度排个序", "compare"),
    ("五个维度整体什么样？", "radar"),
    ("画一下维度雷达", "radar"),
    ("品牌画像如何？", "radar"),
    ("和上版比变了多少？", "delta"),
    ("总分涨了还是跌了？", "delta"),
    ("哪个维度变化最大？", "delta"),
    ("最近 7 天声量怎么样？", "volume"),
    ("每天的讨论量画出来", "volume"),
    ("声量走势如何？", "volume"),
    ("正负面占比怎么样？", "sentiment"),
    ("负面多吗？", "sentiment"),
    ("最近有什么大事？", "events"),
    ("Top 热点事件有哪些？", "events"),
    ("竞品在干什么？", "rivals"),
    ("对手有什么新动作？", "rivals"),
]

# T1 §六 fallback 集（5 个，全部走 §3.2 逐字稿）
FALLBACK_QS = [
    "今天天气怎么样？",
    "帮我把报告重审一下",
    "把摘要发到飞书群",
    "deepseek 股价多少？",
    "明年品牌影响力会涨吗？",
]

# 意图 → 渲染输出必须含的标记（图表类型 + 数据正确性）
CHART_MARK = {
    "total": ["208", "250"],
    "compare": ['"type": "bar"', "本源"],
    "radar": ['"type": "radar"', "信号"],
    "delta": ['"type": "bar"', "-0.3"],
    "volume": ['"type": "line"', "2026-10-11"],
    "sentiment": ['"type": "bar"', '"stacked": true'],
    "events": ["融资落地"],
    "rivals": ["openai", "发布新模型"],
}

DECK = make_deck()


def test_golden_routing():
    for q, exp in GOLDEN:
        got = route(q)
        check("路由: %s -> %s" % (q, exp), got == exp,
              "实际=%s" % got)


def test_golden_render():
    for q, exp in GOLDEN:
        html = render(exp, DECK)
        marks = CHART_MARK[exp]
        ok = all(m in html for m in marks)
        check("渲染: %s 含 %s" % (exp, "/".join(marks[:2])), ok,
              "缺失标记" if not ok else "")
        if exp in ("total", "events", "rivals"):
            check("渲染: %s 非图表形态无 new Chart" % exp,
                  "new Chart" not in html)
        else:
            check("渲染: %s 含 new Chart" % exp, "new Chart" in html)


def test_fallback():
    for q in FALLBACK_QS:
        got = route(q)
        check("fallback 路由: %s -> unknown" % q, got == "unknown",
              "实际=%s" % got)


def test_fallback_verbatim():
    html_src = open(os.path.join(REPO, "ask.html"),
                    encoding="utf-8").read()
    verbatim = "这个问题我答不上来。这个 demo 是只读的"
    check("ask.html 含 T1 §3.2 固定逐字稿", verbatim in html_src)
    m = re.search(r"var FALLBACK_HTML\s*=(.*?);", html_src, re.S)
    fb = m.group(1) if m else ""
    check("fallback 纯文本无图表",
          "new Chart" not in fb and "canvas" not in fb.lower())


def test_null_degradation():
    d = make_deck(sentiment=False, competitors=False)
    cases = [
        ("volume", "数据暂缺"),
        ("sentiment", "数据暂缺"),
        ("events", "暂无事件数据"),
        ("rivals", "竞品数据暂缺"),
    ]
    for intent, expect_text in cases:
        html = render(intent, d)
        check("null 降级: %s 显示「%s」" % (intent, expect_text),
              expect_text in html)
        check("null 降级: %s 不画空图" % intent, "new Chart" not in html)
    html = render("total", d)
    check("null 降级: total 不受 sentiment null 影响", "208" in html)


def test_determinism():
    qs = [q for q, _ in GOLDEN] + FALLBACK_QS
    r1 = [route(q) for q in qs]
    r2 = [route(q) for q in qs]
    r3 = [route(q) for q in qs]
    check("确定性: 25 题 x 3 遍一致", r1 == r2 == r3)


def test_readonly_static():
    src = open(os.path.join(REPO, "ask.html"), encoding="utf-8").read()
    check("只读: ask.html 无 POST",
          not re.search(r"method\s*:\s*['\"]POST['\"]", src, re.I))
    check("只读: ask.html 无 XMLHttpRequest", "XMLHttpRequest" not in src)
    check("只读: ask.html 无 localStorage 写",
          "localStorage.setItem" not in src and "localStorage[" not in src)
    check("只读: ask.html 仅一处 fetch（读 deck.json）",
          src.count("fetch(") == 1 and 'fetch("data/deck.json")' in src)
    for fname in ("scripts/ask_router.py", "scripts/genui_charts.py"):
        tree = ast.parse(open(os.path.join(REPO, fname),
                              encoding="utf-8").read())
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                name = (f.attr if isinstance(f, ast.Attribute)
                        else getattr(f, "id", ""))
                if name in ("system", "popen", "Popen", "urlopen",
                            "request", "socket", "connect"):
                    bad.append(name)
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in ("socket", "urllib",
                                                "http", "subprocess", "os"):
                        bad.append("import " + a.name)
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in ("socket", "urllib",
                                                 "http", "subprocess", "os"):
                    bad.append("from " + node.module)
        check("只读: %s 无网络/系统调用" % fname, not bad, ",".join(bad))
        src_py = open(os.path.join(REPO, fname), encoding="utf-8").read()
        # build_demo/main 是开发者 --demo 预览 CLI（显式调用才写文件），
        # 不在问答链路（route/render）上；审计时排除这两个函数体
        no_demo = re.sub(
            r"def (build_demo|main)\(.*?(?=\ndef |\Z)", "", src_py, flags=re.S)
        writes = re.findall(r"open\([^)]*['\"][wa][^'\"]*['\"]", no_demo)
        check("只读: %s 问答链路无文件写 open()" % fname, not writes,
              ",".join(writes))


def test_readonly_runtime():
    before = set()
    for dp, dn, fn in os.walk(REPO):
        for f in fn:
            before.add(os.path.join(dp, f))
    for q, _ in GOLDEN:
        render(route(q), DECK)
    for q in FALLBACK_QS:
        route(q)
    after = set()
    for dp, dn, fn in os.walk(REPO):
        for f in fn:
            after.add(os.path.join(dp, f))
    new_files = after - before
    check("只读: 运行全程无新文件产生", not new_files,
          ",".join(sorted(new_files)[:3]))


def test_style():
    py_src = open(os.path.join(REPO, "scripts", "genui_charts.py"),
                  encoding="utf-8").read()
    check("风格: 图表组件用 chart.js@4.4.4",
          "chart.js@4.4.4" in py_src)
    check("风格: 图表组件用指挥舱配色",
          "#c1440e" in py_src and "#faf8f3" in py_src)
    html_src = open(os.path.join(REPO, "ask.html"), encoding="utf-8").read()
    check("风格: ask.html 引 chart.js@4.4.4", "chart.js@4.4.4" in html_src)
    check("风格: ask.html 用指挥舱配色",
          "#c1440e" in html_src and "#faf8f3" in html_src)


def test_js_route_consistency():
    """ask.html 内 route()（node 跑）vs Python route()：25 题全一致。"""
    src = open(os.path.join(REPO, "ask.html"), encoding="utf-8").read()
    m = re.search(r"/\* =+ BEGIN route\(\).*?/\* =+ END route\(\) =+ \*/",
                  src, re.S)
    if not m:
        check("JS 路由一致性: 找到 route 块", False)
        return
    driver = m.group(0) + """
var qs = %s;
var out = qs.map(function(q){ return route(q); });
console.log(JSON.stringify(out));
""" % json.dumps([q for q, _ in GOLDEN] + FALLBACK_QS, ensure_ascii=False)
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        f.write(driver)
        js_path = f.name
    try:
        r = subprocess.run(["node", js_path], capture_output=True,
                           text=True, timeout=30)
        if r.returncode != 0:
            check("JS 路由一致性: node 执行成功", False, r.stderr[:200])
            return
        js_out = json.loads(r.stdout.strip())
    finally:
        os.unlink(js_path)
    py_out = [route(q) for q, _ in GOLDEN] + [route(q) for q in FALLBACK_QS]
    check("JS 路由一致性: 25 题 JS 与 Python 结果一致", js_out == py_out,
          "差异数=%d" % sum(1 for a, b in zip(js_out, py_out) if a != b))


def main():
    test_golden_routing()
    test_golden_render()
    test_fallback()
    test_fallback_verbatim()
    test_null_degradation()
    test_determinism()
    test_readonly_static()
    test_readonly_runtime()
    test_style()
    test_js_route_consistency()
    print("")
    print("通过: %d / 失败: %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：")
        for n in FAIL:
            print("  - " + n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
