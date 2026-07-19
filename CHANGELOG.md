# Changelog

All notable changes to MBA (Metric Brand Auditor) are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versions
track `metric-brand-auditor/SKILL.md`'s `version:` field (the release tag).

## v0.6.0 — 2026-07-19

**舆情自动化闭环 —— 从「人工核验候选」到「AI 自动分类 → 折入 → 只审 diff」**:本版把 Brand Watch
的信号处理从人工粘贴候选,升级成一条每日自动流水线:发现(噪音过滤 · 中文)→ LLM 多 provider 预分类
→ 自动折入 `events.yaml` 并开 PR → 人工只审最终 diff 合并。同时用 EVOLUTION 模式对 4 个品牌做 v1→v2
重审,新增 2 个监控品牌(Tesla / Palantir)与第 3、4 个真实 `--panel-drop`。均守 MBA 边界:
**AI 只判类不改分、合并=人工闸门、引文逐字取自源 feed**。

### Added
- **舆情前台 Triage 页**(docs/16)——`site/watch/triage.html`:候选事件卡片打勾采纳 / 打叉丢弃、
  可改 dim/severity/direction/lens,「✅ 提 PR」一键预填 GitHub 新文件深链(取代复制粘贴 + 读 PR diff);
  候选标题中文化。
- **LLM 自动分类流水线**(`watch-discover.yml` + `classify_candidates.py`)——每日 discover(Google
  News RSS,噪音过滤:行情页 / ticker;中文 locale)→ 多 provider 预分类(GLM / OpenAI 兼容 / Anthropic,
  含 429/5xx 退避重试)→ 高置信项 `fold_adopt.py` 折入 `events.yaml` → 自动开「建议入库」PR。无 key 时
  优雅兜底:候选直推 main → 前台 triage。**反捏造:标题/日期/URL 逐字取自源 feed;dim/severity/direction/
  lens 为 model-judged 分类(明确标注、不假装客观);审计分数从不自动变;合并=人工闸门。**
- **`watch-adopt` / `fold_adopt`**——把 triage / auto 采纳的扁平事件按 slug 折入各品牌 `events.yaml`、
  重算 id、跑 `validate_watch`;机器人自动 PR 改为**开 PR 前本地折入**(绕开 GITHUB_TOKEN 开的 PR 上
  workflow 被 GitHub 卡成 `action_required`)。
- **4 场 EVOLUTION v1→v2 重审**——kimichat(K3 驱动)· DeepSeek(8.00→8.28)· Microsoft(8.65→8.55)·
  NVIDIA(8.88→8.80),按已入库 P1 watch 事件驱动 delta 打分、版本化报告 + `consumed_by` 清「建议重审」触发。
- **2 个新监控品牌 + 第 3、4 个真实 `--panel-drop`**——Tesla(马斯克,第 3)· Palantir(Alex Karp,第 4);
  第 3 场创始人晚餐 任正非 × 马斯克;8 个新品牌舆情驾驶舱冷启动(27 条可溯源事件)。
- **首页「重大舆情 · 近期异动」提醒块** + oaf.world/spacex 跨站互链上创始人页 / 驾驶舱页 / 首页。

### Fixed
- `watch-discover` 开 PR 改尽力而为(Actions 默认禁建 PR 时回退分支 + 提示);triage 提 PR 补齐字段拦截、
  discover 噪音过滤;GLM coding 端点 429 → 改走 Anthropic 端点 + 退避重试。

> 规模:**24** 已发布审计品牌 · **24** 创始人档案 · **3** 场创始人晚餐 · **4** 处真实 `--panel-drop`(微软 · 华为 · 特斯拉 · Palantir)。
> 榜首:Apple 8.84 · NVIDIA 8.80(重审后)· SpaceX 8.76 · Amazon 8.72 · Hermes 8.64。

## v0.5.0 — 2026-07-16

**从「品牌监控」到「品牌 + 创始人 + 产业 + 组合」的关系宇宙**:本版把 MBA 从单纯的品牌影响力
审计,扩成一张互相关联的图——每个品牌接上**创始人**,创始人之间可摆**晚餐**推演合作,品牌按
**产业**归类,并一次性把**七家全球科技巨头**纳入监控。均在 MBA「AI 评委模拟 · 反捏造 · 只建议不改分」
边界内;新增两处**首次真实触发 `--panel-drop`**(创始人/董事自冲突)让自冲突机制在发布报告里落地。

