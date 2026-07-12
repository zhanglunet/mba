# MBA MCP Server · 快速上手

> 把 MBA 品牌影响力审计接进任何支持 MCP 的 agent（Claude Desktop、Cursor、OpenClaw、CI…），
> 用自然语言发起审计、订阅品牌演化、收到主动通知。

**包**：`mba-mcp-server` · **传输**：stdio · **Node**：≥ 20 · **源码**：[`packages/mcp-server/`](../packages/mcp-server)

---

## 1. 60 秒上手

### Claude Desktop

编辑 `claude_desktop_config.json`：

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

重启 Claude Desktop，然后直接说：

> 用 mba 审一下 Anthropic

Claude 会调 `propose_audit` 给你一份 PRD（品牌、面板、评委、维度、成本估算）→ 你点头 → `confirm_audit` 启动后台流水线 → `get_status` 轮询进度 → `fetch_report` 拿最终报告。

### Cursor / 其他 MCP 客户端

任何读 `mcpServers` 配置的客户端同理，`command` + `args` + `env` 三件套即可。

---

## 2. 一次完整审计的对话流

| 步 | 你说 / 发生什么 | 工具 |
|---|---|---|
| 1 | "审一下 OpenClaw" | `propose_audit` → 返回 `audit_id` + PRD + 成本估算 |
| 2 | "可以，跑吧"（成本上限可选） | `confirm_audit` → 非阻塞，立即返回 `phase: researching` |
| 3 | "进度怎么样了" | `get_status` → phase / progress% / token 用量 |
| 4 | （done 后）"给我报告" | `fetch_report` → markdown / html |

流水线 5 阶段：**Research（7 维度并行）→ Synthesis → Judging（5 评委并行）→ Merge → Done**。
`confirm_audit` 立即返回，用 `get_status` 轮询——不会阻塞你的对话。

---

## 3. 品牌演化追踪（订阅 + 自动重审 + 通知）

MBA 不只是一次性点查询。订阅一个品牌，它有重大变化时自动重审并通知你。

```
订阅 → 触发（定时/事件/手动）→ 增量重审 → 算 delta → 主动推送
```

### 订阅

> 订阅小米，每 14 天复查一次，有变化 webhook 通知我 https://my.app/hook

```jsonc
// subscribe_brand
{
  "brand": "小米",
  "panel": "auto",
  "triggers": [{ "type": "cron", "config": { "interval_days": 14 } }],
  "notify":   [{ "type": "webhook", "url": "https://my.app/hook" }],
  "min_interval_days": 14,
  "max_per_month": 2
}
```

内置 `CronScheduler` 会在订阅到期时自动触发（服务设了 `ANTHROPIC_API_KEY` 即启动）。

### 手动/事件触发

> 小米发新车了，重审一下

```jsonc
// trigger_evolution
{
  "brand": "小米",
  "event_type": "product_launch",
  "event_summary": "小米 YU7 发布，起售价 25.35 万"
}
```

事件摘要会喂给**变化探针**——只重跑受影响的维度（product / distribution），不动 origin。
成本从全量 ~$3 降到 ~$0.3-0.6/次。

### delta 报告

审计完成后自动算，也可手动拉：

> 给我小米这次 vs 上次的对比

```jsonc
// get_delta_report — previous_audit_id 缺省自动找上一份
{ "audit_id": "xiaomi-20260703-1200" }
```

返回 per-lens 均值差（带 ▲▼）+ Biggest Movements + LLM 变化叙述。

### 通知

审计完成后自动推送到订阅的 notify targets：

| 类型 | 说明 | 需要 |
|---|---|---|
| `webhook` | HTTP POST delta payload | 你的 URL |
| `email` | Resend 发送 | `MBA_RESEND_API_KEY` + `MBA_NOTIFY_FROM` |
| `mcp-push` | 被动，轮询 `get_status` | — |

投递 best-effort、逐 target 独立：单个失败不影响其他，通知错误不会让审计失败。

### 舆情信号（Brand Watch，docs/15）

订阅链路的"水源"：`record_watch_event` 录入可溯源舆情事件（反捏造门槛与
`validate_watch.py` 同套），P0 事件或触发规则命中（30 天滚动窗 P0≥1 / P1≥3 /
加权 4·2·0.5 ≥6，2026-07-12 校准）时，经上表同一条 notify 链路下发**重审建议**——复用管道，不加新轮子。

