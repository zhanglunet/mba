# 01 — 产品需求文档(PRD)

## 1. 项目愿景

让"评估一个品牌的影响力"从一项**手工咨询服务**变成一条**可重复执行、可演化追踪、可跨品牌可比**的自动化流水线。

## 2. 问题陈述

传统的"品牌影响力评估"有三大顽疾:

1. **单线程单视角** —— 一个分析师写一份报告,容易陷入自家叙事或个人偏好
2. **不可复盘** —— 报告一次性,半年后再看不知道哪些结论已过时
3. **打分主观、口径漂移** —— 每个分析师有自己的尺度,跨品牌、跨时间不可比

MBA 用三条对应机制解决:

| 顽疾 | MBA 应对 |
|---|---|
| 单线程单视角 | N 条并行 sub-agent + 5 位人物评委独立打分 |
| 不可复盘 | 版本化目录 + EVOLUTION 模式(只 diff 变了的部分) |
| 打分漂移 | 固定 5 镜头 × 7 维度,跨品牌跨时间同一坐标系 |

## 3. 目标用户

### 3.1 主用户(Primary)

- **AI Native 的早期投资人 / FA**(熟悉 Claude Code、看品牌叙事是工作之一)
  - 痛点:一周看 5-10 个 pitch,品牌叙事真假难辨
  - MBA 给:25 分钟出一份带 5 评委独立打分的报告

- **品牌运营 / 创始人 / GTM 负责人**(想定期 self-audit 自家品牌)
  - 痛点:自我感觉良好 / 看不到 outsider 视角
  - MBA 给:每月跑一次 EVOLUTION,看影响力地图怎么变

### 3.2 次用户(Secondary)

- 内容创作者(写品牌深度文之前先跑一份当事实参考)
- AI Agent 框架开发者(把 MBA 当作可复用的"品牌评估"组件,见 `mcp-server-design.md`)

### 3.3 不是目标用户

- 不熟悉 Claude Code / 命令行的非技术用户(v1 不做 GUI)
- 想要"5 分钟出报告"的人(MBA 默认 25 分钟出一份)
- 想要"打 5 颗星好评"的人(评委可能给低分,这是 feature 不是 bug)

## 4. 功能需求(Functional)

### F1 — 全流程审计

输入一个品牌名(或主页 URL),输出:
- 一份 markdown 报告 + 一份 HTML 报告(Chart.js 雷达图 + 异议热力图 + Mermaid 影响力图)
- 5 位评委独立打分卡
- 每个研究维度的原始材料(`_raw/`)

### F2 — 演化模式(EVOLUTION)

已有报告时再次跑同一品牌:
- 自动识别哪些维度可能变了
- 只对变了的维度做 delta 调研
- 让评委只对变了的维度重打分
- 写入 `versions/v{n+1}_<date>.{md,html}`,保留历史

### F3 — 评委可配置

- 内置 production 评委默认包含 default panel 5 位,并可扩展到行业 panel(如 auto)
- 可通过 `--panel <name>` 选择命名评委组,或通过 `--industry <name>` 按行业映射选择 panel
- 可通过 `--panel-add <slug>` / `--panel-drop <slug>` 做本次运行的临时增删
- 可通过在 `perspectives/` 下追加 `<slug>-perspective/` 目录添加自定义评委(详见 [08-extending.md](08-extending.md))

### F4 — 维度可配置

- 默认 7 维度
- 可通过 `--focus 1,3,7` 限定
- 可在 `references/dimensions.md` 加新维度

### F5 — 多种输出格式

- markdown(给 LLM / 工具消费)
- HTML(给人看,自包含,无构建)
- 中间产物(`_raw/`)用于复盘和 EVOLUTION

## 5. 非功能需求(Non-functional)

| 维度 | 目标 |
|---|---|
| 延迟 | 单品牌 FRESH 模式 ≤ 30 min;EVOLUTION ≤ 10 min |
| 可靠性 | 单 sub-agent 失败时整体不崩,标注缺口继续合成 |
| 成本 | 单次 FRESH 审计 ≤ $5(Anthropic API token 成本) |
| 可读性 | HTML 报告无外部字体依赖,离线可读 |
| 可移植 | 整个流水线只依赖 Claude Code + Anthropic API + 阿里云无影(可选) |
| 透明度 | 每条结论必须有 `_raw/` 引用可追溯 |

## 6. 成功指标

### 短期(v0.x)

