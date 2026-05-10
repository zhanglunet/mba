# HTML Report Template — `report.html`

This is the **scaffold** for the final HTML report. Copy the HTML below verbatim, then fill
the data slots marked `{{ ... }}`. The result is a single self-contained file that opens in
any modern browser with no build step.

## Data slots the Lead must fill

Before writing, prepare these JSON-shaped pieces in your head (or in a scratch buffer):

```js
const DATA = {
  brand: "OpenClaw",
  version: "v1",
  mode: "FRESH",                       // or "EVOLUTION"
  date: "2026-05-09",
  tldr: "<one-paragraph TL;DR — Lead's voice>",

  lenses: [
    "Origin authenticity",
    "Category coinage",
    "Leverage quality",
    "Identity coherence",
    "Real-world signal"
  ],
  judges: [
    { slug: "fusheng",      cn: "傅盛",         scores: [7,8,6,7,5], total: 33,
      verdict: "...", quote: "...", color: "#e74c3c",
      reasoning: ["origin 一句", "category 一句", "leverage 一句", "identity 一句", "signal 一句"] },
    { slug: "jobs",         cn: "Steve Jobs",  scores: [6,7,7,9,5], total: 34,
      verdict: "...", quote: "...", color: "#3498db",
      reasoning: ["...","...","...","...","..."] },
    { slug: "likejia",      cn: "李可佳",       scores: [8,9,7,8,6], total: 38,
      verdict: "...", quote: "...", color: "#2ecc71",
      reasoning: ["...","...","...","...","..."] },
    { slug: "wu-jundong",   cn: "吴俊东",       scores: [7,7,8,7,6], total: 35,
      verdict: "...", quote: "...", color: "#f39c12",
      reasoning: ["...","...","...","...","..."] },
    { slug: "zhang-yiming", cn: "张一鸣",       scores: [6,6,7,7,5], total: 31,
      verdict: "...", quote: "...", color: "#9b59b6",
      reasoning: ["...","...","...","...","..."] }
  ],

  // For Phase 5E (evolution) only — null in fresh mode
  delta: null, // or { fromVersion: "v1", date: "2026-05-09", changes: [...], scoreShift: +1.2 }

  // Mermaid blocks — Lead writes these as strings
  mermaidInfluenceFlow: `
    flowchart LR
      Founder[Founder narrative] --> Identity[Visual + verbal identity]
      Founder --> Category[Category coinage: 龙虾]
      Identity --> Community[Community evangelists]
      Category --> Press[Press amplification]
      Community --> Sentiment[Reception + sentiment]
      Press --> Sentiment
  `,
  mermaidQuadrant: `
    quadrantChart
      title Brand positioning
      x-axis Founder-driven --> Product-driven
      y-axis Domestic --> Global
      "OpenClaw": [0.3, 0.4]
      "BotLearn": [0.6, 0.7]
      "Aibrary": [0.7, 0.8]
  `,
  mermaidMindmap: `
    mindmap
      root((OpenClaw))
        Origin
          ::icon(fa fa-flag)
          founder pivot story
          AI-believer narrative
        Category
          龙虾 metaphor
          Token Economy frame
        ...
  `,
  mermaidGitGraph: null, // evolution mode only

  // Optional sentiment trend; null if no time-series data
  sentimentTrend: null, // or { labels: ["W1","W2",...], datasets: [...] }

  consensus: ["...", "..."],
  dissent: [
    { judges: ["fusheng", "jobs"], topic: "category coinage", quotes: { fusheng: "...", jobs: "..." } }
  ],
  leadRead: "<lead's synthesis paragraph>",
  actions: [
    { text: "...", leverage: "high" },
    { text: "...", leverage: "med" },
    { text: "...", leverage: "low" }
  ],
  citations: [
    { label: "36kr — OpenClaw founder interview", url: "https://..." },
    ...
  ]
};
```

## The HTML scaffold

