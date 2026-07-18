#!/usr/bin/env python3
"""build_watch_cockpit.py — 舆情驾驶舱看板(docs/20 Phase 3)。

为每个有事件的品牌生成 site/watch/<slug>/cockpit.html:管理层视角的舆情看板,
把该品牌 watch/<slug>/events.yaml 聚合成——
  · 管理层摘要区:总事件 / 未消费 P0·P1 / 正面比例 / 投资社区动态
  · 发布时间分布:按月直方图(判断是否集中爆发)
  · 风险主题归因:按 9 监控维度(W1-W9)× 方向(利好/利空/中性/分歧)堆叠条形
  · 来源类型分布 + 投资社区专区(source_type=investor_community 或 dim=W5)
  · 全量信息表:按维度/严重度/方向/来源客户端筛选,每行挂原文链接

图表为**服务端算好的静态内联 SVG**(零依赖、无 JS 报错);表格用内联行 + vanilla JS
筛选。house style 复用星图/时间线页。site/watch/ 已 gitignore,build.sh 里在
build_watch_pages 之后跑(那步会 rm -rf site/watch)。

用法:python3 scripts/build_watch_cockpit.py [slug ...]
"""
import glob, html, os, sys, datetime, collections, json, pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WATCH_DIR = ROOT / "watch"
FOUNDERS_DIR = ROOT / "founders"
OUT_DIR = ROOT / "site" / "watch"
META = ROOT / "site" / "reports-meta.yaml"

WDIM = {
    "W1": "媒体报道", "W2": "社交声量", "W3": "招投标采购", "W4": "监管司法",
    "W5": "资本市场", "W6": "产品口碑", "W7": "人事组织", "W8": "技术知产", "W9": "供应链生态",
}
DIRS = [("pos", "利好", "#1a7a4a"), ("neg", "利空", "#b3241f"),
        ("neutral", "中性", "#8a857c"), ("mixed", "分歧", "#c98a2b")]
DIR_COLOR = {k: c for k, _, c in DIRS}
DIR_CN = {k: cn for k, cn, _ in DIRS}
SEV_COLOR = {"P0": "#b3241f", "P1": "#c1440e", "P2": "#c98a2b", "P3": "#9a958c"}
SRC_CN = {
    "official": "官方", "media": "媒体", "finance": "财经", "social": "社交",
    "investor_community": "投资社区", "search": "搜索", "regulator": "监管", "": "未标注",
}


def esc(s):
    return html.escape(str(s), quote=True)


_EXT_LINKS_CACHE = None


def ext_links_html(slug):
    """从 site/external-links.yaml 读该品牌外部互链,渲染「相关看板」卡(与 SpaceX 报告页同款)。无则空串。"""
    global _EXT_LINKS_CACHE
    if _EXT_LINKS_CACHE is None:
        try:
            _EXT_LINKS_CACHE = yaml.safe_load((ROOT / "site" / "external-links.yaml").read_text(encoding="utf-8")) or {}
        except FileNotFoundError:
            _EXT_LINKS_CACHE = {}
    links = _EXT_LINKS_CACHE.get(slug) or []
    if not links:
        return ""
    cards = []
    for lk in links:
        cards.append(
            f'<a href="{esc(lk.get("url", ""))}" target="_blank" rel="noopener" '
            "style=\"display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border:1px solid #e2dac6;"
            "border-radius:12px;text-decoration:none;color:#2a2e2c;font:14px/1.4 -apple-system,'PingFang SC',sans-serif\">"
            f'<span style="font-size:20px">{esc(lk.get("emoji", ""))}</span>'
            f'<span><b>{esc(lk.get("title", ""))}</b><br>'
            f'<span style="font-size:12px;color:#5a5852">{esc(lk.get("subtitle", ""))}</span></span></a>'
        )
    return (
        '<div style="margin:4px 0 22px;">'
        "<div style=\"font-family:ui-sans-serif,'Inter',-apple-system,sans-serif;font-size:11px;font-weight:700;"
        'letter-spacing:0.06em;text-transform:uppercase;color:var(--muted);margin-bottom:8px;">相关看板 / Related</div>'
        + " ".join(cards) + "</div>"
    )


def _norm_dir(d):
    d = str(d or "neutral").lower()
    return d if d in DIR_COLOR else "neutral"


