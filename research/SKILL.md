---
name: research
description: |
  Deep research with PRD methodology: Proposal → Baseline → Parallel Sub-Agent Team → Auto-Stitch → Lead Synthesis.
  Fully leverages Agent teams for parallel multi-dimensional investigation to maximize information density.
  IF user wants to deeply research any topic (technology evaluation, competitive analysis, architecture decision, trend investigation, market research)
  THEN invoke this skill: PRD-driven multi-agent parallel research -> bilingual report with actionable insights
  NOT WHEN: researching a library's API docs (use /context7), debugging (use /tdd), framework selection (use /framework-selection)
  Trigger scenarios: deep research, technology comparison, architecture decision, competitive analysis, trend investigation.
  Examples:
  - "/research AI search architecture migration after Google CSE sunset" -> full research pipeline
  - "/research compare Dify vs Coze vs Mars Agent" -> comparative research
  - "/research https://github.com/karpathy/autoresearch" -> GitHub project research
  - "/research livestream monetization trends 2026 --quick" -> skip comparison phase
---

# /research — PRD-Driven Deep Research Skill

You are a **Research Lead** orchestrating a multi-agent research team. Follow the PRD methodology (Proposal → Baseline → Task Breakdown → Parallel Execution → Synthesis) to maximize research depth and information density.

**Core Principle**: Break complex research into independent dimensions, dispatch parallel sub-agents for each, then synthesize findings with cross-cutting analysis. This produces higher information density than sequential single-agent research.

## Parameters

- `$ARGUMENTS`: Research topic, question, GitHub URL, or comparison request
- `--quick`: Skip Phase 3 community/ecosystem analysis
- `--no-compare`: Skip Mars Agent comparison
- `--focus {area}`: Narrow research to specific dimensions

## Token Efficiency: English-First, Translate-Last

All research phases (1-4) operate in **English only** to maximize research depth. Bilingual conversion happens in Phase 5 as part of the final report write — not as a separate pass.

## Phase Flow

```
Phase 1  Research Proposal (Lead, sequential)
  |      Parse input -> draft PRD (scope, core questions, dimensions)
  |      GATE 1: User confirms proposal
  v
Phase 2  Baseline + Task Breakdown (Lead, sequential)
  |      Current knowledge state -> evaluation criteria -> task decomposition
  |      GATE 2: User confirms task list before execution
  v
Phase 3  Parallel Execution (Agent Team, N concurrent agents)
  |      TeamCreate -> launch one Agent per dimension -> collect results
  v
Phase 4  Report Stitching + Lead Synthesis (Lead)
  |      Auto-stitch dimension findings -> executive summary -> cross-cutting analysis
  v
Phase 5  Bilingual Report Output (Lead)
         Write bilingual report to docs/E_references/
```

---

## Phase 1: Research Proposal

Execute as Lead. Parse the user's input and draft a structured PRD.

1. **Parse input**: Identify the research topic, decision context, and urgency
   - If GitHub URL: extract `owner/repo`, fetch README via `WebFetch`
   - If topic name: understand the decision space
   - If comparison: identify all candidates

2. **Draft PRD proposal**:

```
### Research Proposal

**Research Objective:** {One clear sentence — what decision or understanding this research enables}

**Context:** {Why this matters now — user's situation, constraints, timeline}

**Scope:**
- In scope: {Specific topics, technologies, dimensions to investigate}
- Out of scope: {What we explicitly will NOT cover}

**Core Questions:** (3-7, each maps to one research dimension)
1. {Independently answerable, maps to a dimension}
2. {Mix of factual and evaluative questions}
...

**Expected Deliverables:**
- {What the user receives — comparison matrix, recommendation, trend analysis, etc.}
- {Format hints — Mermaid diagrams, structured tables, pros/cons}

**Estimated Scope:** {N} dimensions, approximately {10-20} minutes
```

3. **GATE 1**: Present proposal and STOP. Wait for user confirmation. User may narrow scope, add dimensions, or redirect.

---

## Phase 2: Baseline + Task Breakdown

After user confirms the proposal, output Baseline AND Task List in ONE message.

### Baseline Section

```
### Current Knowledge Baseline

**Known State:** (what we already know from training data)
{Honest summary of existing knowledge. Flag stale or uncertain areas.}

**Evaluation Dimensions:**

| Dimension | Criteria | Measurement Method |
|-----------|----------|--------------------|
| {Maps to Core Question 1} | {What to evaluate} | {How to measure} |
| {Maps to Core Question 2} | {Criteria} | {Method} |
...
```

### Task Breakdown Section

Decompose into independent, non-overlapping tasks:
- **One task per logical dimension** — each maps to one Evaluation Dimension
- **No overlap** — each task's scope is explicitly bounded
- **Clear deliverable** — each specifies output format

```
### Research Tasks

| # | Task | Dimension | Scope | Deliverable |
|---|------|-----------|-------|-------------|
| T1 | {task} | {dimension} | {boundaries} | {output format} |
| T2 | {task} | {dimension} | {boundaries} | {output format} |
...

**Execution Plan:** Batch 1 (parallel): T1, T2, T3 | Batch 2 (parallel): T4, T5
```

**GATE 2**: Present and STOP. Say: "Confirmed? I'll launch {N} sub-agents in parallel." Do NOT proceed until user confirms.

---

## Phase 3: Parallel Execution

After user confirms, create a team and dispatch sub-agents.

### Step 1: Create Team

```
TeamCreate(team_name: "research-{topic-slug}")
```

### Step 2: Dispatch Agents in Parallel

Launch agents in a SINGLE message for maximum parallelism. Use `general-purpose` subagent_type.

**Per-dimension agent prompt template** (read `references/agent-prompts.md` for full template):

