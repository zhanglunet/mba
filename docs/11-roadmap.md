# MBA 开发路线图与进度日志

> **文档定位**：本文件同时承担两个职责——  
> 1. **路线图**：记录下一步开发计划，优先级和理由  
> 2. **进度日志**：每次开发动作在此追加记录，形成可查历史

---

## 当前状态快照（2026-06-25）

| 维度 | 状态 | 备注 |
|------|------|------|
| 版本 | v0.2.38 | |
| 5阶段流水线 | ✅ 生产就绪 | Phase 0-5 + Phase 5M（panel-merge）稳定 |
| 评委面板数量 | ✅ 10/10 全部可运行 | default / auto / security-cn-global / ai-app-cn / edu-cn / vc-en / vc-cn / consumer-cn / cross-border / luxury-en |
| 评委全档进度 | ⚠️ 15/43 全档 | 28 人仍在 seed 层，待深化 |
| mbabrand.com | ✅ 上线 | Cloudflare Pages |
| 公开报告 | ✅ 2 份 + 8 个 pending | Lenovo + 成市 Auto；8 品牌建档待审计 |
| CI/CD | ✅ 运行中 | 面板校验 + 结构检查 + 站点构建 |
| 集成测试 | ✅ 已建立 | report-validation.yml（validate_report.py + validate_html_report.py） |
| --dry-run 标志 | ✅ 已实现 | Phase 0 §0.5 dry-run exit |
| --panel-merge 标志 | ✅ 已实现 | Phase 5M 跨面板对比流程 |
| MCP Server 形态 | ✅ v0.1.0 完成 | packages/mcp-server/ · 6 工具 · Phase 2-5 编排 · 22 tests |

### 评委全档分布（v0.2.36）

**已完成全档（15 人）**

| 面板 | 评委 slug |
|------|-----------|
| default | fusheng, jobs, likejia, wu-jundong, zhang-yiming |
| auto | musk, leijun, lixiang, hexiaopeng, libin |
| security-cn-global | zhouhongyi, zhangmingzheng, renzhengfei |
| vc-en | jensenhuang, satyanadella |

**待深化（28 人）**

| 面板 | 待深化评委 | 可用资料情况 |
|------|-----------|-------------|
| ai-app-cn | 3 人（wangxiaochuan, wanghuiwen, limuou） | 中文为主，需 Wuying Pro |
| edu-cn | 3 人（salkhan, shouzicheng, huangzheng） | 部分有英文 PDF |
| vc-en | 3 人（paulgraham, bhorowitz, marcandreessen） | **英文 essay 可直接 WebFetch** |
| vc-cn | 3 人（zhanglei, xuxin, shennp） | 中文为主，需 Wuying Pro |
| consumer-cn | 5 人（jiangnanc, zhongsc, luoyonghao, yangm, zhangl） | 中文为主，需 Wuying Pro |
| cross-border | 4 人（huangzheng-cr, zhoushouzi, chennnian, zhuangshuai） | 中文为主，需 Wuying Pro |

---

## 关键阻断项

| 阻断项 | 影响范围 | 解法 | 状态 |
|--------|----------|------|------|
| Wuying 免费版 `GetLink` 返回 400 | 25 位中文评委无法深化 | 升级到 Pro/Ultra | ❌ 待解 |
| 沙箱 WebFetch 对 paulgraham.com / Wikipedia 返回 403 | vc-en 3 位英文评委受阻 | Wuying 代理访问，或 Jina Reader | ❌ 待解 |

---

## 开发路线图

### 优先级 P0 — 立即可执行，不依赖外部解锁

#### P0-A：深化 vc-en 英文评委（3 人）

**目标**：将 paulgraham、bhorowitz、marcandreessen 从 seed 升级到 full 档  
**理由**：英文 essay 无访问限制，当前环境即可完成，且 vc-en 面板是对海外品牌最常用的面板  
**输出物**：每位评委的 `references/research/01-06.md` + `quotes.md`  
**参考 SOP**：`docs/10-deepening-perspectives.md`

