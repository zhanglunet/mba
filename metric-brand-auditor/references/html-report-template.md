# HTML Report Template — `report.html`

This is the **scaffold** for the final HTML report. Copy the HTML below, replace every
`{{ ... }}` slot with real content, and write the result to `report.html` and
`versions/v1_<date>.html`. The result is a single self-contained file that opens in any
modern browser with no build step (only Chart.js loads from a CDN).

> **House style (current).** MBA reports are an editorial, paper-themed, bilingual (中文 +
> English) document. This template mirrors the live reports on mbabrand.com (e.g. Hermès,
> SpaceX) — paper background `#faf8f3`, burnt-orange accent `#c1440e`, the **five-lens radar
> logo** in the masthead, inline Chart.js (no data-injection framework), and a Legal+Sources
> block. Keep this theme; do **not** reintroduce dark mode or a blue accent.

## What the Lead prepares before writing

- **Identity:** `{{brand}}` (e.g. `Hermès / 爱马仕`), `{{brand_full}}` (English one-liner:
  legal name · ticker · category · est.), `{{panel}}`, `{{mba_version}}`, `{{date}}`,
  `{{judge_count}}`.
- **Scores:** each judge's 5 lens scores (1–10) + total /50; the panel total `{{total}}` /
  `{{max}}` and normalized `{{normalized}}` /10.
