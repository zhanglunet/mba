# MBA — Metric Brand Auditor · 项目全景介绍

> 全面介绍版（非 5 分钟 pitch）。覆盖问题、解法、架构、产品、商业化、壁垒。
>
> 渲染版：`mba-overview-deck.html`（自包含，浏览器直接打开，← / → 翻页）

---

## Slide 1 · 封面

**MBA — Metric Brand Auditor**

把品牌影响力做成可调研、可打分、可比较、可复盘的智能资产。

- 站点：mbabrand.com
- BotLearn：metric-brand-auditor
- 团队：Jason（创意）· 清风（实现）· John（顾问）
- 协作 AI：Claude Opus 4.7

---

## Slide 2 · 一句话定位

**MBA 是 AI 时代的品牌影响力审计协议。**

不是写一份品牌报告，而是把一家公司在 AI Agent 世界里的影响力，拆成 7 个维度 × 5 个镜头，由 Lead 编排、子 agent 并行调研、5 位人物评委独立打分，输出版本化报告。

---

## Slide 3 · 升维：品牌正在变成什么

过去，品牌主要影响**人**。

未来，越来越多的判断会被 **Agent** 参与甚至代理：

- 投资 Agent 筛公司
- 采购 Agent 推荐供应商
- 招聘 Agent 理解雇主品牌
- 消费 Agent 比较产品
- 战略 Agent 持续追踪竞争格局

> 品牌正在从"人类心智资产"变成"智能体世界里可识别、可比较、可调用的信号资产"。

---

## Slide 4 · 问题：品牌很重要，但今天不可审计

| 现有方式 | 缺陷 |
|---|---|
| 咨询公司报告 | 一次性、主观、不可复盘 |
| 舆情 / 社媒工具 | 只能告诉你声量，不能告诉你品类定义权与叙事是否成立 |
| 创始人 / 投资人 / CMO 的判断 | 高度依赖个人经验，难标准化、难跨公司比较、难跨时间追踪 |

> 财务有审计、产品有数据分析、销售有 CRM、舆情有 monitoring。
> **品牌影响力没有审计协议。** MBA 要做这个协议。

---

## Slide 5 · 三个老问题 → MBA 的三个机制

| 传统报告的问题 | MBA 的应对 |
|---|---|
| 单线程单视角 | **N 路并行 sub-agent** + **5 位人物评委**独立打分，Lead 只做合成 |
| 不可复盘 | **版本化目录** `reports/<brand>/versions/v{n}_{date}.{md,html}`，evolution 滚动 |
| 打分主观、口径漂移 | **固定 5 镜头 × 7 维度**，跨品牌、跨评委、跨时间同口径 |

---

## Slide 6 · 7 个调研维度（横向）

子 agent 并行跑的输入维度：

1. **创始 & 起源叙事** — 创世神话省略了什么 / 一手 vs PR 复用
2. **产品 & 定位** — 一句话定位 / 新品类宣称 / 比较与回避
3. **分发 & 渠道** — 自有 / earned / paid 的真实占比
4. **社区 & PR** — 谁在站台 / 谁在攻击 / 各自利益
5. **视觉 & 语言** — 命名 / slogan / 元符号（如 OpenClaw 🦞）
6. **竞品 & 格局** — 谁让出地盘 / 谁借用了它的语言
7. **接收 & 情绪** — 搜索趋势 / 增长 / 媒体口径

---

## Slide 7 · 5 个打分镜头（纵向）

5 位评委手里的同一把尺子：

1. **原创性 / Origin authenticity** — 叙事是否站得住
2. **范畴命名 / Category coinage** — 是否真定义了一个新品类、且粘住
3. **杠杆质量 / Leverage quality** — 影响力渠道是否结构性可持续
4. **身份一致性 / Identity coherence** — 视觉 / 语言 / 产品是否同一种感觉
5. **真实信号 / Real-world signal** — 评委自己愿意为之下注的程度

> 维度是"调研的输入"，镜头是"评委的尺子"，两者通过 `_raw/synthesis.md` 耦合。

---

## Slide 8 · 5 位人物评委

每人一个独立的 perspective skill，加载自己的世界观打分：

| 评委 | 身份 / 视角 |
|---|---|
| **傅盛** | 猎豹移动 / OpenClaw，AI 应用为王 + 战略三板斧 |
| **Steve Jobs** | Apple / NeXT / Pixar，Liberal Arts × Technology + focus = saying no |
| **李可佳** | BotLearn / Aibrary，协议位 + 新物种命名 |
| **吴俊东** | Aibrary 联创 / 前 TAL 战投，教育本质 + 长期关系投资 |
| **张一鸣** | 字节跳动，Context not Control + 火星视角 |

> 每套 skill 基于公开一手访谈与文章（80%+ 一手来源），顶部有 anti-fabrication 红线。

---

## Slide 9 · 流水线五阶段（FRESH 模式）

