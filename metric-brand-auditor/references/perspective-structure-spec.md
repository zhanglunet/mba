# Perspective SKILL.md — Structure Spec

> Source of truth for the H2 layout every `*-perspective/SKILL.md` must satisfy.
> The validator at `scripts/perspective-tools/check_structure.py` enforces this.

## Why this spec exists

15 perspective skills were built over a year of incremental drift. Three patterns emerged:

- Default panel (fusheng / jobs / likejia / wu-jundong / zhang-yiming): Chinese H2,
  has `诚实边界` + `核心心智模型` but no explicit `Anti-Fabrication` H2 — fabrication rules
  live inline in `角色扮演规则`
- Auto panel (musk / lixiang / hexiaopeng / libin / leijun): mixed-language H2, has
  `Anti-Fabrication 红线` + `Self-Conflict Rule` but no formal `Honest Boundary` H2
- Security panel (jensenhuang / satyanadella / zhangmingzheng / renzhengfei / zhouhongyi):
  full English-style H2 with all four guard sections — this is the target shape

Drift makes the MBA Lead's Phase 4 evaluator brittle, blocks any future automated audit,
and makes review of new perspectives slow. This spec freezes the target.

## Required H2 sections (must appear, any of the listed aliases is OK)

| Logical section | Acceptable H2 strings |
|---|---|
| Core Mental Models | `## Core Mental Models` / `## 核心心智模型` |
| Honest Boundary | `## Honest Boundary` / `## 诚实边界` |
| Anti-Fabrication | `## Anti-Fabrication Red Lines` / `## Anti-Fabrication 红线` / `## Anti-Fabrication Guard` |
| Self-Conflict Rule | `## Self-Conflict Rule` |
| Sources / Appendix | `## Sources` / `## 附录：调研来源` |

Other H2 sections (Identity Card, Decision Heuristics, Expression DNA, Persona
Activation Rules, MBA Five-Lens Scoring Bias, etc.) are recommended but not required by
the validator.

## What each required section must contain

### Core Mental Models

- 5-8 mental models the judge uses to read brand signal. 6 is the canonical count.
- Per model: name + 2-4 sentence definition + 1 source attribution
  (reference research file + a line or timestamp anchor) + 1 anti-application
  (when NOT to apply this model)
- Reference shape: `satyanadella-perspective/SKILL.md` L38-70

### Honest Boundary

- Topics where the judge has no first-hand material (private life, internal
  competitor knowledge, post-cutoff events)
- Cross-context expression limits (e.g., Musk's X tone vs founder-mode tone;
  Chinese judges not faking stage-style English)
- Research cutoff date — "after which I cannot speak"
- Reference shape: `jobs-perspective/SKILL.md` L411-423 (`诚实边界`)

### Anti-Fabrication

- Bulleted "do not fabricate" list — dates, numbers, private conversations,
  unpublished strategies, third-party events attributed to me, etc.
- A safe-fallback line: "If the user asks something I don't have first-hand
  material on, I say so and then reason from a mental model — I do not
  manufacture facts"
- Reference shape: `leijun-perspective/SKILL.md` L295-313 (`Anti-Fabrication 红线`)

### Self-Conflict Rule

- Brand family / portfolio where this judge has structural conflict of interest
- Default behavior: `--panel-drop <slug>` for those brands
- Fallback if kept in panel: founder-canon self-check only, MBA Lead sets
  `quality_flag: judge_self_conflict: <slug>`
- Reference shape: `zhangmingzheng-perspective/SKILL.md` L111-118

### Sources / Appendix

- Pointer to `references/research/01..06.md` and any extra files
- Primary vs secondary attribution per file when not obvious
- Reference shape: `jobs-perspective/SKILL.md` L447-end

## Consumer persona variant (PRD-178) — 模拟消费者人设的语义映射

The 5 required H2 sections are **unchanged** for consumer personas (synthetic shopper
personas, e.g. `first-glance-shopper-perspective`). Only the semantics of each section
map differently — the persona's "corpus" is its own `references/scenario.md` (scene
settings + consumer-voice sample lines, anchored by item numbers), not a real person's
recorded material. No `references/research/` six-route corpus: by definition there is
no real first-hand material to deepen, so consumer personas stay seed tier permanently
(seeded in `docs/10-deepening-perspectives.md` §6 as 消费者模拟人设另册).

| Required section | Consumer semantic (per PRD-178/T1 §四) |
|---|---|
| Core Mental Models | 消费决策心智模型（价格锚、口碑传导、社交货币等）；定义引用 scenario.md 设定条目，引用样例句以 scenario.md 逐字命中为准（firewall_check 语料含 scenario.md） |
| Honest Boundary | 必写「**我是模拟人设，非真实人物；无真实购买经历与人口学身份**」+ 研究截止（cutoff）声明 |
| Anti-Fabrication Red Lines | 不虚构销量、市场份额、真实用户数、具体价格事实；不虚构「我买过 / 我朋友用过」的经历；场景设定没有的细节答「不知道」 |
| Self-Conflict Rule | 场景设定关联品类与被审品牌重合时主动申请 `--panel-drop <own-slug>`（静态门禁同专家） |
| Sources | 指向 `references/scenario.md`（逐条列场景设定条目 + 口吻样例句锚定方式） |

Non-required sections for consumer personas: `## Consumer Question Set（C1–C5 题组）`
(the consumer question set replacing the 5 lenses — C2 is the only numeric score and
never enters the expert Score Matrix)、`## 表达DNA / Expression DNA`、`## 内在张力`.
Consumer personas are judged by `check_structure.py` / `quality_check.py` /
`firewall_check.py` / `check_self_conflict.py` exactly like expert personas.

## Adding a new perspective

1. Copy the H2 skeleton from `satyanadella-perspective/SKILL.md` (shortest production
   reference at ~140 lines).
2. Fill each required section per the rubrics above.
3. Run `python3 scripts/perspective-tools/check_structure.py` — must exit 0.
4. The panel yaml referencing this perspective must list it; run
   `python3 scripts/validate_panels.py` to confirm.

## What this spec does NOT enforce

- Word count or depth — that's a quality-gate concern, not a structure concern
- Whether the perspective also ships a `quotes.md` URL-anchor bank
  (production-seed tier) or `references/research/` 6-route deep research
- Language consistency within a perspective (some intentionally mix Chinese
  primary content with English headings for tooling compatibility)
- Whether `Stage 2 Refresh Notes` / `MBA Five-Lens Scoring Bias` / other optional
  sections are present
