# 05 — 使用方法

本文档面向最终用户:怎么调 MBA、有哪些参数、跑通的完整示例、FAQ。

- 装环境 → [06-installation.md](06-installation.md)
- 扩展(加品牌/评委/维度)→ [08-extending.md](08-extending.md)
- 报错/卡住 → 本文 §5 FAQ

## 1. 最简调用

在 Claude Code 里:

```
/mba OpenClaw
```

Lead 会:

1. 检查 `metric-brand-auditor/reports/openclaw/report.md` 是否存在
2. 不存在 → 起草 PRD,等你确认
3. 存在 → 走 EVOLUTION 模式

> **品牌 slug 默认从 brand 名转**:`OpenClaw` → `openclaw`。如果不满意,在 Phase 1 GATE 时改一下,例如 `slug: openclaw-2026q2`。

## 2. 参数清单

| Flag | 类型 | 默认 | 含义 |
|---|---|---|---|
| `<brand>` | 位置参数 | 必填 | 品牌名或主页 URL |
| `--quick` | 开关 | off | 跳过 wuying 云浏览器 leg(只走 web search) |
| `--refresh` | 开关 | off | 强制 EVOLUTION 重跑(已有报告归档到 versions/) |
| `--no-judges` | 开关 | off | 只做合成,跳过评委(快速预览用) |
| `--focus 1,3,7` | 列表 | 全部 7 | 限定调研维度 |
| `--panel vc-en` | 名称 | default | 使用一套命名评委 panel |
| `--industry auto` | 名称 | - | 按行业映射选择 panel,例如 `auto` / `ai` / `consumer` |
| `--panel-add pmarca` | slug | - | 本次临时追加一位评委,不修改 panel 文件 |
| `--panel-drop jobs` | slug | - | 本次临时跳过一位评委,不修改 panel 文件 |
| `--dry-run` | 开关 | off | 预览审计计划(解析路径/面板/模式),不执行任何搜索或文件写入 |
| `--watch` | 开关 | off | Brand Watch 单次舆情扫描:只采可溯源事件进 `watch/<slug>/events.yaml` + 触发规则评估,不跑评委不出报告(docs/15) |
| `--panel-merge` | 开关 | off | 跨面板对比模式:用第二套评委重新打分,生成两套面板的并排比较报告。需与 `--panel`/`--industry` 配合使用,且品牌必须已有历史报告 |
| `list` | 子命令 | - | 列出已审计品牌 + 各自版本数 + 绑定的 panel |
| `panels` | 子命令 | - | 列出 `panels/` 下所有 panel + judge 列表 |
| `panels show <name>` | 子命令 | - | 打印某个 panel 的完整 yaml |
| `panels new <name>` | 子命令 | - | 从 default.yaml 复制出一份 panel 骨架 |

> **全部 panel 可运行**:`default` / `auto` / `security-cn-global` / `ai-app-cn` / `edu-cn` / `vc-en` / `vc-cn` / `consumer-cn` / `cross-border` / `luxury-en` 十套 panel 评委都已建齐(v1 production-seed),可真打分,**已无 skeleton**。`--industry` 名见 `panels/industries.yaml`;未来若新增占位 panel(`status: skeleton`),跑到会自动降级为 synthesis-only。

## 3. 完整示例

### 3.1 第一次跑一个新品牌

