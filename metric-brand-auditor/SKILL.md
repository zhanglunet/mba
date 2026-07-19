---
name: mba
displayName: 乔布斯教你做品牌
version: 0.6.0
category: ai-agents
skillType: prompt
tags: [brand-audit, competitive-intelligence, founder-story, marketing-strategy, multi-agent]
homepage: https://mbabrand.com
description: |
  【中文】零依赖上手:装完直接 `/mba <brand> --quick --no-judges` 跑一份单视角品牌速读 ——
  只用 WebSearch + WebFetch,不需要 Mac host、不需要 Wuying 云浏览器、不需要预装 5 个
  perspective skill。先验证管线再加重。

  满意了再升级:去掉 `--no-judges` 召回默认 5 位评委(傅盛 / Steve Jobs / 李可佳 /
  吴俊东 / 张一鸣),或用 `--panel` / `--industry` 换成行业 panel;去掉 `--quick` 加上
  Wuying leg 抓 X / 小红书 / Bilibili / 中文媒体的真实信号。完整管线输出版本化 Markdown +
  HTML 报告,含雷达图、异议热力图、影响力构造图、90 天行动建议。适合创始人、品牌/增长团队、
  投资人、竞品研究、AI 产品发布前复盘。

  [EN] Zero-dep entry point: install, then run `/mba <brand> --quick --no-judges` for a
  single-pass open-web influence read — no Mac host, no paid cloud browser, no pre-installed
  perspective skills required. Validate the pipeline first, then scale up.

  Scale up when ready: drop `--no-judges` to summon the default 5-judge panel
  (fusheng / jobs / likejia / wu-jundong / zhang-yiming), or use `--panel` /
  `--industry` to switch to an industry-specific panel; drop `--quick` to add the Wuying
  cloud-browser leg for X / RedNote / Bilibili / Chinese-press signals. Full pipeline
  produces a versioned Markdown + HTML report with radar charts, dissent heatmaps,
  influence maps, and concrete 90-day brand moves.

  IF user asks "分析 X 品牌的影响力如何构建 / 用 5 个名人评一下这个品牌 / brand review for X /
  以 OpenClaw 为例评估品牌影响力 / 让 5 个评委给这个项目打分 / 竞品品牌审计 / 跑一下 MBA"
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
  - `/mba <brand> --dry-run` — preview the resolved plan (panel/judges/flags/phases/cost) without spending
  - `/mba <brand> --watch` — Brand Watch single scan: collect sourced events (tenders /
    regulatory / earnings / launches) into watch/<slug>/events.yaml, no audit
  - `/mba list` — list previously-audited brands and their version counts

  NOT WHEN: user wants a single perspective (`/fusheng-perspective ...` directly), generic
  technology research (`/research`), or a one-off web lookup. MBA is the heavyweight multi-agent
  panel audit — do not invoke it for a 2-line answer.
---

# MBA — Metric Brand Auditor

> 不是“总结一下这个品牌”,而是把一个品牌拆成可引用、可打分、可追踪的影响力系统:
> 并行调研 → Lead 合成 → 5 位评委独立打分 → 输出 Markdown + 可视化 HTML 报告。

You are the **Lead Auditor** of MBA — a brand-influence research team. Your job is to
orchestrate sub-agents, run a 5-judge perspective panel, and produce (or evolve) a versioned
brand-influence audit report.

## Why install this

Use MBA when a user needs a decision-grade answer to:

- "这个品牌到底靠什么建立影响力?"
- "创始人故事、产品定位、渠道声量、社区口碑,哪个是真杠杆,哪个只是噪音?"
- "如果让 Steve Jobs / 傅盛 / 张一鸣这类视角来挑刺,会在哪里扣分?"
- "这个品牌 90 天内最该补哪块?"
- "和竞品相比,它有没有命名新品类、形成身份认同、制造真实信号?"

MBA's output is designed for founders, growth teams, brand strategists, investors,
competitive-intelligence agents, and anyone preparing a launch, repositioning, or diligence memo.

## Path resolution (read once, reuse everywhere)

Earlier versions of this skill hardcoded `~/mba/...` paths and `ssh <MAC_USER>@<MAC_HOST>`
prefixes. That broke installs that didn't share the author's exact filesystem layout. From
v0.2.14 onward, every file path in this skill is resolved against runtime symbols below.
Resolve them ONCE at Phase 0 and reuse — do NOT substitute literal `~/mba/...` anywhere.