### Added
- **创始人维度**(docs/21)——`founders/<slug>.yaml`:每个品牌梳理创始人履历(时间线,每条带
  provenance)+ 从人物角度看创始人↔品牌关系(按 5 镜头,`分析:` 前缀)。`build_founder_pages.py`
  生成独立创始人页 + 索引;`validate_founders.py` 硬 gate(brand ∈ 白名单、履历带来源、
  perspective_slug 真实);评委创始人复用其 perspective,非评委 curl 一手。**22 位创始人全覆盖。**
- **创始人晚餐 / 品牌×品牌合作推演**(docs/22)——`collabs/<a>--<b>.yaml`:把两位创始人放一桌,
  按 5 镜头假想推演合作。`build_collab_dinners.py` 生成晚餐页 + **组合器**(选两位创始人 → 有则「开饭」、
  无则「点单」开预填 GitHub issue);`validate_collabs.py` 硬 gate(双方均有创始人档案 + **诚实盒 tensions
  强制**)。**反捏造:发言为 AI 演绎公开立场、合作为假想、不谎称真实合作。** 已上桌 2 场
  (田溯宁×唐杰、梁文锋×黄仁勋「芯片与模型」);首页嵌「创始人晚餐 · 亮点」块(单一真源守漂移)。
- **产业维度**(docs/23)——按产业给品牌分 6 大类(人工智能 / 消费 / 硬科技·航天 / 智能制造·硬件 /
  企业服务·安全 / 教育);`reports-meta.yaml` 的 `industry` 字段单一真源 + 首页产业筛选条 / 卡片标签;
  `check_consistency` 第 10 格硬 gate。
- **七家全球科技巨头入库**(15 → **22 品牌**)——DeepSeek(ai-app-cn)· NVIDIA(vc-en,MBA 最高 8.88)·
  Apple(vc-en,Identity 9.6 全场最高)· Google(vc-en,Category 领跑)· Microsoft · Amazon · Huawei,
  每家含完整审计报告(10 段 + 数字自洽 Score Matrix + 手写内联 Chart.js)+ 创始人档案 + 全套耦合。
- **首次真实 `--panel-drop`**(创始人/董事自冲突落地)——Microsoft(霍夫曼:LinkedIn 售予微软 + 曾任
  微软董事)· Huawei(任正非:创始人评委),按 `self-conflict.yaml` 规则剔除、有效评委打分。

### Fixed
- **全站功能巡检**(docs/24)——Playwright 广度优先爬 177 页 / 188 链接 + 交互测试,修复 4 个真实缺陷:
  roadmap 裸 `.md` 死链、chengshi-auto v1 版本链、历史快照 `_assets/` 断图(build.sh 镜像到
  `versions/_assets/`)、v2 redirect 目标错。交互 11/11 通过;排除 CDN 环境假阳性。

## v0.4.5 — 2026-07-14

**Brand Watch → 舆情驾驶舱**:按 docs/20(舆情驾驶舱需求 × MBA 能力映射)把 Brand Watch
顺势扩展去覆盖企业级「舆情驾驶舱」需求。三阶段落地,均在 MBA「只建议、可复盘」边界内;
反爬/私域内网/小时级实时/处置工单等共同缺口按计划守界不做。

### Added
- **事件 schema 补 4 个舆情驾驶舱字段**(Phase 1,可选、向后兼容)——`related_persons`
  (关联人物)、`source_type`(来源类型枚举)、`suggested_action`(结构化建议动作)、
  `alert_tier`(L1/L2/L3 预警层级覆写),对齐驾驶舱的 7 标签。`validate_watch.py` 枚举 gate +
  `--selftest`(12→17 断言),MCP `watch/store.ts` 镜像 + 序列化(+4 tests,224 全绿)。
- **飞书分层预警 L1/L2/L3**(Phase 2)——`notify_feishu.py` 从单门槛升为三层路由:
  L3 高层预警(P0/建议重审)· L2 专项协同(P1)· L1 日常(评分变动);各层可配独立 webhook
  (`FEISHU_WEBHOOK_L3/L2`)分流到不同群,解析到同一 webhook 的层合并成一张卡(单群不刷屏)。
  事件的 `alert_tier` 可覆写层级。