```
> /mba OpenClaw

[Lead] No prior report for openclaw. Running fresh pipeline:
       discovery → parallel search → synthesis → N-judge panel → merge.
       Estimated 20-25 minutes.

       Drafting Brand Influence PRD...

       ### Brand Influence Research Proposal — OpenClaw

       **Subject:** OpenClaw — 傅盛 / 猎豹在 2026 年发起的"龙虾上大学" Agent 项目,
                    主打"AI 是新物种,该有自己的大学"

       **Research Objective:** Map how OpenClaw's influence is constructed...

       **Default Dimensions (7):** {表格}

       **Wuying cloud-browser leg:** YES
       **Judge panel:** default — fusheng / jobs / likejia / wu-jundong / zhang-yiming
       **Estimated runtime:** ~22 minutes.

       --- GATE 1 ---
       Confirm to proceed, or send edits.

> ok 跑

[Lead] Dispatching 5 sub-agents in parallel for dimensions 1-5...
       (10 min later)
       Dimensions 1-5 complete. Dispatching dimensions 6-7 + wuying leg...
       (8 min later)
       All sub-agents returned. Writing synthesis...
       Synthesis ready. Dispatching 5 judges in parallel...
       (6 min later)
       Reviews complete. Writing report.md and report.html...

       ### Done — OpenClaw v1

       **TL;DR:**
       - {Lead 5-bullet read}

       **Score Matrix:** {表格}

       **Files:**
       - reports/openclaw/report.md
       - reports/openclaw/report.html

       Want a per-judge deep-dive? A competitor scan?
```

### 3.2 半个月后回头看,跑 EVOLUTION

```
> /mba OpenClaw

[Lead] Found v1 dated 2026-04-25 (15 days ago).
       Switching to EVOLUTION mode — I'll do delta research and re-score
       only what's changed. Use --refresh if you want a full rebuild.

       Drafting diff plan...

       ### Likely changed since 2026-04-25:
       - Dimension 3 (Distribution): OpenClaw 2026-05 上了 36kr 头条 → 重跑
       - Dimension 4 (Community): X 上 5 月 8 日有一波吐槽 → 重跑
       - Dimension 7 (Sentiment): 30 天搜索趋势变化 → 重跑

       ### Unchanged (copy from v1):
       - Dimensions 1, 2, 5, 6

       --- GATE 1E ---

> ok 跑

[Lead] (10 min later) v2 ready. Delta highlights:
       - Dimension 3: leverage shift from owned to earned (+1 leverage quality)
       - Dimension 4: first material critic emerged ...

       reports/openclaw/report.md (now v2)
       reports/openclaw/versions/v2_2026-05-09.md (frozen snapshot)
```

### 3.3 只想看商业部分,不要视觉评估

```
> /mba <某品牌> --focus 2,3,4,6,7
```

Lead 只跑维度 2/3/4/6/7,跳过 1(创始叙事)和 5(视觉)。评委仍然 5 人,但他们的 score matrix 只在这 5 个维度上有数。

### 3.4 换一套行业评委 panel

```
> /mba 小米汽车 --industry auto --quick
```

`--industry` 会查 `metric-brand-auditor/panels/industries.yaml`,再解析到对应的
`panels/<name>.yaml`。如果 panel 是 `status: skeleton`,MBA 会清楚提示它仍是占位
或预览状态:能 resolve 到的评委照常跑,缺失的评委降级为 N-of-M 并打
`judges_incomplete` flag;如果全员缺失,才整体降级为 `--no-judges`。

`auto.yaml` 在 v0.2.19 已可用于 Phase 4:雷军是 full v1,马斯克 / 李想 / 何小鹏 /
李斌是 v1 preview。评小米 / Redmi / Xiaomi Auto / SU7 时默认加
`--panel-drop leijun`,避免创始人自评被当成中立横评。

网络安全 / 企业安全 / AI 安全品牌可用:

```
> /mba 某安全公司 --industry security-cn-global --quick
```

`security-cn-global` 会召回周鸿祎、张明正、任正非、黄仁勋、马斯克、Satya Nadella
六位视角。评 360 / Trend Micro / Huawei / NVIDIA / Microsoft 等强关联品牌时,使用
对应 `--panel-drop <judge>`;如果保留该评委,输出只能作为 founder self-check,不能当
中立横评分。

也可以直接指定 panel:

```
> /mba 某 SaaS --panel vc-en
```

首次运行会把解析后的 panel 写进 `reports/<brand>/panel.yaml`;之后同一品牌默认沿用这套
panel,保证 EVOLUTION 版本之间可比。

### 3.5 快速预览,不要评委

```
> /mba 某新品牌 --quick --no-judges
```

跳过 wuying leg + 跳过评委,只跑 Phase 2-3,产出 `_raw/synthesis.md`(没有 `reviews/`)。适合"先看 Lead 怎么看,再决定要不要花成本叫评委"。

