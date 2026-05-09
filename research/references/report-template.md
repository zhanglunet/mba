# Research Report Template (Bilingual)

> This template is used in Phase 5 to generate the final bilingual research report.
> English is the primary language. Chinese serves as reading aid, not replacement.

```markdown
# {Topic} — Research Report / {主题} — 调研报告

> Date: {YYYY-MM-DD} | Researcher: Claude Code /research skill
> Dimensions: {N} | Sub-agents: {N} | Duration: ~{N} minutes

## Executive Summary / 执行摘要

{3-5 sentences answering the Research Objective from Phase 1}
> **中文**：{自然中文翻译}

### Decision Framework / 决策框架
{Mermaid diagram: comparison matrix, positioning chart, or decision flowchart}

## Research Context / 调研背景

### Objective / 目标
{Research objective from Phase 1 proposal}

### Scope / 范围
- In scope: {dimensions investigated}
- Out of scope: {what was excluded}

### Core Questions / 核心问题
1. {Question 1} → Answer: {1-line answer with reference to dimension}
2. {Question 2} → Answer: {1-line answer}
...

## Dimension Findings / 各维度调研结果

### D1: {Dimension Title} / {中文标题}

**Key Findings / 关键发现:**
{Bullet points with [source URL] citations}
> **中文**：{中文翻译}

**Data Points / 数据点:**
| Metric | Value | Source |
|--------|-------|--------|
| {metric} | {value} | {url} |

**Confidence:** {High/Medium/Low} — {reasoning}

### D2: {Dimension Title} / {中文标题}
{Same structure as D1}

### D{N}: ...

## Cross-Cutting Analysis / 交叉分析

### Contradictions / 矛盾点
{Where dimension findings conflict with each other}
> **中文**：{中文翻译}

### Information Gaps / 信息缺口
{What could NOT be determined and why}

### Confidence Matrix / 置信度矩阵
| Dimension | Confidence | Data Quality | Key Limitation |
|-----------|------------|--------------|----------------|
| D1 | High/Med/Low | {quality} | {limitation} |

## Recommendation / 建议

{Clear, actionable recommendation directly answering the Research Objective}
> **中文**：{中文翻译}

### Implementation Roadmap / 实施路线图
{If applicable: phased approach with milestones}

## Mars Agent Comparison / Mars Agent 对比

> Omit this section if --no-compare flag is set.

| Dimension | {Target/Topic} | Mars Agent | Delta |
|-----------|----------------|------------|-------|
| {dim} | {value} | {value} | {analysis} |

### Gaps / 差距
{What Mars Agent could adopt}

### Strengths / 优势
{Where Mars Agent is ahead}

## Key Vocabulary / 重点词汇

| English | Pronunciation | Chinese | Context |
|---------|--------------|---------|---------|
| {term} | {hint} | {中文} | {where it appears in this report} |

## References / 参考资料
1. [{title}]({url}) — {what it provided}
2. [{title}]({url}) — {what it provided}
```
