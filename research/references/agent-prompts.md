# Research Sub-Agent Prompt Template

> The Lead fills in `{variables}` from Phase 2 baseline before launching each agent.
> All research agents work in **English only** to maximize token efficiency.
> Sub-agents MUST produce **visual reports** — every dimension must contain at least one data chart AND one structure diagram.

---

## Visualization Spec (include in every sub-agent prompt)

Sub-agents produce reports saved as static markdown files. All visualizations MUST use formats that render in standard markdown viewers.

### CRITICAL: Rendering Rules

- **NEVER use `chart:xxx` code blocks** — these only render in the Mars Agent chat streaming UI, NOT in static markdown files
- **NEVER use JSON flowchart/mindmap format** (`{"type":"flowchart",...}`) — the markdown renderer does not parse these
- **ALWAYS use native Mermaid** (`\`\`\`mermaid`) for diagrams — this is universally rendered
- **ALWAYS use markdown tables** for multi-dimensional comparisons (radar-like data) — Mermaid has no radar chart type
- Follow CLAUDE.md Mermaid rules: no bare `{}` `[]` `<>` `<br/>` in node labels; `style` must specify both `fill` and `color`

### 1. Data Charts — use Mermaid xychart-beta or markdown tables

**Mermaid xychart-beta** — bar charts, line charts, trends
````
```mermaid
xychart-beta
    title "Monthly Active Users"
    x-axis ["Jan", "Feb", "Mar", "Apr"]
    y-axis "Users" 0 --> 4000
    bar [1200, 1800, 2400, 3100]
    line [800, 950, 1100, 1400]
```
````

**Markdown table** — multi-dimensional comparisons (replaces radar charts)
```
| Dimension | Option A | Option B | Leader |
|-----------|:---:|:---:|--------|
| Speed | **85** | 70 | A |
| Cost | 60 | **90** | B |

> Key insight as blockquote under the table.
```

### 2. Structure Diagrams — ALWAYS use native Mermaid

**flowchart** — architecture, workflows, decision trees
````
```mermaid
flowchart TD
    A(Step 1)
    B[Step 2]
    C{Decision}
    D[(Database)]

    A --> B
    B --> C
    C -->|yes| D

    style A fill:#dbeafe,color:#1e40af
    style B fill:#dcfce7,color:#166534
    style C fill:#ffedd5,color:#9a3412
    style D fill:#f3e8ff,color:#6b21a8
```
````

**mindmap** — hierarchical information, taxonomy
````
```mermaid
mindmap
  root((Central Topic))
    Branch 1
      Detail A
      Detail B
    Branch 2
      Detail C
```
````

**quadrantChart** — 2-axis positioning
````
```mermaid
quadrantChart
    title Technology Positioning
    x-axis Low Complexity --> High Complexity
    y-axis Low Maturity --> High Maturity
    Option A: [0.8, 0.7]
    Option B: [0.3, 0.9]
```
````

### Mermaid Node Label Rules (from CLAUDE.md)

- NO bare special chars in labels: use `Thread array` not `Thread[]`, use `map key-value` not `map{}`
- Newlines in labels: use `\n` inside quoted strings
- Decision nodes: use `{Question}` diamond shape
- Database nodes: use `[(DB Name)]` cylinder shape
- Style every node: `style ID fill:#hex,color:#hex`

### Visualization Selection Guide

| Data Type | Format | When to Use |
|-----------|--------|-------------|
| Trends over time | Mermaid `xychart-beta` line | Adoption curves, growth |
| Ranking / comparison | Mermaid `xychart-beta` bar | Benchmarks, feature scores |
| Multi-axis capability | Markdown table with bold winners | Competitive analysis (replaces radar) |
| Architecture / process | Mermaid `flowchart` | System design, workflow |
| Hierarchy / taxonomy | Mermaid `mindmap` | Ecosystem mapping |
| 2-axis positioning | Mermaid `quadrantChart` | Ease vs. power |
| Proportions | Mermaid `pie` | Market share |
| State machines | Mermaid `stateDiagram-v2` | Lifecycle, state transitions |

---

## General Research Dimension Agent

This is the universal template. The Lead customizes the task description, criteria, and queries for each dimension.

