#!/usr/bin/env python3
"""build_starmap.py — 从真实数据生成品牌监控全维度知识星图 site/starmap.html。

单一真源:watch/matrix.yaml(品牌×W 适用性)· metric-brand-auditor/panels/*.yaml(面板→评委)
· site/reports-meta.yaml(品牌→面板+归一化分)· 本文件内静态编码的 9 监控维度 W1-W9(docs/15 §4.1)
+ 5 镜头 + W→镜头映射。零依赖纯 SVG 星图(灵感来自 zhanglunet/shanghai constellation)。

用法:python3 scripts/build_starmap.py   → 覆盖 site/starmap.html
接入 site/build.sh,与 build_home_cards / build_watch_pages 同批重生成。
"""
import math, json, pathlib, yaml, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
PANELS_DIR = ROOT / "metric-brand-auditor" / "panels"

# ── 静态维度模型(docs/15 §4.1)──────────────────────────────────────────────
LENSES = [  # id 用英文;镜头是 MBA 评分的固定 5 维
    ("Origin", "起源叙事", "创始故事与来源真实性"),
    ("Category", "品类定义", "是否定义/占据一个品类词"),
    ("Leverage", "杠杆护城河", "护城河与增长杠杆的质量"),
    ("Identity", "身份系统", "视觉+语言身份的一致性"),
    ("Signal", "真实信号", "可核查的现实世界信号"),
]
WDIMS = [  # (Wn, 名称, 信号性质, 一句话, [镜头])
    ("W1", "媒体报道", "软+硬", "财经/行业/官方媒体的报道与调查", ["Signal", "Identity"]),
    ("W2", "社交与社区声量", "软", "微博/知乎/小红书/X/Reddit 的大众情绪与热点", ["Identity", "Category"]),
    ("W3", "招投标与采购", "硬", "中标/落标/黑名单/合同额——B2B/B2G 真金白银", ["Leverage", "Signal"]),
    ("W4", "监管司法与合规", "硬", "处罚、问询函、诉讼、召回、禁令", ["Signal", "Leverage"]),
    ("W5", "资本市场信号", "硬", "财报、股价异动、评级、减持、做空报告", ["Signal"]),
    ("W6", "产品口碑与投诉", "软+硬", "电商/应用商店评分、黑猫投诉、质量事件", ["Signal", "Identity"]),
    ("W7", "人事与组织", "硬", "高管变动、裁员/扩张、创始人动向", ["Origin", "Leverage"]),
    ("W8", "技术与知识产权", "硬", "专利、开源、CVE、论文、发射/交付节奏", ["Leverage", "Category"]),
    ("W9", "供应链与生态伙伴", "硬", "合作公告、断供、渠道进退、大客户流失", ["Leverage"]),
]
COLORS = {"lens": "#c1440e", "wdim": "#1a4a7a", "brand": "#111111", "panel": "#1a7a4a", "judge": "#9a958c"}
TYPE_LABEL = {"lens": "镜头", "wdim": "监控维度", "brand": "品牌", "panel": "面板", "judge": "评委"}


def load():
    matrix = yaml.safe_load((ROOT / "watch" / "matrix.yaml").read_text())["brands"]
    meta = yaml.safe_load((ROOT / "site" / "reports-meta.yaml").read_text())
    panels = {}
    for f in sorted(PANELS_DIR.glob("*.yaml")):
        if f.stem == "industries":
            continue
        y = yaml.safe_load(f.read_text())
        if isinstance(y, dict) and "judges" in y:
            panels[y["name"]] = y
    return matrix, meta, panels