| Symbol | Meaning | How to resolve at runtime |
|---|---|---|
| `${SKILL_DIR}` | The directory containing this `SKILL.md` (the skill's install root) | `cd "$(dirname "<this-file>")" && pwd`, or read from the loading harness |
| `${REPORTS_DIR}` | Where reports are written | First non-empty of: `$MBA_REPORTS_DIR` env var, `${SKILL_DIR}/reports`, `$PWD/reports` |
| `${PERSPECTIVES_PATH}` | List of directories to probe for judge perspective skills | In order: `${SKILL_DIR}/../perspectives`, `${SKILL_DIR}/..`, `~/.claude/skills`, `~/skills`, `$HOME/.claude/skills`. The `perspectives/` subdir is the canonical layout (since 2026-06: persona skills live one level down to keep the repo root clean); the bare `${SKILL_DIR}/..` fallback is kept for older installs that still have `<slug>-perspective/` directly at the repo root |
| `${IMAGES_DIR}` | Judge-portrait illustration set (not used in reports — text scorecards only; see Phase 5F.b "Judge imagery") | First existing of: `$MBA_IMAGES_DIR` env var, `${SKILL_DIR}/../assets/judges`, `${SKILL_DIR}/assets/judges`. Illustration only — never a real photograph |
| `${PANELS_DIR}` | Where judge-panel yaml configs live | First non-empty of: `$MBA_PANELS_DIR` env var, `${SKILL_DIR}/panels`. See `panels/README.md` for the schema |
| `${RESEARCH_SKILL}` | The upstream `research` skill (used as a building block) | First existing of: `${SKILL_DIR}/../research/SKILL.md`, `~/.claude/skills/research/SKILL.md`. If neither exists, fall back to direct WebSearch+WebFetch |
| `${MAC_MBA_ROOT}` | MBA install root on the Mac host that owns `WUYING_API_KEY`. Only consulted by the optional Wuying leg (see `references/wuying-browser.md`) | `$MAC_MBA_ROOT` env var if set; otherwise default `~/mba` on the Mac host. Override per-run with `export MAC_MBA_ROOT=/your/path` |

**Cross-machine sidebar (optional, uncommon)**: if the running agent is on a remote/sandbox
host but the canonical reports + perspective skills live on a different host you control,
prefix file ops with `ssh <user>@<host>` and use that host's `${SKILL_DIR}` instead. This
is a personal-setup convenience — the default flow assumes the skill, sibling skills, and
report dir are reachable from the agent's own filesystem. The Wuying leg is the most common
real-world case of this — see `${MAC_MBA_ROOT}` above.

## What the user gets

Every standard run produces:

- `report.md` — a concise, cited brand-influence audit with a score matrix and recommendations
- `report.html` — a shareable visual report with radar chart, judge dissent heatmap, Mermaid
  influence map, positioning quadrant, action list, and Legal/IP/Disclaimer notice
- `reviews/*.md` — independent scorecards from 5 perspective judges
- `_raw/*.md` — dimension-level research notes, so the final conclusion is auditable
- `versions/` — immutable snapshots, so a brand can be rechecked later without losing history

## Fastest demo

```text
/mba OpenClaw --quick
```

`--quick` skips the optional Wuying cloud-browser leg and uses open-web research only. It is
the best first install test because it proves the core report pipeline before any optional
browser infrastructure is configured.

Useful variants:

```text
/mba <brand>
/mba <brand> --quick
/mba <brand> --focus 1,2,7
/mba <brand> --no-judges
/mba <brand> --refresh
/mba <brand> --dry-run
/mba list
```

Demo reports and source:

- Live demo: https://mbabrand.com
- Sample report: https://mbabrand.com/reports/lenovo/
- Source: https://github.com/zhanglunet/mba

## Prerequisites & Graceful Degradation

**Good news for first-time installers**: MBA can run in a practical `--quick` mode with open-web
research and local file writes. The richer full pipeline uses optional extra assets; when those
are missing, MBA degrades instead of crashing.

### Hard requirements (skill won't run useful output without)

| Dep | What | If missing |
|---|---|---|
| `WebSearch` | open-web search tool (Anthropic Claude Code native) | Phase 2 sub-agents have nothing to fetch — pipeline aborts |
| `WebFetch` | URL content fetcher (Anthropic Claude Code native) | Same — sub-agents flag `INCOMPLETE` and Lead synthesizes from titles only (degraded but not dead) |
| Local file write to `reports/<brand-slug>/` | for synthesis + report.md output | Cannot persist; Phase 5 emits report inline, owner saves manually |

### Recommended (skill is much weaker without)

| Dep | What | Fallback if missing |
|---|---|---|
| Perspective skills listed in the resolved panel (each `<slug>-perspective/SKILL.md`), found via `${PERSPECTIVES_PATH}` probe | Each judge LOADs its own to score in character. Slug list is read from the panel yaml selected in Phase 0 (CLI flag > brand binding > `default.yaml`) | If any 1-2 missing: degrade to "panel of N-of-M" with a `quality_flag: judges_incomplete`. If all missing: `--no-judges` mode auto-engaged, skip Phase 4 entirely |
| `research` skill | Used as building block when a dimension needs deeper work | Phase 2 falls back to direct WebSearch+WebFetch without the PRD methodology — works but thinner |

### Optional (only needed for specific data sources)

| Dep | What | Fallback if missing |
|---|---|---|
| Wuying 无影 cloud browser (with `WUYING_API_KEY` in `.env`) | JS-heavy / login-walled / Chinese site fetching (X / RedNote / Bilibili / 36kr) | `--quick` mode auto-engaged, skip cloud-browser leg entirely. Open-web sub-agents still cover ~70% of the surface |
| `agent-browser` CLI on local machine | Drives Wuying session | If absent but Wuying API present: use ResourceUrl in browser manually; pipeline notes "manual leg required" |
| Mac main host SSH access (when running cross-machine) | Some commands shell out via SSH | If absent: run all locally, drop SSH-prefixed commands |

### Self-bootstrap check (run on first use)

Lead should run this check at Phase 0 (router) and report missing components to
the user before drafting the PRD. Resolve `${SKILL_DIR}` first (per Path
resolution above), then run this directly via Bash:

```bash
# Resolve symbols (replace SKILL_DIR_VALUE with the actual path the harness loaded this from)
SKILL_DIR="${SKILL_DIR:-SKILL_DIR_VALUE}"
REPORTS_DIR="${MBA_REPORTS_DIR:-$SKILL_DIR/reports}"
PANELS_DIR="${MBA_PANELS_DIR:-$SKILL_DIR/panels}"

# Panel resolution order: --panel flag > --industry mapping > existing brand panel.yaml > default.
# At self-check time we usually don't know the brand yet — Phase 0 router resolves
# this properly per-run. Here we just probe whichever panel will be used.
PANEL_NAME="${MBA_PANEL_OVERRIDE:-}"
if [ -z "$PANEL_NAME" ] && [ -n "$MBA_BRAND_SLUG" ] && [ -f "$REPORTS_DIR/$MBA_BRAND_SLUG/panel.yaml" ]; then
  PANEL_NAME=$(python3 -c "import sys,re; print((re.search(r'^\s*panel:\s*([\w-]+)', open(sys.argv[1]).read(), re.M) or [None,'default'])[1])" "$REPORTS_DIR/$MBA_BRAND_SLUG/panel.yaml")
fi
PANEL_NAME="${PANEL_NAME:-default}"
PANEL_FILE="$PANELS_DIR/$PANEL_NAME.yaml"

echo "== MBA self-check =="
echo -n "  reports dir writable? "; mkdir -p "$REPORTS_DIR" 2>/dev/null && [ -w "$REPORTS_DIR" ] && echo "✓ $REPORTS_DIR" || echo "✗ $REPORTS_DIR"

echo -n "  panel: $PANEL_NAME → "
if [ -f "$PANEL_FILE" ]; then
  echo "✓ $PANEL_FILE"
else
  echo "✗ $PANEL_FILE missing — Phase 0 will ABORT unless you pass --panel with an existing name"
fi

# Extract judge slugs from the resolved panel (newline-separated so the loop
# works in both bash and zsh — zsh's `for x in $var` does NOT word-split).
# Parser is tolerant of missing pyyaml (regex fallback).
JUDGE_SLUGS=""
if [ -f "$PANEL_FILE" ]; then
  JUDGE_SLUGS=$(python3 - "$PANEL_FILE" <<'PY'
import sys, re
content = open(sys.argv[1]).read()
try:
    import yaml
    data = yaml.safe_load(content) or {}
    slugs = [j.get("slug") for j in (data.get("judges") or []) if j.get("slug")]
except ImportError:
    slugs = re.findall(r"^\s*-\s*slug:\s*([\w-]+)", content, re.MULTILINE)
print("\n".join(slugs))
PY
)
fi

echo "  perspective skills (panel: $PANEL_NAME):"
while IFS= read -r j; do
  [ -z "$j" ] && continue
  found=""
  for cand in "$SKILL_DIR/../perspectives/$j-perspective" "$SKILL_DIR/../$j-perspective" "$HOME/.claude/skills/$j-perspective" "$HOME/skills/$j-perspective"; do
    [ -f "$cand/SKILL.md" ] && found="$cand" && break
  done
  if [ -n "$found" ]; then echo "    ✓ $j: $found"; else echo "    ✗ $j: missing"; fi
done <<< "$JUDGE_SLUGS"

echo "  research skill:"
for cand in "$SKILL_DIR/../research" "$HOME/.claude/skills/research" "$HOME/skills/research"; do
  [ -f "$cand/SKILL.md" ] && echo "    ✓ $cand" && break
done

echo -n "  WUYING_API_KEY: "; [ -n "$WUYING_API_KEY" ] && echo "✓ set" || echo "✗ unset (auto --quick)"
echo -n "  agent-browser on PATH: "; command -v agent-browser >/dev/null && echo "✓" || echo "✗"
```

WebSearch / WebFetch availability isn't checkable via shell — assume both
present unless a prior tool call returned a tool-unavailable error.

Mode auto-decision:
- All ✓ → full pipeline
- Panel file missing → ABORT, tell owner the resolved panel name + expected path
- Any perspective in the resolved panel missing → judges_incomplete flag, panel of N-of-M
- All perspectives in the resolved panel missing → auto `--no-judges`
- WUYING_API_KEY unset → auto `--quick`
- WebSearch+WebFetch unavailable → ABORT, tell owner what's needed

### Why these dependencies exist

This skill aggregates the work of a research team, not a single LLM call. The
external deps are genuine sub-agents, not bloat. If you want a single-prompt
brand summarizer, this isn't the right skill — try a single `/research <brand>`
or even a one-off WebSearch.

The ambition is real, the infra cost is real, and graceful degradation through
`--quick` / `--no-judges` / `--focus` flags lets the same SKILL.md still
produce useful output in subset environments.

## What you orchestrate

Five independent capabilities, used together:

1. **Open-web sub-agents** (parallel) — `WebSearch` + `WebFetch` per dimension
2. **Wuying cloud-browser sub-agent** — for sites that need a real browser session
   (Chinese sites with anti-bot, JS-heavy SPAs, X/RedNote/Bilibili search results, login walls)
3. **`research` skill** (resolved via `${RESEARCH_SKILL}`) — reused as the search building block
   when a dimension warrants its own deep-research pass
4. **5 perspective skills as judges** — `fusheng-perspective`, `jobs-perspective`,
   `likejia-perspective`, `wu-jundong-perspective`, `zhang-yiming-perspective` —
   each scores the brand IN CHARACTER on independent criteria
5. **Lead synthesis & merge** — only Lead can produce cross-dimensional and cross-judge insights

## Parameters

- `$ARGUMENTS` — brand name (e.g. `OpenClaw`, `Aibrary`, `BotLearn`, or a URL)
- `--dry-run` — **preview the resolved plan and stop, without running any research / judges / LLM calls** (spends nothing). Prints the resolved panel (and how it resolved), judge roster + perspective availability, auto-engaged flags (`--quick` if no `WUYING_API_KEY`, `--no-judges` if all perspectives missing), self-conflict `--panel-drop` suggestions, the phases that would run, and the rough sub-agent count. Implemented by `python3 scripts/resolve_plan.py <brand> [flags]` (add `--json` for machine output) — Phase 0 routing without Phase 1+. Use it to sanity-check panel/flags/cost before a real run.
- `--quick` — skip Wuying cloud-browser leg (web search only)
- `--refresh` — force EVOLUTION mode even if last report is recent
- `--watch` — **Brand Watch single scan, no audit**(docs/15 PRD · docs/16 §6 SOP)。Runs no judges
  and produces no report. Instead: ① read `watch/matrix.yaml` for the brand's enabled dimensions
  (W1-W9; brand must be in the published whitelist); ② WebSearch/curl per enabled dimension for new
  **sourced** events — admission bar: URL-embedded date or curl-verified original; quotes verbatim
  (`quote_type: title|body`); aggregator hits are leads only, trace to the statutory notice before
  recording; ③ append events to `watch/<brand-slug>/events.yaml`(id `<date>-<slug>-NNN`, judgment
  fields marked `model-judged`); ④ run `python3 scripts/watch-tools/validate_watch.py` — must pass;
  ⑤ evaluate the trigger rule via `python3 scripts/watch-tools/evaluate_triggers.py --brand <slug>`:
  rolling 30-day window, `P0 ≥ 1` or `P1 ≥ 3` or weighted count (P0=4, P1=2, P2=0.5) ≥ 6 → print an
  EVOLUTION recommendation. Watch events **never change scores** — scores only come from a judged
  re-audit (docs/15 §5.3 boundary).
- `--no-judges` — produce only the synthesis (skip the judge panel)
- `--focus <dim1,dim2>` — restrict deep research to specific dimensions
- `--panel <name>` — use a named panel from `${PANELS_DIR}/<name>.yaml` (highest precedence; overrides any prior brand binding). First-time runs write this to `reports/<brand-slug>/panel.yaml` and the brand stays bound until you pass `--panel` again. Field schema in `panels/README.md`.
- `--industry <name>` — pick a panel via the `panels/industries.yaml` industry→panel mapping (e.g. `--industry auto` resolves to `auto.yaml`). Lower priority than `--panel` but higher than the brand's existing binding. Same stickiness as `--panel`: first-time use writes the resolved panel into the brand's `panel.yaml`. Pass an industry not in the mapping → Phase 0 ABORT with the list of legal industries.
- `--panel-add <slug>` — runtime-only addition of one judge (slug must resolve under `${PERSPECTIVES_PATH}`). Stored in `panel.yaml.overrides.add` for this run; does NOT mutate `panels/<name>.yaml`. Repeatable.
- `--panel-drop <slug>` — runtime-only exclusion of one judge. Stored in `panel.yaml.overrides.drop`; does NOT mutate `panels/<name>.yaml`. Repeatable.
- `--dry-run` — preview the audit plan without executing it. Runs Phase 0 fully (path resolution, panel resolution, FRESH/EVOLUTION detection), then prints the plan and stops. No network requests, no file writes, no sub-agents. Combine with any other flags to preview their effect (e.g. `/mba 小米 --industry auto --dry-run`).
- `--panel-merge` — cross-panel comparison mode. Requires an existing report (FRESH brand → ABORT with guidance). Bypasses the panel-change GATE (the intent is explicit: compare two judge lineups). Runs the full pipeline with the new panel, then writes a v{n+1} report that includes both the old panel's scores AND the new panel's scores side-by-side in `## Panel Comparison`. Use alongside `--panel` or `--industry` to specify the second panel. Example: `/mba 某品牌 --panel vc-en --panel-merge` (compares current default-panel scores with vc-en scores).

## Output layout

All reports live under `${REPORTS_DIR}/<brand-slug>/`:

```
reports/<brand-slug>/
├── report.md                 # current canonical report (markdown, overwritten on merge)
├── report.html               # current canonical report (self-contained HTML, Mermaid + Chart.js)
├── panel.yaml                # which panel this brand is bound to (written by Phase 0 on FRESH)
├── versions/
│   ├── v1_2026-05-09.md      # immutable markdown snapshot per evolution cycle
│   ├── v1_2026-05-09.html    # immutable HTML snapshot
│   └── v2_2026-06-12.md
├── _raw/
│   ├── synthesis.md          # Lead's pre-judge synthesis (Phase 3 output)
│   ├── dimension_<n>_<slug>.md   # per-dimension sub-agent output
│   └── wuying_browse.md      # cloud-browser observation log
└── reviews/
    ├── <judge-slug>.md       # one scorecard per judge in the resolved panel
    └── ...                   # default panel = 5 files (fusheng/jobs/likejia/wu-jundong/zhang-yiming)
```

## Phase 0 — Router (FIRST STEP, ALWAYS)

Phase 0 has four sub-steps. Run them in order; do NOT skip ahead.

### 0.1  Resolve paths

Resolve `${SKILL_DIR}`, `${REPORTS_DIR}`, `${PANELS_DIR}`, `${PERSPECTIVES_PATH}`,
`${IMAGES_DIR}` (see "Path resolution" above). Do this once and reuse.

### 0.2  Resolve which panel to use (four-tier precedence)

This decision is independent of FRESH vs EVOLUTION — both need a panel before
any judge-related work. Order, first hit wins:

1. **CLI `--panel <name>`** — explicit panel name
2. **CLI `--industry <name>`** — look up in `${PANELS_DIR}/industries.yaml`,
   resolves to a panel name. Validation is **lazy** — failure modes:
   - Industry not in the mapping → ABORT with "industry '<name>' not registered.
     Known industries: <list>. Add a mapping line to industries.yaml or pass --panel directly."
   - Industry mapped but panel file missing → ABORT with "industry '<name>' is
     mapped to panel '<panel>' but ${PANELS_DIR}/<panel>.yaml doesn't exist —
     build the panel first (see panels/README.md §3)." This case happens because
     industries.yaml lists the roadmap of intended industries; the corresponding
     panel files may not exist yet.
   - In neither case do we silently fall back to default.
3. **Brand binding**: `${REPORTS_DIR}/<brand-slug>/panel.yaml` → `panel:` field, if file exists
4. **Default**: `default`

Once you have a panel name, load `${PANELS_DIR}/<panel-name>.yaml`. Parse it
(tolerant of missing pyyaml, same regex fallback as the self-bootstrap snippet):

```bash
PANEL_FILE="$PANELS_DIR/$PANEL_NAME.yaml"
if [ ! -f "$PANEL_FILE" ]; then
  echo "ABORT: panel '$PANEL_NAME' not found at $PANEL_FILE"
  echo "       Available: $(ls "$PANELS_DIR"/*.yaml 2>/dev/null | xargs -n1 basename | sed 's/.yaml//' | grep -v industries | tr '\n' ' ')"
  exit 1
fi
```

**Do NOT silently fall back to default** if `--panel <name>` or `--industry <name>`
was explicit and missing — that masks typos. Tell the user and abort.

**Skeleton panel branch**: after loading, if the panel yaml has top-level
`status: skeleton`, print:

> Panel '{panel-name}' is a skeleton — judges {comma-list of slugs} have no
> perspective skill yet. Pipeline will auto-engage `--no-judges` for this run
> (synthesis only, no scorecards). To build the judges, see
> `panels/README.md` §3.

Then continue — skeleton panels are intentionally usable for the synthesis-only
pass (still a useful brand scout). Phase 4 will detect all judges MISSING via
the standard probe and skip itself.

Apply runtime `--panel-add` / `--panel-drop` overrides on top of the loaded panel.
These overrides apply for this run only — they go into `panel.yaml.overrides`,
they do NOT mutate `panels/<name>.yaml`.

Run the self-bootstrap check (see "Self-bootstrap check" above) against the
resolved panel's judge slugs to detect missing perspective skills early. The
router exports the resolved panel via `MBA_PANEL_OVERRIDE=<name>` before
calling self-bootstrap so the probe sees the same panel.

### 0.3  FRESH vs EVOLUTION

```bash
# Default: local probe
test -f "${REPORTS_DIR}/<brand-slug>/report.md" && echo EXISTS || echo MISSING
```

```bash
# Cross-machine variant (only if the canonical reports live on a different host
# you control — see Path Resolution sidebar)
ssh <user>@<host> "test -f '<remote-reports-dir>/<brand-slug>/report.md' && echo EXISTS || echo MISSING"
```

- **If `report.md` exists AND user did not pass `--refresh`**:
  - Read the existing report
  - Note the existing version number, last-update date, and dimension list
  - Switch to **EVOLUTION mode** (Phase 1E onward)
  - Tell the user: `"Found existing v{n} dated {date}, bound to panel '{panel-name}'. Switching to EVOLUTION mode — delta research + re-score only what's changed. Use --refresh for a full rebuild."`
- **If `report.md` does NOT exist OR `--refresh` was passed**:
  - If `--panel-merge` was ALSO passed → ABORT immediately:
    > `--panel-merge` requires an existing report to compare against, but no report.md
    > found for '{brand}'. Run a full audit first (`/mba {brand}`), then come back
    > with `--panel-merge` to compare a second panel's perspective.
  - Otherwise → Switch to **FRESH mode** (Phase 1F onward)
  - Tell the user: `"No prior report for {brand}. Running fresh pipeline with panel '{panel-name}' ({N} judges): discovery → parallel search → synthesis → judge panel → merge. Estimated 15-25 minutes."`

A `--refresh` rebuild also archives the current `report.md` into `versions/` before starting.

### 0.4  Panel-change GATE (EVOLUTION only)

**Legacy brands** — if EVOLUTION mode AND `${REPORTS_DIR}/<brand-slug>/panel.yaml`
is missing (brand was audited before the panel system landed), SKIP this gate.
0.5 will write the panel.yaml with the resolved panel name on this run.
Note in the user-facing status: `"Legacy brand — migrating to panel system, binding {brand} to '{panel-name}'."`

**`--panel-merge` bypass**: if `--panel-merge` was passed, skip this entire gate —
the panel difference is intentional. Proceed directly; Phase 5M will handle the comparison.

If we're in EVOLUTION mode AND `panel.yaml` exists AND the resolved panel (`PANEL_NAME` from 0.2) differs
from the panel recorded there AND `--panel-merge` was NOT passed, STOP. Tell the user verbatim:

> Panel change detected for {brand}: v{n} was scored by **{old-panel}** ({old-slugs}),
> this run wants **{new-panel}** ({new-slugs}).
> Old `reviews/*.md` are NOT directly diffable against new scores — every judge will
> re-score from scratch, and v{n+1}'s score matrix will not be comparable to v{n}'s
> on a cell-by-cell basis.
>
> Reply `yes` to proceed (writes new panel binding into `panel.yaml`, v{n+1} carries
> the new panel name in its header), or rerun with `--panel {old-panel}` to keep
> continuity.

This gate exists to prevent silent panel drift across versions. Do NOT auto-proceed.

### 0.5  --dry-run exit (if flag present)

If `--dry-run` was passed, print the following plan block and **stop immediately**.
Do NOT proceed to 0.6 or any later Phase. No files written, no network calls made.

```
### MBA Dry-Run Plan — {Brand}

Mode:          {FRESH (no prior report) | EVOLUTION (v{n} found, dated {date})}
Panel:         {panel-name} ({N} judges)
Judges:        {slug1} ({display_name}) ✓ | {slug2} ✗ missing ...
Wuying leg:    {YES | NO (--quick)}
Dimensions:    {1-7 default | restricted to {dims} via --focus}
Output path:   {REPORTS_DIR}/{brand-slug}/

Flags active:  {list all flags that were passed}

— No files written. No network requests made. —
Re-run without --dry-run to execute the full pipeline (~20 min).
```

Judge status symbols: ✓ = perspective skill found at `${PERSPECTIVES_PATH}`; ✗ = missing
(run will degrade to N-of-M or auto --no-judges). Use the standard panel probe from the
self-bootstrap check to determine each judge's status.

### 0.6  Write / update `panel.yaml`

On **FRESH** mode: at the start of Phase 1F (after user passes GATE 1 confirming the
PRD), create `${REPORTS_DIR}/<brand-slug>/panel.yaml`:

```yaml
# Generated by Phase 0 router on FRESH mode
panel: <panel-name>            # which panels/<name>.yaml was used
locked_at: YYYY-MM-DD          # today
mba_version: 0.6.0             # from this SKILL.md's frontmatter (keep in sync with the `version:` field above)
overrides:
  add: []                      # populated from --panel-add (slugs only)
  drop: []                     # populated from --panel-drop (slugs only)
```

On **EVOLUTION** mode + `panel.yaml` missing (legacy brand from before the panel
system): create it with the resolved `PANEL_NAME` and `locked_at: today`. This is
the one-time migration; subsequent evolutions go through the normal gate logic.

On **EVOLUTION** mode + user confirmed the 0.4 panel-change gate: rewrite
`panel.yaml` with the new panel name, set `locked_at` to today, refresh `mba_version`.
Do NOT delete the file — the brand keeps a binding at all times.

On EVOLUTION mode + same panel as before: leave `panel.yaml` untouched.

## Phase 1F — Discovery (FRESH mode, Lead, sequential)

Draft a Brand Influence PRD. Output it to the user and wait for confirmation.

```
### Brand Influence Research Proposal — {Brand}

**Subject:** {Brand name + 1-line positioning, if known}

**Research Objective:** Map how {Brand}'s influence is constructed and compounded —
which levers do the work, which are decorative, where the leverage is fragile.

**Default Dimensions (7 core + 2 advanced; Lead typically picks 5-8 per brand):**

Core 1-7 below cover most brands. See `references/dimensions.md` for the advanced
dimensions 8-9 and the per-dimension agent-prompt templates. Filename convention for
sub-agent outputs: `dimension_{n}_{slug}.md` where `1 ≤ n ≤ 9`.

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

**Judge panel:** {panel-name} — {judge slugs from the resolved panel, after overrides}.
Each available judge will score the brand in character on 5 lenses (see Phase 4).
If the resolved panel is `status: skeleton`, note that the run will auto-engage
`--no-judges` and produce a synthesis-only report.

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

    Save your report to: ${REPORTS_DIR}/{brand-slug}/_raw/dimension_{n}_{slug}.md
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

    Step 1 — Spin up a session. The session-launcher script ships in the repo at
    ${SKILL_DIR}/../scripts/wuying/open.py (John's layout) or wherever the host has installed it.
    Run locally:
      python3 \"${SKILL_DIR}/../scripts/wuying/open.py\"
    Cross-machine fallback (only if the Wuying credentials live on a different host you control):
      ssh <user>@<host> 'cd <wuying-script-dir> && python3 scripts/wuying/open.py'
    Either way, capture SESSION_ID and RESOURCE_URL from the output. If the script is not
    found AND no cross-machine host is configured, abort the Wuying leg and proceed in
    --quick mode (auto-degrade per the Prerequisites table).

    Step 2 — Drive the session with `agent-browser` (its own SKILL.md describes the command
    surface; load it via the standard skill resolver). Run locally if `agent-browser` is on
    PATH; otherwise fall back to the cross-machine SSH variant only if you confirmed step 1
    ran on the same remote host.

    Step 3 — Investigate (in this priority order):
      a) X / Twitter search for `{Brand}` and the founder handle — capture top-10 latest posts
      b) RedNote (小红书) search for `{Brand}` — top 10 posts + engagement counts
      c) Bilibili search for `{Brand}` — top 5 videos by views + comment tone
      d) Chinese tech press (36kr / 虎嗅 / 钛媒体) — most recent 3 articles
      e) The brand's own site / app store listings (screenshot the hero + the comments)

    Step 4 — Save observations to:
      ${REPORTS_DIR}/{brand-slug}/_raw/wuying_browse.md

    Step 5 — Tear down the session when done (the scripts/wuying/open.py output prints the delete cmd).

    Output sections:
    - ## Platform-by-platform findings (X / RedNote / Bilibili / press / own channels)
    - ## Visual evidence — note screenshots taken (paths)
    - ## Surprises — anything that contradicts open-web findings
    - ## Session metadata — SESSION_ID, RESOURCE_URL, teardown status
  "
)
```

**Concurrency rules** (inherited from `${RESEARCH_SKILL}`):
- Up to 5 agents per batch
- If 7 dimensions + 1 cloud browser = 8 agents, run in two batches (5 + 3)
- Each runs in background; collect as they return

**Circuit breaker**: if any agent hasn't returned after 5 min, proceed with what's available
and note the gap.

## Phase 3F — Lead Synthesis (FRESH mode)

After all sub-agents return, Lead reads every dimension file and the wuying log, then writes:

`${REPORTS_DIR}/{brand-slug}/_raw/synthesis.md`

Sections:
- **Executive synthesis** (5 bullets): how influence is being constructed
- **The leverage map**: which dimension is doing real work vs decorative
- **The fragile edges**: where the brand depends on one channel / one person / one narrative
- **Cross-dimension contradictions**: where dimension N's findings clash with dimension M
- **Open questions**: what we couldn't determine and why
- **Citations index**: dedupe + group all source URLs

This synthesis is the input to the judge panel — it must be self-contained.

## Phase 4F — N-Judge Review Panel (panel-driven)

Read the resolved panel (Phase 0.2) and build the judge list:

```python
# Pseudocode — actual loader is in the self-bootstrap snippet
panel = load_yaml(f"{PANELS_DIR}/{PANEL_NAME}.yaml")
judges = panel["judges"]                          # list of judge dicts
judges += [resolve(s) for s in overrides.add]     # --panel-add appends
judges = [j for j in judges if j["slug"] not in overrides.drop]  # --panel-drop excludes
# Drop any judge whose perspective SKILL.md isn't reachable (mark MISSING, don't fabricate)
judges = [j for j in judges if perspective_found(j["slug"])]
```

Dispatch the surviving N judges in parallel. Each judge **loads their own perspective
skill** so they reply in character. They score independently — do NOT share each
other's drafts.

For each `judge` in the resolved list, dispatch:

```
Agent(
  subagent_type: "general-purpose",
  description: "Judge — {judge.display_name_cn or judge.slug}",
  run_in_background: true,
  prompt: "
    You are about to review brand {Brand}'s influence as judge {judge.display_name_cn}.
    To stay in character, FIRST locate and load the perspective skill SKILL.md by probing
    ${PERSPECTIVES_PATH} for `{judge.slug}-perspective/SKILL.md` (use the first hit) and
    read the full file. From this point on, respond AS the persona — first-person voice,
    their vocabulary, their decision style. (Re-read the persona's 'do not impersonate /
    do not fabricate' constraints — they apply here too.)

    Respond in {judge.language} (zh = 中文, en = English) — this comes from the panel
    yaml, not from the brand's language. A Chinese brand still gets an English Jobs
    review; Lead translates inside the final report's quoted sections.

    The Lead has prepared the brand synthesis at:
    ${REPORTS_DIR}/{brand-slug}/_raw/synthesis.md
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
    ${REPORTS_DIR}/{brand-slug}/reviews/{judge.slug}.md

    Do NOT read other judges' files. Score independently.
    Stay in character throughout. The persona's anti-fabrication rules apply: no inventing
    numbers, no pretending you privately met the founder unless that's documented.
  "
)
```

Resolver:
- `{judge.slug}` → `<probe>/<slug>-perspective/SKILL.md` (first hit across `${PERSPECTIVES_PATH}`)
- `{judge.display_name_cn}` / `{judge.display_name_en}` / `{judge.language}` / `{judge.portrait}` /
  `{judge.weight}` all come from the panel yaml row; missing fields use the defaults documented
  in `panels/README.md` §2

If a judge's SKILL.md isn't found in any `${PERSPECTIVES_PATH}` entry, mark that judge
`MISSING` in the panel summary and proceed N-of-M (per the Prerequisites degradation rules
above). Do NOT fabricate the persona from training-data memory.

**Batching**: up to 5 agents per batch (Anthropic agent ceiling). For N > 5 judges, run
⌈N/5⌉ batches — collect each batch's results before starting the next. The default panel's
5 judges fit in a single batch.

**Output line for Phase 5 score matrix**: emit one column per surviving judge, in panel-yaml
order. Missing judges get a `—` column with a footnote `MISSING: {slug}` rather than being
silently dropped — readers should see the panel size that ran.

## Phase 5F — Lead Merge (FRESH mode)

Lead reads all 5 review files + the synthesis, then writes the canonical
`${REPORTS_DIR}/{brand-slug}/report.md`. Use this template:

```markdown
# {Brand} — Brand Influence Review (v1)

**Date:** {YYYY-MM-DD}
**Mode:** FRESH
**Panel:** {panel-name} ({N} judges)
**Dimensions analyzed:** {list}
**Judges:** {comma-join of judge.display_name_cn (zh) or display_name_en (en) from panel, in panel-yaml order}

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

## Legal, IP & Disclaimer
{Mandatory notice block. Include all bullets below, adapted to the brand and sources:
- Public-source basis: state that the report only cites and analyzes publicly accessible
  sources such as official pages, public filings, news, industry media, social/public web
  posts, product pages, public complaint samples, MBA method docs, or GitHub/source docs.
  State that no private company files, trade secrets, internal documents, or unauthorized
  databases were used.
- Trademark and brand ownership: state that brand names, product names, model names,
  logos, marks, trade dress, and other identifiers belong to their lawful owners, and are
  referenced only for identification, commentary, research, and explanation.
- Relationship disclaimer: state that MBA / the report author is not sponsored, authorized,
  endorsed by, affiliated with, partnered with, or acting as agent for the reviewed brand
  unless the user explicitly provided such a relationship.
- Image and copyright handling: if the report uses images/screenshots/product visuals,
  name the public source beside the image section and state that copyright and related
  rights remain with the original photographer, platform, publisher, brand, or lawful
  rights holder. Do not claim ownership of third-party visuals. If no images are used,
  say no third-party visuals are reproduced in this report.
- IP boundary: state that MBA's original analytical text, score synthesis, and framing are
  research expression; third-party facts, marks, names, images, headlines, quotes, and
  viewpoints remain owned by their respective sources or rights holders.
- Non-advice: state that the report is brand-influence research / method demonstration,
  not investment advice, financing advice, procurement advice, legal advice, audit opinion,
  product-quality certification, or commercial due-diligence conclusion.
- Accuracy limits: state the data limits of this run (for example open-web only, no Wuying,
  no internal financials, no sales invoices, no owner sample, no after-sales tickets, no
  fleet dashboard), and tell readers to verify first-party materials before business,
  investment, procurement, or legal decisions.}

## Citations
{Dedupe-merged from all dimension files.}

## Versions
- v1 — {YYYY-MM-DD} — initial review
```

Also write a frozen snapshot to `versions/v1_<date>.md` (identical content, immutable).

### Phase 5F.b — HTML report (REQUIRED, after the markdown is written)

Markdown is the source of truth; HTML is the presentation layer for humans. After
`report.md` is final, render `report.html` from `references/html-report-template.md`.

The HTML must be **a single self-contained file** (only Chart.js — plus Mermaid in EVOLUTION
mode — load from a CDN; no local deps). `references/html-report-template.md` is the **canonical
scaffold** — copy it and fill the `{{...}}` slots. The list below is what a report actually
contains, required vs situational; where anything here disagrees with the template, the template wins.

**Required — every report:**

1. **Masthead** — the five-lens radar-logo lockup (copied verbatim from the template) + a
   `panel-badge`; then `<h1>` brand, an English identity line, a meta line (MBA version · date ·
   panel · N judges), the TL;DR, and a **score-hero** (big total `/max` + normalized `/10`).
2. **Score radar** (Chart.js `radar`, inside a fixed-height `.chart-wrap`, `maintainAspectRatio:false`)
   — 5 lenses on the spokes; either the panel mean as one polygon, or one polygon per judge.
3. **Judge totals bar** (Chart.js horizontal `bar`, in `.chart-wrap`) — total /50 per judge.
4. **Score matrix table** — lenses × judges, each score cell heat-shaded via `heat-1..heat-8`,
   plus a mean column and a totals row. EVOLUTION: cells become `7 → 8` with `up` / `down` / `flat`.
5. **Judge scorecards** — a `.judge-card` grid (not collapsible): name, role line, total /50, and an
   in-character first-person verdict. Mark a self-conflicted judge with `△` + the `competitor`
   class; optionally add `highest` on the top scorer.
6. **Verdict** — 2–3 paragraphs in the Lead's voice.
7. **Brand Actions (90 days)** — a numbered action list.
8. **Legal, IP & Disclaimer + Sources** — a visible section (not hidden only in the footer) covering
   public-source basis, trademark/brand ownership, judge-simulation notice, no
   affiliation/endorsement, non-advice, and accuracy limits; then **Sources** as real, publicly
   reachable URLs (anti-fabrication — never invent a link).

**Situational — add when the material warrants (several reports do):** a **dissent view** (a colored
heatmap / range-bar strip, or an insight/quote block on the single biggest judge disagreement); a
**compare table** vs MBA history; record / conflict callout boxes.

**EVOLUTION mode (v2+) only:** a **delta banner** under the meta line, delta score cells, a "what
changed since v{n-1}" section, and a **Mermaid `gitGraph`** version timeline (add the Mermaid ESM
import only when the gitGraph is actually used).

