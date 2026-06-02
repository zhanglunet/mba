# 阿里无影浏览器（Wuying / AgentBay）在 MBA 中的使用全景

> 索引文档。覆盖 `~/mba` 仓库里**所有**与阿里云无影 AgentBay 云浏览器相关的代码、配置、脚本、文档和营销物料。
>
> 适用版本：v0.2.25（2026-06-02 快照）。
> 关键词：Wuying / 无影 / AgentBay / cloud browser / `--quick`。

---

## 1. 一句话总结

MBA 用阿里云**无影 AgentBay** 起一个**一次性云浏览器会话**，专门去抓 `WebFetch` 拿不到的内容（X、小红书、Bilibili、登录墙后的中文媒体、JS 渲染页面）。整条 leg 是**可选**的——`--quick` 模式下完全跳过，开源用户零依赖也能跑。

```
WebSearch + WebFetch  ──┐
                        ├──→ Lead 合成 → 评委打分 → 报告
Wuying cloud browser  ──┘  （可选；--quick 跳过）
```

---

## 2. 架构定位

无影在系统里属于**基建层 / 第三方依赖**。`scripts/wuying/open.py` 是**完全独立**的脚本（`docs/03-architecture.md:100`），只在 Phase 2 的某一个并行 sub-agent 里被调起。

```
┌──────────────────────────────────────────────────────────┐
│ Phase 2 Parallel Research                                │
│                                                          │
│   sub-agent #1 ─ dimension 1 (WebSearch + WebFetch)      │
│   sub-agent #2 ─ dimension 2 (WebSearch + WebFetch)      │
│   ...                                                    │
│   sub-agent #N ─ wuying cloud browser  ← 本文档主角      │
│                  ├─ ssh → scripts/wuying/open.py         │
│                  ├─ agent-browser CLI drive             │
│                  └─ teardown via client.delete()         │
└──────────────────────────────────────────────────────────┘
```

会话生命周期：
- **创建**：`python3 scripts/wuying/open.py` → 拿到 `SESSION_ID` + `RESOURCE_URL`
- **驱动**：本机 `agent-browser` CLI 连接 CDP/WSS endpoint（或手动打开 RESOURCE_URL）
- **拆除**：**强制**调用 `client.delete()` / `delete_by_id()`，并在 `_raw/wuying_browse.md` 里写明 teardown 状态
- **资源密集**：会话按分钟计费，漏关会持续烧钱（`docs/03-architecture.md:178-180`）

---

## 3. 仓库里的 Wuying 全部出现位置

按层级分组。每条都给出**精确文件路径 + 行号**。

### 3.1 配置层 `.env`

| 文件 | 行 | 内容 |
|------|----|------|
| `.env.example` | 1 | `WUYING_API_KEY=your_api_key_here` |
| `.env.example` | 2 | `WUYING_IMAGE_ID=browser_latest` |

> `.env` 不入库；运行时 `scripts/wuying/open.py` 和 `smoke_test.py` 从仓库根目录读 `.env`。
> Key 不得在日志或 print 里完整输出（见 `docs/07-code-standards.md:175-177`）。

### 3.2 脚本层 `scripts/wuying/`

| 文件 | 作用 | 关键行 |
|------|------|--------|
| `scripts/wuying/open.py` | 创建会话 → 打印 `SESSION_ID` + `RESOURCE_URL` → 退出但**不删除** | 28-32（读 key）、37-40（`AgentBay.create()`）、44-51（拿 ResourceUrl）、57-66（打印 teardown 命令） |
| `scripts/wuying/smoke_test.py` | API key 冒烟测试：创建 → 拿 CDP endpoint → 立即删除 | 30-33（读 key）、44-51（创建）、54-58（初始化 browser + CDP endpoint）、60-68（cleanup） |
| `scripts/wuying/README.md` | 脚本说明 | 全文 |

依赖的 Python 包：
- `agentbay`（`AgentBay`、`CreateSessionParams`、`BrowserOption`）
- 安装方式：`pip install --user agentbay-sdk`（`metric-brand-auditor/references/wuying-browser.md:131-133`）

### 3.3 Skill 集成层 `metric-brand-auditor/`

#### `metric-brand-auditor/SKILL.md`

