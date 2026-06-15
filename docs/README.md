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
| - | [wuying-usage.md](wuying-usage.md) | 用户 / 运维 | 阿里云无影 AgentBay 云浏览器 leg 的实操参考 |
| - | [mcp-server-design.md](mcp-server-design.md) | 未来贡献者 | MBA → MCP server 的设计与开发手册(未来形态) |
| - | [hackathon/](hackathon/) | 对外 | 5 分钟 pitch + overview deck(Markdown / HTML / PPTX) |

> 与代码并存的两份"局部 README"也是一等文档:`metric-brand-auditor/panels/README.md`(panel
> 字段与 resolver)和 `site/README.md`(mbabrand.com 发布流程)。

## 维护原则

- **单一事实源**:行为以 `metric-brand-auditor/SKILL.md` 为准。文档解释 SKILL.md,不替代它。
- **当前 vs 未来**:01-08 描述当前 Claude Code skill 模型;`mcp-server-design.md` 描述未来 MCP 化形态,二者不冲突,后者基于前者。
- **改 SKILL.md 之后**:对应章节也要更新(主要影响 03 / 04 / 08)。
- **每个文件顶部 Status / Last verified**:从 v0.3 起强制(本批次先发,后续补)。