- [ ] paulgraham — paulgraham.com essays 6 路径研究
- [ ] bhorowitz — a16z.com blog + hard thing about hard things
- [ ] marcandreessen — pmarca.com archive + 近期 X 发言

#### P0-B：实现 `--dry-run` 标志 ✅ 已完成（2026-06-25）

**目标**：`/mba 小米 --dry-run` 打印 PRD + 面板选择 + 维度计划，不触发真实搜索  
**实现位置**：`metric-brand-auditor/SKILL.md` Phase 0 §0.5 + 参数列表

- [x] SKILL.md 增加 `--dry-run` 参数解析
- [x] Phase 0 新增 §0.5 dry-run exit（原 §0.5 Write panel.yaml 顺延为 §0.6）
- [x] docs/05-usage.md §3.6 补充 `--dry-run` 完整示例

---

### 优先级 P1 — 依赖 Wuying Pro 升级

#### P1-A：批量深化中文评委（25 人）

**触发条件**：Wuying 升级到 Pro/Ultra，`GetLink` 可用  
**执行顺序建议**（按面板使用频率排序）：

1. consumer-cn 5 人（使用频率高，国内品牌大量需求）
2. vc-cn 3 人（投资/创业类品牌需要）
3. ai-app-cn 3 人（AI 产品审计核心面板）
4. cross-border 4 人（出海品牌需求）
5. edu-cn 3 人（教育类）

**每人标准工作量**：约 6 个研究文件（`01-06.md`）+ `quotes.md` 更新  
**验收标准**：`scripts/perspective-tools/quality_check.py` 通过（80% 一手来源）

- [ ] 升级 Wuying 套餐
- [ ] 跑 smoke test 确认 `GetLink` 可用
- [ ] 按顺序深化 25 人

#### P1-B：`--panel-merge` 跨面板对比报告 ✅ 已完成（2026-06-25）

**目标**：支持将两次不同面板的审计结果合并到同一报告的对比章节  
**场景**：同一品牌用 default + vc-en 两套视角对比，形成"内行 vs 外行"差异热力图  
**实现**：SKILL.md v0.2.38；Phase 5M 4步流程；docs/05-usage.md §3.7 用例

- [x] 设计跨面板对比数据结构（Phase 0.3 guard + Phase 0.4 bypass）
- [x] SKILL.md Phase 5M 增加 panel-merge 逻辑（5M.1-5M.4 完整流程）
- [x] HTML 报告模板增加跨面板 diff 热力图组件（面板选择器 toggle + delta 列）

---

### 优先级 P2 — 质量与基础设施

#### P2-A：集成测试 Workflow ✅ 已完成（2026-06-25）

**实现**：基于已发布报告的结构校验（比运行真实流水线更稳定、更快）

- [x] `scripts/validate_report.py`：7 条规则校验 report.md（标题/ScoreMatrix 5镜头/Dissent/Verdict/Legal/Sources）
- [x] `scripts/validate_html_report.py`：7 条规则校验 report.html（canvas/Mermaid/热力图/Verdict/Legal/Sources）
- [x] `tests/fixtures/mock_report.md` + `mock_report.html`：最小合法 fixture
- [x] `.github/workflows/report-validation.yml`：PR/push to main 自动运行

#### P2-B：扩充公开报告（各面板至少 1 份）

**目标**：10 个面板各有 1 份公开样本报告  
**理由**：当前仅 2 份（default + auto），其他 8 个面板无演示  
**选定品牌**：奇安信·Kimi·好未来·Anthropic·元气森林·美团·DJI·爱马仕（各面板 1 份）

- [x] 选定 8 个品牌（每面板 1 个）
- [x] 建档：`published/reports/*/panel.yaml` × 8 + `site/reports-meta.yaml` 8 条 pending 条目
- [x] 运行完整审计（10 份报告全部产出，2026-06-26 ~ 06-28）
- [x] 发布到 `published/reports/`（10 个品牌 report.html 齐全）
- [x] 更新 `site/published-reports.txt`（10 个 slug 全部列入白名单）