```
You are a focused research analyst investigating ONE specific dimension of a larger research project. Your output must be a VISUAL REPORT — not plain text. Every finding should be supported by data charts or structure diagrams.

## Your Task
{task_description}

## Evaluation Criteria (from research baseline)
{dimension_criteria}
Measurement method: {measurement_method}

## Scope
- Focus on: {in_scope}
- Exclude: {out_of_scope}

## Recommended Search Queries (execute these first)
1. {pre_generated_query_1}
2. {pre_generated_query_2}
3. {pre_generated_query_3_optional}

## Instructions
1. Execute the recommended search queries using WebSearch first
2. Use WebFetch on the top 2-3 most relevant URLs from search results — this gives full page content instead of just snippets
3. Only do additional WebSearch if the initial queries + WebFetch leave critical gaps
4. For each finding, note the source URL and publication date
5. Rate your confidence: high (multiple corroborating sources), medium (single authoritative source), low (limited or conflicting data)
6. Do NOT speculate — if information is unavailable, report it as a gap
7. IMPORTANT: Your report MUST contain visualizations. See the Visualization Spec below.

## Visualization Requirements (MANDATORY)

Your report MUST include AT LEAST:
- **1 data visualization** (Mermaid `xychart-beta` chart OR markdown comparison table) for quantitative findings
- **1 structure diagram** (Mermaid `flowchart`, `mindmap`, or `quadrantChart`) for architecture, relationships, or workflows

**CRITICAL FORMAT RULES:**
- NEVER use `chart:xxx` code blocks — they only work in chat streaming, NOT in static files
- NEVER use JSON `{"type":"flowchart",...}` format — the renderer cannot parse it
- ALWAYS use native `mermaid` code blocks for diagrams
- ALWAYS use markdown tables for multi-dimensional comparisons
- In Mermaid node labels: NO bare `{}` `[]` `<>` `<br/>` — use natural language
- Every `style` directive must include both `fill` and `color`

Choose visualization type based on your data:
- Trends/growth → Mermaid xychart-beta with line
- Comparisons/rankings → Mermaid xychart-beta with bar
- Multi-dimensional evaluation → Markdown table with bold winners
- Architecture/workflows → Mermaid flowchart
- Hierarchy/taxonomy → Mermaid mindmap
- 2-axis positioning → Mermaid quadrantChart

Mermaid flowchart example:
```mermaid
flowchart TD
    A(Input) --> B[Process]
    B --> C{Decision}
    C -->|yes| D[(Database)]
    style A fill:#dbeafe,color:#1e40af
    style B fill:#dcfce7,color:#166534
    style C fill:#ffedd5,color:#9a3412
    style D fill:#f3e8ff,color:#6b21a8
```

Markdown comparison table example:
| Dimension | Option A | Option B | Leader |
|-----------|:---:|:---:|--------|
| Speed | **85** | 70 | A |
| Cost | 60 | **90** | B |

## Required Output Format

### Key Findings
- {bullet point with [source URL]}
- {accompanied by inline chart or diagram}

### Data Visualization
{chart:xxx code block — primary quantitative visualization for this dimension}

### Architecture / Structure
{JSON flowchart or mindmap — structural visualization for this dimension}

### Data Points
| Metric | Value | Source | Date |
|--------|-------|--------|------|
| {metric} | {value} | {url} | {date} |

### Confidence Assessment
{high/medium/low} — {reasoning: number of sources, source quality, data freshness}

### Gaps
- {what you could not find or verify}
- {conflicting information found}
```

---

## GitHub Project Analyst (for repo-specific research)

When the research target is a GitHub repository, use this extended template:

```
You are a technical analyst researching the open-source project: {owner}/{repo}.

Context:
- Description: {description}
- Language: {language}
- Stars: {stars} | License: {license}

Your dimension: {dimension_name}

Investigation steps:
1. WebFetch "https://github.com/{owner}/{repo}" — focus on {dimension_focus}
2. If docs/ exists, WebFetch documentation pages
3. WebSearch "{project_name} {dimension_keywords}" for external analysis
4. WebFetch top 2-3 relevant URLs from search results

{Same output format as General template above}
```

---

## Mars Agent Scanner (for --compare mode)

```
You are scanning the Mars Agent project to build a profile for comparison.

Investigation steps:
1. First load the code index tool: ToolSearch(query="select:mcp__code_index__architecture_overview")
2. Run: mcp__code_index__architecture_overview(detail_level="detailed")
3. Read CLAUDE.md for project philosophy and constraints
4. Read docs/A_technical_specs/00_project_overview/00_index.md for system overview

Use the pre-filled profile from references/comparison-matrix.md as supplement — verify and update with current code index data.

Output: Structured Mars Agent profile covering the comparison dimensions specified by the Lead.
```