```
Phase 0  Router          检查 reports/<brand>/report.md 是否存在
  │                      → 存在 ⇒ EVOLUTION 模式
  │                      → 不存在 ⇒ FRESH 模式
  │
Phase 1  Discovery       Lead 起草 PRD，用户确认维度（GATE 1）
  │
Phase 2  Parallel        一条消息派发 N 个 sub-agent（每维度 1 个）
  │      Search          + 1 个 wuying 云浏览器 agent（--quick 时跳过）
  │
Phase 3  Synthesis       Lead 读完所有 _raw/，产出 synthesis.md
  │
Phase 4  5-Judge Panel   并行派发 5 个评委，独立打分互不可见
  │
Phase 5  Lead Merge      产出 report.md + report.html + versions/v{n}.{md,html}
```

---

## Slide 10 · EVOLUTION 模式：可复盘的关键

> 真正有价值的不是"今天品牌几分"，而是"过去 30/90/180 天，品牌影响力发生了什么结构性变化"。

EVOLUTION 模式：

- Phase 0 路由器发现 `report.md` 已存在
- Phase 1E 列 diff plan：自上版以来可能变了什么
- 只重跑**变了的维度**
- 评委只在**受影响维度**上重打分
- 版本号 +1 写入 `versions/v{n}_<date>.{md,html}`

这让 MBA 从一次性报告变成品牌影响力的时间序列。

---

## Slide 11 · 输出物：拿到手是什么

每次运行产出 5 类文件：

| 文件 | 作用 |
|---|---|
| `report.md` | 当前 canonical Markdown 报告（滚动覆盖） |
| `report.html` | 自包含 HTML：Chart.js 雷达图 + 异议热力图 + Mermaid 影响力流程图 |
| `versions/v{n}_{date}.{md,html}` | 每次 evolution 的不可变快照 |
| `reviews/<judge>.md` | 5 位评委的独立打分卡 |
| `_raw/dimension_n_*.md` | 每个维度子 agent 的原始输出（可审计） |

---

## Slide 12 · 仓库 4 层架构

```
mba/
├── metric-brand-auditor/        ← 编排层：流水线主 SKILL
│   ├── SKILL.md                      Lead 的工作手册（Phase 0–5）
│   ├── references/                   维度模板 / 评委模板 / 云浏览器规范 / HTML 脚手架
│   └── reports/<brand>/              每个品牌一个文件夹
│
├── research/                    ← 工具层：PRD 多代理深度调研 skill
│
├── *-perspective/               ← 评委层：5 套人物视角 skill
│   └── fusheng / jobs / likejia / wu-jundong / zhang-yiming
│
└── scripts/wuying/open.py               ← 基建层：阿里云无影 AgentBay 云浏览器
```

每一层对应流水线一个阶段，且可独立调用。

---

## Slide 13 · 一行命令调用

```bash
/mba <brand>              # 标准全流程（自动判断 FRESH / EVOLUTION）
/mba OpenClaw             # 仓库内置 demo case
/mba <brand> --quick      # 跳过云浏览器 leg（开放网 only）
/mba <brand> --refresh    # 强制 EVOLUTION 重跑
/mba <brand> --no-judges  # 只做合成，跳过 5 评委
/mba <brand> --focus 1,3,7  # 只调研指定维度
/mba list                 # 列出已审计品牌 + 各自版本数
```

零依赖入口：`/mba <brand> --quick --no-judges`（只用 WebSearch + WebFetch）。

---

## Slide 14 · 样例：Lenovo 0992.HK

实际跑出的报告含：

- **品牌影响力雷达图**（5 镜头评分）
- **异议热力图**（5 位评委 × 5 镜头打分差异）
- **Mermaid 影响力构造图**（杠杆从哪里来、流到哪里）
- **执行摘要 / 杠杆地图 / 脆弱边缘 / 跨维度矛盾**
- **90 天行动建议**

样例地址：mbabrand.com/reports/lenovo · 含 PDF + 一键安装

---

## Slide 15 · 演示站点 mbabrand.com

- 首页：项目机制与核心理念
- `/reports/<brand>/` 路径：已发布的品牌审计样例
- BotLearn 一键安装入口
- 黑客松 5 分钟 Pitch 稿（MD + HTML）

> 站点本身用 site/ 下的 build.sh 静态生成，published-reports.txt 控制发布列表。

---

## Slide 16 · 技术栈

| 层 | 技术 |
|---|---|
| 编排 | Claude Opus 4.7 + Claude Agent SDK |
| 并行调研 | Lead 一条消息派发 N 个 general-purpose sub-agent |
| 开放网调研 | WebSearch + WebFetch |
| 中文真实信号 | 阿里云无影 AgentBay 云浏览器（X / 小红书 / Bilibili / 中文媒体） |
| 可视化 | Chart.js（雷达 + 热力图）+ Mermaid（流程图） |
| 报告分发 | 自包含 HTML + Markdown + 版本快照 |
| 分发渠道 | BotLearn skill 一键安装 |

---

## Slide 17 · 目标用户与场景

不卖给普通市场部。卖给**真正关心"品牌如何转化为战略资源"的人**：