- **舆情驾驶舱看板**(Phase 3)——`scripts/build_watch_cockpit.py` 为每品牌生成
  `site/watch/<slug>/cockpit.html`:管理层摘要 + 发布时间分布 + 风险主题归因(维度×方向)+
  来源类型分布 + 投资社区专区 + 可筛选全量信息表。图表为零依赖静态内联 SVG。入口:
  舆情时间线页 + 首页每张品牌卡片「舆情驾驶舱 →」。

## v0.4.4 — 2026-07-13

**品牌监控的可视化与触达**:把已有的评分/舆情数据织成可交互的知识星图,并让变化
主动推达飞书群。均为**取自仓库真实数据**的加法(反捏造),不改评分口径。

### Added
- **全维度知识星图** — `mbabrand.com/starmap.html`(`scripts/build_starmap.py`):
  零依赖纯 SVG 星座图,**5 镜头 × 9 监控维度 × 15 品牌 × 10 面板 × 43 评委,
  82 实体 / 184 条真实关系边**(维度→镜头、品牌→面板、品牌→监控维度 core/weak、
  面板→评委),关系源自 `watch/matrix.yaml` + `panels/*.yaml` + `reports-meta.yaml`。
  可搜索/类型筛选/点击聚焦/缩放平移/详情面板;首页 banner + 全站导航入口。
- **每品牌私有知识星图** — `mbabrand.com/starmap/<slug>.html`(15 张,
  `scripts/build_brand_starmap.py`,`site/starmap/` gitignore、部署随 watch 页重生成):
  以单品牌为圆心的 ego 图,画出全局图没有的三样自有数据——内环 **5 镜头**(按评委均分)+
  中环**评委**(细线=每位评委对每个镜头的逐格打分,report.md 评分矩阵 5×N 条真实边)+
  外环**舆情事件流**(P0-P3 定大小、正/负向定颜色,连到其 `lens_map` 影响的镜头),
  版本演化进详情面板。下钻入口:全局星图点品牌节点 + 首页每张卡片。
- **飞书群推送** — 合并到 main 涉及 `watch/**` 或 `site/reports-meta.yaml` 时,
  GitHub Action(`.github/workflows/notify-feishu.yml`)diff 出变化、拼一张飞书交互卡片
  POST 到自定义机器人 webhook 进群。**门槛与首页「建议重审」同口径**(避免刷屏):
  新增 **P0/P1** 事件 / 品牌**新命中**触发规则(复用 `evaluate_triggers.py`)/ **评分变动**。
  `scripts/notify_feishu.py` 支持 `--dry-run` 预览与 `--test` 连通性卡片(`workflow_dispatch`
  手动触发);内容全部取自仓库文件,含可选 HMAC-SHA256 签名;secrets 未配则跳过。见 docs/19。

## v0.4.3 — 2026-07-12

**Brand Watch(舆情监控)整条链路落地**(docs/15 PRD · docs/16 过程记录,W1→W7):
信号采集与审计评分严格分离——watch **只建议、永不改分**。

### Added
- **数据层 + 硬 gate(W1)** — `watch/matrix.yaml`(13 品牌 × W1-W9 适用性矩阵)+
  `watch/<slug>/events.yaml`(事件 schema:逐字 quote ≤100 字、URL 自证日期、判断字段
  恒标 `model-judged`)+ `scripts/watch-tools/validate_watch.py`(静态校验,接
  panel-validation CI,`--selftest` 13 组断言)。
- **试点与滚动采集(W2/W3/W6)** — 源可达性逐源验证;5 品牌 39 条可溯源事件
  (亚信/奇安信/垣信/SpaceX/美团);CCR Routine 每周一自动增量周扫。
- **`--watch` 进 skill + EVOLUTION 消费(W4)** — `/mba <brand> --watch` 单次扫描;
  EVOLUTION Phase 2 先消费事件流再补扫(`consumed_by: vN` 回标);验收:奇安信
  v1→v2 全程由 watch 事件流驱动。
- **首页徽章 + 时间线页(W5)** — 未消费 P0/P1 徽章(漂移 gate 内)+
  `/watch/<slug>/` 事件时间线页(deploy 时生成)。
