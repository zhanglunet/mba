#!/usr/bin/env python3
"""build_brand_starmap.py — 为每个已发布品牌生成一张「品牌私有知识星图」。

与全局星图(build_starmap.py)不同,这里每张图**以单一品牌为圆心**,画出该品牌
独有的三样真实数据:

  1. 评分矩阵 —— 5 镜头(按 mean 分值)+ 每位评委对每个镜头的打分(report.md 的
     Score Matrix 逐格,共 5×N 条真实边)。
  2. 舆情事件流 —— watch/<slug>/events.yaml 每条事件成一个节点,按 P0-P3 严重度
     定大小、按 pos/neg/neutral 方向着色,连到它 lens_map 指向的镜头。
  3. 版本演化 —— reports-meta.yaml 的 score_history(v1→v2→…)进详情面板。

单一真源:published/reports/<slug>/report.md(评分矩阵)· watch/<slug>/events.yaml
· site/reports-meta.yaml · site/published-reports.txt(白名单)。零依赖纯 SVG,复用
build_starmap.py 那套经验证的星座引擎。

用法:python3 scripts/build_brand_starmap.py            → 生成全部已发布品牌
      python3 scripts/build_brand_starmap.py openai     → 只生成指定 slug
接入 site/build.sh,与 build_watch_pages 同批在部署时重生成(site/starmap/ 已 gitignore)。
"""
import math, json, re, sys, pathlib, yaml, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / "published" / "reports"
WATCH = ROOT / "watch"
OUT_DIR = ROOT / "site" / "starmap"

# 5 镜头:id 用小写英文(与 events.yaml 的 lens_map 一致),cn 展示名
LENSES = [
    ("origin", "起源叙事", "Origin"),
    ("category", "品类定义", "Category"),
    ("leverage", "杠杆护城河", "Leverage"),
    ("identity", "身份系统", "Identity"),
    ("signal", "真实信号", "Signal"),
]
LENS_CN = {lid: cn for lid, cn, _ in LENSES}
LENS_BY_EN = {en.lower(): lid for lid, _, en in LENSES}
LENS_ORDER = [lid for lid, _, _ in LENSES]

WDIM_NAME = {
    "W1": "媒体报道", "W2": "社交声量", "W3": "招投标采购", "W4": "监管司法",
    "W5": "资本市场", "W6": "产品口碑", "W7": "人事组织", "W8": "技术知产", "W9": "供应链生态",
}
SEV_R = {"P0": 11.5, "P1": 8.5, "P2": 6.5, "P3": 5.0}
DIR_COLOR = {"pos": "#1a7a4a", "neg": "#b3241f", "neu": "#8a857c", "neutral": "#8a857c"}
DIR_LABEL = {"pos": "正向 ▲", "neg": "负向 ▼", "neu": "中性 ▬", "neutral": "中性 ▬"}


def esc(s):
    return html.escape(str(s), quote=True)


# ── report.md 的 Score Matrix 解析 ───────────────────────────────────────────
def parse_matrix(md):
    """返回 (judges:[name...], lens_scores:{lid:{'mean':float,'by':{judge:float}}}, judge_total:{judge:float})。
    解析不到时返回 (None, None, None)。

    兼容两种标题(`## Score Matrix` / `## 评分矩阵`)与两种单元格(纯分 `8` / delta
    `5→6 ↑1`、`**8.4** ↔`)——delta 单元格取箭头后的**当前值**。只截取标题后第一张
    连续管道表,避免误读后面的对照表。"""
    i = -1
    for h in ("## Score Matrix", "## 评分矩阵", "## Score matrix"):
        i = md.find(h)
        if i >= 0:
            break
    if i < 0:
        return None, None, None
    # 截取标题后的第一张连续 pipe 表
    rows = []
    started = False
    for ln in md[i:].splitlines()[1:]:
        s = ln.strip()
        if s.startswith("|"):
            rows.append(s)
            started = True
        elif started:
            break
    if len(rows) < 3:
        return None, None, None

    def cells(r):
        return [c.strip() for c in r.strip().strip("|").split("|")]

    header = cells(rows[0])            # ['Lens', j1, j2, ..., 'Mean']
    judges = header[1:-1]
    lens_scores, judge_total = {}, {}
    for r in rows[2:]:                  # rows[1] 是 |---|---| 分隔线
        cs = cells(r)
        if len(cs) < len(header):
            continue
        label = cs[0]
        nums = cs[1:1 + len(judges)]
        if "Judge Total" in label or "评委总分" in label or "总分" in label:
            for j, v in zip(judges, nums):
                f = _num(v)
                if f is not None:
                    judge_total[j] = f
            continue
        en = label.split("/")[0].strip().lower()
        lid = LENS_BY_EN.get(en)
        if not lid:
            continue
        by = {}
        for j, v in zip(judges, nums):
            f = _num(v)
            if f is not None:
                by[j] = f
        mean = _num(cs[-1])
        lens_scores[lid] = {"mean": mean, "by": by}
    if not lens_scores:
        return None, None, None
    return judges, lens_scores, judge_total


