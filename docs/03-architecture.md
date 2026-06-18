# 03 — 开发架构

本文档描述代码组织、模块依赖、数据流、关键 abstraction 和 skill 文件格式约定。

## 1. 仓库分层

```
mba/                                   ← 仓库根
├── README.md                          ← 项目门面
├── .env.example                       ← 配置模板
├── .gitignore                         ← .env / reports/ / .botlearn/ / skills/ 等
├── .github/workflows/panel-validation.yml ← CI:校验 panel / 结构 / py_compile / shell / site build
│
│ ── 编排层 ────────────────────────────────
├── metric-brand-auditor/              ← 主 SKILL: MBA 流水线编排器
│   ├── SKILL.md                            Lead 的工作手册(~1000 行)
│   ├── references/                         复用片段
│   │   ├── dimensions.md                   7 默认维度(+ 高级维度 8-9)
│   │   ├── judge-prompt-template.md        评委统一打分模板(5 镜头)
│   │   ├── wuying-browser.md               云浏览器 leg 规范
│   │   ├── html-report-template.md         HTML 报告脚手架
│   │   └── perspective-structure-spec.md   *-perspective/SKILL.md 的 H2 结构规范
│   ├── panels/                             ← 评委编组层:命名 panel yaml
│   │   ├── default.yaml / auto.yaml / security-cn-global.yaml   可运行 panel
│   │   ├── ai-app-cn.yaml … vc-en.yaml     SKELETON 占位 panel(7 个)
│   │   ├── industries.yaml                 行业名 → panel 名映射表
│   │   └── README.md                       panel 字段参考 + resolver 行为
│   └── reports/<brand-slug>/               每个品牌一个目录(运行时产物,.gitignore)
│       ├── report.md / report.html         canonical 报告
│       ├── panel.yaml                      品牌绑定了哪套 panel
│       ├── versions/v{n}_<date>.{md,html}  不可变版本快照
│       ├── _raw/                           过程文件(dimension_* / synthesis / wuying_browse)
│       └── reviews/                        N 评委打分卡(按 panel 大小)
│
│ ── 工具层 ────────────────────────────────
├── research/                          ← /research skill: PRD 多代理深度调研
│   ├── SKILL.md
│   └── references/{agent-prompts,comparison-matrix,report-template}.md
│
│ ── 评委层 ────────────────────────────────
├── perspectives/                      ← 15 套 production 人物视角 skill(目录名 <slug>-perspective/)
│   ├── default panel:  fusheng / jobs / likejia / wu-jundong / zhang-yiming
│   ├── auto panel:     musk / leijun / lixiang / hexiaopeng / libin
│   └── security panel: zhouhongyi / zhangmingzheng / renzhengfei / jensenhuang / satyanadella (+ musk)
│       每套结构:
│       ├── SKILL.md         (frontmatter + 触发规则 + 心智模型 + DNA + 红线)
│       ├── references/research/01-06.md  (6 路调研材料)
│       ├── references/research/quotes.md (部分:URL 锚定金句库)
│       └── references/sources/           (部分:transcript 原文)
│   注:2026-06 起 *-perspective/ 统一收纳到 perspectives/ 下(此前在仓库根);
│       SKILL.md 的 ${PERSPECTIVES_PATH} 优先找 perspectives/,旧布局兜底
│
│ ── 基建层 ────────────────────────────────
├── scripts/
│   ├── validate_panels.py                  ← 校验 panel yaml(零依赖,CI 跑)
│   ├── migrate_legacy_report_panels.py     ← 给老报告补 panel.yaml
│   ├── print_report.sh                     ← report.html → report.pdf(headless Chrome)
│   ├── perspective-tools/                  ← perspective 共用工具
│   │   ├── check_structure.py              校验 SKILL.md H2 结构(CI 跑)
│   │   ├── merge_research.py / quality_check.py
│   │   └── srt_to_transcript.py / download_subtitles.sh
│   └── wuying/{open.py, smoke_test.py}     ← 阿里云无影 AgentBay 会话 + 冒烟测试
├── assets/judges/                     ← 评委插画头像(严禁真人照片)
│
│ ── 发布层 ────────────────────────────────
├── published/reports/<brand>/         ← 经 review 可公开的样例报告源(显式 add)
├── site/                              ← mbabrand.com 源:index.html + build.sh(Cloudflare Pages)
│
│ ── 文档层 ────────────────────────────────
└── docs/                              ← 本文档目录
    ├── README.md (index)
    ├── 01-prd.md ... 08-extending.md
    ├── mcp-server-design.md / wuying-usage.md
    └── hackathon/ (pitch / deck)
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
          │ (复用搜索)    │   │ (人物视角 skill)  │
          └──────┬───────┘   └──────────────────┘
                 │
            可选 ▼
          ┌──────────────┐
          │ wuying       │
          │ (云浏览器)    │
          └──────────────┘
```