def aggregate(slug, events, brand):
    ev = [e for e in events if isinstance(e, dict)]
    unconsumed = [e for e in ev if not e.get("consumed_by")]
    p0 = sum(1 for e in unconsumed if e.get("severity") == "P0")
    p1 = sum(1 for e in unconsumed if e.get("severity") == "P1")
    p2 = sum(1 for e in unconsumed if e.get("severity") == "P2")
    pos = sum(1 for e in ev if _norm_dir(e.get("direction")) == "pos")
    neg = sum(1 for e in ev if _norm_dir(e.get("direction")) == "neg")
    invest = [e for e in ev if e.get("source_type") == "investor_community" or e.get("dim") == "W5"]

    by_month = collections.Counter(str(e.get("date", ""))[:7] for e in ev if e.get("date"))
    # dim × direction 堆叠
    dim_dir = collections.defaultdict(lambda: collections.Counter())
    for e in ev:
        dim_dir[e.get("dim", "?")][_norm_dir(e.get("direction"))] += 1
    by_source = collections.Counter(SRC_CN.get(e.get("source_type", ""), e.get("source_type") or "未标注") for e in ev)

    rows = []
    for e in sorted(ev, key=lambda x: str(x.get("date", "")), reverse=True):
        rows.append({
            "date": str(e.get("date", "")), "dim": e.get("dim", ""),
            "severity": e.get("severity", ""), "direction": _norm_dir(e.get("direction")),
            "source": e.get("source_type", "") or "",
            "title": e.get("title", e.get("id", "")), "url": e.get("url", ""),
            "persons": e.get("related_persons") or [], "action": e.get("suggested_action", "") or "",
            "consumed": e.get("consumed_by", "") or "",
        })
    hit = (p0 >= 1) or (p1 >= 3) or (4 * p0 + 2 * p1 + 0.5 * p2 >= 6)  # 与首页「建议重审」同口径
    return {
        "slug": slug, "brand": brand, "total": len(ev),
        "p0": p0, "p1": p1, "p2": p2, "hit": hit, "pos": pos, "neg": neg, "n_invest": len(invest),
        "by_month": by_month, "dim_dir": dim_dir, "by_source": by_source, "rows": rows,
    }


# ── 静态 SVG 条形 ────────────────────────────────────────────────────────────
def bars_month(by_month, w=560, h=120):
    if not by_month:
        return "<p class='empty'>无日期数据</p>"
    months = sorted(by_month)
    mx = max(by_month.values()) or 1
    n = len(months)
    bw = min(38, (w - 40) / n)
    gap = bw * 0.25
    x0 = 30
    bars, labels = [], []
    for i, m in enumerate(months):
        v = by_month[m]
        bh = (h - 30) * v / mx
        x = x0 + i * (bw + gap)
        y = h - 20 - bh
        bars.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bw:.1f}' height='{bh:.1f}' fill='#1a4a7a' rx='2'><title>{esc(m)}: {v}</title></rect>"
                    f"<text x='{x + bw/2:.1f}' y='{y - 3:.1f}' text-anchor='middle' class='bl'>{v}</text>")
        if n <= 18 or i % 2 == 0:
            labels.append(f"<text x='{x + bw/2:.1f}' y='{h - 6:.1f}' text-anchor='middle' class='ax'>{esc(m[2:])}</text>")
    return f"<svg viewBox='0 0 {w} {h}' class='chart' role='img' aria-label='发布时间分布'>{''.join(bars)}{''.join(labels)}</svg>"


def bars_dim(dim_dir, w=560, rowh=26):
    dims = [d for d in WDIM if d in dim_dir]
    if not dims:
        return "<p class='empty'>无维度数据</p>"
    mx = max(sum(dim_dir[d].values()) for d in dims) or 1
    x0, barw = 96, w - 96 - 40
    h = len(dims) * rowh + 10
    out = []
    for i, d in enumerate(dims):
        y = 6 + i * rowh
        out.append(f"<text x='0' y='{y + 13:.1f}' class='ax dimlbl'>{d} {esc(WDIM[d])}</text>")
        x = x0
        total = sum(dim_dir[d].values())
        for k, _, color in DIRS:
            v = dim_dir[d].get(k, 0)
            if not v:
                continue
            seg = barw * v / mx
            out.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{seg:.1f}' height='16' fill='{color}'><title>{d} {DIR_CN[k]}: {v}</title></rect>")
            x += seg
        out.append(f"<text x='{x + 4:.1f}' y='{y + 13:.1f}' class='bl'>{total}</text>")
    return f"<svg viewBox='0 0 {w} {h}' class='chart' role='img' aria-label='风险主题归因'>{''.join(out)}</svg>"