- **Prose (Lead's voice):** `{{tldr}}`, `{{verdict_paras}}`, `{{action_items}}`.
- **Per judge:** name, role line, total, and an in-character verdict paragraph.
- **Sources:** real, publicly accessible URLs only (anti-fabrication — never invent a link).

Lenses are fixed: **Origin · Category · Leverage · Identity · Signal** (起源 / 品类 / 杠杆 /
身份 / 信号).

## The HTML scaffold

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{{brand}} — MBA Brand Audit {{version}}</title>
<meta name="description" content="{{panel}} panel brand audit of {{brand_full}}. Score: {{total}}/{{max}} · {{normalized}}/10. {{judge_count}} judges × 5 lenses. Audit date: {{date}}."/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
:root {
  --ink: #111;
  --paper: #faf8f3;
  --muted: #6b6760;
  --rule: #1a1a1a;
  --accent: #c1440e;
  --panel: #c1440e;      /* optional per-panel accent; default = --accent */
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{background:var(--paper);color:var(--ink);font-family:ui-serif,"Noto Serif SC","Songti SC",Georgia,serif;line-height:1.6;-webkit-font-smoothing:antialiased;}
.wrap{max-width:820px;margin:0 auto;padding:56px 28px 80px;}
header{border-bottom:2px solid var(--rule);padding-bottom:18px;margin-bottom:36px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.mark{font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-weight:800;letter-spacing:.02em;font-size:20px;}
.mark .dot{color:var(--accent);}
.panel-badge{display:inline-block;padding:3px 10px;border:1.5px solid var(--panel);color:var(--panel);font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:11px;letter-spacing:.08em;text-transform:uppercase;border-radius:3px;}
h1{font-size:clamp(28px,5vw,44px);line-height:1.15;margin:0 0 10px;font-weight:800;letter-spacing:-.01em;}
.brand-en{font-size:17px;color:var(--muted);font-style:italic;margin:0 0 6px;}
.meta-line{font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:13px;color:var(--muted);margin:0 0 28px;}
.meta-line span{margin-right:18px;}
.tldr{background:#fff;border-left:4px solid var(--panel);padding:18px 22px;margin:0 0 36px;font-size:16px;line-height:1.65;}
.tldr strong{color:var(--panel);}

.score-hero{display:flex;gap:28px;margin:0 0 40px;flex-wrap:wrap;align-items:center;}
.score-big{font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:64px;font-weight:900;line-height:1;color:var(--ink);}
.score-sub{font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:14px;color:var(--muted);margin-top:6px;}
.score-norm{font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:28px;font-weight:700;color:var(--panel);}

.charts-row{display:grid;grid-template-columns:1fr 1fr;gap:32px;margin:0 0 44px;}
@media(max-width:600px){.charts-row{grid-template-columns:1fr;}}
.chart-box{background:#fff;border:1px solid #e5e2db;border-radius:8px;padding:20px;}
.chart-wrap{position:relative;height:260px;}
.chart-title{font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 14px;}
canvas{width:100%!important;}

.section-title{font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:40px 0 14px;border-top:1px solid var(--rule);padding-top:16px;}
table{width:100%;border-collapse:collapse;font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:14px;margin:0 0 36px;}
th{background:var(--ink);color:#fff;padding:9px 12px;text-align:left;font-weight:600;font-size:12px;letter-spacing:.05em;}
td{padding:9px 12px;border-bottom:1px solid #e5e2db;}
tr:last-child td{border-bottom:none;}
tr:nth-child(even) td{background:#f7f5f0;}
/* score-cell heat classes: 1=coolest … 8=hottest. Map a 1–10 score → heat-1..heat-8. */
.heat-1{background:#ffe8e8!important;color:#8b0000;}
.heat-2{background:#fff3e0!important;color:#7a4500;}
.heat-3{background:#fffde7!important;}
.heat-4{background:#ffe0c8!important;color:#7a3200;}
.heat-5{background:#ffd0a0!important;color:#6b2600;}
.heat-6{background:#ffb870!important;color:#5a1800;font-weight:700;}
.heat-7{background:#ff9030!important;color:#fff;font-weight:700;}
.heat-8{background:#d4600a!important;color:#fff;font-weight:700;}
.total-row td{font-weight:700;background:var(--paper)!important;}
/* EVOLUTION delta cells */
td.up{color:#1a7a4a;font-weight:700;}
td.down{color:#b5341a;font-weight:700;}
td.flat{color:var(--muted);}

.judge-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:20px;margin:0 0 44px;}
@media(max-width:560px){.judge-grid{grid-template-columns:1fr;}}
.judge-card{background:#fff;border:1px solid #e5e2db;border-radius:8px;padding:18px 20px;}
.judge-card .jname{font-weight:700;font-size:16px;margin:0 0 2px;}
.judge-card .jrole{font-size:12px;color:var(--muted);margin:0 0 10px;font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;}
.judge-card .jscore{font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:28px;font-weight:800;color:var(--panel);}
.judge-card .jscore-max{font-size:14px;color:var(--muted);font-weight:400;}
.judge-card .jverdict{font-size:14px;margin-top:10px;line-height:1.55;color:var(--ink);}
.judge-card.competitor{border-color:#d4a017;background:#fffcf0;}
.judge-card.highest{border-color:var(--panel);border-width:2px;}
.badge-competitor{display:inline-block;background:#d4a017;color:#fff;font-size:10px;padding:1px 7px;border-radius:999px;font-family:ui-sans-serif,sans-serif;font-weight:700;letter-spacing:.04em;margin-left:6px;vertical-align:middle;}

.verdict{border:2px solid var(--rule);padding:22px 26px;margin:0 0 36px;border-radius:6px;}
.verdict p{margin:0 0 10px;font-size:16px;line-height:1.65;}
.verdict p:last-child{margin:0;}

.action-list{margin:0 0 44px;padding:0;}
.action-list li{list-style:none;padding:16px 18px;border:1px solid #e5e2db;border-radius:6px;margin-bottom:10px;background:#fff;}
.action-list li .action-num{font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-weight:700;color:var(--panel);font-size:14px;margin-bottom:6px;}
.action-list li p{margin:0;font-size:15px;line-height:1.6;}

/* ── optional situational blocks (use when relevant; CSS kept house-consistent) ── */
.record-strip{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 36px;}
.record-pill{background:var(--panel);color:#fff;font-family:ui-sans-serif,sans-serif;font-size:12px;font-weight:700;letter-spacing:.04em;padding:5px 12px;border-radius:999px;}
.conflict-box{background:#fffbf0;border:1.5px solid #d4a017;border-radius:6px;padding:14px 18px;margin:0 0 32px;font-family:ui-sans-serif,sans-serif;font-size:13px;line-height:1.6;}
.conflict-box .cf-title{font-weight:700;color:#8a6500;margin-bottom:6px;text-transform:uppercase;letter-spacing:.06em;}
.insight-box{background:#fff6f0;border:1.5px solid var(--panel);border-radius:8px;padding:20px 24px;margin:0 0 36px;}
.insight-box .ib-title{font-family:ui-sans-serif,sans-serif;font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--panel);margin:0 0 10px;}
.quote-block{border-left:3px solid var(--panel);padding:14px 20px;margin:0 0 16px;background:#fff6f0;border-radius:0 6px 6px 0;}
.quote-block p{margin:0;font-size:15px;font-style:italic;line-height:1.65;}
.quote-block .quote-attr{margin-top:8px;font-size:13px;color:var(--muted);font-family:ui-sans-serif,sans-serif;font-style:normal;font-weight:600;}
/* EVOLUTION delta banner (v2+ only) */
.delta-banner{background:linear-gradient(90deg,#fff3e6,#ffe8d1);border-left:4px solid var(--panel);padding:14px 18px;border-radius:6px;margin:0 0 28px;font-size:15px;}

footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--rule);color:var(--muted);font-family:ui-sans-serif,"Inter",-apple-system,sans-serif;font-size:12px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;}

  /* ── logo glyph(五镜头雷达,规范见 mbabrand.com/logo-design.html)── */
  .mark { display: inline-flex; align-items: center; gap: 9px; }
  .mark-glyph { display: block; flex-shrink: 0; }
  .mark-glyph .radar-data { stroke-dasharray: 100; }
  .mark-glyph .radar-dot { transform-box: fill-box; transform-origin: center; transition: transform .25s cubic-bezier(.2,1.4,.4,1); }
  .mark:hover .radar-dot { transform: scale(1.35); }
  @media (prefers-reduced-motion: no-preference) {
    .mark-glyph .radar-data { animation: mba-draw 1.1s cubic-bezier(.6,0,.25,1) .2s backwards; }
    .mark-glyph .radar-dot { animation: mba-pop .4s cubic-bezier(.2,1.6,.4,1) 1.2s backwards; }
  }
  @keyframes mba-draw { from { stroke-dashoffset: 100; fill-opacity: 0; } to { stroke-dashoffset: 0; fill-opacity: 1; } }
  @keyframes mba-pop { from { transform: scale(0); } to { transform: scale(1); } }
</style>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2064%2064'%3E%3Crect%20width='64'%20height='64'%20rx='12'%20fill='%23faf8f3'/%3E%3Cpolygon%20points='32,7%2056.7,25%2047.3,54%2016.7,54%207.3,25'%20fill='none'%20stroke='%23111'%20stroke-width='2.5'%20stroke-linejoin='round'/%3E%3Cpolygon%20points='32,8.6%2048.3,27.7%2043.9,49.4%2023.6,44.6%2014.2,27.2'%20fill='%23c1440e'%20fill-opacity='.18'%20stroke='%23c1440e'%20stroke-width='3'%20stroke-linejoin='round'/%3E%3Ccircle%20cx='32'%20cy='8.6'%20r='4'%20fill='%23c1440e'/%3E%3C/svg%3E" />
</head>
<body>
<div class="wrap">

<!-- MASTHEAD — copy the logo lockup verbatim (site standard, see /logo-design.html) -->
<header>
  <div class="mark" role="img" aria-label="MBA — Metric Brand Auditor"><svg class="mark-glyph" viewBox="0 0 64 64" width="32" height="32" aria-hidden="true" focusable="false"><defs><linearGradient id="mbaGradMk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c1440e" stop-opacity=".30"/><stop offset="1" stop-color="#c1440e" stop-opacity=".06"/></linearGradient></defs><polygon points="32,7 56.7,25 47.3,54 16.7,54 7.3,25" fill="none" stroke="#111" stroke-width="2" stroke-linejoin="round"/><g fill="none" stroke="#111" opacity=".12" stroke-width="1"><polygon points="32,20 44.4,29 39.6,43.5 24.4,43.5 19.6,29" stroke-linejoin="round"/><path d="M32 33V7M32 33 56.7 25M32 33 47.3 54M32 33 16.7 54M32 33 7.3 25"/></g><polygon class="radar-data" pathLength="100" points="32,8.6 48.3,27.7 43.9,49.4 23.6,44.6 14.2,27.2" fill="url(#mbaGradMk)" stroke="#c1440e" stroke-width="2.5" stroke-linejoin="round"/><circle class="radar-dot" cx="32" cy="8.6" r="3.2" fill="#c1440e" stroke="#faf8f3" stroke-width="1.5"/></svg><span>MBA<span class="dot">.</span></span></div>
  <div class="panel-badge">{{panel}} panel</div>
</header>

<h1>{{brand}}</h1>
<p class="brand-en">{{brand_full}}</p>
<p class="meta-line">
  <span>MBA {{mba_version}}</span>
  <span>Audit Date: {{date}}</span>
  <span>Panel: {{panel}}</span>
  <span>{{judge_count}} Judges</span>
</p>

<!-- EVOLUTION only (v2+): delta banner. Delete this block in FRESH mode. -->
<!-- <div class="delta-banner"><strong>较 {{prev_version}} 变化：</strong>{{delta_summary}} <span style="float:right">mean Δ {{score_shift}}</span></div> -->

<div class="tldr">
  <strong>TL;DR：</strong>{{tldr}}
</div>

<div class="score-hero">
  <div>
    <div class="score-big">{{total}}</div>
    <div class="score-sub">/ {{max}}（{{judge_count}} Judges × 50）</div>
  </div>
  <div>
    <div class="score-norm">{{normalized}} / 10</div>
    <div class="score-sub">归一化总分 · Normalized</div>
  </div>
</div>

<div class="charts-row">
  <div class="chart-box">
    <div class="chart-title">维度雷达图 / Lens radar</div>
    <div class="chart-wrap"><canvas id="radarChart"></canvas></div>
  </div>
  <div class="chart-box">
    <div class="chart-title">评委分数对比 / Judge totals</div>
    <div class="chart-wrap"><canvas id="barChart"></canvas></div>
  </div>
</div>

<div class="section-title">Score Matrix</div>
<table>
  <thead>
    <tr><th>Lens</th>{{#each judges}}<th>{{name}}</th>{{/each}}<th>Mean</th></tr>
  </thead>
  <tbody>
    <!-- One row per lens. Give each score cell a heat-N class (1–10 → heat-1..heat-8). -->
    <!-- EVOLUTION: cells become "7 → 8" with class up/down/flat. -->
    <tr>
      <td>Origin / 起源叙事</td>
      <td class="heat-6">9</td><td class="heat-6">9</td><td class="heat-8">10</td><td class="heat-5">8</td><td class="heat-6">9</td>
      <td><strong>9.0</strong></td>
    </tr>
    <!-- … Category / Leverage / Identity / Signal rows … -->
    <tr class="total-row">
      <td>Total</td><td>40</td><td>45</td><td>46</td><td>41</td><td>44</td><td>—</td>
    </tr>
  </tbody>
</table>

<div class="section-title">Judge Scorecards</div>
<div class="judge-grid">
  <!-- One card per judge. Add class "competitor" (+ △ badge) for a self-conflicted judge, -->
  <!-- "highest" to highlight the top scorer. Verdict = in-character, first-person. -->
  <div class="judge-card">
    <div class="jname">{{judge_name}}</div>
    <div class="jrole">{{judge_role}}</div>
    <div class="jscore">{{judge_total}} <span class="jscore-max">/ 50</span></div>
    <div class="jverdict">{{judge_verdict}}</div>
  </div>
  <!-- … repeat for each judge … -->
</div>

<div class="section-title">Verdict</div>
<div class="verdict">
  {{verdict_paras}}   <!-- 2–3 <p> paragraphs, Lead's voice, bilingual as appropriate -->
</div>

<div class="section-title">Brand Actions（90 天）</div>
<ul class="action-list">
  <li>
    <div class="action-num">Action 1 — {{action_title}}（最高优先）</div>
    <p>{{action_body}}</p>
  </li>
  <!-- … 2–3 more actions … -->
</ul>

<footer>
  <span>MBA {{mba_version}} · {{panel}} Panel · {{date}}</span>
  <span>{{brand}} · Score: {{total}}/{{max}} · {{normalized}}/10</span>
</footer>

</div>

<script>
(function() {
  const accent = '#c1440e';
  // ⚠️ EXAMPLE DATA — replace labels/data with this audit's real numbers.
  const lenses = ['Origin', 'Category', 'Leverage', 'Identity', 'Signal'];
  const lensMeans = [9.0, 8.4, 8.0, 9.6, 8.2];              // panel mean per lens
  const judgeNames = ['J1', 'J2', 'J3', 'J4', 'J5'];
  const judgeTotals = [40, 45, 46, 41, 44];                 // each judge total /50

  new Chart(document.getElementById('radarChart').getContext('2d'), {
    type: 'radar',
    data: { labels: lenses, datasets: [{
      label: '{{brand}}', data: lensMeans,
      backgroundColor: 'rgba(193,68,14,0.15)', borderColor: accent, borderWidth: 2.5,
      pointBackgroundColor: accent, pointRadius: 5 }] },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { r: { min: 0, max: 10, ticks: { stepSize: 2, font: { size: 10 }, color: '#6b6760' },
        grid: { color: '#e5e2db' }, pointLabels: { font: { size: 11 }, color: '#111' } } } }
  });

  new Chart(document.getElementById('barChart').getContext('2d'), {
    type: 'bar',
    data: { labels: judgeNames, datasets: [{ label: 'Total / 50', data: judgeTotals,
      backgroundColor: 'rgba(193,68,14,0.80)', borderColor: accent, borderWidth: 1.5 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${ctx.raw}/50` } } },
      scales: { x: { min: 0, max: 50, ticks: { stepSize: 10, font: { size: 10 }, color: '#6b6760' }, grid: { color: '#e5e2db' } },
        y: { ticks: { font: { size: 12 }, color: '#111' }, grid: { display: false } } } }
  });
})();
</script>

<!-- LEGAL + SOURCES — required. Fill {{brand}} / {{panel}} / {{judge_names}}; Sources must be real URLs. -->
<section class="mba-legal" style="max-width:860px;margin:48px auto 0;padding:20px 24px;border-top:2px solid #1a1a1a;font-family:ui-sans-serif,system-ui,sans-serif;font-size:13px;line-height:1.7;color:#6b6760;">
  <h2 style="font-size:15px;color:#111;margin:0 0 12px;">Legal, IP &amp; Disclaimer — 商标、知识产权与免责声明</h2>
  <p><strong>公开资料说明：</strong>本报告仅引用和分析公开可访问资料（新闻报道、行业媒体、品牌官方公开材料、公开访谈与演讲、MBA 方法说明）。报告未使用 {{brand}}、其关联公司或任何第三方的非公开资料、内部文件、商业秘密或未授权数据库。</p>
  <p><strong>商标与品牌归属：</strong>报告中提及的品牌名、产品名、商标、标识及相关商业外观均归其合法权利人所有，仅为识别、评论、研究和说明目的引用，不表示 MBA 与相关权利主体存在赞助、授权、合作或背书关系。</p>
  <p><strong>评委模拟说明：</strong>本报告 {{panel}} 面板评委（{{judge_names}}）为基于公开资料构建的 AI 视角模拟，代表合乎逻辑的分析视角，不代表相关个人的真实观点或表态。与被审计品牌存在竞争关系的评委已用 △ 标注。</p>
  <p><strong>非投资 / 非采购建议：</strong>本报告是品牌影响力研究与方法演示，不构成投资、采购、法律或商业尽调结论。分数反映 MBA {{panel}} 面板在公开资料基础上的判断，不等同于 {{brand}} 的真实经营表现、财务状况或产品质量。</p>
  <p><strong>准确性限制：</strong>本轮为 open-web research，所有结论均受公开资料完整性、发布时间、媒体口径和样本偏差限制。读者在做商业、投资或法律决策前，应自行核验一手资料并咨询专业顾问。</p>
  <p style="margin-top:10px;"><strong>Sources / 来源：</strong>主要公开来源（均可公开访问）：</p>
  <ul style="margin:6px 0 0;padding-left:20px;font-size:12px;">
    <li><a href="{{source_url}}" style="color:#c1440e;">{{source_label}}</a></li>
    <!-- … one <li> per real source … -->
  </ul>
</section>

</body>
</html>
```

## Score-matrix heat classes

Each score cell gets a `heat-N` class by its 1–10 score, coolest→hottest:

| score | 1–2 | 3 | 4 | 5–6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|
| class | `heat-1` | `heat-2`/`heat-3` | `heat-4` | `heat-5` | `heat-6` | `heat-7` | `heat-6`→`heat-7` | `heat-8` |

(Judgement, not a formula — the point is a warm gradient where high scores read hot. Mark
record/notable means with `★`.)

## EVOLUTION mode (v2+) — what to add

A re-audit keeps the same house style plus:

- **Delta banner** under the meta line (`.delta-banner`): one line on what moved + `mean Δ`.
- **Score-matrix delta cells:** `7 → 8` wrapped in `td.up` / `td.down` / `td.flat` (↑/↓/↔),
  and the mean column showing `6.8 → 7.2`.
- **"What changed since {{prev}}"** section: the delta research narrative, per lens.
- **Version timeline:** a small Mermaid `gitGraph` (add the Mermaid ESM import only if used) or
  a simple ordered list of versions with dates + score.
- **Keep the prior version** at `versions/v{n-1}_<date>.html`; link it from the meta/sources.

## Anti-pitfall checklist before finalizing

- [ ] Every `{{...}}` slot is gone — search the file for `{{`, expect zero matches.
- [ ] The masthead is the **five-lens radar logo lockup** (copied verbatim) + favicon present.
- [ ] Theme is paper `#faf8f3` + accent `#c1440e` — no dark-mode block, no blue accent.
- [ ] Both charts have real data and sit in a fixed-height `.chart-wrap` (prevents the Chart.js
      infinite-growth bug); `maintainAspectRatio:false` is set.
- [ ] All judge cards present (even a "withheld" judge — show "withheld", never a fake 0).
- [ ] **Legal, IP &amp; Disclaimer** section exists before/with Sources and covers: public-source
      basis, trademark ownership, judge-simulation notice, non-advice, accuracy limits.
- [ ] **Sources** are real, publicly reachable URLs — never invented (anti-fabrication red line).
- [ ] Opens cleanly in a browser, no `console.error`. (Run `node scripts/qa_report_render.mjs`.)
- [ ] EVOLUTION: delta banner + delta score cells present; FRESH: no version-timeline section.