Each agent receives:
- The specific task description and scope boundaries
- The relevant Baseline dimension and evaluation criteria
- 2-3 pre-generated search queries (saves agent an LLM round-trip)
- Required output format with citation requirements
- Instruction: "Use WebSearch for discovery, then WebFetch on top 2-3 URLs for deep content extraction"
- **Visualization spec** from `references/agent-prompts.md` — the full `chart:xxx` format guide and Mermaid JSON format guide. Each agent MUST produce at least 1 data chart + 1 structure diagram

**Concurrency rules:**
- Launch up to 5 agents per batch (max parallel)
- If >5 dimensions, execute in batches: Batch 1 (T1-T5), wait, Batch 2 (T6+)
- Each agent runs in background (`run_in_background: true`) for parallel execution

**Example dispatch** (3 dimensions):

```
Agent(name: "T1-grounding-analysis", subagent_type: "general-purpose", model: "sonnet", run_in_background: true,
  prompt: "You are a research analyst producing a VISUAL REPORT. ...
  Research Task: {T1 description}\nCriteria: {from baseline}\nQueries: 1. ... 2. ...
  \n{Visualization Spec from references/agent-prompts.md}
  \nOutput MUST include: 1 chart:xxx data chart + 1 structure diagram + findings + data points")

Agent(name: "T2-api-comparison", subagent_type: "general-purpose", model: "sonnet", run_in_background: true,
  prompt: "You are a research analyst producing a VISUAL REPORT. ...
  Research Task: {T2 description}\nCriteria: {from baseline}\nQueries: 1. ... 2. ...
  \n{Visualization Spec from references/agent-prompts.md}
  \nOutput MUST include: 1 chart:xxx data chart + 1 structure diagram + findings + data points")

Agent(name: "T3-roadmap-analysis", subagent_type: "general-purpose", model: "sonnet", run_in_background: true,
  prompt: "You are a research analyst producing a VISUAL REPORT. ...
  Research Task: {T3 description}\nCriteria: {from baseline}\nQueries: 1. ... 2. ...
  \n{Visualization Spec from references/agent-prompts.md}
  \nOutput MUST include: 1 chart:xxx data chart + 1 structure diagram + findings + data points")
```

### Step 3: Collect Results

As each agent completes, note a 1-line summary. After all agents return:
- Cross-validate overlapping observations
- Flag contradictions or gaps
- If any agent returns empty/error, note the gap and proceed with partial results

**Circuit breaker**: If any agent hasn't returned after 3 minutes, proceed with available results.

---

## Phase 4: Report Stitching + Lead Synthesis

The Lead agent now performs two tasks:

### 4a: Auto-Stitch Dimension Findings

Combine all sub-agent results into a structured report body:
- One section per dimension (T1, T2, T3...)
- Preserve source citations (URLs)
- Normalize formatting across dimensions

### 4b: Lead Synthesis (the high-value part)

Write TWO synthesis sections that ONLY the Lead can produce (cross-dimensional insight):

**Executive Summary:**
- 3-5 key findings that directly answer the Core Questions from Phase 1
- Clear recommendation or decision framework
- Overview `chart:radar` comparing all candidates across dimensions (or `chart:bar` for ranking)
- Architecture/positioning diagram: Mermaid `quadrantChart` or JSON `flowchart`

**Cross-Cutting Analysis:**
- `chart:line` trend visualization if time-series data is available across dimensions
- Contradictions found across dimensions (Agent A says X, Agent B says Y)
- Information gaps — what could NOT be determined and why
- Confidence assessment per dimension (high/medium/low) — visualize as `chart:bar` with confidence percentages
- Actionable recommendation directly answering the Research Objective

---

## Phase 5: Bilingual Report Output

### 5a: Write Report

1. Find next sequence number: `ls docs/E_references/ | tail -1` -> extract number + 1
2. Create folder: `docs/E_references/{nn}_{topic_slug}_research/`
3. Write `research_report.md` using `references/report-template.md` as structure

**Bilingual rules** (applied inline during write, NOT as a separate pass):
- Section headers: `## English Title / 中文标题`
- Paragraphs: English first, then `> **中文**：` blockquote
- Tables: English primary, Chinese annotations in cells where helpful
- Code/URLs/technical terms: Keep in English
- Technical terms first occurrence: **middleware** (中间件)
- Key Vocabulary section at end: 15-20 terms with Chinese translations

### 5b: Persist to Research Wiki

After writing the report file, call `curate_research_wiki` to merge findings into the persistent wiki:

```python
from memory.research_wiki import curate_research_wiki, should_curate_research

# topic_slug: derived from the folder name, e.g. "01_ai_search_migration"
report_path = f"docs/E_references/{folder_name}/research_report.md"
if await should_curate_research(user_id, report_path):
    await curate_research_wiki(user_id, report_content, topic_slug)
```

The wiki is stored at `research/wiki.md` (per-user GCS). Failures are non-blocking — log and continue.

### 5c: Present Executive Summary

Show the user:
1. Top 3 actionable insights (bilingual)
2. Link to the full report file
3. Suggested follow-up questions

---

## Prohibited Actions

- Do NOT proceed past a GATE without user confirmation
- Do NOT fabricate metrics — if unavailable, state "N/A" with reason
- Do NOT clone or download repositories locally
- Do NOT modify any Mars Agent code during research
- Do NOT research more than 1 topic per invocation
- Do NOT combine multiple dimensions into a single agent — one agent per dimension
- Do NOT skip agent dispatch and research all dimensions yourself

## References

- `references/agent-prompts.md` — Sub-agent prompt template for research dimensions
- `references/report-template.md` — Bilingual report markdown structure
- `references/comparison-matrix.md` — Mars Agent self-profile + comparison dimensions (for --compare mode)
