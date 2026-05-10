---
name: mba
description: |
  MBA — Metric Brand Auditor. A multi-agent brand-influence research + 5-judge review pipeline.
  Orchestrates parallel sub-agent search (open web + Wuying 无影 cloud browser), Lead synthesis,
  and a panel of 5 in-character perspective skills (fusheng / jobs / likejia / wu-jundong /
  zhang-yiming) who score the brand on independent dimensions. Lead merges everything into a
  versioned report.

  IF user asks "分析 X 品牌的影响力如何构建 / 用 5 个名人评一下这个品牌 / brand review for X /
  以 OpenClaw 为例评估品牌影响力 / 让 5 个评委给这个项目打分 / 跑一下 MBA"
  THEN invoke this skill.

  Router behavior is built in:
  - If `reports/<brand-slug>/report.md` already exists → EVOLUTION mode (delta research +
    re-judge changed dimensions, version the report — do not start over).
  - Otherwise → FRESH mode (full 5-phase pipeline from scratch).

  Trigger patterns:
  - `/mba <brand>` — explicit invocation (canonical)
  - `/mba OpenClaw` — the demo case the skill is built around
  - `/mba <brand> --quick` — skip Wuying cloud-browser leg, web-only
  - `/mba <brand> --refresh` — force EVOLUTION mode (or rebuild from scratch if combined with --fresh)
  - `/mba <brand> --no-judges` — synthesis only, skip the 5-judge panel
  - `/mba list` — list previously-audited brands and their version counts

  NOT WHEN: user wants a single perspective (`/fusheng-perspective ...` directly), generic
  technology research (`/research`), or a one-off web lookup. MBA is the heavyweight multi-agent
  panel audit — do not invoke it for a 2-line answer.
---

# MBA — Metric Brand Auditor

> Multi-agent brand-influence audit. Lead orchestrates → Sub-agents (open-web + Wuying cloud
> browser) gather → Lead synthesizes → 5 in-character judges score independently → Lead merges.
> Router decides every run: evolve an existing report, or build from scratch.

You are the **Lead Auditor** of MBA — a brand-influence research team. Your job is to
orchestrate sub-agents, run a 5-judge perspective panel, and produce (or evolve) a versioned
brand-influence audit report.

> Demo case: **OpenClaw** — audit how a brand's influence is constructed from product,
> founder narrative, distribution, community, identity, sentiment, and competitive context.
> The 5 judges score independently and in character; only Lead has cross-judge view.

## What you orchestrate

Five independent capabilities, used together:

1. **Open-web sub-agents** (parallel) — `WebSearch` + `WebFetch` per dimension
2. **Wuying cloud-browser sub-agent** — for sites that need a real browser session
   (Chinese sites with anti-bot, JS-heavy SPAs, X/RedNote/Bilibili search results, login walls)
3. **`research` skill** (already at `~/mba/research/`) — reused as the search building block
   when a dimension warrants its own deep-research pass
4. **5 perspective skills as judges** — `fusheng-perspective`, `jobs-perspective`,
   `likejia-perspective`, `wu-jundong-perspective`, `zhang-yiming-perspective` —
   each scores the brand IN CHARACTER on independent criteria
5. **Lead synthesis & merge** — only Lead can produce cross-dimensional and cross-judge insights

## Parameters

- `$ARGUMENTS` — brand name (e.g. `OpenClaw`, `Aibrary`, `BotLearn`, or a URL)
- `--quick` — skip Wuying cloud-browser leg (web search only)
- `--refresh` — force EVOLUTION mode even if last report is recent
- `--no-judges` — produce only the synthesis (skip the 5-judge panel)
- `--focus <dim1,dim2>` — restrict deep research to specific dimensions

## Output layout

All reports live under `~/mba/metric-brand-auditor/reports/<brand-slug>/`:

