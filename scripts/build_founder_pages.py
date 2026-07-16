#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_founder_pages.py — 从 founders/<slug>.yaml 生成品牌「创始人维度」页
site/founders/<slug>.html + 索引页 site/founders/index.html。

创始人维度(新增):梳理每个品牌创始人的**履历时间线**,并从**人物角度**梳理
创始人↔品牌的关系(按 5 镜头拆)。数据源 = founders/<slug>.yaml(单一真源,复用
对应评委 perspective 的 06-timeline 调研)。反捏造:履历里程碑均带 provenance
(evidence),创始人↔品牌关系为**标注的分析**,不冒充本人原话。

- 部署产物:由 site/build.sh 在构建时调用;site/founders/ 已 gitignore(与 site/watch/、
  site/starmap/ 同一模式:generated at deploy,不入库)。本地跑一次即可预览。
- 交叉链:→ 该评委 perspective 全景、→ 品牌报告、→ 品牌私有星图、→ 舆情驾驶舱。

用法:python3 scripts/build_founder_pages.py           → 生成全部
      python3 scripts/build_founder_pages.py spacex    → 只生成指定 slug
"""
import glob
import html
import os
import sys

try:
    import yaml
except ImportError:
    print("build_founder_pages: 需要 PyYAML", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOUNDERS_DIR = os.path.join(ROOT, "founders")
COLLABS_DIR = os.path.join(ROOT, "collabs")
OUT_DIR = os.path.join(ROOT, "site", "founders")
META = os.path.join(ROOT, "site", "reports-meta.yaml")


def dinners_for(slug):
    """扫 collabs/*.yaml,返回该品牌参与的晚餐 [(stem, partner_slug)]。"""
    out = []
    for p in sorted(glob.glob(os.path.join(COLLABS_DIR, "*.yaml"))):
        d = yaml.safe_load(open(p, encoding="utf-8")) or {}
        brands = d.get("brands") or []
        if slug in brands and len(brands) == 2:
            partner = brands[0] if brands[1] == slug else brands[1]
            out.append((os.path.splitext(os.path.basename(p))[0], partner))
    return out


def _founder_name(slug):
    p = os.path.join(FOUNDERS_DIR, f"{slug}.yaml")
    if not os.path.exists(p):
        return slug
    return (yaml.safe_load(open(p, encoding="utf-8")) or {}).get("founder", {}).get("name_cn", slug)

# 5 镜头:id / 展示名 / 色板(与 build_brand_starmap 的镜头语义一致)
LENSES = [
    ("origin", "起源叙事", "#c1440e"),
    ("category", "品类定义", "#1a7a4a"),
    ("leverage", "杠杆护城河", "#2563a8"),
    ("identity", "身份系统", "#7c3aed"),
    ("signal", "真实信号", "#b5341a"),
]
LENS_CN = {lid: cn for lid, cn, _ in LENSES}
LENS_COLOR = {lid: c for lid, _, c in LENSES}

FAVICON = ("<link rel=\"icon\" type=\"image/svg+xml\" href=\"data:image/svg+xml,"
           "%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2064%2064'%3E"
           "%3Crect%20width='64'%20height='64'%20rx='12'%20fill='%23faf8f3'/%3E"
           "%3Cpolygon%20points='32,7%2056.7,25%2047.3,54%2016.7,54%207.3,25'%20fill='none'%20"
           "stroke='%23111'%20stroke-width='2.5'%20stroke-linejoin='round'/%3E"
           "%3Cpolygon%20points='32,8.6%2048.3,27.7%2043.9,49.4%2023.6,44.6%2014.2,27.2'%20"
           "fill='%23c1440e'%20fill-opacity='.18'%20stroke='%23c1440e'%20stroke-width='3'%20"
           "stroke-linejoin='round'/%3E%3Ccircle%20cx='32'%20cy='8.6'%20r='4'%20fill='%23c1440e'/%3E"
           "%3C/svg%3E\" />")

MARK = ('<span class="mark" role="img" aria-label="MBA — Metric Brand Auditor">'
        '<svg class="mark-glyph" viewBox="0 0 64 64" width="34" height="34" aria-hidden="true" focusable="false">'
        '<defs><linearGradient id="mbaGradMk" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#c1440e" stop-opacity=".30"/>'
        '<stop offset="1" stop-color="#c1440e" stop-opacity=".06"/></linearGradient></defs>'
        '<polygon points="32,7 56.7,25 47.3,54 16.7,54 7.3,25" fill="none" stroke="#111" stroke-width="2" stroke-linejoin="round"/>'
        '<g fill="none" stroke="#111" opacity=".12" stroke-width="1">'
        '<polygon points="32,20 44.4,29 39.6,43.5 24.4,43.5 19.6,29" stroke-linejoin="round"/>'
        '<path d="M32 33V7M32 33 56.7 25M32 33 47.3 54M32 33 16.7 54M32 33 7.3 25"/></g>'
        '<polygon class="radar-data" pathLength="100" points="32,8.6 48.3,27.7 43.9,49.4 23.6,44.6 14.2,27.2" '
        'fill="url(#mbaGradMk)" stroke="#c1440e" stroke-width="2.5" stroke-linejoin="round"/>'
        '<circle class="radar-dot" cx="32" cy="8.6" r="3.2" fill="#c1440e" stroke="#faf8f3" stroke-width="1.5"/></svg>'
        '<span>MBA<span class="dot">.</span></span></span>')

# 共享 house-style(与 build_watch_pages 同一套变量与 logo 动效)
STYLE = """
  :root { --ink:#111; --paper:#faf8f3; --muted:#6b6760; --rule:#1a1a1a; --accent:#c1440e;
    --up:#1a7a4a; --card:#fff; --hair:#e2ddd3; }
  * { box-sizing:border-box; } html,body { margin:0;padding:0; }
  body { background:var(--paper); color:var(--ink); line-height:1.6;
    font-family: ui-sans-serif,"Inter","PingFang SC","Noto Sans SC",-apple-system,sans-serif; }
  .wrap { max-width:820px; margin:0 auto; padding:40px 28px 72px; }
  header { border-bottom:2px solid var(--rule); padding-bottom:14px; margin-bottom:24px;
    display:flex; align-items:baseline; justify-content:space-between; gap:16px; flex-wrap:wrap; }
  .mark { font-weight:800; letter-spacing:.02em; font-size:22px; display:inline-flex; align-items:center; gap:10px; }
  .mark .dot { color:var(--accent); }
  .mark-glyph { display:block; flex-shrink:0; }
  .mark-glyph .radar-data { stroke-dasharray:100; }
  .mark-glyph .radar-dot { transform-box:fill-box; transform-origin:center; transition:transform .25s cubic-bezier(.2,1.4,.4,1); }
  .mark:hover .radar-dot { transform:scale(1.35); }
  @media (prefers-reduced-motion: no-preference) {
    .mark-glyph .radar-data { animation:mba-draw 1.1s cubic-bezier(.6,0,.25,1) .2s backwards; }
    .mark-glyph .radar-dot { animation:mba-pop .4s cubic-bezier(.2,1.6,.4,1) 1.2s backwards; }
  }
  @keyframes mba-draw { from { stroke-dashoffset:100; fill-opacity:0; } to { stroke-dashoffset:0; fill-opacity:1; } }
  @keyframes mba-pop { from { transform:scale(0); } to { transform:scale(1); } }
  nav a { font-size:13px; color:var(--ink); text-decoration:none; border-bottom:1px solid var(--ink); margin-left:16px; }
  nav a:hover { color:var(--accent); border-color:var(--accent); }
  nav a[aria-current] { color:var(--accent); border-color:var(--accent); }
  h1 { font-size:26px; font-weight:800; margin:0 0 6px; }
  .lede { color:var(--muted); font-size:13.5px; margin:0 0 18px; }
  .fmeta { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:24px; font-size:13px; }
  .fchip { font-size:12px; font-weight:700; border-radius:4px; padding:2px 9px; border:1px solid var(--hair); background:var(--card); }
  .fchip-status { color:var(--up); background:#e4f3ea; border-color:transparent; }
  .xlinks { display:flex; gap:14px; flex-wrap:wrap; margin:0 0 30px; font-size:13px; }
  .xlinks a { color:var(--accent); text-decoration:none; font-weight:600; }
  .xlinks a:hover { border-bottom:1px solid var(--accent); }
  h2 { font-size:16px; font-weight:800; margin:34px 0 14px; padding-bottom:6px; border-bottom:1px solid var(--hair); }
  /* 履历时间线 */
  .tl { list-style:none; margin:0; padding:0 0 0 22px; border-left:2px solid var(--hair); }
  .tl li { position:relative; margin:0 0 18px; }
  .tl li::before { content:""; position:absolute; left:-27px; top:5px; width:9px; height:9px;
    border-radius:50%; background:var(--accent); box-shadow:0 0 0 3px var(--paper); }
  .tl .period { font-weight:800; font-variant-numeric:tabular-nums; font-size:13px; color:var(--ink); }
  .tl .milestone { margin:2px 0 4px; font-size:14.5px; line-height:1.5; }
  .tl .evidence { font-size:12px; color:var(--muted); }
  .tl .lenspills { margin-top:5px; display:flex; gap:6px; flex-wrap:wrap; }
  .lp { font-size:11px; font-weight:700; border-radius:10px; padding:1px 9px; color:#fff; }
  /* 创始人↔品牌关系(5 镜头) */
  .rel { display:grid; gap:12px; }
  .rel .card { background:var(--card); border:1px solid var(--hair); border-radius:6px; padding:12px 15px; border-left:3px solid var(--hair); }
  .rel .card h3 { margin:0 0 5px; font-size:14px; font-weight:800; display:flex; align-items:center; gap:8px; }
  .rel .card .dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
  .rel .card p { margin:0; font-size:13.5px; color:#33302b; line-height:1.6; }
  .sources { list-style:none; margin:0; padding:0; font-size:12px; color:var(--muted); }
  .sources li { margin:0 0 4px; font-family:ui-monospace,monospace; word-break:break-all; }
  footer { margin-top:36px; padding-top:14px; border-top:1px solid var(--rule); color:var(--muted); font-size:12px; line-height:1.7; }
  /* 索引页 */
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:12px; }
  .fcard { display:block; background:var(--card); border:1px solid var(--hair); border-radius:6px;
    padding:14px 16px; text-decoration:none; color:var(--ink); }
  .fcard:hover { border-color:var(--accent); }
  .fcard .n { font-size:16px; font-weight:800; }
  .fcard .r { font-size:12.5px; color:var(--muted); margin-top:3px; }
  .fcard .b { font-size:12px; color:var(--accent); margin-top:6px; font-weight:600; }
"""


def esc(s):
    return html.escape(str(s or ""), quote=False)


def shell(title, desc, nav_html, body):
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}" />
<style>{STYLE}</style>
{FAVICON}
</head>
<body>
<div class="wrap">
  <header>
    {MARK}
    <nav>{nav_html}</nav>
  </header>
{body}
  <footer>
    创始人维度梳理创始人**履历**(每条里程碑带 provenance)与**创始人↔品牌关系**(标注的分析,
    非本人原话)——作调研输入与叙事对照,<strong>不改变任何评分</strong>(分数只能来自评委重审)。
    履历复用对应评委 perspective 的一手调研;数字 / 近期动态以最新公开信息为准。
    © 2026 MBA · Jason · 清风 · John · 技术支持 <a href="https://marsdata.ai" style="color:var(--ink);">marsdata.ai</a>
  </footer>
</div>
</body>
</html>
"""


def render_founder(slug, data, brand_name):
    f = data.get("founder") or {}
    name_cn = f.get("name_cn", "")
    name_en = f.get("name_en", "")
    role = f.get("role", "")
    status = f.get("status", "")
    ps = f.get("perspective_slug")

    # 交叉链
    xlinks = []
    if ps:
        xlinks.append(f'<a href="/judge.html?slug={esc(ps)}">评委视角 {esc(name_cn)} →</a>')
    xlinks.append(f'<a href="/reports/{esc(slug)}/">品牌审计报告 →</a>')
    xlinks.append(f'<a href="/starmap/{esc(slug)}.html">品牌知识星图 →</a>')
    # 驾驶舱页仅在该品牌有舆情事件时生成(build_watch_cockpit);无事件的新品牌不挂死链
    if os.path.exists(os.path.join(ROOT, "watch", slug, "events.yaml")):
        xlinks.append(f'<a href="/watch/{esc(slug)}/cockpit.html">舆情驾驶舱 →</a>')
    for stem, partner in dinners_for(slug):
        xlinks.append(f'<a href="/collabs/{esc(stem)}.html">🍽️ 与 {esc(_founder_name(partner))} 共进晚餐 →</a>')

    # 履历时间线
    tl = []
    for c in (data.get("career") or []):
        pills = "".join(
            f'<span class="lp" style="background:{LENS_COLOR.get(l, "#8a857c")}">{esc(LENS_CN.get(l, l))}</span>'
            for l in (c.get("lens") or [])
        )
        tl.append(f"""      <li>
        <div class="period">{esc(c.get("period"))}</div>
        <div class="milestone">{esc(c.get("milestone"))}</div>
        <div class="evidence">来源:{esc(c.get("evidence"))}</div>
        <div class="lenspills">{pills}</div>
      </li>""")
    tl_html = "\n".join(tl)

    # 创始人↔品牌关系(按 5 镜头顺序)
    rel = data.get("relation") or {}
    cards = []
    for lid, cn, color in LENSES:
        txt = rel.get(lid)
        if not txt:
            continue
        cards.append(f"""      <div class="card" style="border-left-color:{color}">
        <h3><span class="dot" style="background:{color}"></span>{esc(cn)}</h3>
        <p>{esc(txt)}</p>
      </div>""")
    rel_html = "\n".join(cards)

    # 数据源
    src_html = "\n".join(f"      <li>{esc(s)}</li>" for s in (data.get("sources") or []))

    en_suffix = f" · {esc(name_en)}" if name_en else ""
    body = f"""
  <h1>{esc(name_cn)}{en_suffix}</h1>
  <p class="lede">{esc(brand_name)} · 创始人维度 —— 履历时间线 + 从人物角度看创始人↔品牌关系(按 5 镜头)</p>
  <div class="fmeta">
    <span class="fchip">{esc(role)}</span>
    <span class="fchip fchip-status">{esc(status)}</span>
  </div>
  <div class="xlinks">{"".join(xlinks)}</div>

  <h2>履历时间线</h2>
  <ul class="tl">
{tl_html}
  </ul>

  <h2>创始人 ↔ 品牌关系(5 镜头)</h2>
  <div class="rel">
{rel_html}
  </div>

  <h2>数据来源(可复盘)</h2>
  <ul class="sources">
{src_html}
  </ul>
"""
    nav = ('<a href="/">品牌监控</a>'
           '<a href="/founders/" aria-current="page">创始人</a>'
           '<a href="/watch/">舆情信号</a>'
           f'<a href="/reports/{esc(slug)}/">审计报告</a>'
           '<a href="/panorama.html">评委全景</a>')
    title = f"{name_cn} · {brand_name} 创始人维度 · MBA"
    desc = f"{name_cn}（{brand_name} {role}）的履历时间线与创始人↔品牌关系(按 5 镜头),复用 MBA 评委一手调研。"
    return shell(title, desc, nav, body)


def render_index(cards_data):
    """cards_data: [(slug, name_cn, role, brand_name)]"""
    cards = "\n".join(
        f"""    <a class="fcard" href="/founders/{esc(slug)}.html">
      <div class="n">{esc(name_cn)}</div>
      <div class="r">{esc(role)}</div>
      <div class="b">{esc(brand_name)} →</div>
    </a>""" for slug, name_cn, role, brand_name in cards_data
    )
    body = f"""
  <h1>创始人维度 · Founders</h1>
  <p class="lede">从人物角度看品牌:每个品牌创始人的履历时间线 + 创始人↔品牌关系(按 5 镜头)。
    履历复用 MBA 评委的一手调研,每条里程碑带 provenance。<strong>只作调研输入,不改分。</strong><br>
    <a href="/collabs/" style="color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent);font-weight:600">🍽️ 创始人晚餐:把两位创始人放一桌,假想推演合作 →</a></p>
  <div class="grid">
{cards}
  </div>
"""
    nav = ('<a href="/">品牌监控</a>'
           '<a href="/founders/" aria-current="page">创始人</a>'
           '<a href="/collabs/">创始人晚餐</a>'
           '<a href="/watch/">舆情信号</a>'
           '<a href="/panorama.html">评委全景</a>'
           '<a href="/starmap.html">知识星图</a>')
    return shell("创始人维度 · Founders · MBA",
                 "MBA 创始人维度:各品牌创始人的履历时间线与创始人↔品牌关系(按 5 镜头),复用评委一手调研。",
                 nav, body)


def brand_names():
    meta = yaml.safe_load(open(META, encoding="utf-8")) or {}
    out = {}
    for r in (meta.get("reports") or []):
        out[r["slug"]] = r.get("brand_cn") or r.get("card_brand") or r["slug"]
    return out


def main(argv):
    if not os.path.isdir(FOUNDERS_DIR):
        print("build_founder_pages: founders/ 不存在 —— 跳过。")
        return 0
    only = argv[0] if argv else None
    names = brand_names()
    os.makedirs(OUT_DIR, exist_ok=True)
    cards_data = []
    n = 0
    for path in sorted(glob.glob(os.path.join(FOUNDERS_DIR, "*.yaml"))):
        slug = os.path.splitext(os.path.basename(path))[0]
        data = yaml.safe_load(open(path, encoding="utf-8")) or {}
        brand_name = names.get(slug, slug)
        f = data.get("founder") or {}
        cards_data.append((slug, f.get("name_cn", slug), f.get("role", ""), brand_name))
        if only and slug != only:
            continue
        with open(os.path.join(OUT_DIR, f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(render_founder(slug, data, brand_name))
        print(f"[founder-pages] site/founders/{slug}.html")
        n += 1

    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_index(cards_data))
    print(f"[founder-pages] site/founders/index.html({len(cards_data)} 位创始人)")
    print(f"[founder-pages] done — {n} founder page(s) + index")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