| 行 | 内容 |
|----|------|
| 11, 16, 26 | SkillHunt 营销文案：强调"零依赖入口不需要 Wuying" |
| 43 | `--quick` flag 定义：跳过 Wuying leg |
| 114 | `--quick` 详细说明 |
| 160-161 | 依赖矩阵：Wuying API key + `agent-browser` CLI 两层 fallback |
| 230 | 环境检查：`echo "WUYING_API_KEY: ..."` |
| 242 | 自动降级：`WUYING_API_KEY unset → auto --quick` |
| 261 | "Wuying cloud-browser sub-agent — for sites that need a real browser session" |
| 273 | `--quick — skip Wuying cloud-browser leg` |
| 298 | 产物路径：`_raw/wuying_browse.md` |
| 462 | Phase 1 proposal 模板里的 Wuying 字段 |
| 514-553 | **核心：Phase 2 cloud-browser sub-agent prompt 模板**（含 SSH 跨机 fallback、teardown 强制要求） |
| 574 | Lead 合成时必读 `wuying_browse.md` |
| 737 | Phase 5 报告里必须标 accuracy limits（"no Wuying" 也是一种 limit） |
| 902 | EVOLUTION 模式：只在受影响维度才重跑 Wuying leg |
| 935 | 模式变化时（Wuying vs web-only）更新法律声明 |
| 999-1036 | **Wuying leg 风险表 + 自动 teardown 规则**（>15min 强制断开） |
| 1044 | 指针：see `references/wuying-browser.md` |

#### `metric-brand-auditor/references/wuying-browser.md`

完整的操作规范文档（147 行）。覆盖：
- One-shot session lifecycle（创建 → 驱动 → 拆除）
- SSH 进 Mac host 调起脚本
- `agent-browser` CLI 调用约定（注意 PATH on non-login SSH 不含 `/opt/homebrew/bin`）
- 平台抓取规范（X / RedNote / Bilibili / 中文媒体 / brand-owned surfaces）
- `wuying_browse.md` 产物模板
- Failure modes（key missing / SDK missing / RESOURCE_URL 为空 / agent-browser 不能 attach）
- Cost discipline 双规则

### 3.4 项目文档 `docs/`

| 文件 | 行 | 主题 |
|------|----|------|
| `docs/01-prd.md` | 90 | 可移植性原则（"只依赖 Claude Code + Anthropic API + 阿里云无影"） |
| `docs/01-prd.md` | 122 | 用户前置条件 |
| `docs/01-prd.md` | 134 | 反爬降级：写 N/A 不假装拿到 |
| `docs/01-prd.md` | 140 | 版本里程碑：v0.1.0 含无影脚本 |
| `docs/02-product-design.md` | 120 | 产物清单：`wuying_browse.md` 含 session metadata + teardown |
| `docs/02-product-design.md` | 240-242 | Wuying leg 完全降级时的报告标注规则 |
| `docs/03-architecture.md` | 19, 57-58 | 目录结构 |
| `docs/03-architecture.md` | 89 | 架构图里的 wuying 节点 |
| `docs/03-architecture.md` | 96 | Skill 依赖说明 |
| `docs/03-architecture.md` | 100 | "scripts/wuying/open.py 完全独立" |
| `docs/03-architecture.md` | 119 | Phase 2 调度逻辑 |
| `docs/03-architecture.md` | 178-180 | **Wuying session 生命周期 + 资源密集警告** |
| `docs/03-architecture.md` | 275 | Bash 用于跑 open.py |
| `docs/03-architecture.md` | 284 | 第三方依赖表 |
| `docs/03-architecture.md` | 294 | Teardown 强制要求 |
| `docs/04-pipeline.md` | 82, 110 | Phase 1/2 决策："是否走 wuying leg" |
| `docs/04-pipeline.md` | 116 | "对每个维度并行一个 sub-agent + (可选)一个 wuying sub-agent" |
| `docs/04-pipeline.md` | 152 | 批次切分示例：7 维度 + 1 wuying = 8 → 5+3 |
| `docs/04-pipeline.md` | 155-159 | **Wuying sub-agent 特殊性**：先开会话、用 agent-browser 驱动、必须 teardown |
| `docs/04-pipeline.md` | 174 | Phase 3 Lead 必读 wuying_browse.md |
| `docs/04-pipeline.md` | 306 | 错误兜底表：完全失败时降级 web-only |
| `docs/05-usage.md` | 30 | `--quick` flag 文档 |
| `docs/05-usage.md` | 62, 73 | 跑动示例里的 Wuying leg 状态显示 |
| `docs/05-usage.md` | 174 | `--no-judges` 组合用法 |
| `docs/05-usage.md` | 222-225 | FAQ：`WUYING_API_KEY not set` |
| `docs/05-usage.md` | 274 | 成本估算（"Wuying Lite 套餐免费"） |
| `docs/06-installation.md` | 10-13 | 前置条件 |
| `docs/06-installation.md` | 34-35 | `.env` 模板 |
| `docs/06-installation.md` | 40 | 获取 key 流程 |
| `docs/06-installation.md` | 62-65 | smoke_test 步骤 |
| `docs/06-installation.md` | 134 | `ModuleNotFoundError` 故障排查 |
| `docs/06-installation.md` | 157-165 | session teardown 应急脚本 |
| `docs/07-code-standards.md` | 137 | 脚本风格基准 |
| `docs/07-code-standards.md` | 175-177 | **Key 脱敏要求**：teardown 输出必须从 `.env` 重读，不内联 |
| `docs/08-extending.md` | 116-117 | 维度扩展时的批次再切分 |
| `docs/08-extending.md` | 230 | 限流诊断检查项 |
| `docs/08-extending.md` | 242 | scope 红线：不允许把 wuying 替换成"自动绕反爬爬虫" |
| `docs/mcp-server-design.md` | 163 | MCP 化时 wuying_browse.md 作为可复盘中间产物 |
| `docs/mcp-server-design.md` | 212 | MCP tool 参数 `skip_wuying: boolean` |
| `docs/mcp-server-design.md` | 363 | 错误码 `WUYING_UNAVAILABLE`：自动降级 `--quick` |
| `docs/mcp-server-design.md` | 644 | references/wuying-browser.md 在 v0.1 是降级路径 |