### 3.6 正式运行前预览计划（--dry-run）

```
> /mba 小米汽车 --industry auto --dry-run
```

输出示例：

```
### MBA Dry-Run Plan — 小米汽车

Mode:          FRESH (no prior report)
Panel:         auto (5 judges)
Judges:        musk ✓  leijun ✓  lixiang ✓  hexiaopeng ✓  libin ✓
Wuying leg:    YES
Dimensions:    1 2 3 4 5 6 7 (all default)
Output path:   ~/mba/reports/xiaomi-auto/

Flags active:  --industry auto

— No files written. No network requests made. —
Re-run without --dry-run to execute the full pipeline (~20 min).
```

适用场景：
- 确认 `--industry` / `--panel` 解析是否如预期
- 验证所有评委的 perspective skill 都已安装（✓ = 已找到 / ✗ = 缺失）
- 跑正式流水线前确认品牌 slug、输出路径
- 多个 flag 组合时先检查 flag 解析结果

`--dry-run` 与任何其它 flag 组合均有效：

```
/mba 某品牌 --quick --panel vc-en --focus 1,2,7 --dry-run
```

### 3.7 跨面板对比审计（--panel-merge）

适合场景：同一品牌先用 default 面板审计，再想看 vc-en 的硅谷视角，两套结果并排比较。

```
# 第一步：先用默认面板做一次完整审计（已有报告则跳过）
> /mba 某 SaaS 品牌

# 第二步：用 vc-en 面板做对比，生成跨面板比较报告（v2）
> /mba 某 SaaS 品牌 --panel vc-en --panel-merge
```

输出（v2 新增章节）：

```
## Panel Comparison

### Side-by-Side Score Deltas
| Lens     | default mean | vc-en mean | Δ    | Direction |
|----------|-------------|------------|------|-----------|
| Origin   | 6.8          | 7.4        | +0.6 | ↑         |
| Category | 7.0          | 8.2        | +1.2 | ↑↑        |
| Leverage | 6.2          | 5.8        | -0.4 | ↓         |
| Identity | 4.6          | 6.0        | +1.4 | ↑↑        |
| Signal   | 6.4          | 5.2        | -1.2 | ↓↓        |

### Where the panels agree
Origin 和 Leverage 两个维度两套面板评分接近(σ < 1.0)——这是品牌最稳定的信号。

### Where the panels diverge
Category 分歧最大(Δ +1.2):vc-en 评委(PG / Andreessen / Naval)更看重"是否命名了新品类",
而 default 面板(傅盛 / Jobs)更看重执行到位而非命名本身。
```

注意事项：
- `--panel-merge` 必须有历史报告，否则 ABORT 并提示先跑 `/mba <brand>`
- 旧面板的 `reviews/*.md` 会被保留（不覆盖），新面板写入新 slug 的文件
- 研究数据（`_raw/`）默认复用（30 天内），加 `--refresh` 强制重新研究

### 3.8 列出所有已审计品牌

```
> /mba list
```

输出(示意):

```
已审计品牌(reports/ 下):
- openclaw          v3  最近更新 2026-05-09
- aibrary           v2  最近更新 2026-04-12
- bytedance-doubao  v1  最近更新 2026-03-15
```

> 仓库初始 reports/ 为空,跑过 `/mba <brand>` 之后才会出现条目。

## 4. 跑完之后

### 4.1 看报告

```bash
# Markdown 在终端 / VS Code 看
code metric-brand-auditor/reports/openclaw/report.md

# HTML 在浏览器看
open metric-brand-auditor/reports/openclaw/report.html
```

### 4.2 分享给同事

HTML 是单文件,直接拷给同事就行,他们不需要装任何东西。如果想要个 URL → 推到 GitHub 后用 Pages,见 [mcp-server-design.md](mcp-server-design.md) 的 Cloudflare 章节。

### 4.3 复盘 / 二次分析

```bash
ls metric-brand-auditor/reports/openclaw/
  report.md report.html versions/ _raw/ reviews/
```