**✅ P2-B 全部完成**：10 面板各 1 份公开报告，Hermès 创 MBA 三项史上最高（Identity 9.6 / Origin 9.0 / 总分 8.64）。

---

### 优先级 P3 — 未来形态

#### P3-A：MCP Server 封装 ✅ 完成（2026-06-30）

**包**：`packages/mcp-server/` · **npm**：`mba-mcp-server@0.1.0`  
**工具**：`propose_audit` · `confirm_audit` · `get_status` · `fetch_report` · `list_audits` · `add_judge`  
**内置评委**：傅盛 / Jobs / 李可佳 / 吴俊东 / 张一鸣  
**测试**：22 tests passing · TypeScript zero errors

- [x] 确认 MCP Server 框架选型（`@modelcontextprotocol/sdk` + TypeScript + stdio）
- [x] 实现 6 个核心工具 + Phase 2-5 完整 LLM 编排
- [x] 文档 + 示例调用 + site/agents.html 同步

#### P3-B：报告订阅 / 品牌演化追踪

**目标**：用户订阅某品牌，当品牌有重大新闻时自动触发 EVOLUTION 模式重新审计  
**设计文档**：`docs/12-evolution-tracking.md`（2026-06-30）  
**场景**：品牌发布新产品、高管变动、负面事件后自动更新报告  
**新增 MCP 工具**：`subscribe_brand` · `trigger_evolution` · `list_subscriptions` · `get_delta_report` · `unsubscribe_brand`

- [x] 设计触发机制（keyword / news RSS / cron / webhook）
- [x] P3-B-1：`subscribe_brand` + `trigger_evolution` + `list_subscriptions` + `unsubscribe_brand` + CronScheduler（2026-06-30，commit 61fb801，34 tests）
- [x] P3-B-2：delta 报告生成（`get_delta_report` + `scores.json` 结构化打分 + per-lens 均值差 + LLM 变化叙述，2026-07-02，47 tests）
- [x] P3-B-5（成本优化）：EVOLUTION 增量维度重跑 —— 变化探针只重跑变了的维度，成本 ~$3 → ~$0.3-0.6/次（省 80%+），2026-07-02，52 tests
- [x] P3-B-4a：notify 推送出站（webhook POST + Resend email + mcp-push），审计完成自动算 delta 并推送，best-effort 容错，2026-07-02，60 tests
- [ ] P3-B-4b：webhook **接收端**（外部推送触发）—— 需长运行 HTTP daemon
- [ ] P3-B-3：keyword / news 触发器（**阻断**：Wuying Pro GetLink）

---

## 进度日志

> **记录格式**：每次完成一项开发动作后，在此追加一条记录，包括日期、完成事项、commit hash、备注。

---

### 2026-06-25

**事项**：整理开发路线图，创建本文档  
**完成内容**：
- 分析全量代码库（43 评委、10 面板、5阶段流水线、完整文档集）
- 整理当前状态快照（v0.2.36）
- 制定 P0-P3 四级优先级路线图
- 识别关键阻断项（Wuying 免费版限制）

**关键发现**：
- 最高杠杆单点：升级 Wuying 套餐，可解锁 25 位评委深化
- 不依赖 Wuying 的立即可执行项：vc-en 英文评委深化 + `--dry-run` 实现
- 测试覆盖是当前最大技术债（无集成测试）

**commit**：`4d41917` · branch `claude/sharp-turing-496l8b`

---

### 2026-06-25（续）

**事项**：实现 `--dry-run` 标志（v0.2.36 → v0.2.37）  
**完成内容**：
- `metric-brand-auditor/SKILL.md`：
  - 版本号 bump 0.2.36 → 0.2.37
  - 参数列表新增 `--dry-run` 说明
  - Phase 0 新增 §0.5 dry-run exit，原 §0.5 顺延为 §0.6
  - 输出格式：品牌、模式、面板评委状态（✓/✗）、Wuying leg、维度列表、输出路径、生效 flags