### 3.5 README 顶层

| 行 | 内容 |
|----|------|
| 64 | 目录树：`wuying-browser.md` 是云浏览器 leg 规范 |
| 99 | `scripts/wuying/` 描述 |
| 102 | `.env.example` 含 `WUYING_API_KEY` |
| 116-117 | 流水线示意里的 wuying sub-agent |
| 343-355 | **安装小节**：API key 获取（`https://wuying.aliyun.com` → AgentBay 应用）、smoke_test、open.py |

### 3.6 Hackathon 物料

| 文件 | 行 | 主题 |
|------|----|------|
| `scripts/build_hackathon_deck.py` | 469-470 | 把 Wuying 作为"基建层"展示在 PPT 上 |
| `scripts/build_hackathon_deck.py` | 652 | `.env` 模板示例 |
| `scripts/build_overview_pptx.py` | 400 | Phase 2 Parallel Search 描述 |
| `scripts/build_overview_pptx.py` | 482 | 目录树里的 wuying 节点 |
| `docs/hackathon/mba-overview-deck.md` | — | 生成的 deck 文本 |
| `docs/hackathon/mba-overview-deck.html` | — | 生成的 deck 网页 |

### 3.7 营销 / SkillHunt 分发

| 文件 | 行 | 主题 |
|------|----|------|
| `scripts/grow_metric_brand_auditor.sh` | 88-90 | Marketplace description：强调 `--quick --no-judges` **不需要 Wuying** |
| `scripts/grow_metric_brand_auditor.sh` | 122 | "试跑姿势放在门面，不用先备 Wuying 云浏览器" |

### 3.8 历史报告产物（自动生成）

跑过 Wuying leg 的历史报告会保留 `_raw/wuying_browse.md`：

- `published/reports/chengshi-auto/_raw/synthesis.md`
- `published/reports/chengshi-auto/report.md` / `.html`
- `published/reports/chengshi-auto/versions/v2..v6_2026-05-18.md`
- `published/reports/lenovo/report.html`

这些不是代码，是输出样本。

---