**依赖方向:** 严格自顶向下,无环。

- `metric-brand-auditor` 依赖 `panels/*.yaml`(Phase 0 决定哪 N 位评委)、`research`(可选,Phase 2 调研可直接用 sub-agent 不必走 research)、`*-perspective`(Phase 4 按 panel 读取,缺失则降级 N-of-M)、`scripts/wuying/open.py`(可选,`--quick` 跳过)
- 所有路径在 Phase 0 由运行时符号(`${SKILL_DIR}` / `${REPORTS_DIR}` / `${PERSPECTIVES_PATH}` / `${PANELS_DIR}` / `${IMAGES_DIR}`)解析一次后复用 —— v0.2.14 起不再 hardcode `~/mba/...`
- `research` 不依赖任何其他 skill(可独立用)
- `*-perspective` 互不依赖,各自独立。SKILL.md 顶部的"路由规则"靠 metadata 协调,不靠代码
- perspective 研究辅助脚本集中在 `scripts/perspective-tools/`,避免每个 perspective 目录重复维护
- `scripts/wuying/open.py` 完全独立,只是个 Python 脚本

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

路径根:`metric-brand-auditor/reports/<brand-slug>/`。`<brand-slug>` 规则:小写 ASCII + 连字符,例如 `openclaw` / `aibrary` / `bytedance-doubao`。

### 4.5 Perspective skill

> 一套描述某个真实公众人物思维框架的 skill bundle。MBA 只是它的一个**消费者**;perspective skill 自身可以独立 `/<name>-perspective` 触发,做单视角点评。

### 4.6 Wuying session

> 一次性云浏览器会话,生命周期从 `scripts/wuying/open.py` 创建开始,到显式 `Session.delete()` 结束。**资源密集**,SKILL.md 强制要求 teardown 在 `wuying_browse.md` 里有验证。

### 4.7 Panel

> 一份命名的评委名单 yaml(`panels/<name>.yaml`),把"哪 N 位评委上场"从 SKILL.md 里抽出来。
> 一个 panel = 一个 yaml,git 跟踪即"保存"。

Phase 0 的 panel resolver 四层优先级(先命中先用):**`--panel <name>` > `--industry <name>`
(查 `industries.yaml`)> `reports/<brand>/panel.yaml` 的品牌绑定 > `default.yaml`**。`--panel-add` /
`--panel-drop` 在解析后做本次运行的临时增删(写进 `panel.yaml.overrides`,不改 `panels/<name>.yaml`)。

panel 有 `status: skeleton` 字段标记"占位 / 评委未建齐":跑到时 Lead 提示并自动降级为
synthesis-only。当前 9 个可运行(default / auto / security-cn-global / ai-app-cn / edu-cn / vc-en / vc-cn / consumer-cn / cross-border)+ 1 个 skeleton(luxury-en)。
关键不变量:**不要改已在用 panel(尤其 default)的 `judges:`** —— 老品牌 `panel.yaml` 记的是
panel 名,改名单会让 v{n+1} 与 v{n} 不可比;换评委请起新 panel 名。

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

**单一事实源**:`metric-brand-auditor/references/perspective-structure-spec.md` 规定了每个
`*-perspective/SKILL.md` 必须满足的 H2 布局,`scripts/perspective-tools/check_structure.py`
在 CI 里强制校验(`panel-validation.yml` 第二步)。

