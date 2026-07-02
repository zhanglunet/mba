# P3-B · 报告订阅与品牌演化追踪设计

**版本：** v0.1-draft · 2026-06-30  
**状态：** 设计草稿（待实现）  
**前置条件：** P3-A MCP Server v0.1.0 完成（Phase 2-5 编排可运行）

---

## 1. 问题陈述

MBA 当前是"点查询"模式：用户主动发起一次审计，得到一份 v1 报告。  
缺失的是**持续监测**：品牌在以下事件后影响力会发生实质变化——

| 触发类型 | 举例 |
|---|---|
| 产品发布 | 新车型上市、App 大版本、新 SKU |
| 高管变动 | CEO 离职、创始人公开言论 |
| 负面事件 | 数据泄露、食安事故、监管处罚 |
| 行业冲击 | 政策重锤、头部竞对倒闭 |
| 里程碑 | 上市、融资、出海、营收破亿 |

目标：当上述事件发生时，**自动触发 EVOLUTION 模式重审**，产出 delta 报告（新旧对比），并推送给订阅方。

---

## 2. 核心概念

```
Subscription（订阅）
  ├── brand: string          # 被监测品牌
  ├── panel: string          # 使用的评委面板
  ├── triggers: Trigger[]    # 哪些信号触发重审
  ├── notify: NotifyTarget[] # 推送给谁
  └── cadence: Cadence       # 最低重审间隔（防抖）

Trigger
  ├── type: 'keyword' | 'news' | 'cron' | 'webhook'
  └── config: ...

NotifyTarget
  ├── type: 'webhook' | 'email' | 'mcp-push'
  └── url / address: string

Cadence
  ├── min_interval_days: number  # 两次重审之间最短间隔（默认 7 天）
  └── max_per_month: number      # 每月最多自动重审次数（防超限）
```

---

## 3. 触发器类型

### 3.1 keyword（关键词监控）

通过 Wuying Web 搜索轮询，检测到包含品牌名 + 信号词的新内容即触发。

```yaml
type: keyword
config:
  brand_aliases: ["小米", "Xiaomi", "MI"]
  signal_words: ["发布", "上市", "事故", "处罚", "裁员", "IPO", "收购"]
  sources: ["微博热搜", "36kr", "虎嗅", "techcrunch", "reuters"]
  poll_interval_hours: 6
```

**实现方式：** cron job 每 6 小时调 Wuying/Jina 搜索，命中即入队列。

### 3.2 news（新闻 RSS / API）

接入主流新闻 RSS，过滤品牌名，命中即触发。

```yaml
type: news
config:
  rss_feeds:
    - "https://36kr.com/feed"
    - "https://techcrunch.com/feed/"
  brand_filter: ["小米", "Xiaomi"]
```

### 3.3 cron（定期复查）

不管有无事件，每隔 N 天强制重跑一次 EVOLUTION 审计。

```yaml
type: cron
config:
  interval_days: 30   # 月度复查
  run_at: "03:00"     # UTC
```

### 3.4 webhook（主动推送）

外部系统（CRM、新闻聚合、PR 团队的 Slack Bot）通过 HTTP POST 触发。

```
POST /webhooks/trigger
{
  "brand": "xiaomi",
  "event_type": "product_launch",
  "event_summary": "Xiaomi 15 Ultra 发布，起售价 6999",
  "source_url": "https://..."
}
```

---

## 4. 执行流程

```
Trigger fired
    │
    ▼
TriggerQueue（去重 + 防抖）
    │ min_interval_days 未到 → 丢弃
    │ 已有进行中审计 → 合并等待
    ▼
EvolutionJob
    │ 读上次报告（last_audit_id）
    │ 运行 Phase 2-5（EVOLUTION 模式，只重跑变化大的维度）
    ▼
DeltaReport
    │ compare_scores(old, new) → score delta 表
    │ diff_narrative() → 变化叙述（+/-维度，评委分歧变化）
    ▼
Notify
    ├── webhook POST delta_report_url
    ├── email（摘要 + 链接）
    └── MCP push（get_status 轮询可见）
```

---

## 5. EVOLUTION 模式优化（维度差分）✅ 已实现（2026-07-02）

全量重跑 7 维度成本高（~$3/次）。EVOLUTION 模式改为**增量重跑**：

1. **维度变化检测**：对每个维度运行轻量"变化探针"（单次调用，256 tokens），返回 `VERDICT: CHANGED|UNCHANGED` + 一句理由。触发事件（`trigger_evolution` 的 `event_summary`）会通过 `options.evolution_context` 喂给探针，让"新品发布"这类信号精准命中相关维度
2. **只重跑标记为变化的维度**，`UNCHANGED` 维度直接复用上次 `_raw/dimension_N_slug.md`，合成 + 评委 + merge 阶段正常运行
3. **成本估算**：探针 7×~$0.001 + 重跑 2-4×~$0.15 = ~$0.3-0.6/次（vs 全量 ~$3，省 80%+）
4. **保守回退**：探针响应无法解析时默认 `CHANGED`（重研究比用陈旧数据更安全）；上次无对应维度文件时也走全量研究
5. **透明度**：每次演化写 `_raw/evolution_probes.md`，逐维记录 verdict + 复用/重研究状态

**实现**：`src/orchestrator/phase-2-evolution.ts`（`runPhase2Evolution`）；`runner.ts` 在 `mode === 'evolution' && previous_audit_id` 时自动切到此路径；`llm/prompts.ts` 的 `changeProbeSystemPrompt` / `changeProbeUserPrompt`。测试：`tests/orchestrator/phase-2-evolution.test.ts`（5 例）。

---

## 6. MCP 工具扩展（P3-B 新增）

在现有 6 个工具基础上新增：

| 工具 | 说明 |
|---|---|
| `subscribe_brand` | 创建订阅（brand + triggers + notify + cadence） |
| `list_subscriptions` | 列出所有活跃订阅 |
| `unsubscribe_brand` | 删除订阅 |
| `trigger_evolution` | 手动触发 EVOLUTION 重审（等同 webhook） |
| `get_delta_report` | 拉取两个 audit_id 之间的 delta 报告 |

---

## 7. 存储结构扩展

```
~/.mba/
  subscriptions/
    {brand-slug}.yaml          # 订阅配置
  triggers/
    queue.jsonl                # 待处理触发事件队列（append-only）
    processed.jsonl            # 已处理记录（用于去重）
  {audit_id}/                  # 已有结构不变
    delta/
      vs_{prev_audit_id}.md    # delta 报告
      vs_{prev_audit_id}.json  # 结构化 score diff
```

---

## 8. 实现优先级

| 阶段 | 内容 | 估时 |
|---|---|---|
| P3-B-1 | `subscribe_brand` + `trigger_evolution` + cron 触发器 | 1-2 天 |
| P3-B-2 | delta 报告生成（score diff + 叙述） | 1 天 |
| P3-B-3 | keyword / news RSS 触发器 | 1-2 天 |
| P3-B-4 | webhook 接收端 + notify 推送 | 1 天 |

---

## 9. 阻断项

- **Wuying Pro**：keyword 触发器依赖 GetLink() 抓取中文内容，免费版返回 400
- **部署环境**：cron/webhook 需要长运行进程（本地 Node.js daemon 或 Cloudflare Workers Cron Triggers）
- **邮件推送**：需要 SMTP 或 Resend API key

---

*© 2026 MBA · Metric Brand Auditor*
