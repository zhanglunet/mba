# 04 — 程序逻辑与实现方法(流水线详解)

本文档把 MBA 流水线的 6 个 phase 拆开讲:每 phase 在做什么、读什么、写什么、Lead 怎么实现、有什么坑。

> **以 SKILL.md 为准**:本文档解释 `metric-brand-auditor/SKILL.md` 的实际行为。如果两边描述冲突,以 SKILL.md 为准并提交 PR 修本文档。

## 总览图

```
                          [ user input ]
                                │
                                ▼
                         ┌─────────────┐
                         │  Phase 0    │  路由器
                         │  Router     │  decide FRESH | EVOLUTION
                         └──────┬──────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
         ┌─────────────┐                 ┌──────────────┐
         │  Phase 1F   │                 │  Phase 1E    │
         │  Discovery  │                 │  Diff plan   │
         │  + GATE 1   │                 │   + GATE 1E  │
         └──────┬──────┘                 └──────┬───────┘
                │                               │
                ▼                               ▼
         ┌──────────────┐               ┌──────────────┐
         │ Phase 2F     │               │ Phase 2E     │
         │ N parallel   │               │ Delta search │
         │ sub-agents   │               │ (changed dims)│
         └──────┬───────┘               └──────┬───────┘
                │                               │
                └───────────────┬───────────────┘
                                ▼
                         ┌─────────────┐
                         │  Phase 3    │  Lead synthesis
                         └──────┬──────┘
                                ▼
                         ┌─────────────┐
                         │  Phase 4    │  N judges in parallel
                         └──────┬──────┘
                                ▼
                         ┌─────────────┐
                         │  Phase 5    │  Lead merge + HTML render
                         └──────┬──────┘
                                ▼
                          [ report.{md,html} ]
```

## Phase 0 — Router

**职责**:决定走 FRESH 还是 EVOLUTION,告知用户。

**输入**:`brand` 名称、`--refresh` flag(可选)。

**实现**:Lead 直接 `Read reports/<brand-slug>/report.md`。

| 状态 | 决策 |
|---|---|
| 文件不存在 | FRESH 模式,进入 Phase 1F |
| 文件存在 + 没传 `--refresh` | EVOLUTION 模式,进入 Phase 1E |
| 文件存在 + 传了 `--refresh` | FRESH 模式,但先把现有 `report.md` 归档到 `versions/v{n}_archived_<date>.md` |

**输出**:消息给用户,告知进入哪个模式 + 预计耗时。

**坑**:

- brand-slug 不规范导致路径找不到 → SKILL.md 提示 Lead 在确认 PRD 时显式给 slug
- `--refresh` 模式下要把当前 `report.md` 先归档,Lead 必须显式做这步(以免覆盖丢失)

## Phase 1F — Discovery (FRESH)

**职责**:Lead 起草 Brand Influence PRD,等用户 confirm。

**输入**:`brand` 名称、可选 `--focus` / `--panel` / `--industry` / `--panel-add` / `--panel-drop` / `--quick` flag。

**输出**:Markdown PRD,包含:

- Subject(品牌一句话定位)
- Research Objective
- 默认 7 维度表(可被用户裁掉)
- 是否走 wuying leg
- 解析后的 panel 名称与 Judge 名单
- 预估耗时 + 成本

**GATE 1**:Lead 必须停下,等用户确认或编辑。

> 这是当前 Claude Code 模式下唯一的"卡点"。在 MCP 化版本里会变成 `propose_audit` + `confirm_audit` 两阶段(见 mcp-server-design.md)。

**实现要点:**

- PRD 是 markdown,直接打到对话里,**不落盘**(EVOLUTION 模式才需要落盘 diff)
- 用户回复 "ok" / "go" / "确认" → 进入 Phase 2
- 用户回复带编辑(去掉某维度 / 改 slug / 减评委)→ Lead 用编辑后的 PRD 进入 Phase 2
- 用户回复 "cancel" → 终止,什么都不写

## Phase 1E — Diff plan (EVOLUTION)

**职责**:基于上版报告,识别"自上次以来可能变了什么",列出要重跑的维度。

**实现**:Lead 读 `report.md` + `versions/v{n}_<date>.md`,扫一遍可能的"变化触发":

- 新产品发布 / 价格变更 / 重大融资 / 创始人公开发声 / 关键媒体报道
- 时间窗:`last_update_date` 之后的 ≥ 30 天

**输出**:diff plan markdown,列:

- 哪些维度建议 delta 重跑(默认 ≤ 4 个)
- 哪些维度不变(直接复制上版)
- 是否需要 wuying leg

**GATE 1E**:同样要用户确认。

## Phase 2F — Parallel Sub-Agent Search

**职责**:对每个确认的维度并行调研一个 sub-agent +(可选)一个 wuying sub-agent。

**实现核心**(摘自 SKILL.md 的 prompt 模板):