## 4. 会话生命周期（端到端）

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CREATE                                                   │
│    $ python3 scripts/wuying/open.py                         │
│    → 读 .env → AgentBay.create(CreateSessionParams)         │
│    → 打印 SESSION_ID + RESOURCE_URL (wss://...)             │
│    → 进程退出, 会话保持 ALIVE                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. DRIVE                                                    │
│    agent-browser CLI 连 RESOURCE_URL                        │
│    或 Playwright/Puppeteer 连 CDP endpoint                   │
│    或 用户本机打开 URL 手动观察（last resort）                  │
│                                                             │
│    抓取目标:                                                  │
│      - X / Twitter 最新 10 条                                │
│      - RedNote top 10 (含 KOL 画像 + 评论 top-3)             │
│      - Bilibili top 5 视频 (含 角度分类)                      │
│      - 36kr/虎嗅/钛媒体 近 3 篇 (含 slant)                    │
│      - Brand-owned surfaces (hero + footer + pricing + CTA)  │
│                                                             │
│    所有产物落 _raw/wuying_browse.md                          │
│    截图存 /tmp/mba-screenshots/{brand-slug}/                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. TEARDOWN (REQUIRED)                                      │
│    AgentBay.delete_by_id(SESSION_ID)                        │
│    或 client.delete(session) / session.delete()             │
│                                                             │
│    在 wuying_browse.md 里写明:                               │
│      **Torn down:** <ISO timestamp> (success|failure)        │
│                                                             │
│    Lead 在 Phase 3 会读这一段; teardown 缺失 → block 报告      │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 何时用 / 何时跳过

### 用 Wuying 的场景
- X / Twitter 搜索结果（rate-limited / 未登录不可见）
- 小红书 / 抖音 / Bilibili / 知乎（中文反爬）
- App store 评论（动态加载）
- 登录墙后的媒体存档
- 任何需要 JS 渲染才能拿到内容的页面

### 跳过 Wuying 的场景（`--quick`）
- 没有 `WUYING_API_KEY`（自动降级，不报错）
- 只想验证管线（first run / `/mba <brand> --quick --no-judges`）
- 目标品牌没有重要的中文社媒信号
- 成本敏感（虽然 Lite 套餐免费，但分钟计费会积累）

### 降级后报告会怎样
报告 TL;DR 写 `Wuying leg N/A — see _raw/wuying_browse.md`，X / RedNote / Bilibili 这几个维度的"first-person framing"标 `N/A — wuying leg unavailable, web-only fallback used`。评委打分照常进行，但他们看到的素材确实是 web-only 的子集。
（`docs/02-product-design.md:240-242`、`docs/04-pipeline.md:306`）

---

## 6. 成本与风险纪律

| 风险 | 阈值 | 处理 |
|------|------|------|
| Session wall time | > 15 min | 自动 teardown via `scripts/wuying/open.py` cleanup path；log SESSION_ID + teardown 状态到 `_raw/wuying_browse.md` |
| Session 漏关 | 任意 | Lead 在 Phase 3 读 wuying_browse.md 时检查 teardown 字段；缺失 → block 报告 |
| API key 泄露 | 任意 | 不允许内联打印；teardown 输出必须从 `.env` 重读 |
| 反爬 / 内容墙 | 任意 | 在 wuying_browse.md 显式记录"哪些没拿到"，报告里标 N/A 不假装拿到 |
| `agent-browser` 不能 attach | 任意 | 降级 Playwright/Puppeteer 或手动观察；不允许静默跳过 |

**规则两条**（`metric-brand-auditor/references/wuying-browser.md:140-146`）：
1. 一次 skill 调用 = 一个 session。如果晚些再要平台，开新 session，不要让旧的 park 着。
2. teardown 状态必须落 `wuying_browse.md`。Lead 在 Phase 3 检查。

---

## 7. MCP 化路线（v0.3+）

未来 MCP server 会暴露 `mba.audit_brand` tool，含参数：

```jsonc
{
  "brand": "string",
  "skip_wuying": { "type": "boolean", "default": false },
  // ...
}
```

对应错误码 `WUYING_UNAVAILABLE`：云浏览器 leg 失败 → 自动降级 `--quick`，在报告里标注，不阻断流程。
（`docs/mcp-server-design.md:212, 363`）

---

## 8. 快速排错清单

| 症状 | 检查 | 来源 |
|------|------|------|
| `WUYING_API_KEY not set` | `.env` 不存在 / key 仍是 `your_api_key_here` | `docs/05-usage.md:222-225` |
| `ModuleNotFoundError: agentbay` | `pip install --user agentbay-sdk` | `docs/06-installation.md:134` |
| RESOURCE_URL 为空 | SDK 版本不暴露；用 describe-session 直查 | `references/wuying-browser.md:134-136` |
| `agent-browser` 找不到 | non-login SSH 不含 `/opt/homebrew/bin`；用 `bash -lc` 或绝对路径 | `references/wuying-browser.md:36-42` |
| Session 未释放 | 用 `docs/06-installation.md:157-165` 的应急脚本 | `docs/06-installation.md` |

---

## 9. 相关文档

- `metric-brand-auditor/references/wuying-browser.md` — 操作规范权威源
- `docs/03-architecture.md` — 整体架构里的 Wuying 定位
- `docs/04-pipeline.md` — Phase 2 调度细节
- `docs/06-installation.md` — 安装与冒烟测试
- `scripts/wuying/README.md` — 脚本最小说明

---

*生成于 2026-06-02，对应 v0.2.25 仓库快照。如果新增/删除了 Wuying 相关文件，请同步更新本文档第 3 节的位置表。*