- 想看某评委详细打分理由 → `cat reviews/fusheng.md`
- 想知道哪个维度数据来源 → `cat _raw/dimension_3_distribution-channels.md`
- 想看 Lead 合成时怎么想的 → `cat _raw/synthesis.md`

## 5. 常见问题(FAQ)

### Q1: 报错 "WUYING_API_KEY not set"

A: 你没配 `.env` 或 key 还是 placeholder。看 [06-installation.md](06-installation.md) 第 3 节。
   或者用 `--quick` 跳过 wuying leg。

### Q2: 评委给我家品牌打了低分,能投诉吗

A: 不能。评委的低分是 feature 不是 bug —— 那正是你花钱请 outsider 视角的原因。

但如果评委的理由明显**基于错误事实**,**那是 Phase 2 调研出错**,可以:

1. 看 `_raw/dimension_<n>_<slug>.md` 找到错误事实和它的引用
2. 加上正确的资料,跑 `--refresh` 重做
3. 或者直接 `cat _raw/synthesis.md`,看哪个事实点歪了,改完跑 EVOLUTION

### Q3: 跑到一半失败了,怎么续?

A: 当前 Claude Code 模式不支持续跑(状态没持久化在 server 端)。

重新跑 `/mba <brand>` 即可,Lead 会从 Phase 0 开始。但因为 `_raw/` 已经有上次的部分文件,你可以在 Phase 1 GATE 时告诉 Lead "复用 _raw/dimension_1.md, dimension_2.md,只跑剩下的"。

> MCP 化版本会原生支持 `resume_audit`(见 mcp-server-design.md)。

### Q4: 想加自家公司一位同事作为第 6 个评委

A: 见 [08-extending.md](08-extending.md) 第 2 节"添加新评委"。简版:在 `perspectives/` 下复制一个 `*-perspective/` 目录,改 SKILL.md frontmatter + 5 必需章节,然后把 slug 加进某个 `panels/<name>.yaml`,或用 `--panel-add <new-name>` 先临时试跑。

### Q5: Mermaid 图在 HTML 里渲染失败

A: 报告里会有降级表格 + 错误信息。打开 `report.html`,F12 看控制台具体报什么。

常见原因:Lead 在 Mermaid 节点名里用了 `(` `)` 之类元字符没转义。

修复方法:

1. 把 `report.md` 里 Mermaid 块手动改正
2. 让 Claude Code "重新渲染 reports/<brand>/report.html,基于改过的 report.md"
3. 下次 evolution 也会自动修(Lead 会读 report.md 拿数据)

### Q6: 评委总分能比较吗(品牌 A vs 品牌 B)

A: **能**,这是 MBA 设计的核心 —— 跨品牌可比是固定坐标系(5 镜头 × 7 维度)的全部价值所在。

但是注意:

- **均值有意义**(同一坐标系下)
- **单个评委分数有意义**(同一评委用同一标准)
- **单个评委跨品牌打分曲线**有意义(看出评委的偏好)
- **跨品牌跨评委的"加权平均"没意义**(评委独立,不该被加权)

### Q7: 一份报告大概要花多少钱

A: 单次 FRESH 模式约 $4-5(Anthropic API token);EVOLUTION 约 $1-2。Wuying Lite 套餐免费(只用 session 创建/销毁,不用 CDP)。

### Q8: 我想批量跑 10 个品牌,能并发吗

A: 当前不能,Claude Code 是单 session。workaround 是开 10 个 Claude Code 终端各自跑(每个有自己的 cost ceiling 风险)。MCP 化后会有 `mba.start_audit` 异步,可批量 enqueue。

### Q9: 报告语言能改成英文吗

A: 当前默认中英混排(章节标题英文 / 正文中文 / 评委 quote 各自语言)。完全英文模式还没实现,backlog。可以在 GATE 1 显式说"全部用英文"试试 Lead 是否照做。

### Q10: 我能把 MBA 嵌进我自己的 agent 框架里吗

A: 当前 v0.x 不行(Claude Code 专属)。MCP 化后(v0.4+)可以,见 [mcp-server-design.md](mcp-server-design.md)。