- **触发与联动(W7)** — `scripts/watch-tools/evaluate_triggers.py` 运行时评估器
  (30 天滚动窗:P0≥1 / P1≥3 / 加权 4·2·0.5 ≥6——同日按 5 单重审回测校准,
  初版为 P1≥2 / ≥5,见 docs/16 §8.3;`--selftest` 14 组断言);MCP 新增
  `get_watch_events` / `record_watch_event` 两工具(录入门槛 = validate_watch 的 TS
  镜像;P0 或触发命中经既有 `subscribe_brand` 订阅链路下发重审建议)。MCP server
  现有 **16 tools**(19 new tests; 220 total),npm 发布为 `mba-mcp-server@0.2.0`。

## v0.4.2 — 2026-07-07

Real-data research + audit recovery, on top of v0.4.1. Two additions that make
the MCP server both more accurate and more robust — neither needs the sandbox to
have any outbound network of its own.

### Added
- **Live web search in research (opt-in)** — set `MBA_WEB_SEARCH=1` and Phase 2
  researches each dimension with Anthropic's **server-side web_search** tool
  instead of the model's own memory, capturing the real source URLs into
  `_raw/dimension_*.md`. The search runs on Anthropic's infra (`api.anthropic.com`),
  so it needs **no sandbox outbound network** — it works even in a locked-down
  egress policy. Billed per search; cap with `MBA_WEB_SEARCH_MAX_USES` (default 5).
  Only research phases search (judging / synthesis / merge never do).
- **`resume_audit` MCP tool** — resume a stalled audit (process died mid-run, an
  error, or an interrupt) without creating a new one. It keeps the same
  `audit_id`, proposal, panel, and options; reloads the artifacts of every
  finished phase from disk (`_raw/dimension_*.md`, `_raw/synthesis.md`,
  `reviews/*.md`) and re-enters the pipeline at the first phase that never
  completed — so a stall in judging or merging doesn't re-pay for research.
  Wires up the previously-dormant `interrupted` / resume machinery. The MCP
  server now has **14 tools**. (14 new tests; 113 total.)

## v0.4.1 — 2026-07-06

First **npm release** of the MCP server, plus panel / evolution / CI enhancements
on top of v0.4.0. `mba-mcp-server` is now `npx`-installable — no clone required.

### Added
- **`mba-mcp-server` published to npm** — install with
  `npx -y mba-mcp-server@latest` (or point `claude_desktop_config.json` at it).
  Ships two bins: `mba-mcp-server` (MCP stdio) and `mba-webhook-receiver`. MIT.
- **`list_panels` + `get_brand_trend` MCP tools** — `list_panels` exposes the 10
  panels and their rosters so a caller can discover options before choosing a
  `panel`; `get_brand_trend` gives a brand's score trajectory across all its
  audits (the N-audit view that `get_delta_report`'s two-audit compare doesn't).
  The MCP server now has **13 tools**.
- **MCP server CI** (`.github/workflows/mcp-ci.yml`) — typecheck + tests + build
  on every PR/push touching the package, plus a check that the bundled
  personas/panels are in sync with their sources.
- **npm publish automation** — `.github/workflows/publish-npm.yml` publishes
  `mba-mcp-server` to npm on manual dispatch (idempotent, with a `dry_run`
  option). One-time setup: add an `NPM_TOKEN` repo secret (a granular access
  token, so it can publish under a 2FA-protected account).
- **Full panel system in the MCP server** — `propose_audit` now accepts a
  `panel` (default / auto / luxury-en / vc-en / vc-cn / consumer-cn / ai-app-cn /
  edu-cn / cross-border / security-cn-global). The 43 judge personas across all
  10 panels are bundled from the project's authored `perspectives/*` files
  (generated by `scripts/generate-personas.py`), so the MCP server can now
  reproduce every published report — not just the default 5-judge panel.
- **Webhook receiver** (`mba-webhook-receiver`) — a small HTTP server that turns
  an inbound event `POST /webhooks/trigger` into an EVOLUTION re-audit, the
  inbound counterpart to the outbound notifications. Optional `MBA_WEBHOOK_SECRET`
  Bearer auth, `GET /status` + `/health`, shares `MBA_STORE_DIR` with the MCP
  server. Completes the four evolution triggers: subscription cron, manual,
  notify-out, and webhook-in. (`src/http/receiver.ts`, 18 tests.)
