#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_watch_pages.py — 从 watch/<slug>/events.yaml 生成品牌舆情时间线页
site/watch/<slug>/index.html(W5)与全品牌舆情总览页 site/watch/index.html
(全站导航「舆情信号」的落地页,docs/15 §6.2 / docs/16)。

- 部署产物:由 site/build.sh 在构建时调用;site/watch/ 已 gitignore(与 site/reports/
  同一模式:generated at deploy,不入库)。本地跑一次即可预览。
- 事件按日期倒序;P0/P1 高亮;`consumed_by: vN` 的事件标「已入 vN 审计」;
  每条直链原文(反捏造:页面上所有事实都可一键回源)。
- 顶部汇总「待审信号」(未消费 P0/P1)与触发规则评估(2026-07-12 校准:P0≥1 /
  P1≥3 / 加权 4·2·0.5 ≥6 → 建议重审)。
- 总览页对 13 个监控品牌逐一列:事件数 / 待审 P0/P1 / 双口径触发状态(欠账 + 30 天窗;
  窗口口径按**生成时**评估——本页是 deploy 产物、不入库,无 --check 确定性约束)/
  未开采品牌诚实标注。
"""
import datetime
import glob
import html
import os
import sys

try:
    import yaml
except ImportError:
    print("build_watch_pages: 需要 PyYAML", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH_DIR = os.path.join(ROOT, "watch")
OUT_DIR = os.path.join(ROOT, "site", "watch")
META = os.path.join(ROOT, "site", "reports-meta.yaml")
MATRIX = os.path.join(WATCH_DIR, "matrix.yaml")

# 30 天窗触发评估复用 W7 运行时评估器(同一套语义,不复制逻辑)
sys.path.insert(0, os.path.join(ROOT, "scripts", "watch-tools"))
from evaluate_triggers import evaluate  # noqa: E402


def norm_flag(v):
    # YAML 1.1 把 on/off 解析成布尔(docs/16 §2.4)
    return "on" if v is True else ("off" if v is False else str(v))

DIM_LABEL = {
    "W1": "W1 媒体", "W2": "W2 社交", "W3": "W3 招投标", "W4": "W4 监管",
    "W5": "W5 资本", "W6": "W6 口碑", "W7": "W7 人事", "W8": "W8 技术", "W9": "W9 生态",
}


def esc(s):
    return html.escape(str(s or ""), quote=False)


def fmt_date(d):
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def render_event(e):
    sev = e.get("severity", "P3")
    consumed = e.get("consumed_by")
    dirn = {"pos": "↑", "neg": "↓", "mixed": "±", "neutral": "·"}.get(e.get("direction"), "·")
    consumed_html = (f'<span class="echip echip-consumed">已入 {esc(consumed)} 审计</span>'
                     if consumed else '<span class="echip echip-pending">待审</span>')
    return f'''    <article class="event sev-{sev}">
      <div class="e-head">
        <span class="echip echip-{sev}">{sev}</span>
        <span class="echip echip-dim">{DIM_LABEL.get(e.get("dim"), esc(e.get("dim")))}</span>
        <span class="e-date">{fmt_date(e.get("date"))}</span>
        <span class="e-dir" title="方向(模型判断)">{dirn}</span>
        {consumed_html}
      </div>
      <h3 class="e-title">{esc(e.get("title"))}</h3>
      <blockquote class="e-quote">{esc(e.get("quote"))}</blockquote>
      <div class="e-foot">
        <a href="{esc(e.get("url"))}" rel="noopener">原文 →</a>
        <span class="e-lens">镜头:{esc("、".join(e.get("lens_map") or []))}</span>
      </div>
    </article>'''


def render_page(slug, brand_name, events):
    events = sorted(events, key=lambda e: fmt_date(e.get("date")), reverse=True)
    p0 = sum(1 for e in events if e.get("severity") == "P0" and not e.get("consumed_by"))
    p1 = sum(1 for e in events if e.get("severity") == "P1" and not e.get("consumed_by"))
    p2 = sum(1 for e in events if e.get("severity") == "P2" and not e.get("consumed_by"))
    rec = (p0 >= 1) or (p1 >= 3) or (4 * p0 + 2 * p1 + 0.5 * p2 >= 6)  # 2026-07-12 校准
    rec_html = ('<span class="wchip wchip-rec">触发规则命中 · 建议重审</span>' if rec
                else '<span class="wchip wchip-ok">未触发重审建议</span>')
    body = "\n\n".join(render_event(e) for e in events)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{esc(brand_name)} · 舆情信号 · MBA</title>
<meta name="description" content="{esc(brand_name)} 的 Brand Watch 舆情事件流:{len(events)} 条可溯源信号,P0-P3 分级,每条直链原文。" />
<style>
  :root {{ --ink:#111; --paper:#faf8f3; --muted:#6b6760; --rule:#1a1a1a; --accent:#c1440e;
    --down:#b5341a; --up:#1a7a4a; --card:#fff; --hair:#e2ddd3; }}
  * {{ box-sizing:border-box; }} html,body {{ margin:0;padding:0; }}
  body {{ background:var(--paper); color:var(--ink); line-height:1.6;
    font-family: ui-sans-serif,"Inter","PingFang SC","Noto Sans SC",-apple-system,sans-serif; }}
  .wrap {{ max-width:820px; margin:0 auto; padding:40px 28px 72px; }}
  header {{ border-bottom:2px solid var(--rule); padding-bottom:14px; margin-bottom:24px;
    display:flex; align-items:baseline; justify-content:space-between; gap:16px; flex-wrap:wrap; }}
  .mark {{ font-weight:800; letter-spacing:.02em; font-size:22px; }} .mark .dot {{ color:var(--accent); }}
  /* ── logo glyph(五镜头雷达,规范见 /logo-design.html)── */
  .mark {{ display:inline-flex; align-items:center; gap:10px; }}
  .mark-glyph {{ display:block; flex-shrink:0; }}
  .mark-glyph .radar-data {{ stroke-dasharray:100; }}
  .mark-glyph .radar-dot {{ transform-box:fill-box; transform-origin:center; transition:transform .25s cubic-bezier(.2,1.4,.4,1); }}
  .mark:hover .radar-dot {{ transform:scale(1.35); }}
  @media (prefers-reduced-motion: no-preference) {{
    .mark-glyph .radar-data {{ animation:mba-draw 1.1s cubic-bezier(.6,0,.25,1) .2s backwards; }}
    .mark-glyph .radar-dot {{ animation:mba-pop .4s cubic-bezier(.2,1.6,.4,1) 1.2s backwards; }}
  }}
  @keyframes mba-draw {{ from {{ stroke-dashoffset:100; fill-opacity:0; }} to {{ stroke-dashoffset:0; fill-opacity:1; }} }}
  @keyframes mba-pop {{ from {{ transform:scale(0); }} to {{ transform:scale(1); }} }}
  nav a {{ font-size:13px; color:var(--ink); text-decoration:none; border-bottom:1px solid var(--ink); margin-left:16px; }}
  nav a:hover {{ color:var(--accent); border-color:var(--accent); }}
  h1 {{ font-size:26px; font-weight:800; margin:0 0 6px; }}
  .lede {{ color:var(--muted); font-size:13.5px; margin:0 0 18px; }}
  .summary {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:26px; }}
  .wchip {{ font-size:12px; font-weight:800; border-radius:4px; padding:2px 9px; }}
  .wchip-p0 {{ color:#fff; background:var(--down); }}
  .wchip-p1 {{ color:var(--down); background:#fbe9e4; }}
  .wchip-rec {{ color:var(--accent); border:1px dashed var(--accent); padding:1px 8px; }}
  .wchip-ok {{ color:var(--muted); border:1px solid var(--hair); padding:1px 8px; font-weight:600; }}
  .event {{ background:var(--card); border:1px solid var(--hair); border-radius:6px; padding:14px 16px; margin-bottom:12px; }}
  .event.sev-P0 {{ border-left:3px solid var(--down); }}
  .event.sev-P1 {{ border-left:3px solid #d97706; }}
  .e-head {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; font-size:12px; }}
  .echip {{ font-weight:700; border-radius:4px; padding:1px 7px; font-size:11px; }}
  .echip-P0 {{ color:#fff; background:var(--down); }}
  .echip-P1 {{ color:var(--down); background:#fbe9e4; }}
  .echip-P2 {{ color:var(--muted); background:#efece5; }}
  .echip-P3 {{ color:#9a958c; border:1px solid var(--hair); }}
  .echip-dim {{ color:var(--ink); border:1px solid var(--hair); background:var(--paper); }}
  .echip-consumed {{ color:var(--up); background:#e4f3ea; }}
  .echip-pending {{ color:var(--accent); border:1px dashed var(--accent); }}
  .e-date {{ color:var(--muted); font-variant-numeric:tabular-nums; }}
  .e-dir {{ color:var(--muted); }}
  .e-title {{ font-size:15px; font-weight:700; margin:8px 0 6px; line-height:1.45; }}
  .e-quote {{ margin:0 0 8px; padding:6px 12px; border-left:2px solid var(--hair); color:var(--muted); font-size:13px; font-style:italic; }}
  .e-foot {{ display:flex; justify-content:space-between; gap:10px; font-size:12px; }}
  .e-foot a {{ color:var(--accent); text-decoration:none; font-weight:600; }}
  .e-foot a:hover {{ border-bottom:1px solid var(--accent); }}
  .e-lens {{ color:var(--muted); }}
  footer {{ margin-top:32px; padding-top:14px; border-top:1px solid var(--rule); color:var(--muted); font-size:12px; line-height:1.7; }}
</style>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2064%2064'%3E%3Crect%20width='64'%20height='64'%20rx='12'%20fill='%23faf8f3'/%3E%3Cpolygon%20points='32,7%2056.7,25%2047.3,54%2016.7,54%207.3,25'%20fill='none'%20stroke='%23111'%20stroke-width='2.5'%20stroke-linejoin='round'/%3E%3Cpolygon%20points='32,8.6%2048.3,27.7%2043.9,49.4%2023.6,44.6%2014.2,27.2'%20fill='%23c1440e'%20fill-opacity='.18'%20stroke='%23c1440e'%20stroke-width='3'%20stroke-linejoin='round'/%3E%3Ccircle%20cx='32'%20cy='8.6'%20r='4'%20fill='%23c1440e'/%3E%3C/svg%3E" />
</head>
<body>
<div class="wrap">
  <header>
    <span class="mark" role="img" aria-label="MBA — Metric Brand Auditor"><svg class="mark-glyph" viewBox="0 0 64 64" width="34" height="34" aria-hidden="true" focusable="false"><defs><linearGradient id="mbaGradMk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c1440e" stop-opacity=".30"/><stop offset="1" stop-color="#c1440e" stop-opacity=".06"/></linearGradient></defs><polygon points="32,7 56.7,25 47.3,54 16.7,54 7.3,25" fill="none" stroke="#111" stroke-width="2" stroke-linejoin="round"/><g fill="none" stroke="#111" opacity=".12" stroke-width="1"><polygon points="32,20 44.4,29 39.6,43.5 24.4,43.5 19.6,29" stroke-linejoin="round"/><path d="M32 33V7M32 33 56.7 25M32 33 47.3 54M32 33 16.7 54M32 33 7.3 25"/></g><polygon class="radar-data" pathLength="100" points="32,8.6 48.3,27.7 43.9,49.4 23.6,44.6 14.2,27.2" fill="url(#mbaGradMk)" stroke="#c1440e" stroke-width="2.5" stroke-linejoin="round"/><circle class="radar-dot" cx="32" cy="8.6" r="3.2" fill="#c1440e" stroke="#faf8f3" stroke-width="1.5"/></svg><span>MBA<span class="dot">.</span></span></span>
    <nav>
      <a href="/">品牌监控</a>
      <a href="/watch/">舆情总览</a>
      <a href="/reports/{slug}/">审计报告</a>
      <a href="/panorama.html">评委全景</a>
    </nav>
  </header>

  <h1>{esc(brand_name)} · 舆情信号</h1>
  <p class="lede">Brand Watch 事件流 · {len(events)} 条可溯源信号 · 每条直链原文 · 分级与方向为模型判断(docs/15)</p>
  <div class="summary">
    <span class="wchip wchip-p0">待审 P0×{p0}</span>
    <span class="wchip wchip-p1">待审 P1×{p1}</span>
    {rec_html}
  </div>

{body}

  <footer>
    舆情事件流仅作审计触发建议与调研输入,<strong>不改变任何评分</strong>——分数只能来自评委重审
    (docs/15 §5.3)。方向 / 分级为 AI 模型判断,事实字段(日期 / 引用 / 链接)均可溯源。
    © 2026 MBA · Jason · 清风 · John · 技术支持 <a href="https://marsdata.ai" style="color:var(--ink);">marsdata.ai</a>
  </footer>
</div>
</body>
</html>
'''


def render_brand_row(slug, name, dims_on, events, as_of):
    """总览页单品牌行。events 为 None = 该品牌尚无事件流(未开采)。"""
    report_link = f'<a class="b-link" href="/reports/{slug}/">报告 →</a>'
    if events is None:
        return f'''    <article class="brand b-empty">
      <div class="b-head">
        <span class="b-name">{esc(name)}</span><span class="b-slug">{slug}</span>
        <span class="bchip bchip-empty">暂未开采</span>
        <span class="b-dims">开启维度 {dims_on}/9</span>
      </div>
      <div class="b-foot"><span class="b-note">事件流待周扫 Routine 覆盖(docs/16 §7)</span>{report_link}</div>
    </article>'''

    p0 = sum(1 for e in events if e.get("severity") == "P0" and not e.get("consumed_by"))
    p1 = sum(1 for e in events if e.get("severity") == "P1" and not e.get("consumed_by"))
    p2 = sum(1 for e in events if e.get("severity") == "P2" and not e.get("consumed_by"))
    consumed = sum(1 for e in events if e.get("consumed_by"))
    # 欠账口径 == 首页徽章(build_home_cards);2026-07-12 校准:P0≥1 / P1≥3 / 加权≥6
    backlog_hit = (p0 >= 1) or (p1 >= 3) or (4 * p0 + 2 * p1 + 0.5 * p2 >= 6)
    win = evaluate(events, as_of, 30, False)  # 30 天窗口径(W7 评估器)

    chips = []
    if p0:
        chips.append(f'<span class="bchip bchip-p0">待审 P0×{p0}</span>')
    if p1:
        chips.append(f'<span class="bchip bchip-p1">待审 P1×{p1}</span>')
    if backlog_hit:
        chips.append('<span class="bchip bchip-rec">建议重审</span>')
    if not chips:
        chips.append('<span class="bchip bchip-clear">无待审 P0/P1</span>')
    win_txt = ("窗口命中:" + "、".join(win["rules_hit"])) if win["hit"] else "30 天窗未命中"
    return f'''    <article class="brand{' b-hit' if backlog_hit else ''}">
      <div class="b-head">
        <span class="b-name">{esc(name)}</span><span class="b-slug">{slug}</span>
        {''.join(chips)}
      </div>
      <div class="b-foot">
        <span class="b-note">事件 {len(events)} 条(已入审计 {consumed})· {esc(win_txt)}</span>
        <span class="b-links"><a class="b-link" href="/watch/{slug}/">信号 →</a>{report_link}</span>
      </div>
    </article>'''


def render_overview(rows_meta, as_of):
    """rows_meta: [(slug, name, dims_on, events|None)],已按亮灯→有事件→未开采排序。"""
    mined = [r for r in rows_meta if r[3] is not None]
    total_events = sum(len(r[3]) for r in mined)
    def _hit(evts):
        p0 = sum(1 for e in evts if e.get("severity") == "P0" and not e.get("consumed_by"))
        p1 = sum(1 for e in evts if e.get("severity") == "P1" and not e.get("consumed_by"))
        p2 = sum(1 for e in evts if e.get("severity") == "P2" and not e.get("consumed_by"))
        return p0 >= 1 or p1 >= 3 or (4 * p0 + 2 * p1 + 0.5 * p2 >= 6)
    lit = sum(1 for r in mined if _hit(r[3]))
    body = "\n\n".join(render_brand_row(*r, as_of) for r in rows_meta)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>舆情信号 · Brand Watch · MBA</title>
<meta name="description" content="MBA Brand Watch:{len(rows_meta)} 个监控品牌的可溯源舆情事件流总览——待审 P0/P1、触发规则状态、直达各品牌时间线。只建议、不改分。" />
<style>
  :root {{ --ink:#111; --paper:#faf8f3; --muted:#6b6760; --rule:#1a1a1a; --accent:#c1440e;
    --down:#b5341a; --up:#1a7a4a; --card:#fff; --hair:#e2ddd3; }}
  * {{ box-sizing:border-box; }} html,body {{ margin:0;padding:0; }}
  body {{ background:var(--paper); color:var(--ink); line-height:1.6;
    font-family: ui-sans-serif,"Inter","PingFang SC","Noto Sans SC",-apple-system,sans-serif; }}
  .wrap {{ max-width:820px; margin:0 auto; padding:40px 28px 72px; }}
  header {{ border-bottom:2px solid var(--rule); padding-bottom:14px; margin-bottom:24px;
    display:flex; align-items:baseline; justify-content:space-between; gap:16px; flex-wrap:wrap; }}
  .mark {{ font-weight:800; letter-spacing:.02em; font-size:22px; }} .mark .dot {{ color:var(--accent); }}
  /* ── logo glyph(五镜头雷达,规范见 /logo-design.html)── */
  .mark {{ display:inline-flex; align-items:center; gap:10px; }}
  .mark-glyph {{ display:block; flex-shrink:0; }}
  .mark-glyph .radar-data {{ stroke-dasharray:100; }}
  .mark-glyph .radar-dot {{ transform-box:fill-box; transform-origin:center; transition:transform .25s cubic-bezier(.2,1.4,.4,1); }}
  .mark:hover .radar-dot {{ transform:scale(1.35); }}
  @media (prefers-reduced-motion: no-preference) {{
    .mark-glyph .radar-data {{ animation:mba-draw 1.1s cubic-bezier(.6,0,.25,1) .2s backwards; }}
    .mark-glyph .radar-dot {{ animation:mba-pop .4s cubic-bezier(.2,1.6,.4,1) 1.2s backwards; }}
  }}
  @keyframes mba-draw {{ from {{ stroke-dashoffset:100; fill-opacity:0; }} to {{ stroke-dashoffset:0; fill-opacity:1; }} }}
  @keyframes mba-pop {{ from {{ transform:scale(0); }} to {{ transform:scale(1); }} }}
  nav a {{ font-size:13px; color:var(--ink); text-decoration:none; border-bottom:1px solid var(--ink); margin-left:16px; }}
  nav a:hover {{ color:var(--accent); border-color:var(--accent); }}
  nav a[aria-current] {{ color:var(--accent); border-color:var(--accent); }}
  h1 {{ font-size:26px; font-weight:800; margin:0 0 6px; }}
  .lede {{ color:var(--muted); font-size:13.5px; margin:0 0 18px; }}
  .summary {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:26px;
    color:var(--muted); font-size:13px; }}
  .summary strong {{ color:var(--ink); }}
  .brand {{ background:var(--card); border:1px solid var(--hair); border-radius:6px;
    padding:12px 16px; margin-bottom:10px; }}
  .brand.b-hit {{ border-left:3px solid var(--accent); }}
  .brand.b-empty {{ background:transparent; border-style:dashed; }}
  .b-head {{ display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; }}
  .b-name {{ font-size:16px; font-weight:800; }}
  .b-slug {{ color:var(--muted); font-size:12px; font-family:ui-monospace,monospace; }}
  .b-dims {{ color:var(--muted); font-size:12px; margin-left:auto; }}
  .bchip {{ font-size:11px; font-weight:800; border-radius:4px; padding:1px 8px; }}
  .bchip-p0 {{ color:#fff; background:var(--down); }}
  .bchip-p1 {{ color:var(--down); background:#fbe9e4; }}
  .bchip-rec {{ color:var(--accent); border:1px dashed var(--accent); }}
  .bchip-clear {{ color:var(--up); background:#e4f3ea; }}
  .bchip-empty {{ color:var(--muted); border:1px solid var(--hair); font-weight:600; }}
  .b-foot {{ display:flex; justify-content:space-between; align-items:baseline; gap:10px;
    flex-wrap:wrap; margin-top:6px; font-size:12.5px; }}
  .b-note {{ color:var(--muted); }}
  .b-links {{ display:flex; gap:14px; }}
  .b-link {{ color:var(--accent); text-decoration:none; font-weight:600; white-space:nowrap; }}
  .b-link:hover {{ border-bottom:1px solid var(--accent); }}
  .b-empty .b-foot {{ margin-top:4px; }}
  footer {{ margin-top:32px; padding-top:14px; border-top:1px solid var(--rule); color:var(--muted); font-size:12px; line-height:1.7; }}
</style>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2064%2064'%3E%3Crect%20width='64'%20height='64'%20rx='12'%20fill='%23faf8f3'/%3E%3Cpolygon%20points='32,7%2056.7,25%2047.3,54%2016.7,54%207.3,25'%20fill='none'%20stroke='%23111'%20stroke-width='2.5'%20stroke-linejoin='round'/%3E%3Cpolygon%20points='32,8.6%2048.3,27.7%2043.9,49.4%2023.6,44.6%2014.2,27.2'%20fill='%23c1440e'%20fill-opacity='.18'%20stroke='%23c1440e'%20stroke-width='3'%20stroke-linejoin='round'/%3E%3Ccircle%20cx='32'%20cy='8.6'%20r='4'%20fill='%23c1440e'/%3E%3C/svg%3E" />
</head>
<body>
<div class="wrap">
  <header>
    <span class="mark" role="img" aria-label="MBA — Metric Brand Auditor"><svg class="mark-glyph" viewBox="0 0 64 64" width="34" height="34" aria-hidden="true" focusable="false"><defs><linearGradient id="mbaGradMk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c1440e" stop-opacity=".30"/><stop offset="1" stop-color="#c1440e" stop-opacity=".06"/></linearGradient></defs><polygon points="32,7 56.7,25 47.3,54 16.7,54 7.3,25" fill="none" stroke="#111" stroke-width="2" stroke-linejoin="round"/><g fill="none" stroke="#111" opacity=".12" stroke-width="1"><polygon points="32,20 44.4,29 39.6,43.5 24.4,43.5 19.6,29" stroke-linejoin="round"/><path d="M32 33V7M32 33 56.7 25M32 33 47.3 54M32 33 16.7 54M32 33 7.3 25"/></g><polygon class="radar-data" pathLength="100" points="32,8.6 48.3,27.7 43.9,49.4 23.6,44.6 14.2,27.2" fill="url(#mbaGradMk)" stroke="#c1440e" stroke-width="2.5" stroke-linejoin="round"/><circle class="radar-dot" cx="32" cy="8.6" r="3.2" fill="#c1440e" stroke="#faf8f3" stroke-width="1.5"/></svg><span>MBA<span class="dot">.</span></span></span>
    <nav>
      <a href="/">品牌监控</a>
      <a href="/watch/" aria-current="page">舆情信号</a>
      <a href="/panorama.html">评委全景</a>
      <a href="/starmap.html">知识星图</a>
      <a href="/docs.html">文档</a>
      <a href="https://github.com/zhanglunet/mba">GitHub</a>
    </nav>
  </header>

  <h1>舆情信号 · Brand Watch</h1>
  <p class="lede">按 W1-W9 维度持续采集的可溯源事件流(每条直链原文)——审计触发建议与调研输入,
    <strong>只建议、不改分</strong>(docs/15 §5.3)。每周一自动周扫增量。</p>
  <div class="summary">
    <span><strong>{len(mined)}/{len(rows_meta)}</strong> 品牌已开采</span>·
    <span><strong>{total_events}</strong> 条事件</span>·
    <span><strong>{lit}</strong> 个品牌命中触发规则(建议重审)</span>·
    <span>窗口口径评估于 {as_of}</span>
  </div>

{body}

  <footer>
    「建议重审」为欠账口径(未消费 P0≥1 / P1≥3 / 加权 4·2·0.5 ≥6,与首页徽章一致,
    2026-07-12 校准);「窗口命中」为同规则的 30 天滚动窗口径(生成时评估)——窗口答"最近热度",欠账答"待消化",
    两口径互补(docs/16 §8.1)。方向 / 分级为 AI 模型判断,事实字段(日期 / 引用 / 链接)均可溯源。
    © 2026 MBA · Jason · 清风 · John · 技术支持 <a href="https://marsdata.ai" style="color:var(--ink);">marsdata.ai</a>
  </footer>
</div>
</body>
</html>
'''


def main():
    meta = yaml.safe_load(open(META, encoding="utf-8")) or {}
    reports = meta.get("reports") or []
    names = {r["slug"]: r.get("card_brand", r["slug"]) for r in reports}
    matrix = (yaml.safe_load(open(MATRIX, encoding="utf-8")) or {}).get("brands", {})
    as_of = datetime.date.today()

    all_events = {}
    n = 0
    for path in sorted(glob.glob(os.path.join(WATCH_DIR, "*", "events.yaml"))):
        slug = os.path.basename(os.path.dirname(path))
        events = yaml.safe_load(open(path, encoding="utf-8")) or []
        all_events[slug] = events
        out = os.path.join(OUT_DIR, slug)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_page(slug, names.get(slug, slug), events))
        print(f"[watch-pages] site/watch/{slug}/index.html ({len(events)} events)")
        n += 1

    # 总览页:亮灯(欠账口径)在前,有事件次之,未开采最后;组内保持 reports-meta 顺序。
    rows = []
    for r in reports:
        slug = r["slug"]
        dims_on = sum(1 for v in (matrix.get(slug) or {}).values() if norm_flag(v) != "off")
        ev = all_events.get(slug)
        if ev is None:
            group = 2
        else:
            p0 = sum(1 for e in ev if e.get("severity") == "P0" and not e.get("consumed_by"))
            p1 = sum(1 for e in ev if e.get("severity") == "P1" and not e.get("consumed_by"))
            p2 = sum(1 for e in ev if e.get("severity") == "P2" and not e.get("consumed_by"))
            group = 0 if (p0 >= 1 or p1 >= 3 or 4 * p0 + 2 * p1 + 0.5 * p2 >= 6) else 1
        rows.append((group, (slug, names[slug], dims_on, ev)))
    rows = [r for _, r in sorted(rows, key=lambda t: t[0])]

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_overview(rows, as_of))
    print(f"[watch-pages] site/watch/index.html(总览:{len(rows)} 品牌,{n} 个已开采)")
    print(f"[watch-pages] done — {n} brand page(s) + overview")
    return 0


if __name__ == "__main__":
    sys.exit(main())
