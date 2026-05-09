# 03 — 开发架构

本文档描述代码组织、模块依赖、数据流、关键 abstraction 和 skill 文件格式约定。

## 1. 仓库分层

```
mba/                                   ← 仓库根
├── README.md                          ← 项目门面
├── .env.example                       ← 配置模板
├── .gitignore                         ← .env, .DS_Store
│
│ ── 编排层 ────────────────────────────────
├── metric-brand-auditor/              ← 主 SKILL: MBA 流水线编排器
│   ├── SKILL.md                            Lead 的工作手册(~600 行)
│   ├── references/                         复用片段
│   │   ├── dimensions.md                   7 默认维度
│   │   ├── judge-prompt-template.md        评委统一打分模板
│   │   ├── wuying-browser.md               云浏览器 leg 规范
│   │   └── html-report-template.md         HTML 报告脚手架
│   └── reports/<brand-slug>/               每个品牌一个目录
│       ├── report.md / report.html         canonical 报告
│       ├── versions/v{n}_<date>.{md,html}  不可变版本快照
│       ├── _raw/                           过程文件
│       └── reviews/                        5 评委打分卡
│
│ ── 工具层 ────────────────────────────────
├── research/                          ← /research skill: PRD 多代理深度调研
│   ├── SKILL.md
│   └── references/
│       ├── agent-prompts.md
│       ├── comparison-matrix.md
│       └── report-template.md
│
│ ── 评委层 ────────────────────────────────
├── fusheng-perspective/               ← 5 套人物视角 skill
├── jobs-perspective/                       每套结构相同:
├── likejia-perspective/                      ├── SKILL.md         (frontmatter + 触发规则 + DNA)
├── wu-jundong-perspective/                   ├── references/
└── zhang-yiming-perspective/                 │   └── research/
                                              │       ├── 01-writings.md
                                              │       ├── 02-conversations.md
                                              │       ├── 03-expression-dna.md
                                              │       ├── 04-external-views.md
                                              │       ├── 05-decisions.md
                                              │       └── 06-timeline.md
                                              └── scripts/         (字幕下载 / 调研合并工具)
│
│ ── 基建层 ────────────────────────────────
├── wuying_open.py                     ← 阿里云无影 AgentBay 一次性会话
├── test_wuying.py                     ← 冒烟测试 API key
│
│ ── 文档层 ────────────────────────────────
└── docs/                              ← 本文档目录
    ├── README.md (index)
    ├── 01-prd.md ... 08-extending.md
    └── mcp-server-design.md
```

## 2. 模块依赖图

```
                ┌──────────────┐
                │ User in CC   │
                └──────┬───────┘
                       │ "/mba <brand>"
                       ▼
                ┌──────────────────────────┐
                │ metric-brand-auditor     │  (主编排 SKILL)
                └─┬──────────────────┬─────┘
                  │                  │
       Phase 2/3  │                  │  Phase 4
       sub-agents │                  │  judges (各自 LOAD)
                  ▼                  ▼
          ┌──────────────┐   ┌──────────────────┐
          │ research     │   │ *-perspective    │
          │ (复用搜索)    │   │ (5 套人格 skill)  │
          └──────┬───────┘   └──────────────────┘
                 │
            可选 ▼
          ┌──────────────┐
          │ wuying_open  │
          │ (云浏览器)    │
          └──────────────┘
```

**依赖方向:** 严格自顶向下,无环。

- `metric-brand-auditor` 依赖 `research`(可选,Phase 2 调研可直接用 sub-agent 不必走 research)、`*-perspective`(必选,Phase 4 必读)、`wuying_open.py`(可选,`--quick` 跳过)
- `research` 不依赖任何其他 skill(可独立用)
- `*-perspective` 互不依赖,各自独立。SKILL.md 顶部的"路由规则"靠 metadata 协调,不靠代码
- `wuying_open.py` 完全独立,只是个 Python 脚本

## 3. 数据流