- `scripts/qa_report_render.mjs` — headless-render QA for published reports.
  Catches chart infinite-growth, collapsed canvases, unrendered Mermaid, and JS
  errors that static validators miss. Run before publishing: `node
  scripts/qa_report_render.mjs` (needs network for the chart/mermaid CDNs, or
  `--offline-libs <dir>` in air-gapped environments).
- Real public Sources sections backfilled into the hermes / genki-forest /
  meituan / tal-education reports.

### Changed
- CI workflows (`mcp-ci.yml`, `publish-npm.yml`) run on **Node 22** — Node 20 is
  being deprecated on GitHub runners. Package `engines` stays `>=20`.
- Report validators (`validate_report.py`, `validate_html_report.py`) split into
  hard (block CI) vs advisory (warn) rules, with advisory anchors covering MBA's
  real bilingual section variants (TL;DR / Core Insight / 最大分歧 / Judge Total …).
- `release.yml` now sources release notes from the matching CHANGELOG section and
  updates an existing release instead of no-oping.

### Fixed
- Chart.js infinite-growth on the kimichat & qianxin report charts (radar + Lens
  Means bar): canvases now sit in a fixed-height `.chart-wrap` container.

## v0.4.0 — 2026-07-04

The MCP-server + evolution-tracking milestone. MBA is now runnable not just as a
Claude Code skill but as a standalone **MCP server** any MCP-capable agent can
drive, with brand subscriptions, automatic re-audits, and delta reporting.

### Added — MCP Server (`packages/mcp-server`, `mba-mcp-server`)
- TypeScript MCP server (Node ≥ 20, stdio), **11 tools**, **67 tests**.
- **Core audit (6):** `propose_audit`, `confirm_audit`, `get_status`,
  `fetch_report`, `list_audits`, `add_judge` — non-blocking Phase 2-5 LLM
  orchestration (research → synthesis → judging → merge), atomic `state.json`,
  8-phase state machine, retry/backoff client, 5 built-in judges + persona validator.
- **Evolution tracking (5):** `subscribe_brand`, `trigger_evolution`,
  `list_subscriptions`, `unsubscribe_brand`, `get_delta_report`.
  - Cron scheduler + cadence guards (min interval, monthly cap).
  - **Incremental EVOLUTION re-run**: change-probes re-run only moved dimensions
    → cost ~$3 → ~$0.4/run (80%+ savings); triggering event steers the probes.
  - Structured `scores.json` + delta reports (per-lens mean Δ, LLM narrative).
  - **Notifications**: webhook + email push on completion, best-effort per-target.
- End-to-end tests over a real MCP `Client` / in-memory transport.
- Publish-ready: MIT `LICENSE`, `prepublishOnly` guard, clean `npm pack`.

### Added — Pipeline & reports
- **10 published audits** — every panel now has a public sample (Hermès 8.64 sets
  three MBA all-time records; Meituan is the first double-★ investor conflict).
- `--dry-run` flag — print PRD + panel/judge/dimension plan, zero side effects.
- `--panel-merge` flag — cross-panel comparison report with delta heatmap (Phase 5M).

### Added — CI / quality
- `report-validation.yml` — structural validators for report.md + report.html.
- Validators use a hard/advisory rule split (title + score matrix + legal are
  hard; verdict / dissent heatmap / sources are advisory) so bilingual report
  formats pass while real gaps still fail.

### Fixed
- Added the standard MBA Legal/IP/Disclaimer footer to 4 reports that shipped
  without one (hermes, genki-forest, meituan, tal-education), in `.md` and `.html`.
- Regenerated `site/api/` for all 10 reports; added the MCP server to the
  agents-API install manifest.

### Docs & site
- New `docs/13-mcp-quickstart.md` (user-facing) and `docs/12-evolution-tracking.md`.
- README §5.1 MCP section; `site/agents.html`, `site/roadmap.html` synced.

**Full range:** everything since the last published release, v0.2.36.

## v0.2.36 — 2026-06-18
- `cross-border` and `luxury-en` panels made runnable → 10/10 panels operational.

See GitHub Releases for earlier versions.