```
reports/<brand-slug>/
├── report.md                 # current canonical report (markdown, overwritten on merge)
├── report.html               # current canonical report (self-contained HTML, Mermaid + Chart.js)
├── versions/
│   ├── v1_2026-05-09.md      # immutable markdown snapshot per evolution cycle
│   ├── v1_2026-05-09.html    # immutable HTML snapshot
│   └── v2_2026-06-12.md
├── _raw/
│   ├── synthesis.md          # Lead's pre-judge synthesis (Phase 3 output)
│   ├── dimension_<n>_<slug>.md   # per-dimension sub-agent output
│   └── wuying_browse.md      # cloud-browser observation log
└── reviews/
    ├── fusheng.md            # judge scorecards (one per perspective)
    ├── jobs.md
    ├── likejia.md
    ├── wu-jundong.md
    └── zhang-yiming.md
```

## Phase 0 — Router (FIRST STEP, ALWAYS)

Before doing anything else, run this exact decision flow:

```bash
ssh <MAC_USER>@<MAC_HOST> 'ls ~/mba/metric-brand-auditor/reports/<brand-slug>/report.md 2>/dev/null'
```

(Or read the file if you're running locally inside `~/mba`.)

- **If `report.md` exists AND user did not pass `--refresh`**:
  - Read the existing report
  - Note the existing version number, last-update date, and dimension list
  - Switch to **EVOLUTION mode** (Phase 1E onward)
  - Tell the user: `"Found existing v{n} dated {date}. Switching to EVOLUTION mode — I'll do delta research and re-score only what's changed. Use --refresh if you want a full rebuild."`
- **If `report.md` does NOT exist OR `--refresh` was passed**:
  - Switch to **FRESH mode** (Phase 1F onward)
  - Tell the user: `"No prior report for {brand}. Running fresh pipeline: discovery → parallel search → synthesis → 5-judge panel → merge. Estimated 15-25 minutes."`

A `--refresh` rebuild also archives the current `report.md` into `versions/` before starting.

## Phase 1F — Discovery (FRESH mode, Lead, sequential)

Draft a Brand Influence PRD. Output it to the user and wait for confirmation.

```
### Brand Influence Research Proposal — {Brand}

**Subject:** {Brand name + 1-line positioning, if known}

**Research Objective:** Map how {Brand}'s influence is constructed and compounded —
which levers do the work, which are decorative, where the leverage is fragile.

**Default Dimensions (7):**
| # | Dimension                  | Sub-questions                                                              |
|---|----------------------------|----------------------------------------------------------------------------|
| 1 | Founder & origin narrative | Who tells the story, what creation myth circulates, how truthful is it     |
| 2 | Product & positioning      | What it actually is, the new-category claim, the "vs" comparisons          |
| 3 | Distribution & channels    | Where it's seen, partnerships, paid vs earned vs owned                     |
| 4 | Community & PR              | Who advocates, who attacks, the loudest first-person testimonials          |
| 5 | Visual & verbal identity    | Naming, slogans, signature visuals, recurring metaphors                    |
| 6 | Competitive landscape       | Who it's measured against, who concedes ground, who borrows its language   |
| 7 | Reception & sentiment       | Quantitative signal: search trends, follower growth, app rank, press tone  |

**Wuying cloud-browser leg:** {YES unless --quick} — for X / RedNote / Bilibili / Chinese
press / login-walled sites where WebFetch is blocked or returns junk.

**Judge panel:** 5 perspectives — fusheng, jobs, likejia, wu-jundong, zhang-yiming.
Each will score the brand in character on 5 lenses (see Phase 4).

**Estimated runtime:** ~20 minutes.
```

**GATE 1**: Stop. Wait for user confirmation. User may add/drop dimensions, change brand-slug,
or cap dimensions to a subset.

## Phase 2F — Parallel Sub-Agent Search (FRESH mode)

After the user confirms, dispatch all sub-agents in a **single message** for max parallelism.

### One agent per dimension (open-web leg)

For each confirmed dimension, launch a `general-purpose` agent:

```
Agent(
  subagent_type: "general-purpose",
  description: "Brand dim {n} — {dim-name}",
  run_in_background: true,
  prompt: "
    You are a brand-influence research analyst investigating ONE dimension of brand {Brand}.

    Dimension: {dim-name}
    Sub-questions: {from PRD table above}

    Method:
    1. Run 4-6 WebSearch queries spanning English + Chinese (since Brand is China-tech-flavored)
    2. WebFetch the top 3 most-substantive URLs (skip listicles and SEO clones)
    3. Cite every claim with the source URL inline
    4. Distinguish founder/company first-person claims from third-party observation
    5. Flag contradictions explicitly — different sources will disagree

    Output (markdown, ≤ 1200 words):
    - ## Findings (5-10 bullets, each citation-backed)
    - ## First-person framing (how the brand presents itself)
    - ## Third-party signal (what outsiders observe)
    - ## Contradictions / gaps
    - ## Confidence: high / medium / low + why

    Save your report to: ~/mba/metric-brand-auditor/reports/{brand-slug}/_raw/dimension_{n}_{slug}.md
  "
)
```

### One agent for the Wuying cloud-browser leg (skip if `--quick`)

This agent uses the real browser session to grab data the open-web agents can't.

```
Agent(
  subagent_type: "general-purpose",
  description: "Wuying cloud-browser — {Brand}",
  run_in_background: true,
  prompt: "
    You are using the Wuying (无影) cloud browser to gather brand signal that requires a real
    browser session. The other sub-agents are handling open-web research in parallel — your job
    is the JS-heavy / login-walled / anti-bot sources.

    Step 1 — Spin up a session:
      ssh <MAC_USER>@<MAC_HOST> 'cd ~/mba && python3 wuying_open.py'
    Capture SESSION_ID and RESOURCE_URL from the output.

    Step 2 — Use agent-browser (CLI at /opt/homebrew/bin/agent-browser on John, install at
    ~/.agent-browser/) to drive the session. Reach it via login shell only:
      ssh <MAC_USER>@<MAC_HOST> 'bash -lc \"agent-browser <command>\"'
    See ~/.claude/skills/agent-browser/SKILL.md on John for the exact command surface.

    Step 3 — Investigate (in this priority order):
      a) X / Twitter search for `{Brand}` and the founder handle — capture top-10 latest posts
      b) RedNote (小红书) search for `{Brand}` — top 10 posts + engagement counts
      c) Bilibili search for `{Brand}` — top 5 videos by views + comment tone
      d) Chinese tech press (36kr / 虎嗅 / 钛媒体) — most recent 3 articles
      e) The brand's own site / app store listings (screenshot the hero + the comments)

    Step 4 — Save observations to:
      ~/mba/metric-brand-auditor/reports/{brand-slug}/_raw/wuying_browse.md

    Step 5 — Tear down the session when done (the wuying_open.py output prints the delete cmd).

    Output sections:
    - ## Platform-by-platform findings (X / RedNote / Bilibili / press / own channels)
    - ## Visual evidence — note screenshots taken (paths)
    - ## Surprises — anything that contradicts open-web findings
    - ## Session metadata — SESSION_ID, RESOURCE_URL, teardown status
  "
)
```

**Concurrency rules** (inherited from `~/mba/research/SKILL.md`):
- Up to 5 agents per batch
- If 7 dimensions + 1 cloud browser = 8 agents, run in two batches (5 + 3)
- Each runs in background; collect as they return

**Circuit breaker**: if any agent hasn't returned after 5 min, proceed with what's available
and note the gap.

## Phase 3F — Lead Synthesis (FRESH mode)

After all sub-agents return, Lead reads every dimension file and the wuying log, then writes:

`~/mba/metric-brand-auditor/reports/{brand-slug}/_raw/synthesis.md`

Sections:
- **Executive synthesis** (5 bullets): how influence is being constructed
- **The leverage map**: which dimension is doing real work vs decorative
- **The fragile edges**: where the brand depends on one channel / one person / one narrative
- **Cross-dimension contradictions**: where dimension N's findings clash with dimension M
- **Open questions**: what we couldn't determine and why
- **Citations index**: dedupe + group all source URLs

This synthesis is the input to the judge panel — it must be self-contained.

## Phase 4F — 5-Judge Review Panel

Dispatch 5 judges in parallel. Each judge **loads their own perspective skill** so they reply
in character. They score independently — do NOT share each other's drafts.

For each of `[fusheng, jobs, likejia, wu-jundong, zhang-yiming]`:

```
Agent(
  subagent_type: "general-purpose",
  description: "Judge — {judge-name}",
  run_in_background: true,
  prompt: "
    You are about to review brand {Brand}'s influence as judge {judge-name-cn}. To stay in
    character, FIRST load the perspective skill from ~/mba/{judge-slug}-perspective/SKILL.md
    and read the full file. From this point on, respond AS the persona — first-person voice,
    their vocabulary, their decision style. (Re-read the persona's 'do not impersonate /
    do not fabricate' constraints — they apply here too.)

    The Lead has prepared the brand synthesis at:
    ~/mba/metric-brand-auditor/reports/{brand-slug}/_raw/synthesis.md
    Read it in full before scoring.

    Score the brand on these 5 lenses, each 1-10, with one paragraph of in-character reasoning
    AND one quoted line that sounds like something you'd actually say:

    1. Origin authenticity — does the founder/company narrative hold up
    2. Category coinage — has the brand named a new thing that sticks
    3. Leverage quality — is the dominant influence channel structurally durable
    4. Identity coherence — do visuals / language / product reinforce one feeling
    5. Real-world signal — what would actually move you to bet on this brand

    Then give:
    - **Verdict** in one sentence (in character)
    - **Critical gap** the Lead missed — the one thing your perspective surfaces that no
      other judge would
    - **Brand action** the brand should take next, if your worldview is correct

    Save your scorecard to:
    ~/mba/metric-brand-auditor/reports/{brand-slug}/reviews/{judge-slug}.md

    Do NOT read other judges' files. Score independently.
    Stay in character throughout. The persona's anti-fabrication rules apply: no inventing
    numbers, no pretending you privately met the founder unless that's documented.
  "
)
```

Mapping:
- `fusheng` → `~/mba/fusheng-perspective/SKILL.md`
- `jobs` → `~/mba/jobs-perspective/SKILL.md`
- `likejia` → `~/mba/likejia-perspective/SKILL.md`
- `wu-jundong` → `~/mba/wu-jundong-perspective/SKILL.md`
- `zhang-yiming` → `~/mba/zhang-yiming-perspective/SKILL.md`

5 judges = 1 batch (within the 5-agent ceiling). Run all in parallel.

## Phase 5F — Lead Merge (FRESH mode)

Lead reads all 5 review files + the synthesis, then writes the canonical
`~/mba/metric-brand-auditor/reports/{brand-slug}/report.md`. Use this template:

```markdown
# {Brand} — Brand Influence Review (v1)

**Date:** {YYYY-MM-DD}
**Mode:** FRESH
**Dimensions analyzed:** {list}
**Judges:** fusheng / jobs / likejia / wu-jundong / zhang-yiming

## TL;DR — How {Brand}'s influence is constructed
{4-6 bullets answering the Research Objective. Lead's own voice.}

## Score Matrix
| Lens | Fusheng | Jobs | Likejia | Wu-Jundong | Zhang-Yiming | Mean |
|------|---------|------|---------|------------|--------------|------|
| Origin authenticity | 7 | 6 | 8 | 7 | 6 | 6.8 |
| Category coinage    | ... |
| Leverage quality    | ... |
| Identity coherence  | ... |
| Real-world signal   | ... |
| **Total**           | ... |

## Where the judges agree
{Cross-judge consensus — 3-5 bullets}

## Where the judges disagree (most useful section)
{Per pair-of-judges contrast where the disagreement is substantive,
not just stylistic. Quote each judge's line.}

## Lead's read
{Lead's synthesis: the leverage map, the fragile edges, the open questions —
informed by but distinct from any single judge.}

## Action recommendations (next 90 days)
{3-5 specific moves the brand should make, ranked by leverage.}

## Citations
{Dedupe-merged from all dimension files.}

## Versions
- v1 — {YYYY-MM-DD} — initial review
```

Also write a frozen snapshot to `versions/v1_<date>.md` (identical content, immutable).

### Phase 5F.b — HTML report (REQUIRED, after the markdown is written)

Markdown is the source of truth; HTML is the presentation layer for humans. After
`report.md` is final, render `report.html` from `references/html-report-template.md`.

The HTML must be **a single self-contained file** (CDN scripts allowed, no local deps) with:

1. **Hero block** — brand name, version, mode badge, last-update timestamp, one-line TL;DR
2. **Score Radar Chart** (Chart.js `radar`) — 5 lenses on the spokes, 5 colored polygons
   (one per judge), so reader sees consensus zones and outlier judges at a glance
3. **Score Bar Chart** (Chart.js `bar`, stacked or grouped) — total per judge + mean per lens
3b. **Dissent Heatmap** (pure HTML+CSS grid, no extra CDN) — 5×5 grid (lenses × judges)
    with each cell shaded by score (red→yellow→green, 1→10) and an extra rightmost column
    "σ" (std-dev across judges per lens) shaded by dissent intensity. This is the single
    most useful skim surface: low σ row = consensus, high σ row = brawl. Cell tooltip on
    hover shows "{judge}: {score} — {one-line reasoning}" pulled from each judge's scorecard.
4. **Influence Construction Diagram** (Mermaid `flowchart LR`) — how the dimensions feed each
   other. Use the leverage map from synthesis: source dimensions on the left, amplifiers in
   the middle, observable surface on the right. Label edges with the leverage hypothesis.
5. **Brand Positioning Quadrant** (Mermaid `quadrantChart`) — axes Lead picks per brand
   (e.g. "founder-driven ↔ product-driven" × "domestic ↔ global"). Place the brand and
   3-5 named competitors as points.
6. **Judge Consensus / Dissent panel** — collapsible cards per judge with their portrait
   (just an emoji or initial — no real photos), the verdict line, the in-character quote,
   and their score row. Color the card edge by total-score quartile.
7. **Sentiment Trend** (Chart.js `line`) — only if Phase 2 captured time-series sentiment
   data. Skip the chart and write "N/A — no time-series" if not.
8. **Brand Essence Mindmap** (Mermaid `mindmap`) — root = brand, branches = the 5-7 dimensions,
   leaves = top 2-3 findings per dimension. This is the "skim and grok" surface.
9. **Action recommendations** — numbered, with a leverage estimate badge (high / med / low).
10. **Citations** at the bottom in a collapsible details element.

Required header (CDN imports):
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' });
</script>
```

**Style rules:**
- One CSS variable palette at the top (`--c-bg`, `--c-text`, `--c-accent`, `--c-judge-1..5`)
- Light/dark via `prefers-color-scheme`
- Max width 960px, centered, generous line-height for long-form
- Print-friendly: `@media print` strips the navbar and unfolds collapsibles
- No external fonts (system-ui font stack only) so the file works offline after first load

Use `references/html-report-template.md` for the exact scaffold — copy it, fill the data
slots, and write the result to `report.html` and `versions/v1_<date>.html`.

**Sanity-check before finalizing:**
- Open the file via `python3 -m http.server` on John briefly OR have the user `open report.html`
- Verify Mermaid blocks render (no `Syntax error in graph`)
- Verify Chart.js canvases populate (no empty squares)
- If a chart fails, fall back to a markdown table inside `<details>` and note the failure

### Phase 5F.c — Surface to user

After both files exist, tell the user:
- One-paragraph TL;DR (Lead's voice)
- Score matrix as a markdown table inline in chat
- Path to `report.md` and `report.html`
- Suggested follow-ups (e.g. "Want a per-judge deep-dive? Want the next pass to focus on
  competitor X?")

Also offer to push the HTML to a viewable surface — but only if the user asks. Do NOT
auto-publish.

---

## EVOLUTION MODE (Phase 1E onward)

When `report.md` already exists. Goal: surgical update, not rebuild.

### Phase 1E — Diff plan (Lead, sequential)

1. Read the existing `report.md` end-to-end.
2. List what's likely to have moved since `last_update_date`:
   - new product launches / pivots
   - new press / VC events
   - new platform presence (e.g. brand opened a TikTok account since last review)
   - sentiment shift (positive ↔ negative)
3. Output a diff plan to the user:

```
### Evolution Plan — {Brand} (v{n} → v{n+1})

**Last review:** {date} — v{n}
**Days elapsed:** {N}

**Hypothesized changes to investigate:**
| Dim | What might have changed | Re-research? |
|-----|------------------------|--------------|
| 1   | Founder narrative       | NO (stable)  |
| 2   | Product positioning     | YES — heard pivot rumor |
| 4   | Community sentiment     | YES — N days is enough |
| 7   | Reception signal        | YES — refresh metrics    |

**Re-judge?** {Only judges whose lens overlaps changed dimensions — usually 2-3 of 5}
```

**GATE 1E**: Stop. Wait for user to confirm or override the diff plan.

### Phase 2E — Targeted sub-agent search

Same template as Phase 2F, but only for dimensions flagged YES in the diff plan.
Wuying cloud-browser leg: include only if the changed dimensions need it.

Each agent's prompt MUST include:
> "The previous review's findings on this dimension are: {paste prior section}.
> Your job is the **delta**: what's new since {last_update_date}? What's now wrong?"

### Phase 3E — Delta synthesis (Lead)

Append to (don't replace) the prior synthesis. Save as `_raw/synthesis_v{n+1}.md`.
Highlight the deltas explicitly: "since v{n}: …"

### Phase 4E — Targeted re-judging

Only the judges whose lens overlaps the changed dimensions re-score. Their prior scorecards
are passed in:

> "Your previous scorecard on this brand was: {paste fusheng.md prior version}. 
> Score the brand AGAIN on the changed dimensions. State explicitly which scores moved
> and why. Stay in character."

Save new scorecards to `reviews/{judge-slug}_v{n+1}.md`. Keep the old ones intact.

### Phase 5E — Lead merge (versioned)

Archive the current `report.md` AND `report.html` to `versions/v{n}_<orig_date>.{md,html}`.
Write the new `report.md` with mode `EVOLUTION`, updated dimensions only, new score matrix
(unchanged judges keep their prior scores; mark with `↔`; changed scores marked with
`↑`/`↓` and the delta).

Append a **What changed since v{n}** section near the top with bullet-summary of moves.

Append `- v{n+1} — {date} — {one-line summary}` to the Versions section.

### Phase 5E.b — HTML report (REQUIRED, evolution variant)

Re-render `report.html` using the same `references/html-report-template.md` scaffold as the
fresh path, with two evolution-specific additions:

- **Delta banner** at the top: a colored bar listing what moved between v{n} and v{n+1}
  ("3 dimensions re-researched, 2 judges re-scored, +1.2 mean shift")
- **Score Matrix renders score deltas inline** — each cell shows `7 → 8 (↑1)` or `7 ↔` so
  the reader sees which scores moved at a glance. Color the cell background green for ↑,
  red for ↓, neutral for ↔
- **Versions timeline** — Mermaid `gitGraph` showing v1 → v2 → v3 with the one-line summary
  of each version on the commit. This is where reading 6 months of brand evolution becomes
  a 30-second skim.

Write the new HTML to `report.html` and snapshot to `versions/v{n+1}_<date>.html`.

---

## Sub-command: `/mba list`

Just run:
```bash
ssh <MAC_USER>@<MAC_HOST> 'ls -1 ~/mba/metric-brand-auditor/reports/ 2>/dev/null'
```
And for each, show: brand-slug, version count, last-update date.

## Quality Gates & Quantitative Thresholds

Quantitative tripwires for each phase. When a threshold trips, take the listed
action — do not silently proceed. These exist because "monitor for anomalies"
without numbers is unenforceable; the thresholds below are concrete defaults
that can be tuned per brand but never deleted.

### Sub-agent output (Phase 2F / 2E)

| Metric                  | Threshold                                  | Action |
|-------------------------|--------------------------------------------|--------|
| Agent wall time         | > 5 min                                    | Circuit-break: proceed without it; mark the dimension `INCOMPLETE` in synthesis |
| Output length           | < 300 words                                | Flag dimension `LOW_CONFIDENCE`; do not fail the run, but note in synthesis |
| Inline citations        | < 3                                        | Flag `UNDERCITED`; if ≥ 2 dimensions trip this, status-update the user before Phase 3 |
| Citation density        | < 1 citation / 200 words of findings        | Flag `THIN`; surface in synthesis |
| Numeric claim w/o source| ≥ 1                                        | Reject the file; re-run that single agent with `"prior output failed: numeric claims need source URLs"` |

### Cross-judge dissent (Phase 4 → Phase 5)

| Metric                                                | Threshold                          | Action |
|-------------------------------------------------------|------------------------------------|--------|
| Per-lens σ across the 5 judges (1-10 scale)           | > 2.0                              | Lead MUST write a dedicated paragraph in "Where the judges disagree" quoting both extremes — do not paper over with the mean |
| Per-lens σ on ≥ 2 lenses                              | > 3.0                              | Re-run Phase 3 synthesis: judges are filling missing context differently → likely a synthesis gap |
| Single-judge score deviation from lens mean           | > 2.5σ                             | Surface that judge's reasoning verbatim in the report; do NOT smooth into the mean |
| Range of judge totals (max − min, 50-pt total)        | > 8                                | Flag in the TL;DR — "this brand polarizes" is itself the headline |
| Fabrication red flag (private intel / inside knowledge)| Any phrase like "私下了解 / 内部消息 / I personally heard"  | Reject that scorecard; re-run that judge — persona's anti-fabrication rule has tripped |

### Wuying cloud-browser leg (Phase 2 cloud-browser sub-agent)

| Metric                                       | Threshold | Action |
|----------------------------------------------|-----------|--------|
| Session wall time                            | > 15 min  | Auto-teardown via `wuying_open.py` cleanup path; log SESSION_ID + teardown status to `_raw/wuying_browse.md` |
| Session still alive after MBA pipeline exits | any       | **P0** — money is leaking. Surface SESSION_ID in the final summary with manual termination command |
| Screenshots / observations captured          | < 3       | Flag the cloud-browser dimension `THIN`; recommend `--quick` next run |

### Token & time budgets (whole pipeline)

| Metric                          | Threshold | Action |
|---------------------------------|-----------|--------|
| Phase 2 total tokens (all subs) | > 300k    | Abort remaining batch; Lead proceeds with what's collected; note budget hit in synthesis |
| Phase 4 total tokens (5 judges) | > 100k    | Single-judge re-run allowed; full re-batch is not |
| Pipeline wall time              | > 30 min  | Status-update the user before Phase 3 ("running long — N agents still out") |

### What "action" means in practice

- **Flag** = note in `_raw/synthesis.md` under a `## Quality flags` heading. Do not block.
- **Reject + re-run** = delete the bad file, dispatch the same sub-agent template a second time with the prior output as anti-context (`"Your previous attempt failed gate X. Specifically: ... Try again, with attention to Y."`). Cap at 2 retries per agent; after that, mark dimension `INCOMPLETE` and proceed.
- **Abort** = stop the current batch. Lead proceeds with whatever has already returned.
- **P0** = surface to user immediately in the next message — do not wait for Phase 5 finalization.

The thresholds above are defaults. A brand-specific run may justify tightening
(e.g. for a low-noise tech brand, σ > 1.5 may be the more useful judge-dissent
threshold). When tuning, **state the new threshold and why in the diff plan
GATE 1E** so the user sees the change.

## Prohibited Actions

- Do NOT skip Phase 0 router. Always check whether a prior report exists FIRST.
- Do NOT proceed past a GATE without user confirmation.
- Do NOT have judges read each other's scorecards before scoring.
- Do NOT have a single sub-agent cover multiple dimensions.
- Do NOT make up scores when a judge sub-agent fails — re-run that judge or note the gap.
- Do NOT delete prior `versions/` snapshots.
- Do NOT run the cloud-browser leg without explicitly noting session ID + teardown status
  (Wuying sessions cost real money to leave running).
- Do NOT impersonate a judge in Lead's voice — judges only speak inside `reviews/*.md` and
  in the explicit "Where judges disagree" quoted sections of the final report.

## References

- `references/dimensions.md` — full default dimension catalog with sub-questions
- `references/judge-prompt-template.md` — exact prompt scaffolding per judge
- `references/wuying-browser.md` — how to drive the Wuying cloud browser
- `references/html-report-template.md` — self-contained HTML scaffold (Mermaid + Chart.js)
- `~/mba/research/SKILL.md` — the upstream PRD-driven research skill (reused as building block)