```
input: brand name (or URL)
   │
   ▼
[Phase 0] Lead reads reports/<brand-slug>/report.md (if exists)
   │
   ├─→ exists & no --refresh → EVOLUTION mode → Phase 1E
   └─→ otherwise           → FRESH mode    → Phase 1F
   │
   ▼ (FRESH path 示意)
[Phase 1F] PRD draft (markdown) → user gates
   │
   ▼ user confirms
[Phase 2F] N parallel sub-agents (≤5/批)
   │       each writes _raw/dimension_<n>_<slug>.md
   │     + 1 wuying agent writes _raw/wuying_browse.md (skip if --quick)
   ▼
[Phase 3F] Lead reads all _raw/ → writes _raw/synthesis.md
   │
   ▼
[Phase 4F] 5 (or N) judges in parallel
   │       each LOADs *-perspective/SKILL.md
   │       each writes reviews/<judge>.md
   ▼
[Phase 5F] Lead reads synthesis.md + 5 reviews/
   │       writes report.md (Markdown 模板)
   │       renders report.html (HTML 模板)
   │       freezes versions/v{n}_<date>.{md,html}
   ▼
output: 报告路径 + TL;DR
```

EVOLUTION 路径(Phase 1E onward)与 FRESH 同形,但只对"变了的维度"重跑 Phase 2-4,版本号 +1。详见 [04-pipeline.md](04-pipeline.md)。

## 4. 关键 Abstraction

### 4.1 Skill bundle

> 一组可执行 prompt + 引用的 markdown,组成一个可被 Claude Code 通过 `/<name>` 触发的功能单元。

每个 skill bundle 的标准结构:

```
{skill-name}/
├── SKILL.md                ← entry point,frontmatter + body
├── references/             ← prompt 片段,被 SKILL.md 引用
└── scripts/                ← 可选,辅助脚本(数据准备、调研工具)
```

### 4.2 Sub-agent

> 由 Lead 通过 `Agent(subagent_type, prompt)` 调起的并行子任务。每个 sub-agent 有自己的 prompt + 工具集 + token 预算,执行结束后把 markdown 落到指定路径。

MBA 中 sub-agent 有两类:

- **Research sub-agent**:用 `general-purpose` agent type,跑 `WebSearch + WebFetch`,产出维度调研
- **Judge sub-agent**:用 `general-purpose` agent type,但**第一步就 LOAD perspective skill**,确保 in-character 输出

### 4.3 Phase

> Lead 工作流的最小步骤单元。每个 phase 有明确的输入(读哪些文件)、输出(写哪些文件)、可选的 GATE(等用户确认才继续)。

MBA 共 6 个 phase(0-5)。Phase 0 是路由,1-5 是主流程。EVOLUTION 模式有自己的 1E-5E。

### 4.4 Artifact store

> 一个品牌一个目录,所有产物都落盘可读。MBA 不持久化任何内存状态 —— 重跑只需要 `report.md` 和 `_raw/` 在那。

路径根:`metric-brand-auditor/reports/<brand-slug>/`。`<brand-slug>` 规则:小写 ASCII + 连字符,例如 `openclaw` / `zhifang-atelier` / `bytedance-doubao`。

### 4.5 Perspective skill

> 一套描述某个真实公众人物思维框架的 skill bundle。MBA 只是它的一个**消费者**;perspective skill 自身可以独立 `/<name>-perspective` 触发,做单视角点评。

### 4.6 Wuying session

> 一次性云浏览器会话,生命周期从 `wuying_open.py` 创建开始,到显式 `Session.delete()` 结束。**资源密集**,SKILL.md 强制要求 teardown 在 `wuying_browse.md` 里有验证。

## 5. SKILL.md 文件格式

每个 SKILL.md 顶部必须有 YAML frontmatter:

```yaml
---
name: mba                          # slash command 名,小写
description: |                     # 触发规则,多行,Claude 用此判断激活
  MBA — Metric Brand Auditor.
  IF user asks "..." THEN invoke this skill.
  NOT WHEN: ...
  Trigger patterns: ...
---
```

body 部分按 phase 组织,每个 phase 含:

- "## Phase X — 名称" 标题
- "### Output" 写哪个文件
- "### GATE" 是否等用户确认
- 必要时给 sub-agent 的完整 prompt 模板(用 ``` 块包裹)

## 6. Perspective skill 文件格式

每个 `*-perspective/SKILL.md` 必须含 4 个章节(否则 add_judge 校验失败,见 [mcp-server-design.md](mcp-server-design.md)):

1. **YAML frontmatter** + 触发规则
2. **核心心智模型 / 决策启发式**(≥ 5 条编号项)
3. **表达 DNA**(怎么说话,带样例)
4. **Anti-fabrication 红线**(明确"不要激活"/"不可编造"/"留白")

`references/research/` 下的 6 路调研材料(`01-writings` / `02-conversations` / `03-expression-dna` / `04-external-views` / `05-decisions` / `06-timeline`)是 SKILL.md 的素材源,不是 skill 自身的一部分 —— 但是日后 EVOLUTION / refresh perspective 时的入口。

## 7. 数据格式约定

### 7.1 brand-slug → 路径

```
brand: "OpenClaw"          → slug: openclaw         → reports/openclaw/
brand: "字节豆包"           → slug: bytedance-doubao → reports/bytedance-doubao/
brand: "智坊 atelier"       → slug: zhifang-atelier  → reports/zhifang-atelier/
```

slug 由 Lead 在 Phase 1 决定,用户可在 GATE 1 改。

### 7.2 dimension 文件命名

```
_raw/dimension_<n>_<slug>.md
```

- `<n>` 是 1-7
- `<slug>` 与 dimensions.md 的 H2 标题对应:
  - `1` → `founder-narrative`
  - `2` → `product-positioning`
  - `3` → `distribution-channels`
  - `4` → `community-pr`
  - `5` → `visual-verbal-identity`
  - `6` → `competitive-landscape`
  - `7` → `reception-sentiment`

### 7.3 review 文件命名

```
reviews/<judge>.md
```

`<judge>` ∈ `{fusheng, jobs, likejia, wu-jundong, zhang-yiming}` ∪ 用户自定义。

### 7.4 version 文件命名

```
versions/v{n}_<YYYY-MM-DD>.{md,html}
```

`<n>` 从 1 起,EVOLUTION 模式每次 +1。`v1` 由 FRESH 模式产生,`v2+` 由 EVOLUTION 产生。

## 8. 不依赖编译 / 不依赖 build

整个仓库**没有 build 步骤**。改 SKILL.md 即生效,改 markdown 即生效。HTML 报告是 Lead 在 Phase 5 实时渲染出的字符串,通过 Write 工具落盘。

这是有意为之 —— 让贡献门槛降到"会改 markdown 就行"。

> MCP 化版本会引入 TypeScript build(见 [mcp-server-design.md](mcp-server-design.md)),但当前版本不需要。

## 9. 与 Claude Code 框架的关系

MBA 是 Claude Code 的 **skill consumer** —— 它假设以下 Claude Code 能力存在:

- `/<skill-name>` 触发机制
- `Agent(subagent_type, prompt, run_in_background)` sub-agent dispatch
- `Read` / `Write` / `Edit` 文件工具
- `WebSearch` / `WebFetch`
- `Bash` 用于跑 `python3 wuying_open.py`

如果 Claude Code 取消或重命名以上任何能力,SKILL.md 必须同步改。

## 10. 与外部生态的接口

| 外部 | 接口 | MBA 怎么用 |
|---|---|---|
| Anthropic API | Claude Code 内部代理 | 所有 LLM 调用走它 |
| 阿里云无影 AgentBay | Python SDK `agentbay` | `wuying_open.py` 创建 / 销毁 session |
| GitHub | git push / pull | 报告版本控制 + 团队协作 |
| (未来) Cloudflare Pages | 静态托管 | 把 reports/ 公开给同事看,详见 mcp-server-design.md |

## 11. 关键约束 / 不变量

- 评委独立打分,**互不可见对方 review 文件**(在 Phase 4 prompt 里显式说"DO NOT read other judges' files")
- `versions/` 下的文件**不可变**(EVOLUTION 不改它们,只 append 新版本)
- `report.md` 是 canonical(滚动覆盖),`versions/v{n}_*.md` 是 immutable snapshot
- 评委 perspective skill 顶部的 anti-fabrication 红线**适用 MBA 调用时**(在 Phase 4 prompt 里显式 re-read)
- Wuying session 必须 teardown,在 `wuying_browse.md` 里写明 teardown 状态