```
Agent(
  subagent_type: "general-purpose",
  description: "Brand dim {n} — {dim-name}",
  run_in_background: true,
  prompt: """
    You are a brand-influence research analyst investigating ONE dimension of brand {Brand}.
    Dimension: {dim-name}
    Sub-questions: {from PRD}

    Method:
    1. Run 4-6 WebSearch queries (English + Chinese)
    2. WebFetch the top 3 most-substantive URLs
    3. Cite every claim
    4. Distinguish first-person vs third-party
    5. Flag contradictions

    Output (markdown, ≤ 1200 words):
    - ## Findings (5-10 bullets)
    - ## First-person framing
    - ## Third-party signal
    - ## Contradictions / gaps
    - ## Confidence: high / medium / low

    Save to: ~/mba/metric-brand-auditor/reports/{brand-slug}/_raw/dimension_{n}_{slug}.md
  """
)
```

**并发规则:**

- 每批 ≤ 5 个 agent(Anthropic 隐式限制)
- 7 维度 + 1 wuying = 8 → 分两批 (5 + 3)
- 全部 `run_in_background: true`,Lead 等所有完成

**Wuying sub-agent 特殊性:**

- 需要先跑 `python3 wuying_open.py` 起会话
- 用 `agent-browser` CLI 驱动 → 拿数据 → 落盘 `_raw/wuying_browse.md`
- **必须 teardown**(MBA 把 wuying session 看作"花钱在跑"的资源,不能漏关)
- 失败时降级:不伪造数据,在报告里标 N/A

**Circuit breaker**:任何 agent 5 min 没返回 → Lead 用已有结果继续,标记缺口。

## Phase 2E — Delta search (EVOLUTION)

**职责**:只对 diff plan 里"变了的维度"重跑 sub-agent。

**实现**:与 Phase 2F 相同的 prompt 模板,但 sub-agent 数量减少(典型 2-4 个)。

**重要细节**:Phase 2E 的 sub-agent prompt 里**会带上上版 dimension 文件的内容**作为基线,告诉 sub-agent "上次发现这些,这次只关注 delta",避免重复劳动。

## Phase 3F / 3E — Lead Synthesis

**职责**:Lead 读所有 `_raw/dimension_*.md` 和 `_raw/wuying_browse.md`,产出 `_raw/synthesis.md`。

**输出章节**(固定):

- Executive synthesis(5 bullets:影响力如何被构造)
- Leverage map(哪个维度做实功 vs 装饰)
- Fragile edges(品牌在哪些点单点依赖)
- Cross-dimension contradictions(维度 N 与 M 矛盾在哪)
- Open questions(没搞明白的)
- Citations index(去重合并)

**实现要点:**

- 这是一次单 LLM 调用,Lead 自己干,不开 sub-agent
- synthesis.md 必须 self-contained:评委只读这一个文件就能打分,不必看 7 个维度文件

## Phase 4F / 4E — Judge Review Panel

**职责**:N 评委独立打分,各自落 `reviews/<judge>.md`。

**实现核心**(摘自 SKILL.md):

```
for judge in [fusheng, jobs, likejia, wu-jundong, zhang-yiming]:
  Agent(
    subagent_type: "general-purpose",
    description: "Judge — {judge}",
    run_in_background: true,
    prompt: """
      FIRST load ~/mba/{judge}-perspective/SKILL.md and READ FULLY.
      From now on, respond AS the persona — first-person, their vocabulary, their style.
      Re-read anti-fabrication rules — they apply.

      Read synthesis at:
      ~/mba/metric-brand-auditor/reports/{brand-slug}/_raw/synthesis.md

      Score on 5 lenses (1-10):
      1. Origin authenticity
      2. Category coinage
      3. Leverage quality
      4. Identity coherence
      5. Real-world signal

      Each lens: one paragraph in-character + one signature quote.

      End with:
      - Verdict (1 sentence, in character)
      - Critical gap (the thing only YOU would surface)
      - Brand action (what to do next, if your worldview holds)

      Save to: ~/mba/metric-brand-auditor/reports/{brand-slug}/reviews/{judge}.md

      DO NOT read other judges' files. Score independently.
    """
  )
```

**为什么 5 个 = 1 批**:刚好不超 Anthropic 5 并发上限,一个回合搞定。

**人格化纪律:**

- 每个 perspective skill 顶部都有 anti-fabrication 红线,prompt 中显式提醒"那些规则也适用这里"
- "DO NOT read other judges' files" 是关键 —— 防止评委趋同
- prompt 里要写 "first-person voice",否则 sub-agent 容易写成"傅盛认为..."而非"我认为..."

**失败处理**:某个评委返回失败 → Lead 在 Phase 5 报告里把那行标 "—" 不打分,均值用剩余评委。

**EVOLUTION 模式的差别**:Phase 4E 评委只对 diff plan 里变了的维度重打分,其他镜头分数从上版 reviews 里复制。**所以评委文件 EVOLUTION 时不全部重写,而是**针对受影响镜头 patch**。

## Phase 5F / 5E — Lead Merge

**职责**:Lead 读 synthesis + N reviews → 写 `report.md` → 渲染 `report.html` → 冻结 `versions/v{n}_<date>.{md,html}`。

### 5.a markdown 报告

模板见 `metric-brand-auditor/SKILL.md`,章节顺序固定(详见 [02-product-design.md](02-product-design.md) §2.1)。