```jsonc
// record_watch_event — 事实字段可溯源，判断字段恒标 model-judged
{
  "brand": "qianxin",
  "event": {
    "date": "2026-07-10", "dim": "W3", "severity": "P1", "direction": "pos",
    "title": "某大行 NDR 集采中标", "quote": "……原文逐字标题……", "quote_type": "title",
    "url": "https://example.com/notice", "fetched_at": "2026-07-12T08:00:00Z",
    "lens_map": ["leverage", "signal"]
  }
}
// get_watch_events — 读事件流 + 触发评估（只读）
{ "brand": "qianxin", "unconsumed_only": true }
```

**边界**：watch 工具只录信号、只发建议，**永不改分**——分数只能来自评委重审
（docs/15 §5.3）。事件写入 `MBA_WATCH_DIR`（默认 `./watch`）。

---

## 4. 自定义评委

内置 5 位评委（傅盛 / Jobs / 李可佳 / 吴俊东 / 张一鸣）。用 `add_judge` 注册自己的：

```jsonc
// add_judge — validate_only 先校验不注册
{
  "name": "my-critic",
  "persona_markdown": "# My Critic\n\n## Decision heuristics\n...\n\n## Anti-fabrication\n只基于简报证据推理，不编造私下见解。",
  "validate_only": true
}
```

校验器会检查 anti-fabrication 红线、决策启发式、长度等。通过后去掉 `validate_only` 正式注册。

---

## 5. 全部 16 个工具

**核心审计**

| 工具 | 作用 |
|---|---|
| `propose_audit` | 生成 PRD，返回 `audit_id`（不立即跑） |
| `confirm_audit` | 确认后启动 Phase 2-5，非阻塞 |
| `get_status` | 轮询 phase / progress% / token |
| `fetch_report` | 拉报告（markdown / html / both） |
| `list_audits` | 列出本机所有审计 |
| `resume_audit` | 从中断/失败的 phase 续跑审计 |
| `list_panels` | 列出可用面板及其评委阵容 |
| `add_judge` | 注册自定义评委 persona |

**演化追踪**

| 工具 | 作用 |
|---|---|
| `subscribe_brand` | 订阅品牌自动重审（cron/webhook 触发器） |
| `trigger_evolution` | 手动触发 EVOLUTION 重审（cadence guard） |
| `list_subscriptions` | 列出活跃订阅 |
| `unsubscribe_brand` | 删除订阅 |
| `get_delta_report` | 对比两次审计的评分变化 |
| `get_brand_trend` | 同品牌跨多次审计的评分轨迹 |

**舆情监控（Brand Watch）**

| 工具 | 作用 |
|---|---|
| `get_watch_events` | 读品牌舆情事件流 + 30 天滚动窗触发评估（只读） |
| `record_watch_event` | 录入可溯源舆情事件；P0/触发命中经订阅链路下发重审建议（永不改分） |

---

## 6. 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(必填)* | Anthropic API key |
| `MBA_STORE_DIR` | `~/.mba` | 审计产物存储目录 |
| `MBA_MAX_PARALLEL` | `5` | 单次审计最大并行子任务 |
| `MBA_MAX_CONCURRENT_AUDITS` | `3` | 最大同时审计数 |
| `MBA_LOG_LEVEL` | `info` | `error / warn / info / debug / trace` |
| `MBA_RESEND_API_KEY` | *(可选)* | Resend API key，启用邮件通知 |
| `MBA_NOTIFY_FROM` | *(可选)* | 邮件发件地址（配 Resend 时必填） |

---

## 7. 存储结构

```
~/.mba/
  audits/{audit_id}/
    state.json                 # 审计状态机
    _raw/                      # 7 维度研究 + synthesis + evolution_probes
    reviews/{judge}.md         # 各评委打分
    scores.json                # 结构化打分（供 delta 用）
    report.md / report.html    # 最终报告
    delta/vs_{prev}.md         # delta 报告
    versions/                  # 版本快照
  subscriptions/{id}.json      # 订阅配置
  judges/{slug}.md             # 自定义评委 persona
```

---

## 8. 深入

- [`packages/mcp-server/README.md`](../packages/mcp-server/README.md) · 开发 / 发布 / 测试
- [`docs/12-evolution-tracking.md`](12-evolution-tracking.md) · 演化追踪完整设计
- [`docs/mcp-server-design.md`](mcp-server-design.md) · 架构设计草案
- [`docs/04-pipeline.md`](04-pipeline.md) · 5 阶段流水线的人类详解

---

*© 2026 MBA · Metric Brand Auditor*