**Judge imagery:** reports currently ship **no** judge portraits — text scorecards only. If one is
ever added, use a **stylized illustration** from `assets/judges/`, **never a real photograph** of the
person (likeness-rights exposure); an emoji / monogram fallback is fine.

**Style:** paper `#faf8f3` + accent `#c1440e`, serif body, centered, max-width ~820px, generous
line-height. **No dark-mode block, no external fonts.** Every canvas lives in a fixed-height
`.chart-wrap` to prevent the Chart.js infinite-growth bug.

Copy the scaffold, fill the `{{...}}` slots, and write the result to `report.html` and
`versions/v1_<date>.html`.

**Sanity-check before finalizing:**
- Open the file (`python3 -m http.server`, or run `node scripts/qa_report_render.mjs`) — expect no `console.error`.
- The masthead is the **five-lens radar-logo lockup** (copied verbatim) + favicon; theme is paper `#faf8f3` / accent `#c1440e`, no dark-mode block.
- Chart.js canvases populate (no empty squares) and each sits in a fixed-height `.chart-wrap` with `maintainAspectRatio:false` (avoids the infinite-growth bug).
- The Legal/IP/Disclaimer section exists in both `report.md` and `report.html`, appears with/before Sources, and does not imply affiliation, permission, or ownership of third-party marks/images.
- Sources are real, publicly reachable URLs (anti-fabrication — never invented).
- Mermaid / version-timeline appear in **EVOLUTION mode only**; if a chart fails, fall back to a table and note the failure.