15 套 perspective 经一年增量演化形成了三种风格(默认 panel 全中文 H2、auto panel 中英混排、
security panel 全英式 H2),structure-spec 用"逻辑章节 + 可接受别名"统一它们。必须出现的 5 个
H2 章节(任一别名即可):

| 逻辑章节 | 可接受 H2(任一) |
|---|---|
| Core Mental Models | `## Core Mental Models` / `## 核心心智模型`(5-8 条,典型 6) |
| Honest Boundary | `## Honest Boundary` / `## 诚实边界`(无一手材料的话题 + cutoff 日期) |
| Anti-Fabrication | `## Anti-Fabrication Red Lines` / `## Anti-Fabrication 红线` / `## Anti-Fabrication Guard` |
| Self-Conflict Rule | `## Self-Conflict Rule`(强关联品牌 → 默认 `--panel-drop`) |
| Sources / Appendix | `## Sources` / `## 附录:调研来源`(指向 `references/research/01-06.md`) |

其它 H2(Identity Card / Decision Heuristics / Expression DNA / Persona Activation Rules /
MBA Five-Lens Scoring Bias 等)推荐但不强制。frontmatter + 触发规则始终必备。

`references/research/` 下的 6 路调研材料(`01-writings` / `02-conversations` /
`03-expression-dna` / `04-external-views` / `05-decisions` / `06-timeline`)是 SKILL.md 的
素材源;部分 perspective 还带 `references/research/quotes.md`(URL 锚定金句库,production-seed
档)或 `references/sources/`(transcript 原文)。它们不是 skill 自身的一部分 —— 但是日后
EVOLUTION / refresh perspective 时的入口。

## 7. 数据格式约定

### 7.1 brand-slug → 路径

```
brand: "OpenClaw"          → slug: openclaw         → reports/openclaw/
brand: "字节豆包"           → slug: bytedance-doubao → reports/bytedance-doubao/
brand: "Aibrary"           → slug: aibrary          → reports/aibrary/
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

`<judge>` = 解析后 panel 里每位评委的 slug,文件数 = panel 大小(default 5 / auto 5 /
security-cn-global 6)。slug 取自 15 套 perspective 之一(`fusheng` / `jobs` / `likejia` /
`wu-jundong` / `zhang-yiming` / `musk` / `leijun` / `lixiang` / `hexiaopeng` / `libin` /
`zhouhongyi` / `zhangmingzheng` / `renzhengfei` / `jensenhuang` / `satyanadella`)∪ 用户自定义。
EVOLUTION 模式重打分写 `reviews/<judge>_v{n+1}.md`,旧卡保留。

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
- `Bash` 用于跑 `python3 scripts/wuying/open.py`

如果 Claude Code 取消或重命名以上任何能力,SKILL.md 必须同步改。

## 10. 与外部生态的接口

| 外部 | 接口 | MBA 怎么用 |
|---|---|---|
| Anthropic API | Claude Code 内部代理 | 所有 LLM 调用走它 |
| 阿里云无影 AgentBay | Python SDK `agentbay` | `scripts/wuying/open.py` 创建 / 销毁 session |
| GitHub | git push / pull | 报告版本控制 + 团队协作 |
| (未来) Cloudflare Pages | 静态托管 | 把 reports/ 公开给同事看,详见 mcp-server-design.md |

## 11. 关键约束 / 不变量

- 评委独立打分,**互不可见对方 review 文件**(在 Phase 4 prompt 里显式说"DO NOT read other judges' files")
- `versions/` 下的文件**不可变**(EVOLUTION 不改它们,只 append 新版本)
- `report.md` 是 canonical(滚动覆盖),`versions/v{n}_*.md` 是 immutable snapshot
- 评委 perspective skill 顶部的 anti-fabrication 红线**适用 MBA 调用时**(在 Phase 4 prompt 里显式 re-read)
- Wuying session 必须 teardown,在 `wuying_browse.md` 里写明 teardown 状态