def _num(s):
    s = str(s).replace("*", "")
    if "→" in s:                       # delta 单元格 `5→6 ↑1` / `33→34` → 取当前值(箭头后)
        s = s.split("→")[-1]
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


# ── 事件流 ───────────────────────────────────────────────────────────────────
def load_events(slug):
    f = WATCH / slug / "events.yaml"
    if not f.exists():
        return []
    try:
        docs = yaml.safe_load(f.read_text()) or []
    except Exception:
        return []
    return [e for e in docs if isinstance(e, dict) and e.get("id")]


# ── 单品牌图 ─────────────────────────────────────────────────────────────────
def build_brand_graph(slug, meta_entry):
    md_path = REPORTS / slug / "report.md"
    if not md_path.exists():
        return None
    judges, lens_scores, judge_total = parse_matrix(md_path.read_text())
    if lens_scores is None:
        return None
    events = load_events(slug)

    cn = meta_entry.get("brand_cn", slug)
    en = meta_entry.get("brand_en", "")
    ticker = meta_entry.get("ticker", "")
    panel = meta_entry.get("panel", "—")
    version = meta_entry.get("version", "")
    score = meta_entry.get("score_normalized")
    hist = meta_entry.get("score_history", []) or []
    tldr = (meta_entry.get("headline") or meta_entry.get("tl_dr") or "").strip()

    nodes, edges = [], []

    # 圆心:品牌
    hist_html = " → ".join(f"{h['v']} {h['score']}" for h in hist) if hist else "—"
    subtitle = " · ".join(x for x in [en, ticker] if x)
    brand_meta = (
        f"<span class='mrow'><b>面板</b> {esc(panel)}　<b>版本</b> {esc(version)}　"
        f"<b>归一化</b> {esc(score) if score is not None else '—'}/10</span>"
        f"<span class='mrow'><b>评分演化</b> {esc(hist_html)}</span>"
        + (f"<span class='mrow tldr'>{esc(tldr)}</span>" if tldr else "")
        + f"<a class='mlink' href='/reports/{esc(slug)}/'>查看完整审计报告 ↗</a>"
    )
    nodes.append({"id": "brand", "name": cn, "type": "brand", "metaHtml": brand_meta,
                  "x": 0, "y": 0, "r": 19, "c": "#111111"})

    # 镜头(5):内环,按 mean 定大小
    R_L = 160
    lens_angle = {}
    for i, lid in enumerate(LENS_ORDER):
        a = -math.pi / 2 + i * (2 * math.pi / 5)
        lens_angle[lid] = a
        sc = lens_scores.get(lid, {})
        mean = sc.get("mean")
        by = sc.get("by", {})
        r = 10 + (mean or 0) * 1.35
        breakdown = "、".join(f"{esc(j)} {int(v) if v == int(v) else v}" for j, v in by.items())
        m = (f"<span class='mrow'><b>{esc(LENS_CN[lid])}</b> 镜头均分 "
             f"<b style='color:#c1440e;font-size:16px'>{esc(mean) if mean is not None else '—'}</b>/10</span>"
             f"<span class='mrow'><b>各评委打分</b> {breakdown or '—'}</span>")
        nodes.append({"id": f"lens:{lid}", "name": LENS_CN[lid], "type": "lens", "metaHtml": m,
                      "x": round(math.cos(a) * R_L, 1), "y": round(math.sin(a) * R_L, 1),
                      "r": round(r, 1), "c": "#c1440e"})
        edges.append({"s": "brand", "t": f"lens:{lid}", "w": mean})

    # 评委(N):中环 + brand→judge + judge→lens 逐格
    R_J = 268
    nj = len(judges) or 1
    maxtot = max(judge_total.values()) if judge_total else 1
    for i, j in enumerate(judges):
        a = -math.pi / 2 + (i + 0.5) * (2 * math.pi / nj)
        tot = judge_total.get(j)
        r = 6 + (tot / maxtot * 8 if tot else 4)
        per = "、".join(
            f"{esc(LENS_CN[lid])} {int(lens_scores[lid]['by'][j]) if lens_scores[lid]['by'].get(j) is not None and lens_scores[lid]['by'][j] == int(lens_scores[lid]['by'][j]) else lens_scores[lid]['by'].get(j)}"
            for lid in LENS_ORDER if lens_scores.get(lid, {}).get("by", {}).get(j) is not None
        )
        m = (f"<span class='mrow'><b>评委总分</b> {esc(tot) if tot is not None else '—'}</span>"
             f"<span class='mrow'><b>五镜头打分</b> {per or '—'}</span>")
        jid = f"judge:{i}"
        nodes.append({"id": jid, "name": j, "type": "judge", "metaHtml": m,
                      "x": round(math.cos(a) * R_J, 1), "y": round(math.sin(a) * R_J, 1),
                      "r": round(r, 1), "c": "#9a958c"})
        edges.append({"s": "brand", "t": jid})
        for lid in LENS_ORDER:
            v = lens_scores.get(lid, {}).get("by", {}).get(j)
            if v is not None:
                edges.append({"s": jid, "t": f"lens:{lid}", "cell": 1, "w": v})

    # 舆情事件(M):外环,按 lens_map 主镜头定角度,严重度定大小,方向定颜色
    R_E = 372
    consumed_versions = {}
    for k, e in enumerate(events):
        sev = str(e.get("severity", "P3")).upper()
        direction = str(e.get("direction", "neu")).lower()
        lmap = [l for l in (e.get("lens_map") or []) if l in LENS_BY_EN.values()]
        dim = e.get("dim", "")
        # 角度:贴近首个映射镜头,否则均匀铺开
        if lmap:
            base_a = lens_angle.get(lmap[0], -math.pi / 2 + k * (2 * math.pi / max(len(events), 1)))
        else:
            base_a = -math.pi / 2 + k * (2 * math.pi / max(len(events), 1))
        a = base_a + (((k * 2654435761) % 1000) / 1000 - 0.5) * 0.9
        rad = R_E + (((k * 40503) % 1000) / 1000 - 0.5) * 90
        title = e.get("title", e.get("id", "事件"))
        short = title[:16] + ("…" if len(title) > 16 else "")
        quote = e.get("quote", "")
        url = e.get("url", "")
        date = e.get("date", "")
        consumed = e.get("consumed_by")
        if consumed:
            consumed_versions.setdefault(consumed, 0)
            consumed_versions[consumed] += 1
        dim_txt = f"{dim} {WDIM_NAME.get(dim, '')}".strip()
        m = (f"<span class='mrow ptag'><span class='sev sev-{esc(sev)}'>{esc(sev)}</span>"
             f"<span class='dir dir-{esc(direction)}'>{DIR_LABEL.get(direction, direction)}</span>"
             f"<span class='dimt'>{esc(dim_txt)}</span><span class='dt'>{esc(date)}</span></span>"
             f"<span class='mrow evt-title'>{esc(title)}</span>"
             + (f"<span class='mrow evt-quote'>「{esc(quote)}」</span>" if quote else "")
             + (f"<a class='mlink' href='{esc(url)}' rel='nofollow noopener' target='_blank'>核验原文 ↗</a>" if url else ""))
        eid = f"ev:{k}"
        nodes.append({"id": eid, "name": short, "type": "event", "metaHtml": m,
                      "x": round(math.cos(a) * rad, 1), "y": round(math.sin(a) * rad, 1),
                      "r": SEV_R.get(sev, 5.0), "c": DIR_COLOR.get(direction, "#8a857c")})
        if lmap:
            for l in lmap:
                edges.append({"s": eid, "t": f"lens:{l}", "evt": 1})
        else:
            edges.append({"s": eid, "t": "brand", "evt": 1, "weak": 1})

    counts = {
        "lens": 5, "judge": len(judges), "event": len(events),
        "p0": sum(1 for e in events if str(e.get("severity")).upper() == "P0"),
    }
    return {
        "slug": slug, "cn": cn, "en": subtitle, "score": score, "version": version,
        "panel": panel, "n_events": len(events), "n_judges": len(judges),
        "nodes": nodes, "edges": edges, "counts": counts,
    }