| 用户 | 场景 |
|---|---|
| **创始人 / CEO Office** | 战略叙事一致性诊断 / 融资 deck 前的品牌镜子 |
| **投资人 / VC / PE** | Brand Influence Due Diligence / portfolio 持续监控 |
| **战略部 / IR** | 上市公司品牌叙事审计 / 竞品定位追踪 |
| **品牌 / 增长团队** | 发布前复盘 / 品类定义权验证 |
| **咨询公司** | 输入素材层，加速尽调与战略项目 |

---

## Slide 18 · 商业化路径（三层）

| 层 | 形态 | 价值 |
|---|---|---|
| 1 | **单次审计**（高价值） | 创业 / 上市公司 / 投资标的一次完整 Brand Influence Audit |
| 2 | **持续监控订阅** | portfolio / watchlist / 自家 + 核心竞品的月度 evolution |
| 3 | **Skills 平台化** | Brand Audit / Category Mapping / Narrative Diff / Investor Memo / IPO Narrative Check / Founder Story Audit 等可调用 skills |

第二层的本质：把品牌影响力变成时间序列。

---

## Slide 19 · 壁垒：五件事

1. **审计框架** — 7 维度 × 5 镜头，固定口径
2. **多智能体流程** — Lead 拆解、Research Agents 并行、Judge Skills 独立、可复盘
3. **版本化数据库** — 每次审计是一次品牌快照，时间越长系统越知道品牌如何演化
4. **跨品牌 benchmark** — 审计足够多公司后，能比较谁有品类定义权、谁的叙事在增强
5. **可治理输出** — 评委头像 / 评分 / 辩论标注为 AI 模拟；商业化版本升级成角色化 Lens（Investor / Founder / Product / Category / Distribution / Culture）

---

## Slide 20 · 与单一 AI 报告的区别

| 维度 | 普通 AI 品牌分析 | MBA |
|---|---|---|
| 调研路径 | 单 prompt 单线程 | N 路并行 sub-agent + 云浏览器 leg |
| 打分主体 | 模型自己 | 5 位独立人格评委（互不可见） |
| 维度口径 | 每次漂移 | 固定 7 维度 × 5 镜头 |
| 时间维度 | 一次性 | EVOLUTION 模式 + 版本快照 |
| 可审计性 | 黑盒 | 子 agent 原始输出 + 评委打分卡 + 引用索引全留痕 |
| 输出形态 | 一段文字 | Markdown + 自包含 HTML（雷达 / 热力图 / 流程图） |

---

## Slide 21 · Anti-fabrication 红线

5 套人物视角 skill 都基于**公开一手资料**：

- 访谈、文章、播客 transcript
- 每套 SKILL.md 顶部明确：**不替本人编造未公开内容**
- 评委对自己留白的话题（家庭、未公开决策细节）保持沉默
- 网站明确声明：评委头像、评分、辩论是 AI 模拟，不代表本人真实意见，不构成投资建议或真实品牌评价

> 商业化版本会去掉真人模拟风险，升级为角色化 Lens（Investor Lens / Founder Lens / Product Lens / Category Lens / Distribution Lens / Culture Lens）。

---

## Slide 22 · 已落地的实物清单

- ✅ `metric-brand-auditor/SKILL.md`（~600 行主手册）
- ✅ 5 套 perspective skill，每套 6 路调研 + research/01–06.md
- ✅ `research` skill（可独立 `/research` 调用）
- ✅ Wuying 云浏览器 leg + smoke test
- ✅ 自包含 HTML 报告模板（Chart.js + Mermaid）
- ✅ 演示站点 mbabrand.com + 静态构建脚本
- ✅ BotLearn 一键安装：`metric-brand-auditor` v0.2.15+
- ✅ Lenovo 样例报告 + PDF
- ✅ 黑客松 5 分钟 Pitch 稿（MD + HTML）

---

## Slide 23 · 愿景：Brand Influence Ledger

> 未来每一家重要公司，都需要一份持续更新的 **Brand Influence Ledger**。

就像公司有：

- 财务报表（财务）
- 数据看板（产品）
- CRM（销售）
- 监控系统（舆情）

**品牌影响力也应该有自己的审计系统。**

它决定一家公司能调动多少社会资源——人才、渠道、资本、定价权、品类话语权、以及在 AI Agent 世界里被正确理解和优先推荐的能力。

---

## Slide 24 · 一句话总结

**我们不是在做 AI 品牌报告。**

**我们是在做 AI 时代的品牌影响力审计协议。**

MBA 把品牌影响力从主观感觉，变成可调研、可打分、可比较、可复盘、可持续追踪的智能资产。

---

## Slide 25 · 谢谢

- 站点：**mbabrand.com**
- 一键安装：**botlearn.ai/skillhunt/v2/s/metric-brand-auditor**
- 样例：**mbabrand.com/reports/lenovo**
- 团队：Jason · 清风 · John
- 技术支持：marsdata.ai

`/mba <brand> --quick --no-judges` — 三十秒上手。