- `docs/05-usage.md`：参数表增行，新增 §3.6 dry-run 完整示例
- `site/roadmap.html`：P0-B 三个子任务标为完成，版本快照更新为 v0.2.37，追加进度日志

**同步发现**：WebFetch paulgraham.com 返回 HTTP 403，沙箱阻断仍有效。P0-A（vc-en 评委深化）暂挂起。

**commit**：待推送（与 P2-A 合并提交）

---

### 2026-06-25（续二）

**事项**：集成测试 Workflow 建立（P2-A）  
**完成内容**：
- `scripts/validate_report.py`：报告 Markdown 结构校验器（7 条规则）
- `scripts/validate_html_report.py`：HTML 报告组件校验器（7 条规则）
- `tests/fixtures/mock_report.md` + `mock_report.html`：最小合法 mock fixture
- `.github/workflows/report-validation.yml`：CI workflow（PR + push to main）
- 本地测试：2 份 HTML ✓、1 份 Markdown ✓、2 份 mock fixture ✓

**commit**：待推送

---

### 2026-06-25（续三）

**事项**：实现 `--panel-merge` 跨面板对比（P1-B，v0.2.37 → v0.2.38）  
**完成内容**：
- `metric-brand-auditor/SKILL.md` v0.2.38：
  - 参数列表新增 `--panel-merge` 描述
  - Phase 0.3：FRESH 品牌（无先前 report.md）触发 `--panel-merge` 时 ABORT
  - Phase 0.4：`--panel-merge` bypass clause（跳过面板相同检测）；STOP 条件追加 "AND `--panel-merge` was NOT passed"
  - Phase 5M（新增完整章节）：
    - 5M.1 读取旧版 score.json / report.md 提取分值
    - 5M.2 用新面板正常跑 N-Judge（复用 Phase 4）
    - 5M.3 生成 Panel Comparison 报告节（side-by-side delta 表 + 共识/分歧/fingerprint + cross-panel verdict）
    - 5M.4 HTML 模板扩展（面板选择器 toggle + 5 镜头 delta 热力图列）
- `docs/05-usage.md`：
  - 参数表新增 `--panel-merge` 行
  - §3.7 新增"跨面板对比审计"两步示例（Step 1 首次审计 + Step 2 panel-merge）

**commit**：待推送

---

### 2026-06-25（续四）

**事项**：P2-B 报告扩充基础设施（8 品牌建档）  
**完成内容**：
- 选定 8 个品牌，覆盖全部 8 个待补面板：
  - 奇安信（security-cn-global）、Kimi（ai-app-cn）、好未来（edu-cn）、Anthropic（vc-en）
  - 元气森林（consumer-cn）、美团（vc-cn）、DJI（cross-border）、爱马仕（luxury-en）
- `published/reports/{slug}/panel.yaml` × 8（status: pending，锁定面板 + mba_version: 0.2.38）
- `site/reports-meta.yaml`：追加 8 条 pending 条目（含 run_cmd、panel、ticker 等字段）

**待完成**：在 Claude Code 会话中逐一运行真实审计 → 生成 report.md/html → 更新 published-reports.txt → 移除 pending status

**commit**：待推送

---

---

### 2026-06-30

**事项**：P3-A MCP Server v0.1.0 全量完成 + P3-B 设计文档  
**完成内容**：
- PR-01~03：pnpm workspace 架构、TypeScript 8 阶段状态机、FilesystemStore 原子写入、6 工具框架
- PR-04：Phase 2-5 LLM 完整编排（llm/client.ts 重试逻辑、llm/prompts.ts 全套 prompt、四个 orchestrator、runner.ts 非阻塞链式执行 + cost guard）；22 tests passing，TypeScript zero errors
- PR-05 文件：scripts/add-shebang.js，README.md 状态更新，site/api/install.json 新增 MCP server 条目
- P3-B 设计文档 docs/12-evolution-tracking.md：4 种触发器（keyword/news/cron/webhook）、增量维度重跑方案、5 个新 MCP 工具设计、存储结构扩展
- roadmap.html + agents.html + docs/11-roadmap.md 同步更新

