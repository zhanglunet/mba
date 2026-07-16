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
  ├── type: 'cron' | 'webhook'   # 均已接线;keyword/news 已于 2026-07-16 从 schema 移除(见 §3 注)
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

> **⚠️ schema 现状(2026-07-16 清账)**:`subscribe_brand` 的 trigger enum **只保留 `cron` 与 `webhook`**——两者均已接线(`cron` 由 scheduler 定期轮询,`webhook` 由 receiver 的 `POST /webhooks/trigger` 入站)。**`keyword` / `news` 已从 schema 移除**:它们此前被 schema 收下、但 scheduler 从不执行(静默 no-op),会让用户"订阅了却永不触发";移除后 `subscribe_brand` 对这两种 type 明确报错,而非静默吞掉。下面 §3.1 / §3.2 保留为**未来 RSS 接入(P3-B-3)的设计草案**,当出网可用、真正接 RSS 时再把 type 引回。

### 3.1 keyword（关键词监控 · 设计草案,未接线）

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

### 3.2 news（新闻 RSS / API · 设计草案,未接线）

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

## 5.5 Brand Watch 事件流消费 ✅ skill 侧已接(2026-07-12 · W4)

Brand Watch(docs/15 PRD / docs/16 实现)为每个已发布品牌维护连续事件流
`watch/<slug>/events.yaml`(可溯源:URL + 逐字引用 + 时间戳;P0-P3 分级 + `lens_map`)。
EVOLUTION 与它的接口(SKILL.md 已落):

1. **Phase 1E 先消费**:读 `last_update_date` 之后的全部事件;P0/P1 事件的 `lens_map`
   维度**必须**在 diff plan 标 YES,并引用事件 id 作证据(diff plan 模板新增
   `Watch events since v{n}` 行)——不重复发现 watch 流已记录的东西;
2. **Phase 2E 贴入 prompt**:与被标维度相关的事件(id/date/title/quote/url)作为
   **已核实线索**贴给 sub-agent,指示"先从事件 URL 验证与扩展,再泛搜"——
   有据事件优先级高于新发现;
3. **边界**:watch 事件只作调研输入与重审触发建议,**绝不直接改分**(docs/15 §5.3);
4. MCP 侧对应(`get_watch_events` / `record_watch_event` 与探针的
   `evolution_context` 喂入)排在 W7,见 docs/16 §1。

与 §5 维度差分的关系:watch 事件是"变化探针"之前更廉价、更有据的第一层证据——
有 P0/P1 事件的维度可以跳过探针直接标 CHANGED。

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

## 7.5 通知推送（notify）✅ 已实现（2026-07-02）

演化审计完成后（`trigger_evolution` 或 cron scheduler 触发），runner 的 `onComplete`
钩子自动算 delta 并推送到订阅的 notify targets：

- **`webhook`**：HTTP POST delta payload（`event: "mba.evolution.done"` + brand/audit_id/overall_delta/summary/delta_markdown）到指定 URL，10s 超时
- **`email`**：通过 Resend API 发送（需 `MBA_RESEND_API_KEY` + `MBA_NOTIFY_FROM`），未配置时静默跳过
- **`mcp-push`**：被动服务，客户端轮询 `get_status` / `get_delta_report` 即可

**容错**：每个 target 独立投递（`Promise` 逐个 await），单个失败不影响其他；通知错误
不会导致审计失败（best-effort，`onComplete` 包在 try/catch 内）。

**实现**：`src/notify/{webhook,email,dispatch}.ts`；`runner.ts` 的 `onComplete` 可选参数；
`trigger-evolution.ts` 构造 onComplete（算 delta → dispatchNotifications）。
测试：`tests/notify/dispatch.test.ts`（8 例，mock fetch）。

---

## 8. 实现优先级

| 阶段 | 内容 | 状态 |
|---|---|---|
| P3-B-1 | `subscribe_brand` + `trigger_evolution` + cron 触发器 | ✅ 完成 2026-06-30 |
| P3-B-2 | delta 报告生成（score diff + 叙述） | ✅ 完成 2026-07-02 |
| P3-B-5 | EVOLUTION 增量维度重跑（成本优化） | ✅ 完成 2026-07-02 |
| P3-B-4a | notify 推送（webhook out + email） | ✅ 完成 2026-07-02 |
| P3-B-4b | webhook **接收端**（外部推送触发） | ✅ 完成 2026-07-05 |
| P3-B-3 | keyword / news RSS 触发器 | ⛔ 未接线(需出网)；2026-07-16 已从 schema **移除**死枚举(静默 no-op),接 RSS 时再引回 |

---

## 9. 阻断项

- **Wuying Pro**：keyword 触发器依赖 GetLink() 抓取中文内容，免费版返回 400
- **webhook 接收端**：✅ 已实现（`mba-webhook-receiver`，`src/http/receiver.ts` + `src/receiver-main.ts`）。`POST /webhooks/trigger` 把外部事件转成 EVOLUTION 重审，共享 `MBA_STORE_DIR`，可选 `MBA_WEBHOOK_SECRET` 鉴权。仍需用户提供一个长运行部署位（小 VM / 容器 / systemd）——这是**部署**要求，非构建阻断。notify **出站** + webhook **入站** 均已就绪。
- **邮件推送**：已接 Resend，需用户提供 `MBA_RESEND_API_KEY`

---

*© 2026 MBA · Metric Brand Auditor*