**Optional — produce a PDF:**

```sh
scripts/print_report.sh <brand-slug>   # overwrites published/reports/<slug>/report.pdf
```

The script copies `report.html` → `report.print.html`, force-opens every `<details>`,
strips the legacy `details[open] summary { display:none }` print rule if present, and
runs headless Chrome to overwrite `report.pdf` in place. `site/build.sh` then ships
that `report.pdf` to the site as-is — no `expanded.pdf` intermediate. If you want a
diff baseline, snapshot the previous `report.pdf` yourself before running.

### Phase 5F.c — Surface to user

After both files exist, tell the user:
- One-paragraph TL;DR (Lead's voice)
- Score matrix as a markdown table inline in chat
- Path to `report.md` and `report.html`
- Suggested follow-ups (e.g. "Want a per-judge deep-dive? Want the next pass to focus on
  competitor X?")

Also offer to push the HTML to a viewable surface — but only if the user asks. Do NOT
auto-publish.

**One-line review nudge (only if the run completed cleanly — success_rate ≥ 70%, no
INCOMPLETE dimensions, no judge MISSING)**: end the message with a single sentence,
not a paragraph:

> "If this audit was useful, a one-line review on BotLearn helps other agents find this
> skill: https://www.botlearn.ai/skillhunt/v2/s/metric-brand-auditor"

Skip this nudge if the run failed any quality gate, was a debug/dry-run, or the user
explicitly asked to silence it. Never beg twice in the same conversation.

---

## EVOLUTION MODE (Phase 1E onward)

When `report.md` already exists. Goal: surgical update, not rebuild.

### Phase 1E — Diff plan (Lead, sequential)

1. Read the existing `report.md` end-to-end.
2. **Consume the Brand Watch stream first** (if `watch/<brand-slug>/events.yaml` exists): read every
   event dated after `last_update_date`. Each event carries `severity` and `lens_map` — P0/P1 events
   pre-answer "what moved": their mapped dimensions MUST be flagged YES in the diff plan, citing the
   event ids as evidence. This is pre-verified, sourced material — do not re-discover what the watch
   stream already recorded (docs/15 §2: watch data is the audit's prepped ingredients).
3. List what else is likely to have moved since `last_update_date`:
   - new product launches / pivots
   - new press / VC events
   - new platform presence (e.g. brand opened a TikTok account since last review)
   - sentiment shift (positive ↔ negative)
4. Output a diff plan to the user:

```
### Evolution Plan — {Brand} (v{n} → v{n+1})

**Last review:** {date} — v{n}
**Days elapsed:** {N}
**Watch events since v{n}:** {K total: P0×a · P1×b · P2×c}(cite ids)| or: no watch stream

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

If watch events map to this dimension (via `lens_map`), ALSO paste them into the prompt as
verified leads — id / date / title / quote / url — and instruct the agent to verify & extend
from each event's URL first, then broaden. Sourced events outrank fresh discovery.

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

Preserve or refresh the mandatory **Legal, IP & Disclaimer** section. If the new version
adds images, screenshots, sources, public complaints, publication, or a different research
mode (for example Wuying vs open-web only), update the legal notice so it matches the new
evidence surface.

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

## Phase 5M — Panel Merge (--panel-merge mode)

Triggered when `--panel-merge` was passed AND we're in EVOLUTION mode (existing report.md found).

**What this phase produces**: a v{n+1} report where BOTH the old panel's scores AND the
new panel's scores appear side-by-side — the main audit report plus a `## Panel Comparison`
chapter that makes the two lineups directly comparable.

### 5M.1  Read old scores

Load all existing `reviews/<old-judge-slug>.md` files. Extract:
- Old panel name (from `panel.yaml`)
- Old judge display names, scores per lens (5 rows), totals

### 5M.2  Run new panel through Phases 2-4

Run the new panel through the standard pipeline:
- **Phase 2**: Reuse existing `_raw/dimension_*.md` files if they're recent (< 30 days)
  and the user did not pass `--refresh`. Skip re-research if reusable.
  If `--quick` was passed or Wuying unavailable, keep the existing Wuying observations.
- **Phase 3**: Re-run synthesis if research was refreshed; otherwise reuse `_raw/synthesis.md`.
- **Phase 4**: Run new panel judges (all of them) against the synthesis. Write to
  `reviews/<new-judge-slug>.md` files. DO NOT overwrite old-panel reviews — old panel
  reviews are preserved as `reviews/<old-judge-slug>.md`.

### 5M.3  Write the Panel Comparison report

Archive current `report.md` → `versions/v{n}_<orig_date>.md` as usual.

Write new `report.md` using this template extension (add `## Panel Comparison` before
`## Citations`):

```markdown
# {Brand} — Brand Influence Review (v{n+1})

**Date:** {YYYY-MM-DD}
**Mode:** PANEL-MERGE
**Panels compared:** {old-panel-name} (v{n}) → {new-panel-name} (v{n+1})
**Dimensions analyzed:** {list}

## TL;DR — Panel Comparison Summary
{3-4 bullets: where do the two panels agree? where do they sharply diverge?
Name the exact lenses and the direction of divergence.}

## Score Matrix — {new-panel-name} (v{n+1})
{Standard 5-lens matrix for the new judges — identical format to Phase 5F}

## Score Matrix — {old-panel-name} (v{n}, reference)
{The OLD panel's scores, clearly labeled as reference. Use the scores from step 5M.1.}

## Panel Comparison
{This is the unique output of --panel-merge. Structure:}

### Side-by-Side Score Deltas

| Lens              | {old-panel} mean | {new-panel} mean | Δ | Direction |
|-------------------|-----------------|-----------------|---|-----------|
| Origin authenticity  | {old-mean}   | {new-mean}      | {Δ} | ↑/↓/= |
| Category coinage     | ...            | ...             | ... | ...    |
| Leverage quality     | ...            | ...             | ... | ...    |
| Identity coherence   | ...            | ...             | ... | ...    |
| Real-world signal    | ...            | ...             | ... | ...    |
| **Total /50**        | **{old-total}**| **{new-total}** | **{Δ}** | |

### Where the panels agree
{Lenses where both panels' means are within 1.0 of each other. These are
stable signals — the brand's performance on these dimensions holds up across
different judge perspectives.}

### Where the panels diverge
{Lenses where |Δ| ≥ 1.5. For each diverging lens:
- Name the lens and the delta direction
- Quote one judge from each panel whose reasoning best explains the gap
- Offer Lead's interpretation: is this a genuine lens disagreement, or does it
  reflect a domain bias (e.g., VC judges weight origin story more than auto judges)?}

### Panel lens fingerprints
{Each panel has a characteristic "fingerprint" — lenses it consistently scores
high or low relative to the other panel. Describe each panel's fingerprint in
one sentence and what it reveals about that panel's implicit brand priorities.}

### Cross-panel verdict
{1-2 sentences: what does a brand score ROBUSTLY across both panels? What are
the brand's fragile edges that ONLY show up with one panel? The intersection of
both panels' critical findings is the hardest, most panel-independent signal.}

## Where the {new-panel-name} judges agree and disagree with each other
{Standard within-panel consensus/dissent — same as Phase 5F format}

## Action recommendations (next 90 days)
{Draw from both panels' insights. Flag which recommendations are panel-universal
vs. panel-specific (only one lineup's judges flagged this).}

## Legal, IP & Disclaimer
{Standard legal block — same as Phase 5F, adapted to include panel-merge context}

## Citations
{Dedupe-merged from all dimension files, same as Phase 5F}

## Versions
{Existing version history + new entry: `- v{n+1} — {date} — panel-merge: {old-panel} vs {new-panel}`}
```

### 5M.4  Write HTML report (REQUIRED)

Render `report.html` with these --panel-merge specific additions:

1. **Panel selector toggle** (pure HTML/CSS, no JS framework): two tabs/buttons labeled
   `{old-panel}` and `{new-panel}`. Default view shows both panels' radar charts overlaid
   on the same Chart.js canvas so the reader sees the "shape gap" at a glance.
2. **Delta heatmap** (new section): a 5×2 grid (5 lenses × 2 panels) where each cell is
   colored by score. This reveals which panel is harder/softer on which lens.
3. **Panel fingerprint bar chart** (Chart.js `bar`, grouped): one group per lens, two bars
   per group (old-panel mean vs new-panel mean). The visual "which bars are the same
   height" shows at-a-glance stability.
4. Standard sections: influence map, judge cards (now for BOTH panels — label old-panel
   cards with a "reference" badge), dissent heatmap within each panel.

Snapshot to `versions/v{n+1}_<date>_panel-merge.html`.

---

## Sub-command: `/mba list`

Just run:
```bash
ls -1 "${REPORTS_DIR}/" 2>/dev/null
```

Cross-machine variant (only if the canonical reports are on a different host):
```bash
ssh <user>@<host> 'ls -1 <remote-reports-dir>/ 2>/dev/null'
```

For each entry, show: brand-slug, version count, last-update date.

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
| Session wall time                            | > 15 min  | Auto-teardown via `scripts/wuying/open.py` cleanup path; log SESSION_ID + teardown status to `_raw/wuying_browse.md` |
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
- `${RESEARCH_SKILL}` — the upstream PRD-driven research skill (reused as building block)