- 跑通 5+ 真实品牌(OpenClaw / Aibrary / BotLearn / 任意 2 个外部测试)
- 5 评委的打分能稳定区分(同一品牌不同评委分差 ≥ 2 分,证明评委没"被洗"成同质)
- HTML 报告渲染零错(Chart.js + Mermaid 全部成功)

### 中期(v1.0)

- 至少 3 个外部用户独立用过(不是仓库 owner)
- 至少一份报告被引用进真实决策(投资 / 品牌策略调整)
- 评委扩展点被使用(有人加了第 6 个评委)

### 长期

- MCP 化后,被嵌入 ≥ 2 个 agent 框架(参考 `mcp-server-design.md`)

## 7. 范围边界(明确不做)

- ❌ **不做实时数据**:报告反映 cutoff 时刻的快照,不做 live dashboard
- ❌ **不做评委的金融预测**:评委给"杠杆质量"打分,不给"未来 6 个月估值"
- ❌ **不做 SaaS 多租户**:用户自带 API key 自己跑(SaaS 是 Layer 2,见 `mcp-server-design.md`)
- ❌ **不做反爬攻防**:云浏览器 leg 遇到 captcha 就降级到 web-only,不强行绕
- ❌ **不替评委编造**:每个 perspective skill 顶部都有 anti-fabrication 红线,违反 = bug

## 8. 假设与约束

- 用户已熟悉 Claude Code 的 skill 调用方式(没接触过的用户不是当前 v0.x 的目标)
- 用户有 Anthropic API key 和(可选)阿里云无影 AgentBay key
- 评估对象主要是中国/全球科技品牌(因此评委选择偏中国 + Jobs)
- 报告语言以中文为主,英文术语保留
- 不假设有 GPU / 不假设有数据库

## 9. 风险与缓解

| 风险 | 缓解 |
|---|---|
| Anthropic API 限流 | sub-agent 数量受 `MBA_MAX_PARALLEL`(默认 5)限制 + 指数退避 |
| 评委被"洗"成同质化 | 5 评委各自 perspective skill 独立 LOAD + anti-fabrication 红线 + "DO NOT read other judges' files"显式注入 |
| 用户用错 API key 烧了一笔 | `--quick` 跳过云浏览器、Phase 1 PRD 显示成本估算、用户在 GATE 1 可终止 |
| 反爬 / 内容墙 | wuying-browser.md 显式记录"哪些没拿到",报告里标 N/A 不假装拿到了 |
| SKILL.md 漂移 / 文档过期 | 03 / 04 文档明确"以 SKILL.md 为准",每次大改 SKILL 同步更新 |
| 评委依赖的人物公开资料过期 | 每个 perspective 有 cutoff 注明日期,调研材料每半年补一次 |

## 10. 版本与里程碑

- **v0.1.0** — 5 perspective skills + 无影脚本(已发)
- **v0.2.0** — metric-brand-auditor + research skill(已发)
- **v0.2.1** — README 重写 + 完整 docs/(已发)
- **v0.2.14** — 路径去 hardcode,引入 `${SKILL_DIR}` 等运行时符号(已发)
- **v0.2.19** — panel 系统:`panels/*.yaml` + `--panel` / `--industry` + 品牌绑定;auto panel 可运行(已发)
- **v0.2.2x** — security-cn-global 6 人 panel + perspective 增至 15 套 + perspective-structure-spec + CI 校验 + site 发布(mbabrand.com)
- **2026-06** — perspective skill 收纳到 `perspectives/` 子目录(SKILL.md 路径兼容旧布局)+ For-Agents 机读层(`site/api/*.json` + `llms.txt` + `agents.html`)+ 项目介绍 presentation deck(当前)
- **v0.3** — 填齐 7 个 SKELETON 行业 panel 的评委 + 持续改进 SKILL.md(以 issue 驱动)
- **v0.4+** — MCP 化(参考 [mcp-server-design.md](mcp-server-design.md))

## 11. 衍生需求(待评估)

- **批量审计**:一次跑 10 个竞品,产出对比表
- **品牌报告订阅**:用户订阅一个 brand,每月自动 EVOLUTION 推送
- **评委辩论模式**:5 评委读完彼此 review 之后再写一轮"反驳",看共识能否被打破
- **本地静态服务**:把 reports/ 起一个 `python3 -m http.server` 给同事内网访问

这些都不在 v0.x 范围内,留作 RFC。
