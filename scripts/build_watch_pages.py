#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_watch_pages.py — 从 watch/<slug>/events.yaml 生成品牌舆情时间线页
site/watch/<slug>/index.html(W5,docs/15 §6.2 / docs/16)。

- 部署产物:由 site/build.sh 在构建时调用;site/watch/ 已 gitignore(与 site/reports/
  同一模式:generated at deploy,不入库)。本地跑一次即可预览。
- 事件按日期倒序;P0/P1 高亮;`consumed_by: vN` 的事件标「已入 vN 审计」;
  每条直链原文(反捏造:页面上所有事实都可一键回源)。
- 顶部汇总「待审信号」(未消费 P0/P1)与触发规则评估(P0≥1 或 P1≥2 → 建议重审)。
"""
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
    rec = (p0 >= 1) or (p1 >= 2)
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
</head>
<body>
<div class="wrap">
  <header>
    <span class="mark">MBA<span class="dot">.</span></span>
    <nav>
      <a href="/">品牌监控</a>
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


def main():
    meta = yaml.safe_load(open(META, encoding="utf-8")) or {}
    names = {r["slug"]: r.get("card_brand", r["slug"]) for r in (meta.get("reports") or [])}
    n = 0
    for path in sorted(glob.glob(os.path.join(WATCH_DIR, "*", "events.yaml"))):
        slug = os.path.basename(os.path.dirname(path))
        events = yaml.safe_load(open(path, encoding="utf-8")) or []
        out = os.path.join(OUT_DIR, slug)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_page(slug, names.get(slug, slug), events))
        print(f"[watch-pages] site/watch/{slug}/index.html ({len(events)} events)")
        n += 1
    print(f"[watch-pages] done — {n} brand page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