**强制 Legal/IP/Disclaimer 模块**:每份 `report.md` 必须在 Citations/Sources 前包含
`Legal, IP & Disclaimer`。该模块必须说明:

- 报告仅引用公开资料,未使用非公开文件、商业秘密或未授权数据库
- 商标、品牌名、产品名、车型名、logo、商业外观等归合法权利方所有
- MBA / 作者与被评品牌无赞助、授权、合作、背书或代理关系(除非用户明确提供)
- 第三方图片、截图、产品视觉的版权与相关权利归原权利方所有
- MBA 的文字分析/评分框架是研究性表达,不改变第三方资料的原有权利归属
- 报告不构成投资、融资、采购、法律、审计、产品质量认证或商业尽调建议
- 结论受运行模式和资料边界限制,重大决策前需核验一手资料

### 5.b HTML 报告

**渲染方法**:Lead 直接生成完整 HTML 字符串,Write 落盘。**没有 SSR/build**。

**模板源**:`metric-brand-auditor/references/html-report-template.md` 提供 scaffold,Lead 把数据填进去。HTML 必须和 Markdown 一样在 Citations 前显示 Legal/IP/Disclaimer,不能只放在 footer 或隐藏脚注里。

**Sanity check**:Lead 写完后必须告诉用户 "open report.html",并提示 "如果 Mermaid 报错请告诉我"。

> MCP 化后会改成自动用 headless 浏览器校验。

### 5.c Surface to user

Lead 在对话里给:

- 一段 TL;DR(Lead 自己的声音,不是任何评委的)
- Score Matrix 表格内联
- `report.md` 和 `report.html` 路径
- 后续建议("要深挖某个评委吗?要重点关注竞品 X 吗?")

## EVOLUTION 模式细节

EVOLUTION 不是"重跑一次整个流程",而是"对变了的维度做 surgical update"。

差异点:

| Phase | FRESH | EVOLUTION |
|---|---|---|
| 1 | 起草新 PRD | 列 diff plan |
| 2 | 跑全部 7 维度 | 只跑变了的 ≤ 4 维度 |
| 3 | 写新 synthesis | 把新 dimension 嵌入旧 synthesis,产出 delta-synthesis |
| 4 | resolved panel 的 N 位评委全打 | resolved panel 的评委只对变了的维度重打分,其他维度沿用上版 |
| 5 | report.md v1 | report.md v{n+1},Versions 章节 append 一行 |

**关键不变量:**

- `versions/v{n}_<date>.md` 是**不可变快照**,EVOLUTION 不改这些文件,只 append 新版本
- `report.md`(canonical) 滚动覆盖
- 跨版本对比需要 diff `v1.md` 与 `v2.md`(MCP 化后会有 `mba.diff_versions` 工具)

## 错误处理与部分失败

| 错误 | 处理 |
|---|---|
| 1 个维度 sub-agent 超时 | 标"Confidence: low",Phase 3 Lead 在 contradictions 里提及 |
| Wuying leg 完全失败 | 降级 web-only,在 report TL;DR 写 "Wuying leg N/A — see _raw/wuying_browse.md" |
| 1 个评委超时 | 那行打 "—",均值用剩余 |
| Phase 5 HTML Mermaid 语法错 | 退回 markdown 表格,在 details 里写"Mermaid render failed: <error>" |
| Anthropic 限流 | sub-agent 内置指数退避;持续失败由 Phase 2 circuit breaker 处理 |

## 性能与成本

| 阶段 | 时长(典型) | token 用量(典型) |
|---|---|---|
| Phase 0-1 | 1-2 min | < 5K |
| Phase 2 | 10-15 min | ~ 800K input + 30K output |
| Phase 3 | 2-3 min | ~ 100K input + 5K output |
| Phase 4 | 5-8 min | ~ 250K input + 25K output |
| Phase 5 | 2-3 min | ~ 60K input + 15K output |
| **总计** | **~25 min** | **~1.2M input + 80K output** |

按 Claude Sonnet 价格(input $3/MTok, output $15/MTok),单次 FRESH 审计成本约 **$4-5**。EVOLUTION 通常是 1/3 成本。

## 与 SKILL.md 的对应关系

| 本文档章节 | SKILL.md 章节 |
|---|---|
| Phase 0 — Router | "## Phase 0 — Router (FIRST STEP, ALWAYS)" |
| Phase 1F — Discovery | "## Phase 1F — Discovery (FRESH mode, Lead, sequential)" |
| Phase 2F — Parallel Search | "## Phase 2F — Parallel Sub-Agent Search (FRESH mode)" |
| Phase 3F — Synthesis | "## Phase 3F — Lead Synthesis (FRESH mode)" |
| Phase 4F — Judge Panel | "## Phase 4F — 5-Judge Review Panel" |
| Phase 5F — Merge | "## Phase 5F — Lead Merge (FRESH mode)" + "### Phase 5F.b — HTML report" + "### Phase 5F.c — Surface to user" |
| EVOLUTION 1E-5E | "## EVOLUTION MODE (Phase 1E onward)" |