Copy this verbatim and inject `DATA` plus rendered HTML strings into the slots.

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{brand}} — MBA Brand Audit ({{version}})</title>
<style>
  :root {
    --c-bg: #fafaf7;
    --c-surface: #ffffff;
    --c-text: #1a1a1a;
    --c-muted: #666;
    --c-accent: #2c3e50;
    --c-border: #e5e5e0;
    --c-judge-1: #e74c3c;
    --c-judge-2: #3498db;
    --c-judge-3: #2ecc71;
    --c-judge-4: #f39c12;
    --c-judge-5: #9b59b6;
    --c-up: #27ae60;
    --c-down: #c0392b;
    --c-flat: #95a5a6;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --c-bg: #14151a;
      --c-surface: #1f2128;
      --c-text: #e8e8ea;
      --c-muted: #9aa;
      --c-accent: #5fa8d3;
      --c-border: #2c2e36;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--c-bg);
    color: var(--c-text);
    font: 16px/1.65 system-ui, -apple-system, "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif;
  }
  .wrap { max-width: 960px; margin: 0 auto; padding: 32px 20px 80px; }
  header.hero {
    border-bottom: 1px solid var(--c-border);
    padding-bottom: 24px;
    margin-bottom: 32px;
  }
  header.hero h1 { font-size: 34px; margin: 0 0 8px; }
  .badges { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 16px; }
  .badge {
    display: inline-block; padding: 3px 10px; font-size: 12px;
    border-radius: 999px; background: var(--c-surface); border: 1px solid var(--c-border);
  }
  .badge.mode-FRESH { background: #e8f6ef; color: #1a7a4c; border-color: #a8d8b9; }
  .badge.mode-EVOLUTION { background: #fff3e6; color: #b76b00; border-color: #ffd1a3; }
  .tldr { font-size: 18px; color: var(--c-muted); }
  section { margin: 40px 0; }
  section > h2 {
    font-size: 22px; margin: 0 0 16px;
    border-left: 4px solid var(--c-accent); padding-left: 12px;
  }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  @media (max-width: 720px) { .grid-2 { grid-template-columns: 1fr; } }
  .card {
    background: var(--c-surface); border: 1px solid var(--c-border);
    border-radius: 8px; padding: 16px;
  }
  .judge-card { border-left-width: 4px; border-left-style: solid; }
  .judge-card h3 { margin: 0 0 4px; font-size: 18px; }
  .judge-card .quote {
    font-style: italic; color: var(--c-muted);
    border-left: 2px solid var(--c-border); padding-left: 10px; margin: 10px 0;
  }
  .score-row { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
  .score-pill {
    background: var(--c-bg); border: 1px solid var(--c-border);
    border-radius: 4px; padding: 2px 8px; font-size: 12px;
  }
  table.score-matrix {
    width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px;
  }
  table.score-matrix th, table.score-matrix td {
    border: 1px solid var(--c-border); padding: 8px 10px; text-align: center;
  }
  table.score-matrix th { background: var(--c-surface); }
  table.score-matrix td.lens { text-align: left; font-weight: 600; }
  td.up   { background: rgba(39,174,96,.12); color: var(--c-up); }
  td.down { background: rgba(192,57,43,.12); color: var(--c-down); }
  td.flat { color: var(--c-flat); }
  /* Dissent heatmap */
  .heatmap {
    display: grid; gap: 2px;
    background: var(--c-border);
    border: 1px solid var(--c-border);
    border-radius: 6px; overflow: hidden;
    font-size: 13px;
  }
  .heatmap .hcell {
    padding: 12px 8px; text-align: center;
    background: var(--c-surface);
    position: relative; cursor: default;
    transition: transform .15s;
  }
  .heatmap .hcell.score { font-weight: 600; font-size: 16px; color: #111; }
  .heatmap .hcell.label { background: var(--c-surface); color: var(--c-muted); font-size: 12px; }
  .heatmap .hcell.label.lens { text-align: left; padding-left: 12px; font-weight: 600; color: var(--c-text); }
  .heatmap .hcell.score:hover { transform: scale(1.06); z-index: 2; box-shadow: 0 2px 10px rgba(0,0,0,.18); }
  .heatmap .hcell.sigma {
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .heatmap .hcell .tip {
    visibility: hidden; opacity: 0;
    position: absolute; bottom: 110%; left: 50%; transform: translateX(-50%);
    background: #1a1a1a; color: #fff; padding: 6px 10px; border-radius: 4px;
    font-size: 12px; white-space: nowrap; max-width: 280px; white-space: normal;
    width: max-content; max-width: 240px;
    transition: opacity .15s; pointer-events: none; z-index: 10;
    box-shadow: 0 4px 12px rgba(0,0,0,.25);
  }
  .heatmap .hcell:hover .tip { visibility: visible; opacity: 1; }
  .heatmap-legend {
    display: flex; align-items: center; gap: 8px;
    font-size: 12px; color: var(--c-muted); margin-top: 8px;
  }
  .heatmap-legend .swatch {
    width: 140px; height: 12px; border-radius: 3px;
    background: linear-gradient(90deg, #c0392b 0%, #f39c12 50%, #27ae60 100%);
  }
  .mermaid { background: var(--c-surface); padding: 16px; border-radius: 8px; border: 1px solid var(--c-border); }
  canvas { background: var(--c-surface); border-radius: 8px; padding: 12px; border: 1px solid var(--c-border); }
  details { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 8px; padding: 12px 16px; margin: 12px 0; }
  summary { cursor: pointer; font-weight: 600; }
  ol.actions li { margin: 8px 0; }
  .leverage { font-size: 11px; padding: 2px 8px; border-radius: 4px; margin-left: 8px; }
  .leverage.high { background: #e74c3c; color: white; }
  .leverage.med  { background: #f39c12; color: white; }
  .leverage.low  { background: #95a5a6; color: white; }
  .delta-banner {
    background: linear-gradient(90deg, #fff3e6, #ffe8d1);
    border-left: 4px solid #f39c12; padding: 14px 18px; border-radius: 6px;
    margin: 0 0 24px;
  }
  @media print {
    body { background: white; color: black; }
    .wrap { max-width: 100%; }
    details[open] summary { display: none; }
    details { border: none; padding: 0; }
    canvas, .mermaid { page-break-inside: avoid; }
  }
</style>
</head>
<body>
<div class="wrap">

  <header class="hero">
    <h1>{{brand}} — Brand Influence Audit</h1>
    <div class="badges">
      <span class="badge">{{version}}</span>
      <span class="badge mode-{{mode}}">{{mode}}</span>
      <span class="badge">{{date}}</span>
      <span class="badge">5 judges · 5 lenses</span>
    </div>
    <p class="tldr">{{tldr}}</p>
  </header>

  <!-- DELTA BANNER (evolution mode only) -->
  <!-- {{#if delta}} -->
  <div class="delta-banner">
    <strong>What changed since {{delta.fromVersion}}:</strong>
    {{delta.changes joined with " · "}}
    <span style="float:right">mean Δ {{delta.scoreShift}}</span>
  </div>
  <!-- {{/if}} -->

  <section>
    <h2>Score radar — 5 judges across 5 lenses</h2>
    <canvas id="radar" height="360"></canvas>
  </section>

  <section>
    <h2>Score totals</h2>
    <div class="grid-2">
      <canvas id="totals" height="280"></canvas>
      <canvas id="lensMean" height="280"></canvas>
    </div>
  </section>

  <section>
    <h2>Dissent heatmap — where do the judges fight</h2>
    <p style="color: var(--c-muted); margin-top: -6px;">
      Each cell: that judge's score on that lens (1-10), shaded red→yellow→green.
      Last column σ = standard deviation across judges; high σ = real disagreement.
      Hover any cell for the judge's one-line reasoning.
    </p>
    <div id="heatmap" class="heatmap"></div>
    <div class="heatmap-legend">
      <span>1</span><span class="swatch"></span><span>10</span>
      <span style="margin-left: 24px; color: var(--c-muted);">σ column shading: pale = consensus · saturated = brawl</span>
    </div>
  </section>

  <section>
    <h2>How influence is constructed</h2>
    <div class="mermaid">{{mermaidInfluenceFlow}}</div>
  </section>

  <section>
    <h2>Brand positioning</h2>
    <div class="mermaid">{{mermaidQuadrant}}</div>
  </section>

  <section>
    <h2>Score matrix</h2>
    <!-- Render the table from DATA.judges × DATA.lenses.
         In EVOLUTION mode each cell is "7 → 8 (↑1)" with td class="up"/"down"/"flat".
         In FRESH mode each cell is just the number. -->
    {{score_matrix_table}}
  </section>

  <section>
    <h2>Judge panel</h2>
    <div class="grid-2">
      {{#each judges}}
      <div class="judge-card card" style="border-left-color: {{this.color}}">
        <h3>{{this.cn}}</h3>
        <div class="score-row">
          {{#each this.scores}}<span class="score-pill">{{../../lenses[@index]}}: {{this}}</span>{{/each}}
          <span class="score-pill" style="font-weight:600">total {{this.total}}</span>
        </div>
        <p><strong>Verdict:</strong> {{this.verdict}}</p>
        <p class="quote">"{{this.quote}}"</p>
      </div>
      {{/each}}
    </div>
  </section>

  <section>
    <h2>Where the judges agree</h2>
    <ul>{{#each consensus}}<li>{{this}}</li>{{/each}}</ul>
  </section>

  <section>
    <h2>Where they disagree (most useful section)</h2>
    {{#each dissent}}
    <details open>
      <summary>{{this.judges joined with " vs "}} — {{this.topic}}</summary>
      {{#each this.quotes}}
      <p><strong>{{@key}}:</strong> "{{this}}"</p>
      {{/each}}
    </details>
    {{/each}}
  </section>

  <section>
    <h2>Brand essence — mindmap</h2>
    <div class="mermaid">{{mermaidMindmap}}</div>
  </section>

  <!-- {{#if sentimentTrend}} -->
  <section>
    <h2>Sentiment trend</h2>
    <canvas id="sentiment" height="240"></canvas>
  </section>
  <!-- {{/if}} -->

  <!-- {{#if mermaidGitGraph}} -->
  <section>
    <h2>Version timeline</h2>
    <div class="mermaid">{{mermaidGitGraph}}</div>
  </section>
  <!-- {{/if}} -->

  <section>
    <h2>Lead's read</h2>
    <p>{{leadRead}}</p>
  </section>

  <section>
    <h2>Action recommendations (next 90 days)</h2>
    <ol class="actions">
      {{#each actions}}
      <li>{{this.text}} <span class="leverage {{this.leverage}}">{{this.leverage}} leverage</span></li>
      {{/each}}
    </ol>
  </section>

  <details>
    <summary>Citations ({{citations.length}})</summary>
    <ul>
      {{#each citations}}
      <li><a href="{{this.url}}" target="_blank" rel="noopener">{{this.label}}</a></li>
      {{/each}}
    </ul>
  </details>

</div>

<footer>
  <div>本报告由 <strong>MBA — Metric Brand Auditor</strong> 自动生成 · cutoff {{date}}</div>
  <div>Lead: MBA orchestrator · Judges: {{judgeList}}</div>
  {{#if teamCredit}}<div>{{teamCredit}}</div>{{/if}}
  <div style="margin-top: 0.8rem; padding-top: 0.6rem; border-top: 1px dashed var(--c-border);">
    想给自己的品牌跑一份这样的报告?
    在 BotLearn 一键安装 →
    <a href="https://www.botlearn.ai/skillhunt/v2/s/metric-brand-auditor" style="color: var(--c-accent); font-weight: 600;">↓ Install MBA</a>
    · <a href="https://github.com/zhanglunet/mba" style="color: var(--c-accent);">GitHub</a>
    · <a href="https://mbabrand.com" style="color: var(--c-accent);">mbabrand.com</a>
  </div>
</footer>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  const dark = matchMedia('(prefers-color-scheme: dark)').matches;
  mermaid.initialize({
    startOnLoad: true,
    theme: dark ? 'dark' : 'neutral',
    securityLevel: 'loose',
    flowchart: { curve: 'basis' }
  });
</script>
<script>
  // DATA injected by Lead — replace this block with the actual JSON
  const DATA = {{DATA_JSON}};

  // Radar — 5 lenses × 5 judges
  new Chart(document.getElementById('radar'), {
    type: 'radar',
    data: {
      labels: DATA.lenses,
      datasets: DATA.judges.map(j => ({
        label: j.cn,
        data: j.scores,
        borderColor: j.color,
        backgroundColor: j.color + '22',
        borderWidth: 2,
        pointRadius: 3
      }))
    },
    options: {
      responsive: true,
      scales: { r: { suggestedMin: 0, suggestedMax: 10, ticks: { stepSize: 2 } } },
      plugins: { legend: { position: 'bottom' } }
    }
  });

  // Totals per judge (bar)
  new Chart(document.getElementById('totals'), {
    type: 'bar',
    data: {
      labels: DATA.judges.map(j => j.cn),
      datasets: [{
        label: 'Total score',
        data: DATA.judges.map(j => j.total),
        backgroundColor: DATA.judges.map(j => j.color)
      }]
    },
    options: {
      indexAxis: 'y',
      plugins: { legend: { display: false }, title: { display: true, text: 'Total per judge' } },
      scales: { x: { suggestedMax: 50 } }
    }
  });

  // Mean per lens (bar)
  const means = DATA.lenses.map((_, i) =>
    DATA.judges.reduce((s, j) => s + j.scores[i], 0) / DATA.judges.length
  );
  new Chart(document.getElementById('lensMean'), {
    type: 'bar',
    data: {
      labels: DATA.lenses,
      datasets: [{ label: 'Mean score', data: means, backgroundColor: '#2c3e50' }]
    },
    options: {
      plugins: { legend: { display: false }, title: { display: true, text: 'Mean per lens' } },
      scales: { y: { suggestedMin: 0, suggestedMax: 10 } }
    }
  });

  // Dissent heatmap (pure DOM, no chart lib)
  (function renderHeatmap() {
    const root = document.getElementById('heatmap');
    const cols = DATA.judges.length + 2; // 1 lens label + N judges + 1 sigma
    root.style.gridTemplateColumns = `1.6fr repeat(${DATA.judges.length}, 1fr) .9fr`;

    // Score → color (red → yellow → green, 1..10)
    const scoreColor = (s) => {
      if (s == null || isNaN(s)) return 'var(--c-surface)';
      const t = Math.max(0, Math.min(1, (s - 1) / 9));
      // 0 = red(192,57,43), .5 = amber(243,156,18), 1 = green(39,174,96)
      const lerp = (a, b, k) => Math.round(a + (b - a) * k);
      let r, g, b;
      if (t < 0.5) {
        const k = t * 2;
        r = lerp(192, 243, k); g = lerp(57, 156, k); b = lerp(43, 18, k);
      } else {
        const k = (t - 0.5) * 2;
        r = lerp(243, 39, k); g = lerp(156, 174, k); b = lerp(18, 96, k);
      }
      return `rgba(${r},${g},${b},.78)`;
    };
    // σ → color (pale gray → saturated purple)
    const sigmaColor = (sd) => {
      const t = Math.max(0, Math.min(1, sd / 2.5)); // σ above 2.5 capped
      return `rgba(155, 89, 182, ${0.10 + t * 0.65})`;
    };
    const std = (arr) => {
      const m = arr.reduce((a, b) => a + b, 0) / arr.length;
      return Math.sqrt(arr.reduce((a, b) => a + (b - m) ** 2, 0) / arr.length);
    };

    const make = (cls, html, style) => {
      const el = document.createElement('div');
      el.className = 'hcell ' + cls;
      el.innerHTML = html;
      if (style) Object.assign(el.style, style);
      return el;
    };

    // Header row: blank, judge names, σ
    root.appendChild(make('label', ''));
    DATA.judges.forEach(j => root.appendChild(make('label', j.cn)));
    root.appendChild(make('label sigma', 'σ'));

    // One row per lens
    DATA.lenses.forEach((lens, i) => {
      root.appendChild(make('label lens', lens));
      const scoresRow = DATA.judges.map(j => j.scores[i]);
      DATA.judges.forEach((j, k) => {
        const s = j.scores[i];
        const tip = (j.reasoning && j.reasoning[i])
          ? `<div class="tip"><strong>${j.cn}:</strong> ${s} — ${j.reasoning[i]}</div>`
          : `<div class="tip"><strong>${j.cn}:</strong> ${s}</div>`;
        root.appendChild(make('score', `${s}${tip}`, { background: scoreColor(s) }));
      });
      const sd = std(scoresRow);
      root.appendChild(make('sigma', sd.toFixed(2), { background: sigmaColor(sd) }));
    });
  })();

  // Sentiment trend (optional)
  if (DATA.sentimentTrend) {
    new Chart(document.getElementById('sentiment'), {
      type: 'line',
      data: DATA.sentimentTrend,
      options: { plugins: { legend: { position: 'bottom' } } }
    });
  }
</script>
</body>
</html>
```

## Filling the score matrix table

The Lead generates the inner `<tbody>` HTML, not the chart library. For each lens row:

**FRESH mode** (one number per cell):
```html
<tr>
  <td class="lens">Origin authenticity</td>
  <td>7</td><td>6</td><td>8</td><td>7</td><td>6</td>
  <td><strong>6.8</strong></td>
</tr>
```

**EVOLUTION mode** (delta-aware cells):
```html
<tr>
  <td class="lens">Origin authenticity</td>
  <td class="flat">7 ↔</td>
  <td class="up">6 → 8 (↑2)</td>
  <td class="flat">8 ↔</td>
  <td class="down">7 → 5 (↓2)</td>
  <td class="flat">6 ↔</td>
  <td><strong>6.8 → 6.8</strong></td>
</tr>
```

## Anti-pitfall checklist before finalizing

- [ ] All `{{...}}` placeholders are replaced (search the file for `{{` — should match zero)
- [ ] `DATA = {...}` is valid JSON (no trailing commas, all strings escaped)
- [ ] Each Mermaid string compiles — paste into https://mermaid.live to verify before embedding
- [ ] All 5 judge cards present, even if one judge "withheld" — show "withheld" not 0
- [ ] In EVOLUTION mode the delta banner is present and the score matrix uses delta cells
- [ ] In FRESH mode there's no `gitGraph` section (only meaningful from v2 onward)
- [ ] File opens correctly in a browser (test on John: `cd ~/mba/metric-brand-auditor/reports/<brand-slug> && python3 -m http.server 8080`)
- [ ] Mermaid `mindmap` indentation is consistent (Mermaid is whitespace-sensitive)
- [ ] No `console.error` in browser devtools

## When charts don't fit the data

The defaults assume 5 lenses × 5 judges = 25 scores. If the user dropped lenses or
withheld a judge, **degrade gracefully**:
- Withheld judge → omit from radar dataset, show "withheld" badge in their card
- Dropped lens → smaller radar, fewer table columns, recompute means
- No sentiment time-series → skip the section entirely (not a stub)
- One-judge run (`--no-judges` is forbidden if HTML is emitted; if the user disables judges,
  the HTML output is also skipped — markdown-only)