**commit**：069c5c4（PR-04）· c18c465（文档）· 待推送（PR-05 + P3-B）

---

### 2026-07-02

**事项**：P3-B-1 订阅+触发落地 + P3-B-2 delta 报告  
**完成内容**：
- **P3-B-1**（commit 61fb801）：4 个新 MCP 工具（`subscribe_brand` / `trigger_evolution` / `list_subscriptions` / `unsubscribe_brand`）+ `SubscriptionStore` JSON 持久化 + `CronScheduler`（setInterval 轮询到期订阅，fire-and-forget 触发演化）；cadence guard（min_interval_days + max_per_month）；34 tests
- **P3-B-2**（本次）：`get_delta_report` 工具 —— 新增 `src/orchestrator/scores.ts`（从 judge review 解析结构化打分，英文 lens 名作锚点，中英文都能解析）；Phase 4 生成时持久化 `scores.json`；delta 计算 per-lens 均值差 + LLM 变化叙述；旧 audit 无 scores.json 时从 reviews/ 重建；`FilesystemStore.listFiles` 辅助方法；47 tests passing
- MCP Server 现共 **11 个工具**（6 核心 + 4 订阅 + 1 delta）
- 同步修正 docs/11-roadmap.md 中 P2-B / P3-B-1 的 stale 勾选状态

**commit**：a185b9c（P3-B-2）

---

### 2026-07-02（续）

**事项**：EVOLUTION 增量维度重跑（成本优化）  
**完成内容**：
- `src/orchestrator/phase-2-evolution.ts`（`runPhase2Evolution`）：演化审计时先用廉价"变化探针"（256 tokens）逐维判断 CHANGED/UNCHANGED，只重跑变了的维度，UNCHANGED 直接复用上次 `_raw/dimension_N_slug.md`
- `llm/prompts.ts`：`changeProbeSystemPrompt` / `changeProbeUserPrompt`；触发事件通过 `options.evolution_context` 喂给探针
- `runner.ts`：`mode === 'evolution' && previous_audit_id` 时自动切到增量路径，否则全量研究
- `trigger-evolution.ts`：把 `event_type + event_summary + source_url` 组装成 `evolution_context` 写入 audit options
- 保守回退：探针无法解析 → 默认 CHANGED；无基线维度文件 → 全量研究
- 透明度：写 `_raw/evolution_probes.md` 逐维记录
- **成本**：~$3/次 → ~$0.3-0.6/次（省 80%+）
- 测试：52 tests passing（新增 5），TypeScript zero errors
- docs/12-evolution-tracking.md §5 标记已实现

**commit**：4931e1e

---

### 2026-07-02（续二）

**事项**：P3-B-4a notify 推送出站  
**完成内容**：
- `src/notify/webhook.ts`：`sendWebhook` —— fetch POST JSON，10s 超时，网络错误捕获进结果不抛出
- `src/notify/email.ts`：`sendEmail` —— Resend API（需 `MBA_RESEND_API_KEY` + `MBA_NOTIFY_FROM`），未配置静默返回
- `src/notify/dispatch.ts`：`dispatchNotifications` —— 逐个 target 独立投递（webhook/email/mcp-push），单个失败不影响其他
- `runner.ts`：新增可选 `onComplete(finalState)` 钩子，'done' 后 best-effort 调用（try/catch 包裹）
- `trigger-evolution.ts`：构造 onComplete —— 有基线时算 delta（getDeltaReport）→ dispatchNotifications；无基线时推送简单摘要
- README + docs/12 §7.5 补通知说明和环境变量
- 测试：60 tests passing（新增 8，mock global fetch + stubEnv），TypeScript zero errors

**闭环打通**：品牌变化 → trigger_evolution → 增量重审 → 算 delta → webhook/email 主动通知

**commit**：待推送

<!-- 在此追加后续进度记录，格式参考上方 -->
