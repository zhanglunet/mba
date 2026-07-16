# MBA 文档目录

本目录覆盖 MBA(Metric Brand Auditor)当前代码库的完整设计与实现说明。

## 阅读顺序

新人推荐顺序:**01 → 02 → 03 → 04 → 06 → 05**(产品 → 技术 → 用)

| 编号 | 文档 | 受众 | 一句话 |
|---|---|---|---|
| - | [`../README.md`](../README.md) | 所有人 | 项目门面、5 分钟概览 |
| 01 | [01-prd.md](01-prd.md) | 产品 / 决策者 | 解决什么问题、目标用户、成功指标、范围边界 |
| 02 | [02-product-design.md](02-product-design.md) | 设计 / PM | 用户旅程、报告产物、评委卡片、维度语义 |
| 03 | [03-architecture.md](03-architecture.md) | 工程 | 仓库分层、模块依赖、数据流、关键 abstraction |
| 04 | [04-pipeline.md](04-pipeline.md) | 工程 | 5 阶段流水线的实现细节(每 phase 的输入/输出/坑) |
| 05 | [05-usage.md](05-usage.md) | 用户 | 怎么调、参数清单、5 个完整示例、FAQ |
| 06 | [06-installation.md](06-installation.md) | 用户 | 环境前置、克隆、配 .env、校验、故障排除 |
| 07 | [07-code-standards.md](07-code-standards.md) | 贡献者 | SKILL.md 写法、命名、commit、Python 风格 |
| 08 | [08-extending.md](08-extending.md) | 贡献者 | 加品牌 / 评委 / 维度 / 改 HTML 模板 |
| 09 | [09-agent-api.md](09-agent-api.md) | 集成方 / 贡献者 | For-Agents 机读层:/api 端点契约、生成器、CI 漂移守卫 |
| 10 | [10-deepening-perspectives.md](10-deepening-perspectives.md) | 贡献者 | seed → full tier 深化 SOP + 43 评委 tier 进度表 + Wuying 取数前提 |
| 11 | [11-roadmap.md](11-roadmap.md) | 全员 | **开发路线图 + 进度日志**：P0-P3 优先级计划、当前阻断项、每次开发动作记录 |
| 12 | [12-evolution-tracking.md](12-evolution-tracking.md) | 贡献者 | P3-B 报告订阅与品牌演化追踪设计 + 实现（触发器 / delta / 增量重跑 / 通知） |
| 13 | [13-mcp-quickstart.md](13-mcp-quickstart.md) | **用户 / 集成方** | MCP server 快速上手：安装、一次完整审计、演化订阅、舆情信号、16 工具参考 |
| 14 | [14-deepening-summary.md](14-deepening-summary.md) | 全员 | Perspective 深化收尾点时快照(2026-07-10):全景 + 坑记录,**非 live tracker**(权威 tier 名单以 docs/10 §6 / panels/*.yaml 为准) |
| 15 | [15-brand-watch-prd.md](15-brand-watch-prd.md) | 产品 / 决策者 | **品牌舆情监控(Brand Watch)需求分析 PRD**:9 监控维度(招投标 W3 深潜)、事件模型与 P0-P3 分级、舆情→EVOLUTION 触发规则、13 品牌适用性矩阵 |
| 16 | [16-brand-watch-implementation.md](16-brand-watch-implementation.md) | 贡献者 | **Brand Watch 实现与过程记录**:W 系列开发计划、数据层与校验器实现、源可达性验证表(含 b2b.10086.cn TLS workaround)、试点采集记录与 SOP;**做一项记一项** |
| 17 | [17-logo-design.md](17-logo-design.md) | 设计 / 对外 | 站标设计说明与使用规范:五镜头雷达 glyph + 字标(线上版 [mbabrand.com/logo-design.html](https://mbabrand.com/logo-design.html)) |
| 18 | [18-social-fulltext.md](18-social-fulltext.md) | 贡献者 / 运维 | 中文社媒正文(知乎/微博/小红书)免费方案调研(无影平替)+ 本机 Playwright 抓取脚本(`scripts/social-fetch/`);线上版 [mbabrand.com/social-fetch.html](https://mbabrand.com/social-fetch.html) |
| 19 | [19-feishu-notify.md](19-feishu-notify.md) | 运维 / 用户 | **飞书群推送**:品牌监控/舆情信号有变化(新增 P0/P1 事件 / 建议重审 / 评分变动)时,CI 合并到 main 自动推一张飞书卡片;配置(webhook + 可选签名)、门槛、卡片格式、`--dry-run` 调试 |
| 20 | [20-sentiment-cockpit-mapping.md](20-sentiment-cockpit-mapping.md) | 产品 / 决策者 / BD | **舆情驾驶舱需求 × MBA 能力映射**:企业级舆情监测的通用需求(主体/数据源/7 标签/看板/分层预警)逐项对照 MBA Brand Watch,标 ✅可复用/🔧需适配/➕增量/⚠️共同缺口;含覆盖度速览 |
| 21 | [21-founder-dimension.md](21-founder-dimension.md) | 产品 / 贡献者 | **创始人维度**:梳理品牌创始人履历 + 从人物角度看创始人↔品牌关系(按 5 镜头);`founders/<slug>.yaml` 数据层 + `build_founder_pages.py` 生成独立创始人页 + `validate_founders.py` 硬 gate;含 schema、SOP、反捏造约定、开发计划存档 |
| - | [wuying-usage.md](wuying-usage.md) | 用户 / 运维 | 阿里云无影 AgentBay 云浏览器 leg 的实操参考 |
| - | [mcp-server-design.md](mcp-server-design.md) | 未来贡献者 | MBA → MCP server 的设计与开发手册(原始设计草案) |
| - | [hackathon/](hackathon/) | 对外 | 5 分钟 pitch + overview deck(Markdown / HTML / PPTX) |
| - | [daily/](daily/) | 全员 | **每日工作日报**:每天盘点前一天合并到 main 的提交/PR(`scripts/new_daily.py`,cron 自动落库);`week` 子命令合成周报草稿 |
| - | [weekly/](weekly/) | 全员 | 每周进展周报(`scripts/new_weekly.py`,Markdown 单一真源 → `site/weekly.html`) |

> 与代码并存的两份"局部 README"也是一等文档:`metric-brand-auditor/panels/README.md`(panel
> 字段与 resolver)和 `site/README.md`(mbabrand.com 发布流程)。

## 维护原则

- **单一事实源**:行为以 `metric-brand-auditor/SKILL.md` 为准。文档解释 SKILL.md,不替代它。
- **两种形态**:01-08 描述 Claude Code skill 模型;12-13 + `packages/mcp-server/` 是已实现的 MCP server 形态(mba-mcp-server v0.2.0,16 工具),`mcp-server-design.md` 是其原始设计草案。二者共享同一条 5 阶段流水线逻辑。
- **改 SKILL.md 之后**:对应章节也要更新(主要影响 03 / 04 / 08)。
- **每个文件顶部 Status / Last verified**:从 v0.3 起强制(本批次先发,后续补)。