# ── 页面渲染 ─────────────────────────────────────────────────────────────────
def render(g):
    data_json = json.dumps({"nodes": g["nodes"], "edges": g["edges"]},
                           ensure_ascii=False, separators=(",", ":"))
    sc = f"{g['score']}/10" if g["score"] is not None else "—"
    lede = (f"以 <b>{esc(g['cn'])}</b> 为圆心的品牌私有星图:内环 <b>5 镜头</b>(按评委均分定大小)· "
            f"中环 <b>{g['n_judges']} 位评委</b>(细线为每位评委对每个镜头的逐格打分)· "
            f"外环 <b>{g['n_events']} 条舆情事件</b>(P0-P3 定大小、正负向定颜色,连到其影响的镜头)。"
            f"归一化总分 <b>{esc(sc)}</b>。")
    return (TEMPLATE
            .replace("__DATA__", data_json)
            .replace("__BRAND__", esc(g["cn"]))
            .replace("__SUBTITLE__", esc(g["en"] or ""))
            .replace("__SLUG__", esc(g["slug"]))
            .replace("__LEDE__", lede)
            .replace("__NE__", str(g["n_events"]))
            .replace("__NJ__", str(g["n_judges"]))
            .replace("__P0__", str(g["counts"]["p0"])))


TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>__BRAND__ · 品牌私有知识星图 · MBA</title>
<meta name="description" content="__BRAND__ 的品牌私有知识星图:评分矩阵(5 镜头 × 评委逐格打分)+ 舆情事件流 + 版本演化,按真实数据连成的关联图谱。" />
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2064%2064'%3E%3Crect%20width='64'%20height='64'%20rx='12'%20fill='%23faf8f3'/%3E%3Cpolygon%20points='32,7%2056.7,25%2047.3,54%2016.7,54%207.3,25'%20fill='none'%20stroke='%23111'%20stroke-width='2.5'%20stroke-linejoin='round'/%3E%3Cpolygon%20points='32,8.6%2048.3,27.7%2043.9,49.4%2023.6,44.6%2014.2,27.2'%20fill='%23c1440e'%20fill-opacity='.18'%20stroke='%23c1440e'%20stroke-width='3'%20stroke-linejoin='round'/%3E%3Ccircle%20cx='32'%20cy='8.6'%20r='4'%20fill='%23c1440e'/%3E%3C/svg%3E" />
<style>
  :root{--ink:#111;--paper:#faf8f3;--muted:#6b6760;--rule:#1a1a1a;--accent:#c1440e;--card:#fff;--hair:#e2ddd3;}
  *{box-sizing:border-box;} html,body{margin:0;padding:0;}
  body{background:var(--paper);color:var(--ink);font-family:ui-sans-serif,"Inter","PingFang SC","Noto Sans SC",-apple-system,sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased;}
  .wrap{max-width:1180px;margin:0 auto;padding:32px 22px 40px;}
  header{border-bottom:2px solid var(--rule);padding-bottom:14px;margin-bottom:18px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;}
  .mark{display:inline-flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.02em;font-size:22px;line-height:1;color:var(--ink);text-decoration:none;}
  .mark .dot{color:var(--accent);}
  .mark-glyph .radar-data{stroke-dasharray:100;}
  .mark-glyph .radar-dot{transform-box:fill-box;transform-origin:center;transition:transform .25s cubic-bezier(.2,1.4,.4,1);}
  .mark:hover .radar-dot{transform:scale(1.35);}
  @media (prefers-reduced-motion:no-preference){.mark-glyph .radar-data{animation:mba-draw 1.1s cubic-bezier(.6,0,.25,1) .2s backwards;}.mark-glyph .radar-dot{animation:mba-pop .4s cubic-bezier(.2,1.6,.4,1) 1.2s backwards;}}
  @keyframes mba-draw{from{stroke-dashoffset:100;fill-opacity:0;}to{stroke-dashoffset:0;fill-opacity:1;}}
  @keyframes mba-pop{from{transform:scale(0);}to{transform:scale(1);}}
  nav a{font-size:13px;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--ink);margin-left:16px;}
  nav a:hover,nav a[aria-current]{color:var(--accent);border-color:var(--accent);}
  h1{font-size:24px;font-weight:800;margin:0 0 4px;letter-spacing:-.01em;}
  h1 .sub{font-weight:500;font-size:15px;color:var(--muted);margin-left:8px;}
  .lede{color:var(--muted);font-size:13.5px;margin:0 0 12px;max-width:82ch;}
  .lede a,.crumb a{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent);}
  .crumb{font-size:12.5px;color:var(--muted);margin:0 0 12px;}
  .controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 12px;}
  .tog{font-size:12px;font-weight:600;border:1px solid var(--hair);border-radius:999px;padding:3px 11px;cursor:pointer;background:#fff;color:var(--muted);display:inline-flex;align-items:center;gap:6px;user-select:none;}
  .tog .sw{width:9px;height:9px;border-radius:2px;}
  .tog.off{opacity:.4;text-decoration:line-through;}
  .btn{font:inherit;font-size:12px;font-weight:600;border:1px solid var(--hair);border-radius:999px;padding:4px 12px;cursor:pointer;background:#fff;color:var(--ink);}
  .btn:hover{border-color:var(--accent);color:var(--accent);}
  .legend{font-size:11.5px;color:var(--muted);display:inline-flex;align-items:center;gap:4px;margin-left:4px;}
  .legend .d{width:9px;height:9px;border-radius:50%;display:inline-block;}
  .stage{position:relative;background:radial-gradient(ellipse at center,#fffdf9,#f5f1e8);border:1px solid var(--hair);border-radius:10px;overflow:hidden;height:min(74vh,740px);}
  svg.kg{width:100%;height:100%;display:block;cursor:grab;touch-action:none;}
  svg.kg.drag{cursor:grabbing;}
  .kg-edge{stroke:#b9b2a5;stroke-width:.7;opacity:.4;}
  .kg-edge.cell{stroke:#c98a5a;stroke-width:.5;opacity:.16;}
  .kg-edge.evt{stroke-dasharray:2 3;opacity:.28;}
  .kg-edge.weak{stroke-dasharray:2 3;opacity:.16;}
  .kg-edge.hi{stroke:var(--accent);opacity:.9;stroke-width:1.2;}
  .kg-edge.lo{opacity:.05;}
  .kg-node circle{stroke:#fff;stroke-width:1.2;cursor:pointer;}
  .kg-node text{font-size:9px;fill:var(--ink);paint-order:stroke;stroke:#fdfbf6;stroke-width:2.6px;pointer-events:none;opacity:0;transition:opacity .12s;font-family:ui-sans-serif,sans-serif;}
  .kg-node.lab text,.kg-node:hover text{opacity:1;}
  .kg-node.hi circle{stroke:var(--accent);stroke-width:2;}
  .kg-node.lo{opacity:.2;}
  .kg-node.nomatch{opacity:.08;}
  .kg-node.match circle{stroke:var(--accent);stroke-width:2;}
  .panel{position:absolute;top:12px;right:12px;width:min(340px,88%);background:#fff;border:1px solid var(--hair);border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.14);padding:14px 16px;font-size:13px;display:none;max-height:calc(100% - 24px);overflow:auto;}
  .panel.on{display:block;}
  .panel h3{margin:0 0 2px;font-size:16px;padding-right:18px;}
  .panel .ptype{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#fff;padding:1px 8px;border-radius:999px;margin-bottom:8px;}
  .panel .pmeta{color:var(--muted);line-height:1.6;}
  .panel .px{position:absolute;top:8px;right:12px;cursor:pointer;color:var(--muted);font-size:18px;border:none;background:none;}
  .panel .mrow{display:block;margin-bottom:5px;}
  .panel .mrow b{color:var(--ink);}
  .panel .tldr{color:var(--ink);font-style:italic;padding-top:3px;border-top:1px dashed var(--hair);}
  .panel .evt-title{color:var(--ink);font-weight:600;}
  .panel .evt-quote{color:var(--muted);font-style:italic;}
  .panel .ptag{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:7px;}
  .panel .sev{font-weight:700;color:#fff;border-radius:4px;padding:0 6px;font-size:11px;}
  .panel .sev-P0{background:#b3241f;} .panel .sev-P1{background:#c1440e;} .panel .sev-P2{background:#c98a2b;} .panel .sev-P3{background:#9a958c;}
  .panel .dir{font-weight:700;font-size:11px;}
  .panel .dir-pos{color:#1a7a4a;} .panel .dir-neg{color:#b3241f;} .panel .dir-neu,.panel .dir-neutral{color:#8a857c;}
  .panel .dimt{font-size:11px;color:var(--muted);} .panel .dt{margin-left:auto;font-size:11px;color:var(--muted);}
  .panel .mlink{display:inline-block;margin-top:6px;color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent);font-size:12px;}
  .panel .pconn{margin-top:10px;font-size:12px;color:var(--muted);border-top:1px solid var(--hair);padding-top:8px;}
  .panel .pconn b{color:var(--ink);}
  .hint{font-size:11.5px;color:var(--muted);margin:8px 2px 0;}
  footer{margin-top:20px;padding-top:14px;border-top:1px solid var(--rule);color:var(--muted);font-size:12px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;}
  footer a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--ink);}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <a class="mark" href="/" role="img" aria-label="MBA — Metric Brand Auditor">
      <svg class="mark-glyph" viewBox="0 0 64 64" width="34" height="34" aria-hidden="true" focusable="false"><defs><linearGradient id="mbaGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c1440e" stop-opacity=".30"/><stop offset="1" stop-color="#c1440e" stop-opacity=".06"/></linearGradient></defs><polygon points="32,7 56.7,25 47.3,54 16.7,54 7.3,25" fill="none" stroke="#111" stroke-width="2" stroke-linejoin="round"/><g fill="none" stroke="#111" opacity=".12" stroke-width="1"><polygon points="32,20 44.4,29 39.6,43.5 24.4,43.5 19.6,29" stroke-linejoin="round"/><path d="M32 33V7M32 33 56.7 25M32 33 47.3 54M32 33 16.7 54M32 33 7.3 25"/></g><polygon class="radar-data" pathLength="100" points="32,8.6 48.3,27.7 43.9,49.4 23.6,44.6 14.2,27.2" fill="url(#mbaGrad)" stroke="#c1440e" stroke-width="2.5" stroke-linejoin="round"/><circle class="radar-dot" cx="32" cy="8.6" r="3.2" fill="#c1440e" stroke="#faf8f3" stroke-width="1.5"/></svg>
      <span>MBA<span class="dot">.</span></span>
    </a>
    <nav><a href="/">品牌监控</a><a href="/watch/">舆情信号</a><a href="/panorama.html">评委全景</a><a href="/starmap.html">知识星图</a><a href="/docs.html">文档</a><a href="https://github.com/zhanglunet/mba">GitHub</a></nav>
  </header>

  <p class="crumb"><a href="/starmap.html">← 全维度知识星图</a>　/　<a href="/reports/__SLUG__/">__BRAND__ 审计报告</a></p>
  <h1>__BRAND__<span class="sub">__SUBTITLE__ · 品牌私有星图</span></h1>
  <p class="lede">__LEDE__</p>

  <div class="controls">
    <span class="tog" data-type="lens"><span class="sw" style="background:#c1440e"></span>镜头 5</span>
    <span class="tog" data-type="judge"><span class="sw" style="background:#9a958c"></span>评委 __NJ__</span>
    <span class="tog" data-type="event"><span class="sw" style="background:#1a7a4a"></span>舆情事件 __NE__</span>
    <button class="btn" id="kg-reset">重置视图</button>
    <span class="legend"><span class="d" style="background:#1a7a4a"></span>正向<span class="d" style="background:#b3241f;margin-left:8px"></span>负向<span class="d" style="background:#8a857c;margin-left:8px"></span>中性 · 大小=P0-P3 严重度</span>
  </div>

  <div class="stage" id="kg-host"></div>
  <p class="hint">点节点看评分/事件详情 · 悬停显示标签 · 滚轮缩放 · 拖拽平移。橙色细线=某评委对某镜头的逐格打分 · 虚线=舆情事件影响的镜头。__P0__ 条 P0 事件。</p>

  <footer>
    <span>MBA · __BRAND__ 品牌私有星图 · 数据源:report.md 评分矩阵 · watch/__SLUG__/events.yaml · reports-meta.yaml</span>
    <span><a href="/reports/__SLUG__/">审计报告</a> · <a href="/starmap.html">全局星图</a></span>
  </footer>
</div>

<script type="application/json" id="kg-data">__DATA__</script>
<script>
(function(){
  var NS='http://www.w3.org/2000/svg';
  var host=document.getElementById('kg-host');
  var data=JSON.parse(document.getElementById('kg-data').textContent);
  var nodes=data.nodes, edges=data.edges, byId={}; nodes.forEach(function(n){byId[n.id]=n;});
  var TYPE_LABEL={lens:'镜头',judge:'评委',brand:'品牌',event:'舆情事件'};

  var xs=nodes.map(function(n){return n.x;}), ys=nodes.map(function(n){return n.y;});
  var pad=70, minX=Math.min.apply(0,xs)-pad, maxX=Math.max.apply(0,xs)+pad, minY=Math.min.apply(0,ys)-pad, maxY=Math.max.apply(0,ys)+pad;
  var vb={x:minX,y:minY,w:maxX-minX,h:maxY-minY}, home={x:minX,y:minY,w:maxX-minX,h:maxY-minY};

  var svg=document.createElementNS(NS,'svg'); svg.setAttribute('class','kg');
  svg.setAttribute('aria-label','品牌私有星图:'+nodes.length+' 个实体按真实关系连成的关联图谱');
  function setVB(){ svg.setAttribute('viewBox',vb.x+' '+vb.y+' '+vb.w+' '+vb.h); }
  setVB(); host.appendChild(svg);
  var gE=document.createElementNS(NS,'g'), gN=document.createElementNS(NS,'g'); svg.appendChild(gE); svg.appendChild(gN);

  var adj={}; nodes.forEach(function(n){adj[n.id]={};});
  edges.forEach(function(e){ if(byId[e.s]&&byId[e.t]){adj[e.s][e.t]=1;adj[e.t][e.s]=1;} });

  edges.forEach(function(e){ if(!byId[e.s]||!byId[e.t])return;
    var ln=document.createElementNS(NS,'line');
    ln.setAttribute('class','kg-edge'+(e.cell?' cell':'')+(e.evt?' evt':'')+(e.weak?' weak':''));
    ln.setAttribute('x1',byId[e.s].x);ln.setAttribute('y1',byId[e.s].y);ln.setAttribute('x2',byId[e.t].x);ln.setAttribute('y2',byId[e.t].y);
    e.el=ln; gE.appendChild(ln);
  });
  nodes.forEach(function(n){
    var g=document.createElementNS(NS,'g'); g.setAttribute('class','kg-node'); g.setAttribute('data-type',n.type);
    var c=document.createElementNS(NS,'circle'); c.setAttribute('cx',n.x);c.setAttribute('cy',n.y);c.setAttribute('r',n.r);c.setAttribute('fill',n.c);
    var t=document.createElementNS(NS,'text'); t.setAttribute('x',n.x);t.setAttribute('y',n.y-n.r-2);t.setAttribute('text-anchor','middle');t.textContent=n.name;
    g.appendChild(c); g.appendChild(t); n.g=g;
    if(n.type==='lens'||n.type==='brand'){g.classList.add('lab');}
    g.addEventListener('mouseenter',function(){focus(n.id);});
    g.addEventListener('click',function(ev){ev.preventDefault();openPanel(n.id);focus(n.id);});
    gN.appendChild(g);
  });
  svg.addEventListener('mouseleave',function(){ if(!locked)focus(null); });

  var locked=null;
  function baseLab(n){return n.type==='lens'||n.type==='brand';}
  function focus(id){
    if(id===null){ nodes.forEach(function(n){n.g.classList.remove('hi','lo');n.g.classList.toggle('lab',baseLab(n));});
      edges.forEach(function(e){e.el&&e.el.classList.remove('hi','lo');}); return; }
    nodes.forEach(function(n){ var near=(n.id===id)||adj[id][n.id];
      n.g.classList.toggle('hi',n.id===id); n.g.classList.toggle('lo',!near); n.g.classList.toggle('lab',near); });
    edges.forEach(function(e){ var on=(e.s===id||e.t===id); e.el.classList.toggle('hi',on); e.el.classList.toggle('lo',!on); });
  }

  var panel=document.createElement('div'); panel.className='panel';
  panel.innerHTML='<button class="px" aria-label="关闭">×</button><span class="ptype"></span><h3></h3><div class="pmeta"></div><div class="pconn"></div>';
  host.appendChild(panel);
  panel.querySelector('.px').addEventListener('click',function(){panel.classList.remove('on');locked=null;focus(null);});
  function openPanel(id){
    var n=byId[id]; locked=id;
    var pt=panel.querySelector('.ptype'); pt.textContent=TYPE_LABEL[n.type]; pt.style.background=n.c;
    panel.querySelector('h3').textContent=n.name;
    panel.querySelector('.pmeta').innerHTML=n.metaHtml||'';
    var conns=Object.keys(adj[id]).map(function(k){return byId[k];}).filter(Boolean);
    var byT={}; conns.forEach(function(m){(byT[m.type]=byT[m.type]||[]).push(m.name);});
    var h=Object.keys(byT).map(function(t){return '<b>'+TYPE_LABEL[t]+'</b>('+byT[t].length+')：'+byT[t].slice(0,10).join('、')+(byT[t].length>10?'…':'');}).join('<br>');
    panel.querySelector('.pconn').innerHTML=conns.length?('关联 '+conns.length+' 个：<br>'+h):'';
    panel.classList.add('on');
  }

  var off={};
  function applyVis(){ nodes.forEach(function(n){n.g.style.display=off[n.type]?'none':'';});
    edges.forEach(function(e){e.el.style.display=(off[byId[e.s].type]||off[byId[e.t].type])?'none':'';}); }
  Array.prototype.forEach.call(document.querySelectorAll('.tog'),function(el){
    el.addEventListener('click',function(){var ty=el.getAttribute('data-type');off[ty]=!off[ty];el.classList.toggle('off',off[ty]);applyVis();});
  });

  svg.addEventListener('wheel',function(ev){ev.preventDefault();
    var pt=svg.createSVGPoint();pt.x=ev.clientX;pt.y=ev.clientY;var m=svg.getScreenCTM();if(!m)return;var p=pt.matrixTransform(m.inverse());
    var k=ev.deltaY<0?0.85:1.18; var nw=Math.max(120,Math.min(home.w*2.4,vb.w*k)), nh=nw*(vb.h/vb.w);
    vb.x=p.x-(p.x-vb.x)*(nw/vb.w); vb.y=p.y-(p.y-vb.y)*(nh/vb.h); vb.w=nw; vb.h=nh; setVB();
  },{passive:false});
  var drag=null;
  svg.addEventListener('pointerdown',function(ev){drag={x:ev.clientX,y:ev.clientY,vx:vb.x,vy:vb.y};svg.classList.add('drag');svg.setPointerCapture(ev.pointerId);});
  svg.addEventListener('pointermove',function(ev){if(!drag)return;var m=svg.getScreenCTM();if(!m)return;var s=vb.w/svg.clientWidth;vb.x=drag.vx-(ev.clientX-drag.x)*s;vb.y=drag.vy-(ev.clientY-drag.y)*s;setVB();});
  svg.addEventListener('pointerup',function(){drag=null;svg.classList.remove('drag');});
  document.getElementById('kg-reset').addEventListener('click',function(){vb.x=home.x;vb.y=home.y;vb.w=home.w;vb.h=home.h;setVB();panel.classList.remove('on');locked=null;focus(null);});
})();
</script>
</body>
</html>
"""


def main(argv):
    meta = yaml.safe_load((ROOT / "site" / "reports-meta.yaml").read_text())
    meta_by = {m["slug"]: m for m in meta.get("reports", [])}
    whitelist = [ln.strip() for ln in (ROOT / "site" / "published-reports.txt").read_text().splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
    only = [a for a in argv if not a.startswith("-")]
    targets = [s for s in whitelist if (not only or s in only)]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    built, skipped = [], []
    for slug in targets:
        m = meta_by.get(slug, {"slug": slug})
        g = build_brand_graph(slug, m)
        if g is None:
            skipped.append(slug)
            continue
        (OUT_DIR / f"{slug}.html").write_text(render(g), encoding="utf-8")
        built.append((slug, len(g["nodes"]), len(g["edges"]), g["n_events"]))
    for slug, nn, ne, nev in built:
        print(f"[brand-starmap] {slug}.html — {nn} nodes / {ne} edges / {nev} events")
    if skipped:
        print(f"[brand-starmap] skipped (no report.md / matrix): {', '.join(skipped)}")
    print(f"[brand-starmap] built {len(built)} brand maps → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
