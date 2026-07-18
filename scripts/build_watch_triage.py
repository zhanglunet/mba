#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_watch_triage.py — 生成「舆情候选 triage」前台页(site/watch/triage.html)。

把每日自动发现的候选事件(watch/_candidates/*.json,由 fetch_candidate.py discover 产出)
聚合成一个**前台可视化审核页**:每条候选一张卡片,带 ✓采纳 / ✗丢弃 / 待定,可就地改
dim/severity/direction/lens;选完一键**复制「已采纳」YAML**(粘进 watch/<slug>/events.yaml)。

反捏造边界(与 discover 一致,docs/15/16):
  - url / quote / date 取自源 feed,页面从不编造;
  - dim / severity / direction / lens 是**人工判断**(页面上你打的勾),不是自动打分;
  - **前台不写库**:页面只在浏览器里(localStorage)记你的选择 + 导出 YAML,git 仍是唯一真源
    —— 采纳项必须 commit 进 events.yaml 再跑 validate_watch.py 才生效。任何访客都改不了审计仓库。

数据源:watch/_candidates/*.json(committed)。产物:
  - site/watch/triage.html —— 自包含(候选数据 inline),Cloudflare Pages 直接托管;
  - site/watch/candidates.json —— 结构化聚合(供 agent / 其它页复用)。
两者都在 gitignored 的 site/watch/ 下,随 build 重生成(同 cockpit)。

用法:python3 scripts/build_watch_triage.py
"""
import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND_DIR = os.path.join(ROOT, "watch", "_candidates")
WATCH = os.path.join(ROOT, "watch")
OUT_DIR = os.path.join(ROOT, "site", "watch")


def _existing_events(slug):
    """返回 (已入库 url 集合, 该 slug 已用 id 的最大 NNN 尾号)。
    用 max 尾号(而非计数)续号,避免删过事件后新 id 与旧 id 撞号。"""
    path = os.path.join(WATCH, slug, "events.yaml")
    urls, maxseq = set(), 0
    if os.path.exists(path):
        try:
            import yaml
            for e in (yaml.safe_load(open(path, encoding="utf-8")) or []):
                if isinstance(e, dict) and e.get("id"):
                    if e.get("url"):
                        urls.add(str(e["url"]).strip())
                    m = re.search(r"-(\d+)$", str(e["id"]))
                    if m:
                        maxseq = max(maxseq, int(m.group(1)))
        except Exception:
            pass
    return urls, maxseq


def load_candidates():
    """聚合 watch/_candidates/*.json;剔除已入库(url 命中)与跨文件重复(key)。"""
    seen_keys = set()
    per_slug_urls = {}
    per_slug_count = {}
    cands = []
    for jf in sorted(glob.glob(os.path.join(CAND_DIR, "*.json"))):
        try:
            doc = json.load(open(jf, encoding="utf-8"))
        except Exception:
            continue
        batch_date = os.path.splitext(os.path.basename(jf))[0]
        for c in doc.get("candidates", []):
            key = c.get("key")
            slug = c.get("slug")
            if not key or not slug or key in seen_keys:
                continue
            if slug not in per_slug_urls:
                per_slug_urls[slug], per_slug_count[slug] = _existing_events(slug)
            if str(c.get("url", "")).strip() in per_slug_urls[slug]:
                continue  # 已入库,跳过
            seen_keys.add(key)
            c = dict(c)
            c["batch"] = batch_date
            cands.append(c)
    # 稳定排序:日期倒序 → slug → key
    cands.sort(key=lambda c: (c.get("date", ""), c.get("slug", ""), c.get("key", "")), reverse=True)
    return cands, per_slug_count


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>舆情候选 Triage · MBA</title>
<meta name="description" content="MBA Brand Watch 候选事件前台审核:打勾采纳 / 打叉丢弃,一键导出 events.yaml。url/quote/date 取自源 feed,判断字段人工定,前台不写库。" />
<style>
:root{--ink:#111;--paper:#faf8f3;--muted:#6b6760;--rule:#1a1a1a;--accent:#c1440e;--green:#1a7a4a;--red:#9a2313;--warn:#d97706;}
*{box-sizing:border-box}html,body{margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:ui-sans-serif,"Inter",-apple-system,"Noto Sans SC",sans-serif;line-height:1.55}
.wrap{max-width:1000px;margin:0 auto;padding:40px 22px 96px}
header{border-bottom:2px solid var(--rule);padding-bottom:14px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:10px}
.mark{font-weight:800;font-size:19px;letter-spacing:.02em}.mark .dot{color:var(--accent)}
nav a{font-size:13px;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--ink);margin-left:14px}nav a:hover{color:var(--accent);border-color:var(--accent)}
h1{font-size:clamp(24px,4vw,34px);font-weight:900;letter-spacing:-.01em;margin:0 0 6px}
.sub{color:var(--muted);font-size:14px;margin:0 0 18px}
.note{background:#fffbf0;border:1px solid #e8d96e;border-radius:8px;padding:12px 16px;font-size:12.5px;color:#7a6b00;margin-bottom:20px;line-height:1.6}
.note b{color:#5c5100}
.toolbar{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid #e0ddd8;padding:12px 0;margin-bottom:16px;display:flex;gap:10px 16px;flex-wrap:wrap;align-items:center}
.counts{font-size:13px;font-weight:700;display:flex;gap:12px}
.counts .k-ok{color:var(--green)}.counts .k-no{color:var(--red)}.counts .k-wait{color:var(--muted)}
select.brandf{font:inherit;font-size:13px;padding:5px 8px;border:1px solid #cfc9bf;border-radius:6px;background:#fff}
.btn{font:inherit;font-size:13px;font-weight:700;padding:7px 14px;border-radius:6px;border:1.5px solid var(--rule);background:#fff;cursor:pointer}
.btn:hover{background:#f3efe9}
.btn.primary{background:var(--green);border-color:var(--green);color:#fff}
.btn.primary:hover{filter:brightness(1.06)}
.grid{display:flex;flex-direction:column;gap:12px}
.card{background:#fff;border:1.5px solid #e0ddd8;border-left-width:5px;border-radius:8px;padding:14px 16px;transition:border-color .15s,opacity .15s}
.card[data-status="ok"]{border-left-color:var(--green);background:#f6fbf8}
.card[data-status="no"]{border-left-color:var(--red);opacity:.5;background:#fdf6f5}
.card[data-status="wait"]{border-left-color:#cfc9bf}
.card-top{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:6px}
.chip{font-size:11px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;padding:2px 9px;border-radius:20px;background:#2c1a4a;color:#fff}
.cdate{font-size:12px;color:var(--muted)}
.csrc{font-size:12px;color:var(--muted)}
.quote{font-size:15px;font-weight:600;margin:2px 0 8px;line-height:1.45}
.quote a{color:var(--ink);text-decoration:none;border-bottom:1px dotted #b0aaa0}
.quote a:hover{color:var(--accent);border-color:var(--accent)}
.fields{display:flex;gap:8px 12px;flex-wrap:wrap;align-items:center;margin:8px 0 4px}
.fields label{font-size:11px;color:var(--muted);font-weight:700}
.fields select{font:inherit;font-size:12px;padding:3px 6px;border:1px solid #cfc9bf;border-radius:5px;background:#fff}
.lenswrap{display:flex;gap:6px;flex-wrap:wrap}
.lenswrap span{font-size:11px;padding:2px 7px;border-radius:12px;border:1px solid #cfc9bf;cursor:pointer;user-select:none;color:var(--muted)}
.lenswrap span.on{background:var(--accent);border-color:var(--accent);color:#fff}
.acts{display:flex;gap:8px;margin-top:10px}
.act{font:inherit;font-size:12.5px;font-weight:700;padding:5px 14px;border-radius:6px;border:1.5px solid #cfc9bf;background:#fff;cursor:pointer}
.act.yes[aria-pressed="true"]{background:var(--green);border-color:var(--green);color:#fff}
.act.no[aria-pressed="true"]{background:var(--red);border-color:var(--red);color:#fff}
.empty{text-align:center;color:var(--muted);padding:60px 20px;font-size:15px}
dialog{border:2px solid var(--rule);border-radius:10px;max-width:720px;width:92%;padding:0}
dialog::backdrop{background:rgba(0,0,0,.45)}
.dlg-head{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid #e0ddd8}
.dlg-head b{font-size:15px}
.dlg-body{padding:14px 18px}
.dlg-body textarea{width:100%;height:320px;font-family:"Consolas",ui-monospace,monospace;font-size:12px;line-height:1.5;border:1px solid #cfc9bf;border-radius:6px;padding:10px;resize:vertical;background:#fbfaf7}
.dlg-hint{font-size:12px;color:var(--muted);margin:0 0 10px;line-height:1.6}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--rule);color:var(--muted);font-size:12.5px;line-height:1.7}
</style>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2064%2064'%3E%3Crect%20width='64'%20height='64'%20rx='12'%20fill='%23faf8f3'/%3E%3Cpolygon%20points='32,7%2056.7,25%2047.3,54%2016.7,54%207.3,25'%20fill='none'%20stroke='%23111'%20stroke-width='2.5'%20stroke-linejoin='round'/%3E%3Cpolygon%20points='32,8.6%2048.3,27.7%2043.9,49.4%2023.6,44.6%2014.2,27.2'%20fill='%23c1440e'%20fill-opacity='.18'%20stroke='%23c1440e'%20stroke-width='3'%20stroke-linejoin='round'/%3E%3Ccircle%20cx='32'%20cy='8.6'%20r='4'%20fill='%23c1440e'/%3E%3C/svg%3E" />
</head>
<body>
<div class="wrap">
  <header>
    <span class="mark">MBA<span class="dot">.</span></span>
    <nav>
      <a href="/">首页</a>
      <a href="/watch/cockpit.html">舆情驾驶舱</a>
      <a href="https://github.com/zhanglunet/mba">GitHub</a>
    </nav>
  </header>

  <h1>舆情候选 Triage</h1>
  <p class="sub">每日自动发现的候选信号 —— 在这里 <b>打勾采纳 / 打叉丢弃</b>,不必读 PR diff。选完一键复制 YAML,粘进 <code>watch/&lt;slug&gt;/events.yaml</code>。</p>

  <div class="note">
    <b>反捏造边界</b>:每条候选的 <b>标题 / 引用 / 日期 / 原文链接取自源 feed</b>(Google News RSS),页面从不编造。
    <b>维度 / 等级 / 方向 / 镜头是你的人工判断</b>(下方你打的勾),不是自动打分。
    <b>前台不写审计仓库</b>:你的选择只存在本浏览器(localStorage),采纳项需 <b>复制 YAML → commit 进 events.yaml → 跑 validate_watch.py</b> 才生效 —— git 仍是唯一真源,任何访客都改不了打分。
  </div>

  <div class="toolbar">
    <div class="counts">
      <span class="k-ok">✓ 采纳 <b id="c-ok">0</b></span>
      <span class="k-no">✗ 丢弃 <b id="c-no">0</b></span>
      <span class="k-wait">待定 <b id="c-wait">0</b></span>
    </div>
    <select class="brandf" id="brandf"><option value="">全部品牌</option></select>
    <button class="btn primary" id="export">复制「已采纳」YAML ▸</button>
    <button class="btn" id="export-no">复制丢弃清单</button>
    <button class="btn" id="reset">清空我的选择</button>
  </div>

  <div class="grid" id="grid"></div>

  <footer>
    候选由 <code>watch-discover</code> workflow 每日发现(<code>fetch_candidate.py discover</code>)。本页只做人工 triage,
    <b>不改任何审计分数</b>(docs/15 §5.3:watch 只建议、不自动改分)。采纳事件入库后,由评委在 EVOLUTION 重审时消费。
    <span id="genstamp"></span>
  </footer>
</div>

<dialog id="dlg">
  <div class="dlg-head"><b id="dlg-title">已采纳事件 YAML</b><button class="btn" onclick="document.getElementById('dlg').close()">关闭</button></div>
  <div class="dlg-body">
    <p class="dlg-hint" id="dlg-hint"></p>
    <textarea id="dlg-text" readonly></textarea>
    <div style="margin-top:10px"><button class="btn primary" id="dlg-copy">复制到剪贴板</button></div>
  </div>
</dialog>

<script>
const DATA = __DATA__;
const NEXTSEQ = __NEXTSEQ__;
const DIMS_ALL = ["W1","W2","W3","W4","W5","W6","W7","W8","W9"];
const SEVS = ["P0","P1","P2","P3"];
const DIRS = ["pos","neg","neutral","mixed"];
const LENSES = ["origin","category","leverage","identity","signal"];
const LS = "mba-triage-v1";
function loadState(){try{return JSON.parse(localStorage.getItem(LS))||{}}catch(e){return {}}}
function saveState(s){localStorage.setItem(LS,JSON.stringify(s))}
let state = loadState();
const esc = s => (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function stFor(c){
  return state[c.key] || {status:"wait", dim:"", sev:"", dir:"", lens:(c.lens_suggest||["signal"]).slice(), title:c.title||c.quote};
}
function render(){
  const grid = document.getElementById("grid");
  const bf = document.getElementById("brandf").value;
  grid.innerHTML = "";
  let shown = 0;
  DATA.forEach(c=>{
    if(bf && c.slug!==bf) return;
    shown++;
    const s = stFor(c);
    const card = document.createElement("div");
    card.className="card"; card.dataset.status=s.status;
    const dimOpts = (c.applicable_dims&&c.applicable_dims.length?c.applicable_dims:DIMS_ALL);
    card.innerHTML = `
      <div class="card-top">
        <span class="chip">${esc(c.slug)}</span>
        <span class="cdate">${esc(c.date||"日期?")}</span>
        ${c.source?`<span class="csrc">· 来源:${esc(c.source)}</span>`:""}
      </div>
      <div class="quote"><a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.quote)} ↗</a></div>
      <div class="fields">
        <label>维度</label><select data-f="dim"><option value="">W?</option>${dimOpts.map(d=>`<option ${s.dim===d?"selected":""}>${d}</option>`).join("")}</select>
        <label>等级</label><select data-f="sev"><option value="">P?</option>${SEVS.map(p=>`<option ${s.sev===p?"selected":""}>${p}</option>`).join("")}</select>
        <label>方向</label><select data-f="dir"><option value="">?</option>${DIRS.map(d=>`<option ${s.dir===d?"selected":""}>${d}</option>`).join("")}</select>
        <label>镜头</label><span class="lenswrap">${LENSES.map(l=>`<span class="lens ${s.lens.includes(l)?"on":""}" data-lens="${l}">${l}</span>`).join("")}</span>
      </div>
      <div class="acts">
        <button class="act yes" aria-pressed="${s.status==='ok'}">✓ 采纳</button>
        <button class="act no" aria-pressed="${s.status==='no'}">✗ 丢弃</button>
      </div>`;
    // wire
    card.querySelector(".act.yes").onclick=()=>{setStatus(c,s.status==="ok"?"wait":"ok")};
    card.querySelector(".act.no").onclick=()=>{setStatus(c,s.status==="no"?"wait":"no")};
    card.querySelectorAll(".fields select").forEach(sel=>{
      sel.onchange=()=>{const f=sel.dataset.f;s[f]=sel.value;state[c.key]=s;saveState(state)};
    });
    card.querySelectorAll(".lens").forEach(sp=>{
      sp.onclick=()=>{const l=sp.dataset.lens;const i=s.lens.indexOf(l);if(i<0)s.lens.push(l);else s.lens.splice(i,1);state[c.key]=s;saveState(state);sp.classList.toggle("on")};
    });
    grid.appendChild(card);
  });
  if(shown===0) grid.innerHTML='<div class="empty">没有候选。每日 <code>watch-discover</code> 跑完后,新信号会出现在这里。</div>';
  updateCounts();
}
function setStatus(c,st){const s=stFor(c);s.status=st;state[c.key]=s;saveState(state);render()}
function updateCounts(){
  let ok=0,no=0,wait=0;
  DATA.forEach(c=>{const st=(state[c.key]||{}).status||"wait";if(st==="ok")ok++;else if(st==="no")no++;else wait++});
  document.getElementById("c-ok").textContent=ok;
  document.getElementById("c-no").textContent=no;
  document.getElementById("c-wait").textContent=wait;
}
function yamlFor(){
  // 按 slug 分组,batch 内顺延 NNN(从 events.yaml 现有计数续号)
  const bySlug={};
  DATA.forEach(c=>{if((state[c.key]||{}).status==="ok"){(bySlug[c.slug]=bySlug[c.slug]||[]).push(c)}});
  const blocks=[];
  Object.keys(bySlug).sort().forEach(slug=>{
    let seq=(NEXTSEQ[slug]||0);
    const lines=[`# ── watch/${slug}/events.yaml 追加以下 ${bySlug[slug].length} 条(triage 采纳) ──`];
    bySlug[slug].forEach(c=>{
      seq++;
      const s=stFor(c);
      const nnn=String(seq).padStart(3,"0");
      const id=`${c.date||"YYYY-MM-DD"}-${slug}-${nnn}`;
      const lens=(s.lens&&s.lens.length?s.lens:["signal"]);
      const t=(s.title||c.title||c.quote).replace(/"/g,'\\"');
      const qq=(c.quote||"").replace(/"/g,'\\"');
      lines.push(
`- id: ${id}
  date: ${c.date||"YYYY-MM-DD"}
  dim: ${s.dim||"W?"}
  severity: ${s.sev||"P?"}
  direction: ${s.dir||"neutral"}
  direction_by: model-judged
  title: "${t}"
  quote: "${qq}"
  quote_type: title
  url: ${c.url}
  fetched_at: "${c.fetched_at||""}"
  lens_map: [${lens.join(", ")}]
  source_type: ${c.source?"media":"media"}
  note: "前台 triage 采纳;标题/日期/URL 取自源 feed,维度/等级/方向为人工判断。"`);
    });
    blocks.push(lines.join("\n"));
  });
  return blocks.join("\n\n");
}
function openDlg(title,hint,text){
  document.getElementById("dlg-title").textContent=title;
  document.getElementById("dlg-hint").textContent=hint;
  document.getElementById("dlg-text").value=text;
  document.getElementById("dlg").showModal();
}
document.getElementById("export").onclick=()=>{
  const y=yamlFor();
  if(!y){openDlg("已采纳事件 YAML","还没有采纳任何候选 —— 先在卡片上点「✓ 采纳」。","");return}
  const miss=DATA.some(c=>{const s=state[c.key];return s&&s.status==="ok"&&(!s.dim||!s.sev||!s.dir)});
  openDlg("已采纳事件 YAML",
    "复制后粘进对应 watch/<slug>/events.yaml,删掉已处理的候选,再跑 python3 scripts/watch-tools/validate_watch.py。"+(miss?" ⚠️ 有采纳项的 维度/等级/方向 还没选全(显示为 W?/P?),补齐再提交。":""),
    y);
};
document.getElementById("export-no").onclick=()=>{
  const ids=DATA.filter(c=>(state[c.key]||{}).status==="no").map(c=>`${c.slug}  ${c.date}  ${c.url}`);
  openDlg("丢弃清单","这些候选被判为噪音 / 不入库(仅供你记录,页面不改仓库)。",ids.join("\n")||"(无)");
};
document.getElementById("reset").onclick=()=>{if(confirm("清空本浏览器里所有 triage 选择?")){state={};saveState(state);render()}};
document.getElementById("dlg-copy").onclick=async()=>{
  const t=document.getElementById("dlg-text");t.select();
  try{await navigator.clipboard.writeText(t.value)}catch(e){document.execCommand("copy")}
  document.getElementById("dlg-copy").textContent="已复制 ✓";
  setTimeout(()=>document.getElementById("dlg-copy").textContent="复制到剪贴板",1500);
};
// brand filter options
(function(){
  const slugs=[...new Set(DATA.map(c=>c.slug))].sort();
  const sel=document.getElementById("brandf");
  slugs.forEach(s=>{const o=document.createElement("option");o.value=s;o.textContent=s;sel.appendChild(o)});
  sel.onchange=render;
  document.getElementById("genstamp").textContent="· 生成 __GEN__ · "+DATA.length+" 条候选";
})();
render();
</script>
</body>
</html>
"""


def main():
    cands, next_count = load_candidates()
    os.makedirs(OUT_DIR, exist_ok=True)
    import datetime
    gen = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    # 结构化聚合(供 agent / 复用)
    json.dump({"generated_at": gen, "count": len(cands), "candidates": cands},
              open(os.path.join(OUT_DIR, "candidates.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    def safe_json(obj):
        # 安全内嵌进 <script>:防 </script> 突破 + U+2028/2029 破坏 JS 字面量
        s = json.dumps(obj, ensure_ascii=False)
        s = s.replace("<", "\u003c").replace(">", "\u003e").replace("&", "\u0026")
        s = s.replace(chr(0x2028), "\u2028").replace(chr(0x2029), "\u2029")
        return s

    page = (HTML
            .replace("__DATA__", safe_json(cands))
            .replace("__NEXTSEQ__", safe_json(next_count))
            .replace("__GEN__", gen))
    open(os.path.join(OUT_DIR, "triage.html"), "w", encoding="utf-8").write(page)
    print(f"[watch-triage] site/watch/triage.html — {len(cands)} 候选 / {len(next_count)} 品牌")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