def bars_source(by_source, w=560, rowh=24):
    items = by_source.most_common()
    if not items:
        return ""
    mx = max(v for _, v in items) or 1
    x0, barw = 76, w - 76 - 36
    h = len(items) * rowh + 8
    out = []
    for i, (name, v) in enumerate(items):
        y = 5 + i * rowh
        seg = barw * v / mx
        out.append(f"<text x='0' y='{y + 12:.1f}' class='ax'>{esc(name)}</text>"
                   f"<rect x='{x0}' y='{y:.1f}' width='{seg:.1f}' height='15' fill='#6b6760' rx='2'/>"
                   f"<text x='{x0 + seg + 4:.1f}' y='{y + 12:.1f}' class='bl'>{v}</text>")
    return f"<svg viewBox='0 0 {w} {h}' class='chart' role='img' aria-label='来源类型分布'>{''.join(out)}</svg>"


def legend():
    return " ".join(f"<span class='lg'><i style='background:{c}'></i>{cn}</span>" for _, cn, c in DIRS)


def render(d):
    posneg = d["pos"] + d["neg"]
    pos_pct = f"{round(100 * d['pos'] / posneg)}%" if posneg else "—"
    # 全量表行 + 内联 JSON(供筛选)
    trs = []
    for r in d["rows"]:
        who = "、".join(r["persons"])
        title_cell = f"<a href='{esc(r['url'])}' target='_blank' rel='nofollow noopener'>{esc(r['title'])}</a>" if r["url"] else esc(r["title"])
        act = f"<div class='act'>建议:{esc(r['action'])}</div>" if r["action"] else ""
        who_html = f"<span class='who'>{esc(who)}</span>" if who else ""
        badge = f"<span class='consumed'>已消费 {esc(r['consumed'])}</span>" if r["consumed"] else ""
        trs.append(
            f"<tr data-dim='{esc(r['dim'])}' data-sev='{esc(r['severity'])}' data-dir='{esc(r['direction'])}' data-src='{esc(r['source'])}'>"
            f"<td class='nowrap'>{esc(r['date'])}</td>"
            f"<td><span class='chip' style='background:{SEV_COLOR.get(r['severity'], '#999')}'>{esc(r['severity'])}</span></td>"
            f"<td class='nowrap'>{esc(r['dim'])} {esc(WDIM.get(r['dim'], ''))}</td>"
            f"<td style='color:{DIR_COLOR[r['direction']]}'>{DIR_CN[r['direction']]}</td>"
            f"<td>{esc(SRC_CN.get(r['source'], r['source']))}</td>"
            f"<td>{title_cell} {who_html} {badge}{act}</td></tr>"
        )
    dim_opts = "".join(f"<option value='{k}'>{k} {esc(v)}</option>" for k, v in WDIM.items())
    src_opts = "".join(f"<option value='{k}'>{esc(vn)}</option>" for k, vn in SRC_CN.items() if k)
    founder_crumb = (f"　/　<a href='/founders/{esc(d['slug'])}.html'>创始人维度</a>"
                     if d.get("has_founder") else "")

    return TEMPLATE \
        .replace("__FOUNDER_CRUMB__", founder_crumb) \
        .replace("__BRAND__", esc(d["brand"])).replace("__SLUG__", esc(d["slug"])) \
        .replace("__TOTAL__", str(d["total"])).replace("__P0__", str(d["p0"])).replace("__P1__", str(d["p1"])) \
        .replace("__POSPCT__", pos_pct).replace("__NINV__", str(d["n_invest"])) \
        .replace("__CHART_MONTH__", bars_month(d["by_month"])) \
        .replace("__CHART_DIM__", bars_dim(d["dim_dir"])) \
        .replace("__CHART_SRC__", bars_source(d["by_source"])) \
        .replace("__LEGEND__", legend()) \
        .replace("__DIM_OPTS__", dim_opts).replace("__SRC_OPTS__", src_opts) \
        .replace("__EXT_LINKS__", ext_links_html(d["slug"])) \
        .replace("__ROWS__", "\n".join(trs))


TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>__BRAND__ · 舆情驾驶舱 · MBA</title>
<meta name="description" content="__BRAND__ 舆情驾驶舱:管理层摘要 + 风险主题归因 + 投资社区 + 可筛选全量事件表,数据取自 watch 事件流。" />
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2064%2064'%3E%3Crect%20width='64'%20height='64'%20rx='12'%20fill='%23faf8f3'/%3E%3Cpolygon%20points='32,7%2056.7,25%2047.3,54%2016.7,54%207.3,25'%20fill='none'%20stroke='%23111'%20stroke-width='2.5'%20stroke-linejoin='round'/%3E%3Cpolygon%20points='32,8.6%2048.3,27.7%2043.9,49.4%2023.6,44.6%2014.2,27.2'%20fill='%23c1440e'%20fill-opacity='.18'%20stroke='%23c1440e'%20stroke-width='3'%20stroke-linejoin='round'/%3E%3Ccircle%20cx='32'%20cy='8.6'%20r='4'%20fill='%23c1440e'/%3E%3C/svg%3E" />
<style>
  :root{--ink:#111;--paper:#faf8f3;--muted:#6b6760;--rule:#1a1a1a;--accent:#c1440e;--card:#fff;--hair:#e2ddd3;}
  *{box-sizing:border-box;} html,body{margin:0;padding:0;}
  body{background:var(--paper);color:var(--ink);font-family:ui-sans-serif,"Inter","PingFang SC","Noto Sans SC",-apple-system,sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased;}
  .wrap{max-width:1000px;margin:0 auto;padding:32px 22px 48px;}
  header{border-bottom:2px solid var(--rule);padding-bottom:14px;margin-bottom:18px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;}
  .mark{display:inline-flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.02em;font-size:22px;line-height:1;color:var(--ink);text-decoration:none;}
  .mark .dot{color:var(--accent);}
  nav a{font-size:13px;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--ink);margin-left:16px;}
  nav a:hover,nav a[aria-current]{color:var(--accent);border-color:var(--accent);}
  h1{font-size:24px;font-weight:800;margin:0 0 2px;}
  h1 .sub{font-weight:500;font-size:15px;color:var(--muted);margin-left:8px;}
  .crumb{font-size:12.5px;color:var(--muted);margin:0 0 16px;}
  .crumb a{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent);}
  h2{font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700;margin:26px 0 10px;border-bottom:1px solid var(--hair);padding-bottom:6px;}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;}
  .kpi{background:var(--card);border:1px solid var(--hair);border-radius:8px;padding:13px 15px;}
  .kpi .l{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700;}
  .kpi .v{font-size:28px;font-weight:800;line-height:1.15;margin-top:3px;}
  .kpi .s{font-size:11.5px;color:var(--muted);margin-top:2px;}
  .kpi .v.warn{color:var(--accent);}
  .panelbox{background:var(--card);border:1px solid var(--hair);border-radius:8px;padding:14px 16px;}
  .chart{width:100%;height:auto;display:block;}
  .chart .ax{font-size:9px;fill:var(--muted);} .chart .bl{font-size:9px;fill:var(--ink);} .chart .dimlbl{font-size:9.5px;fill:var(--ink);}
  .empty{color:var(--muted);font-size:13px;margin:6px 0;}
  .lgs{margin:8px 0 0;font-size:11.5px;color:var(--muted);}
  .lg{margin-right:12px;white-space:nowrap;} .lg i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px;vertical-align:middle;}
  .filters{display:flex;gap:8px;flex-wrap:wrap;margin:2px 0 10px;}
  .filters select,.filters input{font:inherit;font-size:12.5px;padding:5px 9px;border:1px solid var(--hair);border-radius:6px;background:#fff;}
  table{width:100%;border-collapse:collapse;font-size:12.5px;}
  th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--hair);vertical-align:top;}
  th{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);position:sticky;top:0;background:var(--paper);}
  td a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--hair);}
  td a:hover{color:var(--accent);border-color:var(--accent);}
  .nowrap{white-space:nowrap;}
  .chip{color:#fff;font-weight:700;font-size:10.5px;padding:1px 7px;border-radius:4px;}
  .who{color:var(--muted);font-size:11px;} .consumed{color:var(--muted);font-size:10.5px;border:1px solid var(--hair);border-radius:999px;padding:0 6px;}
  .act{color:var(--muted);font-size:11.5px;font-style:italic;margin-top:2px;}
  .tablewrap{overflow-x:auto;border:1px solid var(--hair);border-radius:8px;}
  .disclaim{font-size:11.5px;color:var(--muted);margin-top:8px;}
  footer{margin-top:28px;padding-top:14px;border-top:1px solid var(--rule);color:var(--muted);font-size:12px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;}
  footer a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--ink);}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;} @media(max-width:720px){.grid2{grid-template-columns:1fr;}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <a class="mark" href="/" aria-label="MBA"><span>MBA<span class="dot">.</span></span></a>
    <nav><a href="/">品牌监控</a><a href="/watch/">舆情信号</a><a href="/starmap.html">知识星图</a><a href="/docs.html">文档</a><a href="https://github.com/zhanglunet/mba">GitHub</a></nav>
  </header>

  <p class="crumb"><a href="/watch/__SLUG__/">← __BRAND__ 舆情时间线</a>　/　<a href="/watch/cockpit.html">全站驾驶舱</a>　/　<a href="/watch/">舆情总览</a>　/　<a href="/reports/__SLUG__/">审计报告</a>__FOUNDER_CRUMB__</p>
  <h1>__BRAND__<span class="sub">舆情驾驶舱</span></h1>
  __EXT_LINKS__

  <h2>管理层摘要</h2>
  <div class="kpis">
    <div class="kpi"><div class="l">总事件</div><div class="v">__TOTAL__</div><div class="s">可溯源事件流</div></div>
    <div class="kpi"><div class="l">未消费 P0</div><div class="v warn">__P0__</div><div class="s">待审计消化</div></div>
    <div class="kpi"><div class="l">未消费 P1</div><div class="v warn">__P1__</div><div class="s">待审计消化</div></div>
    <div class="kpi"><div class="l">正面比例</div><div class="v">__POSPCT__</div><div class="s">利好 /(利好+利空)</div></div>
    <div class="kpi"><div class="l">投资社区动态</div><div class="v">__NINV__</div><div class="s">投资社区 / 资本市场</div></div>
  </div>

  <div class="grid2" style="margin-top:14px;">
    <div><h2 style="margin-top:0">发布时间分布</h2><div class="panelbox">__CHART_MONTH__</div></div>
    <div><h2 style="margin-top:0">来源类型分布</h2><div class="panelbox">__CHART_SRC__</div></div>
  </div>

  <h2>风险主题归因(维度 × 方向)</h2>
  <div class="panelbox">__CHART_DIM__<div class="lgs">__LEGEND__</div></div>

  <h2>全量信息表</h2>
  <div class="filters">
    <select id="f-dim"><option value="">全部维度</option>__DIM_OPTS__</select>
    <select id="f-sev"><option value="">全部等级</option><option>P0</option><option>P1</option><option>P2</option><option>P3</option></select>
    <select id="f-dir"><option value="">全部方向</option><option value="pos">利好</option><option value="neg">利空</option><option value="neutral">中性</option><option value="mixed">分歧</option></select>
    <select id="f-src"><option value="">全部来源</option>__SRC_OPTS__</select>
    <input id="f-q" type="search" placeholder="搜索标题/人物…" />
    <button id="f-reset" class="filters" style="cursor:pointer">重置</button>
  </div>
  <div class="tablewrap">
    <table id="tbl"><thead><tr><th>日期</th><th>等级</th><th>维度</th><th>方向</th><th>来源</th><th>标题 / 关联人物 / 建议</th></tr></thead>
    <tbody>__ROWS__</tbody></table>
  </div>
  <p class="disclaim">舆情信号只提示、不改评分;方向/等级为模型判断,重审时可被评委推翻。引用为源站逐字标题/摘句,点标题核验原文。</p>

  <footer>
    <span>MBA · __BRAND__ 舆情驾驶舱 · 数据源:watch/__SLUG__/events.yaml</span>
    <span><a href="/watch/__SLUG__/">时间线</a> · <a href="/reports/__SLUG__/">审计报告</a></span>
  </footer>
</div>
<script>
(function(){
  var q=function(id){return document.getElementById(id);};
  var rows=[].slice.call(document.querySelectorAll('#tbl tbody tr'));
  var fd=q('f-dim'),fs=q('f-sev'),fr=q('f-dir'),fc=q('f-src'),fq=q('f-q');
  function apply(){
    var dim=fd.value,sev=fs.value,dir=fr.value,src=fc.value,kw=fq.value.trim().toLowerCase();
    rows.forEach(function(tr){
      var ok=(!dim||tr.dataset.dim===dim)&&(!sev||tr.dataset.sev===sev)&&(!dir||tr.dataset.dir===dir)
           &&(!src||tr.dataset.src===src)&&(!kw||tr.textContent.toLowerCase().indexOf(kw)>=0);
      tr.style.display=ok?'':'none';
    });
  }
  [fd,fs,fr,fc].forEach(function(el){el.addEventListener('change',apply);});
  fq.addEventListener('input',apply);
  q('f-reset').addEventListener('click',function(){fd.value=fs.value=fr.value=fc.value='';fq.value='';apply();});
})();
</script>
</body>
</html>
"""


# ── 全站聚合驾驶舱 ────────────────────────────────────────────────────────────
def aggregate_all(brand_ds):
    dim_dir = collections.defaultdict(lambda: collections.Counter())
    by_source, by_month = collections.Counter(), collections.Counter()
    rows, total = [], 0
    p0 = p1 = pos = neg = ninv = 0
    for d in brand_ds:
        total += d["total"]; p0 += d["p0"]; p1 += d["p1"]
        pos += d["pos"]; neg += d["neg"]; ninv += d["n_invest"]
        for k, c in d["by_source"].items():
            by_source[k] += c
        for dim, cc in d["dim_dir"].items():
            for k, v in cc.items():
                dim_dir[dim][k] += v
        for m, c in d["by_month"].items():
            by_month[m] += c
        for r in d["rows"]:
            rr = dict(r); rr["brand"] = d["brand"]; rr["slug"] = d["slug"]
            rows.append(rr)
    rows.sort(key=lambda r: r["date"], reverse=True)
    brands = sorted(brand_ds, key=lambda d: (not d["hit"], -d["total"]))
    return {"n_brands": len(brand_ds), "total": total, "p0": p0, "p1": p1, "pos": pos,
            "neg": neg, "n_invest": ninv, "n_hit": sum(1 for d in brand_ds if d["hit"]),
            "dim_dir": dim_dir, "by_source": by_source, "rows": rows, "brands": brands}


def render_agg(a):
    head = TEMPLATE.split("</head>", 1)[0].replace("__BRAND__", "全站") + "</head>"
    posneg = a["pos"] + a["neg"]
    pos_pct = f"{round(100 * a['pos'] / posneg)}%" if posneg else "—"

    # 各品牌信号强度表
    strength = []
    for d in a["brands"]:
        st = ("<span class='chip' style='background:#b3241f'>建议重审</span>" if d["hit"]
              else "<span style='color:var(--muted)'>正常</span>")
        strength.append(
            f"<tr><td><a href='/watch/{esc(d['slug'])}/cockpit.html'>{esc(d['brand'])}</a></td>"
            f"<td class='nowrap'>{d['total']}</td><td class='nowrap'>{d['p0']}</td>"
            f"<td class='nowrap'>{d['p1']}</td><td>{st}</td>"
            f"<td class='nowrap'><a href='/watch/{esc(d['slug'])}/'>时间线</a></td></tr>")

    # 全量表(带品牌列)
    trs = []
    for r in a["rows"]:
        who = f"<span class='who'>{esc('、'.join(r['persons']))}</span>" if r["persons"] else ""
        title_cell = (f"<a href='{esc(r['url'])}' target='_blank' rel='nofollow noopener'>{esc(r['title'])}</a>"
                      if r["url"] else esc(r["title"]))
        act = f"<div class='act'>建议:{esc(r['action'])}</div>" if r["action"] else ""
        cons = f"<span class='consumed'>已消费 {esc(r['consumed'])}</span>" if r["consumed"] else ""
        trs.append(
            f"<tr data-brand='{esc(r['slug'])}' data-dim='{esc(r['dim'])}' data-sev='{esc(r['severity'])}'"
            f" data-dir='{esc(r['direction'])}' data-src='{esc(r['source'])}'>"
            f"<td class='nowrap'><a href='/watch/{esc(r['slug'])}/cockpit.html'>{esc(r['brand'])}</a></td>"
            f"<td class='nowrap'>{esc(r['date'])}</td>"
            f"<td><span class='chip' style='background:{SEV_COLOR.get(r['severity'], '#999')}'>{esc(r['severity'])}</span></td>"
            f"<td class='nowrap'>{esc(r['dim'])} {esc(WDIM.get(r['dim'], ''))}</td>"
            f"<td style='color:{DIR_COLOR[r['direction']]}'>{DIR_CN[r['direction']]}</td>"
            f"<td>{esc(SRC_CN.get(r['source'], r['source']))}</td>"
            f"<td>{title_cell} {who} {cons}{act}</td></tr>")

    brand_opts = "".join(f"<option value='{esc(d['slug'])}'>{esc(d['brand'])}</option>" for d in a["brands"])
    dim_opts = "".join(f"<option value='{k}'>{k} {esc(v)}</option>" for k, v in WDIM.items())
    src_opts = "".join(f"<option value='{k}'>{esc(vn)}</option>" for k, vn in SRC_CN.items() if k)

    return (head + AGG_BODY
            .replace("__NB__", str(a["n_brands"])).replace("__TOTAL__", str(a["total"]))
            .replace("__P0__", str(a["p0"])).replace("__P1__", str(a["p1"]))
            .replace("__NHIT__", str(a["n_hit"])).replace("__NINV__", str(a["n_invest"]))
            .replace("__POSPCT__", pos_pct)
            .replace("__STRENGTH__", "\n".join(strength))
            .replace("__CHART_DIM__", bars_dim(a["dim_dir"])).replace("__CHART_SRC__", bars_source(a["by_source"]))
            .replace("__LEGEND__", legend())
            .replace("__BRAND_OPTS__", brand_opts).replace("__DIM_OPTS__", dim_opts).replace("__SRC_OPTS__", src_opts)
            .replace("__ROWS__", "\n".join(trs)))


AGG_BODY = r"""
<body>
<div class="wrap">
  <header>
    <a class="mark" href="/" aria-label="MBA"><span>MBA<span class="dot">.</span></span></a>
    <nav><a href="/">品牌监控</a><a href="/watch/">舆情信号</a><a href="/starmap.html">知识星图</a><a href="/docs.html">文档</a><a href="https://github.com/zhanglunet/mba">GitHub</a></nav>
  </header>

  <p class="crumb"><a href="/watch/">← 舆情总览</a>　/　全站舆情驾驶舱</p>
  <h1>全站舆情驾驶舱<span class="sub">所有品牌的舆情信号</span></h1>

  <h2>全站摘要</h2>
  <div class="kpis">
    <div class="kpi"><div class="l">监控品牌</div><div class="v">__NB__</div><div class="s">有事件流的品牌</div></div>
    <div class="kpi"><div class="l">总事件</div><div class="v">__TOTAL__</div><div class="s">可溯源信号</div></div>
    <div class="kpi"><div class="l">未消费 P0</div><div class="v warn">__P0__</div><div class="s">全站待审计</div></div>
    <div class="kpi"><div class="l">未消费 P1</div><div class="v warn">__P1__</div><div class="s">全站待审计</div></div>
    <div class="kpi"><div class="l">建议重审</div><div class="v warn">__NHIT__</div><div class="s">亮灯品牌数</div></div>
    <div class="kpi"><div class="l">投资社区</div><div class="v">__NINV__</div><div class="s">投资社区 / 资本市场</div></div>
  </div>

  <h2>各品牌信号强度</h2>
  <div class="tablewrap">
    <table><thead><tr><th>品牌</th><th>事件</th><th>未消费 P0</th><th>未消费 P1</th><th>状态</th><th>时间线</th></tr></thead>
    <tbody>__STRENGTH__</tbody></table>
  </div>

  <h2>全站风险主题归因(维度 × 方向)</h2>
  <div class="panelbox">__CHART_DIM__<div class="lgs">__LEGEND__</div></div>

  <h2 style="margin-top:22px">来源类型分布</h2>
  <div class="panelbox">__CHART_SRC__</div>

  <h2>全站信息表</h2>
  <div class="filters">
    <select id="f-brand"><option value="">全部品牌</option>__BRAND_OPTS__</select>
    <select id="f-dim"><option value="">全部维度</option>__DIM_OPTS__</select>
    <select id="f-sev"><option value="">全部等级</option><option>P0</option><option>P1</option><option>P2</option><option>P3</option></select>
    <select id="f-dir"><option value="">全部方向</option><option value="pos">利好</option><option value="neg">利空</option><option value="neutral">中性</option><option value="mixed">分歧</option></select>
    <select id="f-src"><option value="">全部来源</option>__SRC_OPTS__</select>
    <input id="f-q" type="search" placeholder="搜索标题/人物…" />
    <button id="f-reset" style="cursor:pointer;font:inherit;font-size:12.5px;padding:5px 9px;border:1px solid var(--hair);border-radius:6px;background:#fff">重置</button>
  </div>
  <div class="tablewrap">
    <table id="tbl"><thead><tr><th>品牌</th><th>日期</th><th>等级</th><th>维度</th><th>方向</th><th>来源</th><th>标题 / 关联人物 / 建议</th></tr></thead>
    <tbody>__ROWS__</tbody></table>
  </div>
  <p class="disclaim">舆情信号只提示、不改评分;方向/等级为模型判断,重审时可被评委推翻。引用为源站逐字标题/摘句,点标题核验原文。</p>

  <footer>
    <span>MBA · 全站舆情驾驶舱 · 数据源:watch/*/events.yaml</span>
    <span><a href="/watch/">舆情总览</a> · <a href="/">品牌监控</a></span>
  </footer>
</div>
<script>
(function(){
  var q=function(id){return document.getElementById(id);};
  var rows=[].slice.call(document.querySelectorAll('#tbl tbody tr'));
  var fb=q('f-brand'),fd=q('f-dim'),fs=q('f-sev'),fr=q('f-dir'),fc=q('f-src'),fq=q('f-q');
  function apply(){
    var br=fb.value,dim=fd.value,sev=fs.value,dir=fr.value,src=fc.value,kw=fq.value.trim().toLowerCase();
    rows.forEach(function(tr){
      var ok=(!br||tr.dataset.brand===br)&&(!dim||tr.dataset.dim===dim)&&(!sev||tr.dataset.sev===sev)
           &&(!dir||tr.dataset.dir===dir)&&(!src||tr.dataset.src===src)&&(!kw||tr.textContent.toLowerCase().indexOf(kw)>=0);
      tr.style.display=ok?'':'none';
    });
  }
  [fb,fd,fs,fr,fc].forEach(function(el){el.addEventListener('change',apply);});
  fq.addEventListener('input',apply);
  q('f-reset').addEventListener('click',function(){fb.value=fd.value=fs.value=fr.value=fc.value='';fq.value='';apply();});
})();
</script>
</body>
</html>
"""


def main(argv):
    meta = yaml.safe_load(open(META, encoding="utf-8")) or {}
    names = {r["slug"]: r.get("card_brand", r["slug"]) for r in (meta.get("reports") or [])}
    only = [a for a in argv if not a.startswith("-")]
    founders = {p.stem for p in FOUNDERS_DIR.glob("*.yaml")} if FOUNDERS_DIR.is_dir() else set()
    built = 0
    brand_ds = []
    for path in sorted(glob.glob(str(WATCH_DIR / "*" / "events.yaml"))):
        slug = os.path.basename(os.path.dirname(path))
        if only and slug not in only:
            continue
        events = yaml.safe_load(open(path, encoding="utf-8")) or []
        if not events:
            continue
        d = aggregate(slug, events, names.get(slug, slug))
        d["has_founder"] = slug in founders
        brand_ds.append(d)
        outdir = OUT_DIR / slug
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "cockpit.html").write_text(render(d), encoding="utf-8")
        print(f"[watch-cockpit] site/watch/{slug}/cockpit.html ({d['total']} events)")
        built += 1
    # 全站聚合驾驶舱(不受 only 过滤影响时才有意义:only 未指定时才写)
    if brand_ds and not only:
        agg = aggregate_all(brand_ds)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "cockpit.html").write_text(render_agg(agg), encoding="utf-8")
        print(f"[watch-cockpit] site/watch/cockpit.html — 全站 {agg['n_brands']} 品牌 / {agg['total']} events / {agg['n_hit']} 亮灯")
    print(f"[watch-cockpit] done — {built} cockpit page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
