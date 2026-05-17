# MBA MCP Server — 设计思路与开发手册

**Status:** Draft 1 · 2026-05-09
**Owner:** zhanglunet
**Scope:** 把 MBA(Metric Brand Auditor)从"在我自己的 Claude Code 里跑"演化为"任何 MCP-capable agent 都能 install 的 skill"

---

## 目录

- [Part 1 — 设计思路](#part-1--设计思路)
- [Part 2 — 架构](#part-2--架构)
- [Part 3 — API 规约](#part-3--api-规约)
- [Part 4 — 扩展点](#part-4--扩展点)
- [Part 5 — 开发手册](#part-5--开发手册)
- [Part 6 — 安全与成本](#part-6--安全与成本)
- [Part 7 — 路线图](#part-7--路线图)
- [附录 A — 与现有 SKILL.md 的映射](#附录-a--与现有-skillmd-的映射)
- [附录 B — Caller 接入示例](#附录-b--caller-接入示例)

---

# Part 1 — 设计思路

## 1.1 问题陈述

当前 MBA 是 Claude Code 专属的 skill 包(`metric-brand-auditor/SKILL.md`),只能在用户本机的 Claude Code CLI 里通过 `/mba <brand>` 触发。这带来三个问题:

1. **触达面窄** —— OpenClaw / Hermes / Cursor / Cline / 任何自建 agent 框架都用不上
2. **没法自动化** —— 想在 CI 里"每周对自家品牌跑一次"需要人坐在 Claude Code 前面
3. **依赖 Claude Code 的交互** —— SKILL.md 里的 GATE 1(让用户确认 PRD)假定有交互式终端

把 MBA 包成 **MCP server** 一次性解决这三个问题:任何支持 MCP 的客户端都能装,远程 agent 也能调,GATE 改成两阶段提交(`propose` → `confirm`)就能在非交互场景跑。

## 1.2 三个不做(明确 scope)

| 不做 | 原因 |
|---|---|
| **托管 SaaS / 集中式品牌库** | 那是 Layer 2 的工作,本设计只覆盖"open-source MCP server",caller 自己持有 API key 和报告 |
| **评委市场 / 第三方上架** | 第一版只支持随 bundle 发布的内置评委 + 用户本地添加自定义评委,不做评委发现/分发 |
| **多 LLM 后端抽象** | 第一版强依赖 Anthropic API。换 backend 等后面真有人提需求再说 |

## 1.3 核心抽象

### Skill bundle = 评委 + 编排,不可分包

随 bundle 发布的 perspective skill 是 MBA 的灵魂,一起包发布。允许用户**追加**自定义评委,但不允许从安装包里删除内置评委(可以选择不让某个评委参与某次审计,但 server 内的内置数据始终在)。

### Audit job = 有状态、可中断、可恢复

一次品牌审计典型耗时 15-25 分钟,中途任何环节都可能失败(网络抖动、API rate limit、sub-agent 超时)。状态机必须显式建模,失败可以从最后一个 checkpoint 续跑,而不是从头来过。

### Caller-owned everything

API key、artifact 存储路径、UI 触发点都在 caller 进程内,server 进程是无状态的(状态全部落地在 filesystem,server 重启可恢复)。这是 MCP 推荐的部署模型,也避开"我们要不要保管你的 key"这个法律 + 信任地雷。

## 1.4 为什么是 MCP(对比其他选项)

| 选项 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| **MCP server** | 一套接 N 个客户端;协议成熟;tool/resource/prompt 三种原语刚好覆盖 MBA 的需求 | 远程模式还在演化(SSE → Streamable HTTP) | ✅ 主推 |
| REST API | 任何语言都能 call | 每个 caller 都要写 client 胶水;丢失 Claude Code 那种"agent 自动选工具"的语义 | ❌ |
| gRPC | 性能好 | 学习曲线;agent 圈不普及 | ❌ |
| Anthropic Managed Agents | 托管省事 | 锁死 Anthropic;caller 要走 Anthropic 账号 | ⏸️ 可作为可选第二投递通道 |
| Claude Code Plugin only | 跟现状一样 | 触达面窄 | ❌ 现状 |

---

# Part 2 — 架构

## 2.1 进程模型

```
┌─────────────────────────────────────────────────────────────┐
│  Caller process                                              │
│  (Claude Desktop / OpenClaw runtime / Hermes / Cursor / CI)  │
│                                                               │
│   ANTHROPIC_API_KEY ──┐                                       │
│   MBA_STORE_DIR ──────┤  (env)                                │
│   MBA_LOG_LEVEL ──────┘                                       │
└──────────────┬──────────────────────────────────────────────┘
               │  MCP over stdio (default) | SSE | streamable HTTP
               ▼
┌─────────────────────────────────────────────────────────────┐
│  mba-mcp-server (single Node process)                        │
│                                                               │
│   ┌────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│   │ Transport  │→ │ Tool         │→ │ Orchestrator       │  │
│   │ (stdio/SSE)│  │ Dispatcher   │  │ (Lead 逻辑)         │  │
│   └────────────┘  └──────────────┘  └─────────┬──────────┘  │
│                                                │              │
│         ┌──────────────────┬───────────────────┼──────┐      │
│         ▼                  ▼                   ▼      ▼      │
│   ┌──────────┐    ┌────────────────┐   ┌──────────┐  ...    │
│   │ Anthropic│    │ Judge bundle   │   │ Artifact │         │
│   │ client   │    │ loader         │   │ store    │         │
│   │          │    │ (内嵌 5 评委 + │   │ (filesys)│         │
│   │          │    │  用户自定义)   │   │          │         │
│   └──────────┘    └────────────────┘   └──────────┘         │
│         │                                                     │
│         └──→ caller-provided ANTHROPIC_API_KEY                │
└─────────────────────────────────────────────────────────────┘
                                                                 
   Artifact filesystem(默认 ~/.mba/audits/<audit_id>/):       
       state.json          ← 状态机当前快照                      
       proposal.md         ← Phase 1 输出(待 confirm)           
       _raw/               ← 子 agent 原始输出                   
       reviews/            ← 评委打分                            
       report.md / html    ← 最终产物                            
```

**进程边界关键点:**
- server 是无状态进程,所有持久数据写 filesystem
- 一个 server 实例可以同时跑多个并发 audit(每个 audit 一个 worker promise)
- 单 audit 内部 sub-agent 调用走 `Promise.all` 并行,但受 `MBA_MAX_PARALLEL`(默认 5)限流

## 2.2 Audit 生命周期状态机

```
                  ┌─────────┐
                  │  none   │   (audit_id 不存在)
                  └────┬────┘
        propose_audit  │
                       ▼
                  ┌──────────┐    failed   ┌─────────┐
                  │ proposed │────────────→│ failed  │
                  └────┬─────┘             └─────────┘
       confirm_audit   │
                       ▼
                  ┌─────────────┐
                  │ researching │  ← Phase 2: N parallel sub-agents
                  └────┬────────┘
                       ▼
                  ┌──────────────┐
                  │ synthesizing │  ← Phase 3: Lead 合成
                  └────┬─────────┘
                       ▼
                  ┌──────────┐
                  │ judging  │   ← Phase 4: 5 (or N) judges in parallel
                  └────┬─────┘
                       ▼
                  ┌──────────┐
                  │ merging  │   ← Phase 5: Lead 合成最终报告
                  └────┬─────┘
                       ▼
                  ┌──────┐
                  │ done │
                  └──────┘
```

**状态持久化协议:**
- 每次状态切换写 `state.json` 用 atomic rename(`tmp` → `state.json`)
- `state.json` 包含 `phase`, `started_at`, `last_progress_at`, `completed_phases[]`, `failed_phases[]`, `partial_results{}`
- server 重启时扫 `~/.mba/audits/`,把所有非 `done`/`failed` 的 audit 标记为 `interrupted`,等 caller 调 `resume_audit` 触发续跑

## 2.3 报告产物

每个 audit 产出 4 类 artifact,落盘到 `<store>/audits/<audit_id>/`:

| Artifact | 用途 | 谁读 |
|---|---|---|
| `state.json` | 状态机快照 | server 自己 + caller(通过 `get_status` 间接看) |
| `proposal.md` / `_raw/synthesis.md` / `_raw/dimension_*.md` / `_raw/wuying_browse.md` | 中间产物,留作可复盘 | 人工审计 / 后续 evolution |
| `reviews/<judge>.md` | 评委打分卡 | merge 阶段读 |
| `report.md` / `report.html` / `versions/v{n}_<date>.{md,html}` | 终态报告 | 用户读 |

`report.html` 仍然是自包含 HTML(Chart.js + Mermaid 走 CDN),caller 直接 `open` 就能看。

---

# Part 3 — API 规约

## 3.1 工具列表(server 暴露给 caller 的)

| Tool | 同步/异步 | 用途 |
|---|---|---|
| `propose_audit` | 同步 | 给品牌名生成 PRD,返回 audit_id + proposal markdown |
| `confirm_audit` | 异步 | 用户/agent 同意 PRD(可带 edits)后启动 Phase 2-5 |
| `get_status` | 同步 | 查询 audit 状态、进度、token 累计 |
| `fetch_report` | 同步 | 拉最终报告(markdown / html / both) |
| `list_audits` | 同步 | 列出本机所有 audit |
| `cancel_audit` | 同步 | 取消进行中的 audit(发送中断信号) |
| `resume_audit` | 同步 | 恢复一个 `interrupted` 状态的 audit |
| `add_judge` | 同步 | 注册自定义评委到本 server 实例(内存 + 磁盘) |
| `add_dimension` | 同步 | 注册自定义调研维度 |
| `serve_reports` | 同步 | 启本地静态服务(可选,默认关) |

## 3.2 详细 schema(JSON Schema 摘要)

### `propose_audit`

```jsonc
{
  "name": "propose_audit",
  "description": "Given a brand name (or URL), generate a PRD proposal and return an audit_id. Does NOT start research yet — caller must call confirm_audit.",
  "inputSchema": {
    "type": "object",
    "required": ["brand"],
    "properties": {
      "brand": { "type": "string", "description": "Brand name or homepage URL" },
      "mode": { "enum": ["fresh", "evolution", "auto"], "default": "auto" },
      "focus_dimensions": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Restrict research to these dimension names (default = all 7)"
      },
      "judges": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Subset of judge names to invoke (default = all 5 built-in)"
      },
      "skip_wuying": { "type": "boolean", "default": false },
      "language": { "enum": ["zh", "en", "auto"], "default": "auto" }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "audit_id": { "type": "string", "description": "format: <brand-slug>-<yyyymmdd>-<HHMM>" },
      "proposal_markdown": { "type": "string" },
      "estimated_runtime_min": { "type": "number" },
      "estimated_token_cost_usd": { "type": "number" }
    }
  }
}
```

### `confirm_audit`

```jsonc
{
  "name": "confirm_audit",
  "description": "Confirm the proposal and start Phase 2 onwards. Non-blocking — returns immediately with status=researching.",
  "inputSchema": {
    "type": "object",
    "required": ["audit_id"],
    "properties": {
      "audit_id": { "type": "string" },
      "edits": {
        "type": "object",
        "description": "Optional overrides to the proposal",
        "properties": {
          "drop_dimensions": { "type": "array", "items": { "type": "string" } },
          "add_dimensions": { "type": "array", "items": { "type": "string" } },
          "drop_judges": { "type": "array", "items": { "type": "string" } }
        }
      }
    }
  }
}
```

### `get_status`

```jsonc
{
  "name": "get_status",
  "inputSchema": {
    "type": "object",
    "required": ["audit_id"],
    "properties": { "audit_id": { "type": "string" } }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "audit_id": { "type": "string" },
      "phase": { "enum": ["proposed", "researching", "synthesizing", "judging", "merging", "done", "failed", "interrupted"] },
      "progress_pct": { "type": "number" },
      "started_at": { "type": "string", "format": "date-time" },
      "last_progress_at": { "type": "string", "format": "date-time" },
      "completed_phases": { "type": "array", "items": { "type": "string" } },
      "errors": { "type": "array", "items": { "type": "object" } },
      "tokens_used": { "type": "object", "properties": { "input": { "type": "number" }, "output": { "type": "number" } } }
    }
  }
}
```

### `fetch_report`

```jsonc
{
  "name": "fetch_report",
  "inputSchema": {
    "type": "object",
    "required": ["audit_id"],
    "properties": {
      "audit_id": { "type": "string" },
      "format": { "enum": ["markdown", "html", "both"], "default": "markdown" }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "markdown": { "type": "string" },
      "html": { "type": "string" },
      "version": { "type": "number" },
      "generated_at": { "type": "string", "format": "date-time" }
    }
  }
}
```

### `add_judge`

```jsonc
{
  "name": "add_judge",
  "description": "Register a custom judge persona. Caller must supply a markdown file conforming to the perspective-skill schema (front matter + character DNA + anti-fabrication rules).",
  "inputSchema": {
    "type": "object",
    "required": ["name", "persona_markdown"],
    "properties": {
      "name": { "type": "string", "pattern": "^[a-z][a-z0-9-]{1,30}$" },
      "persona_markdown": { "type": "string" },
      "validate_only": { "type": "boolean", "default": false }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "registered": { "type": "boolean" },
      "validation": {
        "type": "object",
        "properties": {
          "has_anti_fabrication": { "type": "boolean" },
          "has_decision_heuristics": { "type": "boolean" },
          "warnings": { "type": "array", "items": { "type": "string" } }
        }
      }
    }
  }
}
```

## 3.3 资源(MCP resources)

Server 把内置数据当 resource 暴露,caller 可读但不可写:

| URI | 内容 |
|---|---|
| `mba://judges/fusheng` | 傅盛 perspective 全文 markdown |
| `mba://judges/jobs` | Steve Jobs perspective |
| `mba://judges/likejia` | 李可佳 perspective |
| `mba://judges/wu-jundong` | 吴俊东 perspective |
| `mba://judges/zhang-yiming` | 张一鸣 perspective |
| `mba://dimensions/default` | 默认 7 维度规范 |
| `mba://audits/<audit_id>/report.md` | 已完成 audit 的报告 |
| `mba://audits/<audit_id>/report.html` | 同上,HTML 版 |

caller 可以用这些 resource 做"先看一眼评委长什么样再决定要不要用"之类的预浏览。

## 3.4 错误码与重试

| Code | 含义 | 重试? |
|---|---|---|
| `INVALID_BRAND` | 品牌名解析失败 | 否,要 caller 改 input |
| `AUDIT_NOT_FOUND` | audit_id 不存在 | 否 |
| `AUDIT_ALREADY_RUNNING` | 同 brand 同 mode 已在跑 | 等当前结束或 cancel |
| `ANTHROPIC_RATE_LIMIT` | API 限流 | 是,server 内部退避指数重试 3 次,然后冒泡 |
| `ANTHROPIC_OVERLOADED` | 5xx | 是 |
| `ANTHROPIC_AUTH` | API key 无效 | 否 |
| `WUYING_UNAVAILABLE` | 云浏览器 leg 失败 | 否,自动降级为 `--quick`,在报告里标注 |
| `JUDGE_PERSONA_INVALID` | add_judge 校验未过 | 否 |
| `STORE_FULL` | 磁盘满 | 否 |

---

# Part 4 — 扩展点

## 4.1 自定义评委 (`add_judge`)

调用方提交一份 markdown,server 做 schema 校验:

**必须包含的章节(否则 register 失败):**

1. YAML front matter 含 `name`, `description`, `expertise`
2. 至少一段"决策启发式 / 心智模型"(任意命名,只要 ≥ 5 条编号项)
3. 至少一段"表达 DNA"(展示这个角色怎么说话)
4. **明确的 anti-fabrication 红线**(必须包含字符串"不要激活" / "不可编造" / "anti-fabrication" 之一)

**校验通过后:**

- 写到 `~/.mba/judges/<name>.md`(持久化)
- 加到内存 judge registry
- 返回 `registered: true`

**`add_judge` 不重启 server**,后续 audit 立刻可以在 `judges` 参数里引用这个 name。

**移除自定义评委:** 删 `~/.mba/judges/<name>.md` 即可,server 启动时重新扫描。**随 bundle 发布的内置评委不可删**。

## 4.2 自定义维度 (`add_dimension`)

```jsonc
{
  "name": "founder-twitter-presence",
  "title_zh": "创始人 Twitter 阵地",
  "sub_questions": [
    "How often does the founder post?",
    "What's the engagement-to-follower ratio?"
  ],
  "search_seeds": [
    "<founder> twitter",
    "<founder> X handle"
  ]
}
```

## 4.3 Hooks(给 power user)

未来扩展:`registerHook(phase, fn)` 让外部代码在 Phase 2/3/4/5 前后插入逻辑。第一版**不做**,先看是否真有需求。

---

# Part 5 — 开发手册

## 5.1 技术选型

| 项 | 选择 | 理由 |
|---|---|---|
| 语言 | **TypeScript** | MCP TS SDK 最成熟;`npx mba-mcp-server` 一行装;生态广 |
| 运行时 | Node 20+ | 内置 fetch / atomic file ops |
| 包管理 | pnpm + workspaces | 一个 monorepo 装下 server + future SDK |
| MCP SDK | `@modelcontextprotocol/sdk` (官方) | |
| LLM 客户端 | `@anthropic-ai/sdk` | |
| 验证 | `zod` | tool input/output schema 自动转 JSON Schema |
| 测试 | `vitest` | |
| Bundler | `esbuild` → 单文件 dist | npx 启动快 |

> Python 版本(`pip install mba-mcp-server`) 计划在 v0.3 加,先把 TS 版打磨到稳定。

## 5.2 仓库结构(扩展后)

```
mba/                                     ← 仓库根
├── packages/
│   └── mcp-server/                      ← 新增
│       ├── src/
│       │   ├── index.ts                 entry: 装 transport + dispatcher
│       │   ├── server.ts                MCP server 实例化
│       │   ├── tools/
│       │   │   ├── propose-audit.ts
│       │   │   ├── confirm-audit.ts
│       │   │   ├── get-status.ts
│       │   │   ├── fetch-report.ts
│       │   │   ├── list-audits.ts
│       │   │   ├── cancel-audit.ts
│       │   │   ├── resume-audit.ts
│       │   │   ├── add-judge.ts
│       │   │   ├── add-dimension.ts
│       │   │   └── serve-reports.ts
│       │   ├── orchestrator/
│       │   │   ├── state-machine.ts     状态切换 + atomic write
│       │   │   ├── phase-1-proposal.ts
│       │   │   ├── phase-2-research.ts  N 个 sub-agent 并行
│       │   │   ├── phase-3-synthesis.ts
│       │   │   ├── phase-4-judging.ts
│       │   │   └── phase-5-merge.ts
│       │   ├── judges/
│       │   │   ├── built-in.ts          运行时把内置 perspective 内联进 bundle
│       │   │   ├── loader.ts            校验 + 注册自定义评委
│       │   │   └── validate.ts
│       │   ├── llm/
│       │   │   ├── anthropic-client.ts  用 caller 提供的 key
│       │   │   └── prompt-builder.ts
│       │   ├── store/
│       │   │   ├── filesystem.ts        ~/.mba/audits/ 读写
│       │   │   └── atomic.ts
│       │   ├── resources/
│       │   │   └── handler.ts           mba:// URI 解析
│       │   └── types.ts
│       ├── tests/
│       │   ├── tools/                   per-tool unit tests
│       │   ├── orchestrator/            phase-by-phase
│       │   ├── e2e/                     mini-brand 全流程
│       │   └── fixtures/                录制的 anthropic 响应
│       ├── package.json
│       ├── tsconfig.json
│       ├── vitest.config.ts
│       └── README.md
│
├── metric-brand-auditor/                ← 现状保留
│   └── SKILL.md                              做为人类可读规范,
│                                              未来 mcp-server 启动时扫这个文件
│                                              当 prompt 模板源(单一事实源)
├── *-perspective/                       ← 现状保留,被 judges/built-in.ts 编译时内联
├── research/
├── docs/
│   └── mcp-server-design.md             ← 本文
├── pnpm-workspace.yaml                  ← 新增
└── package.json                         ← 新增(root)
```

## 5.3 Quick start

```bash
# 一次性
pnpm install
pnpm --filter mcp-server build

# 开发循环
pnpm --filter mcp-server dev      # tsc --watch
pnpm --filter mcp-server test     # vitest watch
pnpm --filter mcp-server inspect  # 启用 MCP Inspector

# 发布
pnpm --filter mcp-server release  # bump + build + npm publish
```

## 5.4 本地接到 Claude Desktop 调试

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```jsonc
{
  "mcpServers": {
    "mba-dev": {
      "command": "node",
      "args": ["<HOME>/mba/packages/mcp-server/dist/index.js"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "MBA_STORE_DIR": "/tmp/mba-dev-audits",
        "MBA_LOG_LEVEL": "debug"
      }
    }
  }
}
```

重启 Claude Desktop,在对话里说"用 mba 审 OpenClaw" → Claude 应该自动调 `propose_audit`。

发布版本则用:

```jsonc
{
  "mcpServers": {
    "mba": {
      "command": "npx",
      "args": ["-y", "mba-mcp-server@latest"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

## 5.5 测试策略

### 单元测试(快、无网络)

- `tools/*` — 每个 tool 的 input schema 校验、output 形状
- `orchestrator/state-machine.ts` — 所有合法/非法状态转移
- `judges/validate.ts` — anti-fabrication 红线、front matter 校验

### 合约测试(中速)

- 用 `record/replay` 模式针对 Anthropic API mock(`fixtures/anthropic-response-*.json`)
- 跑 phase 2 / 3 / 4 / 5 各自的"理想路径"和"一个 sub-agent 失败"路径

### E2E 测试(慢,需要真 API key,可选)

- 跑一个 mini brand:1 维度 + 1 评委(只调 `wu-jundong-perspective` 看耗时)
- 校验:`audit_id` 全状态机走完、`report.md` 内容非空、`report.html` 无 Mermaid 语法错
- 加 `MBA_TEST_API_KEY` env 才会触发,避免误烧 token

## 5.6 调试技巧

| 场景 | 工具 |
|---|---|
| 看每条 MCP message | `MBA_LOG_LEVEL=trace`,server 把 `JSON-RPC` 双向 log 到 stderr |
| 不通过 Claude 直接调工具 | `npx @modelcontextprotocol/inspector node dist/index.js` 起一个 web UI |
| 排查"audit 卡在某个 phase" | `cat ~/.mba/audits/<id>/state.json` 看 last_progress_at |
| 复现一次失败的 phase 2 | `MBA_REPLAY=<audit_id> pnpm --filter mcp-server replay` |

## 5.7 发布

- **semver 规则**:
  - patch: bug fix / 文案
  - minor: 新工具 / 新内置评委 / 不破坏 schema
  - major: input/output schema 不向后兼容(慎重)
- **每次发布前**:
  - `pnpm --filter mcp-server test` 全绿
  - `npx @modelcontextprotocol/inspector` 手动跑一遍 propose → confirm → status → fetch
  - 在仓库 root 起 GitHub Release,release notes 同步到 `metric-brand-auditor/SKILL.md` 顶部 changelog

---

# Part 6 — 安全与成本

## 6.1 API key 处理

- `ANTHROPIC_API_KEY` 只通过 env 读,**不写日志**(包括 trace 级)
- key 不进 `state.json`、不进 audit artifacts
- audit 失败时返回给 caller 的 error 必须脱敏,凡是包含 `Authorization` / `sk-ant-` / `Bearer` 前缀的字符串**一律截断**

## 6.2 成本透明

- `get_status` 返回 `tokens_used.input` / `tokens_used.output`
- `propose_audit` 返回 `estimated_token_cost_usd`(基于历史均值的粗估,标注"±50%")
- 进入 `confirm_audit` 时显式接受 cost ceiling: `confirm_audit({audit_id, max_cost_usd: 5})`,超过则中断

## 6.3 防滥用 / 默认上限

| 限制 | 默认 | env override |
|---|---|---|
| 单 audit 最大 token | 1.5M input + 200K output | `MBA_MAX_TOKENS_PER_AUDIT` |
| 单 audit 最大耗时 | 30 min | `MBA_MAX_AUDIT_RUNTIME_MIN` |
| 同时进行的 audit 数 | 3 | `MBA_MAX_CONCURRENT_AUDITS` |
| 单 server 实例存储上限 | 5 GB | `MBA_STORE_MAX_GB`(超时 reject 新 audit) |

---

# Part 7 — 路线图

| 版本 | 范围 | 预估 |
|---|---|---|
| **v0.1** | TS MCP server MVP:5 工具 + 5 内置评委 + filesystem store + stdio transport | 1-2 周 |
| **v0.2** | `add_judge` / `add_dimension` 扩展点 + `cancel_audit` / `resume_audit` 状态恢复 | 1 周 |
| **v0.3** | Streamable HTTP transport(让 server 可以远程部署)+ `serve_reports` | 3-5 天 |
| **v0.4** | Python 版 (`pip install`)(直接复用 TS 的 schema 通过 codegen) | 1 周 |
| **v0.5** | OpenClaw / Hermes 官方接入示例 + 在他们 marketplace 上架 | 协作驱动 |
| **v1.0** | API 稳定锁版,文档站(用 Cloudflare Pages 托管) | 锁版后 1 个月 |

非目标(明确不做):

- 跨 LLM backend 抽象(谁要谁来 PR)
- 评委市场 / 第三方上架
- 托管 SaaS

---

# 附录 A — 与现有 SKILL.md 的映射

| `metric-brand-auditor/SKILL.md` 的内容 | mcp-server 的对应位置 |
|---|---|
| Phase 0 路由 | `orchestrator/state-machine.ts` 的 `decideMode()` |
| Phase 1F PRD 起草 | `tools/propose-audit.ts` |
| GATE 1 等用户确认 | 拆成 `propose_audit` 返回 + `confirm_audit` 收 |
| Phase 2F 并行 sub-agent | `orchestrator/phase-2-research.ts` |
| Phase 3F Lead 合成 | `orchestrator/phase-3-synthesis.ts` |
| Phase 4F 5 评委 | `orchestrator/phase-4-judging.ts` + `judges/built-in.ts` |
| Phase 5F 合并 + HTML | `orchestrator/phase-5-merge.ts` + `references/html-report-template.md`(直接读) |
| `references/dimensions.md` | `mba://dimensions/default` resource |
| `references/judge-prompt-template.md` | `judges/prompt-builder.ts` 内联 |
| `references/wuying-browser.md` | Wuying leg 是可选的;v0.1 先实现成"WebFetch + WebSearch + 标记"的降级路径 |

**SKILL.md 的角色变化:**
- 现在:Lead 在 Claude Code 里读它来知道怎么编排
- 未来:仍然是**单一事实源**,mcp-server 启动时扫这个文件提取 phase 边界、prompt 模板、维度定义。这样改文档 = 改行为,不需要双写

## 附录 B — Caller 接入示例

### B.1 Claude Desktop / Claude Code

`~/.claude.json` 或 Claude Desktop config:

```jsonc
{
  "mcpServers": {
    "mba": {
      "command": "npx",
      "args": ["-y", "mba-mcp-server"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

对话:"用 mba 审一下 OpenClaw" → Claude 自动调 propose → 把 PRD 给用户看 → 用户 ok → 自动 confirm → 等 25 min → fetch_report 拿结果展示。

### B.2 Cursor

`.cursor/mcp.json`(同上)。

### B.3 Custom agent(OpenClaw / Hermes 框架)

伪代码(假设它们的 SDK 形状):

```ts
const mcpClient = await connectMCP({
  command: "npx",
  args: ["-y", "mba-mcp-server"],
  env: { ANTHROPIC_API_KEY: process.env.MY_KEY },
});

agent.registerTools(mcpClient.listTools());

// 用户在 OpenClaw 对话里说"评估 OpenClaw 这个品牌"
// agent 决定调 mba 的 propose_audit
// agent 收到 PRD,展示给用户
// 用户在 OpenClaw UI 里点"go" → agent 调 confirm_audit
// agent 轮询 get_status,完成后调 fetch_report,把 markdown 渲染回对话窗口
```

### B.4 CI / 定时任务

```bash
#!/bin/bash
# weekly-brand-scan.sh

AUDIT_ID=$(mcp-cli --server "npx -y mba-mcp-server" \
  call propose_audit --brand "OpenClaw" --mode evolution \
  | jq -r '.audit_id')

mcp-cli call confirm_audit --audit_id "$AUDIT_ID"

# poll until done
while true; do
  PHASE=$(mcp-cli call get_status --audit_id "$AUDIT_ID" | jq -r '.phase')
  [[ "$PHASE" == "done" || "$PHASE" == "failed" ]] && break
  sleep 60
done

mcp-cli call fetch_report --audit_id "$AUDIT_ID" --format html \
  > "/var/www/brand-reports/openclaw-$(date +%Y%m%d).html"
```

---

## 下一步

按时间顺序的 PR 队列(便于追踪):

1. **PR-01:** `pnpm-workspace.yaml` + 空的 `packages/mcp-server/` 骨架(package.json / tsconfig / vitest 配好,跑空 test 通过)
2. **PR-02:** `state-machine.ts` + filesystem store + 全部状态转移的单元测试
3. **PR-03:** `tools/propose-audit.ts` + `tools/confirm-audit.ts` + 校验 schema
4. **PR-04:** `orchestrator/phase-2-research.ts`(只跑 1 维度的最小版)
5. **PR-05:** `orchestrator/phase-3-synthesis.ts` + `phase-4-judging.ts`(把 5 评委打包内联)
6. **PR-06:** `phase-5-merge.ts` + HTML 渲染
7. **PR-07:** `add_judge` + `add_dimension`
8. **PR-08:** README + npm publish 第一版 v0.1.0

每个 PR 独立可 merge,每步都有可演示的 demo。