def build_graph():
    matrix, meta, panels = load()
    nodes, edges = [], []

    def add(id, name, type, meta_txt, weight=1.0):
        nodes.append({"id": id, "name": name, "type": type, "meta": meta_txt, "w": weight})

    # 镜头(5)
    for lid, cn, desc in LENSES:
        add(f"lens:{lid}", cn, "lens", f"{cn}（{lid}）· {desc}", 1.6)
    # 监控维度(9)+ W→镜头
    for wn, name, kind, oneline, lensmap in WDIMS:
        add(f"wdim:{wn}", f"{wn} {name}", "wdim", f"{oneline}｜{kind}信号｜映射镜头：{'·'.join(lensmap)}", 1.3)
        for L in lensmap:
            edges.append({"s": f"wdim:{wn}", "t": f"lens:{L}"})
    # 面板(10)+ 面板→评委
    seen_judges = {}
    for pname, p in panels.items():
        roster = [j for j in p.get("judges", [])]
        add(f"panel:{pname}", p.get("display_name", pname), "panel",
            f"面板 · {len(roster)} 位评委：{'、'.join(j.get('display_name_cn', j['slug']) for j in roster)}", 1.25)
        for j in roster:
            jid = f"judge:{j['slug']}"
            if jid not in seen_judges:
                cn = j.get("display_name_cn", j["slug"]); en = j.get("display_name_en", "")
                seen_judges[jid] = {"cn": cn, "en": en, "panels": []}
                add(jid, cn, "judge", f"评委 · {en}", 0.7)
            seen_judges[jid]["panels"].append(pname)
            edges.append({"s": f"panel:{pname}", "t": jid})
    # 评委 meta 补面板归属
    for jid, info in seen_judges.items():
        for n in nodes:
            if n["id"] == jid:
                n["meta"] = f"评委 · {info['en']}｜所属面板：{'、'.join(info['panels'])}"
    # 品牌(15)+ 品牌→面板 + 品牌→W(核心维度)
    for slug, dims in matrix.items():
        m = meta.get(slug, {}) if isinstance(meta, dict) else {}
        cn = m.get("brand_cn", slug); en = m.get("brand_en", ""); panel = m.get("panel")
        score = m.get("score_normalized")
        core = [w for w in ("W1","W2","W3","W4","W5","W6","W7","W8","W9") if dims.get(w) == "core"]
        appl = [w for w in ("W1","W2","W3","W4","W5","W6","W7","W8","W9") if dims.get(w) is True]
        sc = f"{score}/10" if score is not None else "—"
        add(f"brand:{slug}", cn, "brand",
            f"品牌 · {en}｜面板 {panel or '—'}｜归一化 {sc}｜核心监控维度：{'·'.join(core) or '—'}",
            1.0 + (0.05 * len(core)))
        nodes[-1]["url"] = f"/starmap/{slug}.html"  # 下钻:品牌私有星图
        if panel and f"panel:{panel}" in {n['id'] for n in nodes}:
            edges.append({"s": f"brand:{slug}", "t": f"panel:{panel}"})
        for w in core:
            edges.append({"s": f"brand:{slug}", "t": f"wdim:{w}"})
        for w in appl:  # 适用(○)作弱连
            edges.append({"s": f"brand:{slug}", "t": f"wdim:{w}", "weak": 1})

    # ── 确定性布局:按类型分同心带 + 均匀角度 + 种子抖动 ──────────────────────
    BAND = {"lens": 95, "wdim": 195, "panel": 300, "brand": 400, "judge": 500}
    seed = [20260713]
    def rnd():
        seed[0] = (seed[0] * 1103515245 + 12345) & 0x7fffffff
        return seed[0] / 0x7fffffff
    by_type = {}
    for n in nodes:
        by_type.setdefault(n["type"], []).append(n)
    for type, arr in by_type.items():
        base = BAND[type]; N = len(arr)
        for i, n in enumerate(arr):
            a = 2 * math.pi * i / N + rnd() * 0.5
            rad = base + (rnd() - 0.5) * 70
            n["x"] = round(math.cos(a) * rad, 1)
            n["y"] = round(math.sin(a) * rad, 1)
            n["r"] = round({"lens": 14, "wdim": 11, "panel": 10, "brand": 9, "judge": 4.5}[type] * (0.85 + 0.3 * n["w"]) / 1.2, 1)
            n["c"] = COLORS[type]
    return {"nodes": nodes, "edges": edges}


# ── 页面模板(house style + 雷达 logo + 星图 JS/CSS,零外部依赖)────────────────
def render(graph):
    data_json = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
    counts = {}
    for n in graph["nodes"]:
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    legend = " · ".join(f"{TYPE_LABEL[t]} {counts.get(t,0)}" for t in ("brand","wdim","lens","panel","judge"))
    return TEMPLATE.replace("__DATA__", data_json).replace("__LEGEND__", html.escape(legend)) \
                   .replace("__NODES__", str(len(graph["nodes"]))).replace("__EDGES__", str(len(graph["edges"])))


TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>品牌监控全维度知识星图 · MBA</title>
<meta name="description" content="MBA 品牌监控全维度知识星图:品牌 × 9 监控维度 × 5 镜头 × 面板 × 评委,按真实关系连成的关联图谱。可搜索、聚焦、按类型筛选。" />
<meta property="og:title" content="MBA 品牌监控知识星图" />
<meta property="og:url" content="https://mbabrand.com/starmap.html" />
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
  .lede{color:var(--muted);font-size:13.5px;margin:0 0 14px;max-width:80ch;}
  .lede a{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent);}
  .controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 12px;}
  .controls input{font:inherit;font-size:13px;padding:6px 12px;border:1px solid var(--hair);border-radius:999px;min-width:180px;background:#fff;}
  .controls input:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent);}
  .tog{font-size:12px;font-weight:600;border:1px solid var(--hair);border-radius:999px;padding:3px 11px;cursor:pointer;background:#fff;color:var(--muted);display:inline-flex;align-items:center;gap:6px;user-select:none;}
  .tog .sw{width:9px;height:9px;border-radius:2px;}
  .tog.off{opacity:.4;text-decoration:line-through;}
  .btn{font:inherit;font-size:12px;font-weight:600;border:1px solid var(--hair);border-radius:999px;padding:4px 12px;cursor:pointer;background:#fff;color:var(--ink);}
  .btn:hover{border-color:var(--accent);color:var(--accent);}
  .stage{position:relative;background:radial-gradient(ellipse at center,#fffdf9,#f5f1e8);border:1px solid var(--hair);border-radius:10px;overflow:hidden;height:min(72vh,720px);}
  svg.kg{width:100%;height:100%;display:block;cursor:grab;touch-action:none;}
  svg.kg.drag{cursor:grabbing;}
  .kg-edge{stroke:#b9b2a5;stroke-width:.6;opacity:.35;}
  .kg-edge.weak{stroke-dasharray:2 3;opacity:.18;}
  .kg-edge.hi{stroke:var(--accent);opacity:.85;stroke-width:1.1;}
  .kg-edge.lo{opacity:.06;}
  .kg-node circle{stroke:#fff;stroke-width:1.2;cursor:pointer;transition:transform .12s;}
  .kg-node text{font-size:9px;fill:var(--ink);paint-order:stroke;stroke:#fdfbf6;stroke-width:2.6px;pointer-events:none;opacity:0;transition:opacity .12s;font-family:ui-sans-serif,sans-serif;}
  .kg-node.lab text,.kg-node:hover text{opacity:1;}
  .kg-node.hi circle{stroke:var(--accent);stroke-width:2;}
  .kg-node.lo{opacity:.22;}
  .kg-node.nomatch{opacity:.08;}
  .kg-node.match circle{stroke:var(--accent);stroke-width:2;}
  .panel{position:absolute;top:12px;right:12px;width:min(320px,86%);background:#fff;border:1px solid var(--hair);border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.12);padding:14px 16px;font-size:13px;display:none;}
  .panel.on{display:block;}
  .panel h3{margin:0 0 2px;font-size:16px;}
  .panel .ptype{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#fff;padding:1px 8px;border-radius:999px;margin-bottom:8px;}
  .panel .pmeta{color:var(--muted);line-height:1.6;}
  .panel .px{position:absolute;top:8px;right:12px;cursor:pointer;color:var(--muted);font-size:18px;border:none;background:none;}
  .panel .pconn{margin-top:10px;font-size:12px;color:var(--muted);}
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
    <nav><a href="/">品牌监控</a><a href="/watch/">舆情信号</a><a href="/panorama.html">评委全景</a><a href="/starmap.html" aria-current="page">知识星图</a><a href="/docs.html">文档</a><a href="https://github.com/zhanglunet/mba">GitHub</a></nav>
  </header>

  <h1>品牌监控全维度知识星图</h1>
  <p class="lede">__NODES__ 个实体 · __EDGES__ 条关系:<b>品牌</b> × <b>9 监控维度 W</b> × <b>5 镜头</b> × <b>面板</b> × <b>评委</b>,按真实数据连成的关联图谱。数据源:<a href="https://github.com/zhanglunet/mba/blob/main/watch/matrix.yaml">watch/matrix.yaml</a> · panels/*.yaml · reports-meta.yaml（由 <code>scripts/build_starmap.py</code> 生成）。</p>

  <div class="controls">
    <input id="kg-search" type="search" placeholder="搜索品牌/维度/评委…" autocomplete="off" />
    <span class="tog" data-type="brand"><span class="sw" style="background:#111"></span>品牌</span>
    <span class="tog" data-type="wdim"><span class="sw" style="background:#1a4a7a"></span>监控维度</span>
    <span class="tog" data-type="lens"><span class="sw" style="background:#c1440e"></span>镜头</span>
    <span class="tog" data-type="panel"><span class="sw" style="background:#1a7a4a"></span>面板</span>
    <span class="tog" data-type="judge"><span class="sw" style="background:#9a958c"></span>评委</span>
    <button class="btn" id="kg-reset">重置视图</button>
  </div>

  <div class="stage" id="kg-host"></div>
  <p class="hint">点节点看详情与关联 · 悬停显示标签 · 滚轮缩放 · 拖拽平移 · 上方筛选类型 / 搜索。灵感来自 <a href="https://github.com/zhanglunet/shanghai" style="color:var(--accent)">zhanglunet/shanghai</a> 的知识星图。</p>

  <footer>
    <span>MBA · 品牌监控全维度星图 · 图例:__LEGEND__</span>
    <span><a href="/docs.html">文档</a> · <a href="https://github.com/zhanglunet/mba">GitHub</a></span>
  </footer>
</div>

<script type="application/json" id="kg-data">__DATA__</script>
<script>
(function(){
  var NS='http://www.w3.org/2000/svg';
  var host=document.getElementById('kg-host');
  var data=JSON.parse(document.getElementById('kg-data').textContent);
  var nodes=data.nodes, edges=data.edges, byId={}; nodes.forEach(function(n){byId[n.id]=n;});
  var TYPE_LABEL={lens:'镜头',wdim:'监控维度',brand:'品牌',panel:'面板',judge:'评委'};

  // viewBox 适配所有点
  var xs=nodes.map(function(n){return n.x;}), ys=nodes.map(function(n){return n.y;});
  var pad=60, minX=Math.min.apply(0,xs)-pad, maxX=Math.max.apply(0,xs)+pad, minY=Math.min.apply(0,ys)-pad, maxY=Math.max.apply(0,ys)+pad;
  var vb={x:minX,y:minY,w:maxX-minX,h:maxY-minY}, home={x:minX,y:minY,w:maxX-minX,h:maxY-minY};

  var svg=document.createElementNS(NS,'svg'); svg.setAttribute('class','kg');
  svg.setAttribute('aria-label','知识星图:'+nodes.length+' 个实体按真实关系连成的关联图谱');
  function setVB(){ svg.setAttribute('viewBox',vb.x+' '+vb.y+' '+vb.w+' '+vb.h); }
  setVB(); host.appendChild(svg);
  var gE=document.createElementNS(NS,'g'), gN=document.createElementNS(NS,'g'); svg.appendChild(gE); svg.appendChild(gN);

  // 邻接
  var adj={}; nodes.forEach(function(n){adj[n.id]={};});
  edges.forEach(function(e){ if(byId[e.s]&&byId[e.t]){adj[e.s][e.t]=1;adj[e.t][e.s]=1;} });

  // 边
  edges.forEach(function(e){ if(!byId[e.s]||!byId[e.t])return;
    var ln=document.createElementNS(NS,'line'); ln.setAttribute('class','kg-edge'+(e.weak?' weak':''));
    ln.setAttribute('x1',byId[e.s].x);ln.setAttribute('y1',byId[e.s].y);ln.setAttribute('x2',byId[e.t].x);ln.setAttribute('y2',byId[e.t].y);
    e.el=ln; gE.appendChild(ln);
  });
  // 节点
  nodes.forEach(function(n){
    var g=document.createElementNS(NS,'g'); g.setAttribute('class','kg-node'); g.setAttribute('data-type',n.type);
    var c=document.createElementNS(NS,'circle'); c.setAttribute('cx',n.x);c.setAttribute('cy',n.y);c.setAttribute('r',n.r);c.setAttribute('fill',n.c);
    var t=document.createElementNS(NS,'text'); t.setAttribute('x',n.x);t.setAttribute('y',n.y-n.r-2);t.setAttribute('text-anchor','middle');t.textContent=n.name;
    g.appendChild(c); g.appendChild(t); n.g=g;
    if(n.type==='lens'||n.type==='wdim'){g.classList.add('lab');} // 核心维度常显标签
    g.addEventListener('mouseenter',function(){focus(n.id);});
    g.addEventListener('click',function(ev){ev.preventDefault();openPanel(n.id);focus(n.id);});
    gN.appendChild(g);
  });
  svg.addEventListener('mouseleave',function(){ if(!locked)focus(null); });

  var locked=null;
  function focus(id){
    if(id===null){ nodes.forEach(function(n){n.g.classList.remove('hi','lo');n.g.classList.toggle('lab',n.type==='lens'||n.type==='wdim');});
      edges.forEach(function(e){e.el&&e.el.classList.remove('hi','lo');}); return; }
    nodes.forEach(function(n){ var near=(n.id===id)||adj[id][n.id];
      n.g.classList.toggle('hi',n.id===id); n.g.classList.toggle('lo',!near); n.g.classList.toggle('lab',near); });
    edges.forEach(function(e){ var on=(e.s===id||e.t===id); e.el.classList.toggle('hi',on); e.el.classList.toggle('lo',!on); });
  }

  // 详情面板
  var panel=document.createElement('div'); panel.className='panel';
  panel.innerHTML='<button class="px" aria-label="关闭">×</button><span class="ptype"></span><h3></h3><div class="pmeta"></div><div class="pconn"></div>';
  host.appendChild(panel);
  panel.querySelector('.px').addEventListener('click',function(){panel.classList.remove('on');locked=null;focus(null);});
  function openPanel(id){
    var n=byId[id]; locked=id;
    var pt=panel.querySelector('.ptype'); pt.textContent=TYPE_LABEL[n.type]; pt.style.background=n.c;
    panel.querySelector('h3').textContent=n.name;
    panel.querySelector('.pmeta').textContent=n.meta;
    var conns=Object.keys(adj[id]).map(function(k){return byId[k];}).filter(Boolean);
    var byT={}; conns.forEach(function(m){(byT[m.type]=byT[m.type]||[]).push(m.name);});
    var html=Object.keys(byT).map(function(t){return '<b>'+TYPE_LABEL[t]+'</b>('+byT[t].length+')：'+byT[t].slice(0,8).join('、')+(byT[t].length>8?'…':'');}).join('<br>');
    var drill=n.url?('<a href="'+n.url+'" style="display:inline-block;margin:2px 0 10px;color:#c1440e;text-decoration:none;border-bottom:1px solid #c1440e;font-weight:600">查看 '+n.name+' 品牌私有星图 →</a><br>'):'';
    panel.querySelector('.pconn').innerHTML=drill+(conns.length?('关联 '+conns.length+' 个：<br>'+html):'（无关联）');
    panel.classList.add('on');
  }

  // 类型筛选
  var off={};
  function applyVis(){ nodes.forEach(function(n){n.g.style.display=off[n.type]?'none':'';});
    edges.forEach(function(e){e.el.style.display=(off[byId[e.s].type]||off[byId[e.t].type])?'none':'';}); }
  Array.prototype.forEach.call(document.querySelectorAll('.tog'),function(el){
    el.addEventListener('click',function(){var ty=el.getAttribute('data-type');off[ty]=!off[ty];el.classList.toggle('off',off[ty]);applyVis();});
  });

  // 搜索
  document.getElementById('kg-search').addEventListener('input',function(e){
    var q=e.target.value.trim().toLowerCase();
    if(!q){nodes.forEach(function(n){n.g.classList.remove('match','nomatch');n.g.classList.toggle('lab',n.type==='lens'||n.type==='wdim');});return;}
    nodes.forEach(function(n){var m=n.name.toLowerCase().indexOf(q)>=0;n.g.classList.toggle('match',m);n.g.classList.toggle('nomatch',!m);n.g.classList.toggle('lab',m);});
  });

  // 缩放 + 平移
  svg.addEventListener('wheel',function(ev){ev.preventDefault();
    var pt=svg.createSVGPoint();pt.x=ev.clientX;pt.y=ev.clientY;var m=svg.getScreenCTM();if(!m)return;var p=pt.matrixTransform(m.inverse());
    var k=ev.deltaY<0?0.85:1.18; var nw=Math.max(120,Math.min(home.w*2.4,vb.w*k)), nh=nw*(vb.h/vb.w);
    vb.x=p.x-(p.x-vb.x)*(nw/vb.w); vb.y=p.y-(p.y-vb.y)*(nh/vb.h); vb.w=nw; vb.h=nh; setVB();
  },{passive:false});
  var drag=null;
  svg.addEventListener('pointerdown',function(ev){drag={x:ev.clientX,y:ev.clientY,vx:vb.x,vy:vb.y};svg.classList.add('drag');svg.setPointerCapture(ev.pointerId);});
  svg.addEventListener('pointermove',function(ev){if(!drag)return;var m=svg.getScreenCTM();if(!m)return;var s=vb.w/svg.clientWidth;vb.x=drag.vx-(ev.clientX-drag.x)*s;vb.y=drag.vy-(ev.clientY-drag.y)*s;setVB();});
  svg.addEventListener('pointerup',function(){drag=null;svg.classList.remove('drag');});
  document.getElementById('kg-reset').addEventListener('click',function(){vb.x=home.x;vb.y=home.y;vb.w=home.w;vb.h=home.h;setVB();panel.classList.remove('on');locked=null;focus(null);document.getElementById('kg-search').value='';document.getElementById('kg-search').dispatchEvent(new Event('input'));});
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    g = build_graph()
    out = ROOT / "site" / "starmap.html"
    out.write_text(render(g), encoding="utf-8")
    print(f"[starmap] {out} — {len(g['nodes'])} nodes / {len(g['edges'])} edges")
