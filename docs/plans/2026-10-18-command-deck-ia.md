# PRD-062/T1：指挥舱 dashboard 信息架构设计（草稿 v1）

> 依据：trend `adopted/PRD-062-mba-command-deck.md`；mba 真实报告结构
> （`published/reports/deepseek/report.md` §Score Matrix，2026-10-18 已核实）；
> 现有报告 HTML 模板风格（`published/reports/deepseek/report.html`）。
> T1 只定信息架构与接口约定，不写实现代码。

## 一、设计原则

1. **展示层**：dashboard 只展示、不重新打分、不改 mba 现有评分逻辑。
2. **一眼看**：管理层每天打开 1 分钟掌握品牌现状；首屏三个区块，无需滚动即见核心数字。
3. **数据诚实**：每个区块独立标注"上次更新时间"；过期数据明确提示，不拿旧数当新闻。

## 二、关键核实：维度结构（5 lens，非 7 维度）

**核实结论**：PRD §方案-1 写"综合评分 + 7 维度雷达"，但实测 mba 真实报告
`published/reports/deepseek/report.md` 的 `## Score Matrix` 章节为 **5 个 lens**：

| # | Lens key | 中文名 | v3 Mean（实测） |
|---|---|---|---|
| 1 | origin | 起源叙事 | 8.6 |
| 2 | category | 品类定义 | 8.2 |
| 3 | leverage | 杠杆点 | 7.8 |
| 4 | identity | 身份系统 | 8.0 |
| 5 | signal | 真实信号 | 9.0 |

**本文档口径**：一律以报告产物的实际 lens 结构为准（当前 5 个），雷达图画 5 轴。
若未来 panel 维度增减，以最新报告产物为准，dashboard 跟随——
聚合 JSON 里 `lenses` 为数组，不硬编码维度数量（见 §五）。

## 三、三个区块信息架构（固定）

### 区块一：品牌健康度

| 指标 | 说明 | 数据来源 | 刷新频率 |
|---|---|---|---|
| 综合评分 | 总分 X/250 ＋ 归一化 X/10 | 报告 `## Score Matrix` 表尾（Score Total / Score Normalized） | 随报告产出更新（事件驱动） |
| 5 lens 雷达 | 5 个 lens 的 Mean 值，雷达图 | Score Matrix 表 Mean 列 | 随报告产出更新 |
| 版本与日期 | 报告版本（vN）＋ 审计日期 | 报告标题 / meta description | 随报告产出更新 |
| 变化指示 | 每个 lens 的 Δ vs 上一版（↑n / ↔）＋ 总分 Δ | Mean 列"Δ vs v2"标记、表尾 v2 对比数 | 随报告产出更新 |

### 区块二：舆情

| 指标 | 说明 | 数据来源 | 刷新频率 |
|---|---|---|---|
| 近 7 天声量曲线 | 每日声量条形图（可叠正负面堆叠） | 舆情采集器（T2 新建）→ 聚合 JSON `sentiment.daily_volume` | 每日 |
| 正负面占比 | 近 7 天 positive/negative/neutral 占比 | 同上 `daily_volume` 汇总 | 每日 |
| Top3 热点事件 | 标题 ＋ 一句话摘要 ＋ 情感倾向 ＋ 时间 ＋ 来源链接 | 同上 `sentiment.top_events` | 每日 |
| 采集状态 | 正常 / 数据暂缺 | 采集器心跳（`sentiment` 段是否为 null） | 每日 |

降级规则：采集失败或源不可用时，本区块显示"数据暂缺"，不阻断健康度/竞品区块。

### 区块三：竞品动态

| 指标 | 说明 | 数据来源 | 刷新频率 |
|---|---|---|---|
| 竞品关键事件 | Top5：品牌 ＋ 事件标题 ＋ 时间 ＋ 来源链接 | 竞品追踪（T2 新建，对标品牌列表可配置）→ `competitors.events` | 每周 |
| 对标品牌清单 | 当前追踪的品牌列表（配置项展示） | `competitors.watch_list` | 随配置变更 |
| （预留）对标评分对比 | 本品牌 vs 对标品牌综合评分条形对比 | 二期"多品牌视图"启用，一期接口预留 `comparison` 字段 | — |

> 口径说明：PRD 非目标明确"第一期不做多品牌对比视图"，故一期竞品区块以
> "关键事件时间线"为主；评分对比字段在聚合 JSON 预留，二期直接可用。

## 四、页面形态

- **单页 HTML**：一个文件（如 `dashboard.html`）＋ 一个聚合 JSON（`data/deck.json`），
  静态托管或 `file://` 均可打开，无需后端。
- **复用报告模板风格**（`published/reports/deepseek/report.html` 已验证可复用的部分）：
  - `<meta name="viewport" content="width=device-width,initial-scale=1">`（手机可看已有基础）
  - CSS 变量：`--paper: #faf8f3` / `--ink: #111` / `--accent: #c1440e` / `--muted` 等
  - 字体栈：`ui-serif, "Noto Serif SC", "Songti SC", Georgia, serif`
  - 版式：`.wrap` 居中窄栏（报告 820px；指挥舱可放宽到 960px 容纳三区块）
  - 顶部 `header` ＋ `.mark` 品牌标识行（沿用 MBA 标识语）
  - 图表：报告已用 `chart.js@4.4.4` CDN（radar/bar）；指挥舱沿用同一 CDN，
    声量曲线用 bar/line、正负面占比用 doughnut，不引入重型框架
- **手机可看**：三区块在窄屏自动堆叠；图表容器 `width: 100%`；正文字号不小于 14px。
- **"上次更新时间"展示**：页面顶部通栏状态条，三个区块各自独立标注
  `更新于 YYYY-MM-DD HH:mm`（取聚合 JSON 各段 `updated_at`）。
- **数据过期提示规则**：
  - 舆情段 `updated_at` 超过 26 小时 → 本区块顶部琥珀色提示"舆情数据可能过期"；
  - 竞品段超过 8 天 → 同理提示；
  - 健康度段直接显示报告版本与审计日期（如"v3 · 2026-07-20"），不判断过期
    （报告产出即事件驱动更新）；
  - 某段为 null → 显示"数据暂缺"灰色占位，不阻断其他区块。

## 五、聚合 JSON 接口约定（T2 产出物，T3 只读）

dashboard **只读一个聚合 JSON**，不直连任何采集源。T2 聚合脚本负责生成，
T3 看板只做渲染，T4 定时任务负责刷新。

```jsonc
{
  "brand": "deepseek",
  "generated_at": "2026-10-18T09:00:00+08:00",
  "health": {
    "updated_at": "2026-07-20T10:00:00+08:00",
    "score_total": 208,
    "score_max": 250,
    "score_normalized": 8.32,
    "report_version": "v3",
    "report_date": "2026-07-20",
    "lenses": [
      {"key": "origin", "name_cn": "起源叙事", "mean": 8.6, "delta": "↔"},
      {"key": "category", "name_cn": "品类定义", "mean": 8.2, "delta": "↔"},
      {"key": "leverage", "name_cn": "杠杆点", "mean": 7.8, "delta": "↔"},
      {"key": "identity", "name_cn": "身份系统", "mean": 8.0, "delta": "↔"},
      {"key": "signal", "name_cn": "真实信号", "mean": 9.0, "delta": "↑0.2"}
    ]
  },
  "sentiment": {
    "updated_at": "2026-10-18T08:00:00+08:00",
    "daily_volume": [
      {"date": "2026-10-12", "count": 120, "positive": 70, "negative": 12, "neutral": 38}
    ],
    "top_events": [
      {"title": "…", "summary": "…", "sentiment": "positive", "at": "2026-10-17T15:00:00+08:00", "url": "https://…"}
    ]
  },
  "competitors": {
    "updated_at": "2026-10-15T08:00:00+08:00",
    "watch_list": ["…"],
    "events": [
      {"brand": "…", "title": "…", "at": "2026-10-14T10:00:00+08:00", "url": "https://…"}
    ],
    "comparison": null
  }
}
```

字段约定：
- 时间一律 ISO 8601 ＋ 时区（`+08:00`）。
- 任一段缺失/采集失败 → 该段为 `null`（不是空对象），看板显示"数据暂缺"。
- `lenses` 为数组，不硬编码数量（维度增减时看板自适应）。
- `delta` 取值：`"↔"` / `"↑n"` / `"↓n"`（与报告图例一致）。
- `sentiment` 枚举：`positive` / `negative` / `neutral`。
- `comparison` 一期为 `null`，二期启用多品牌对比时填入
  `[{"brand":"…","score_total":…,"score_normalized":…}]`。

## 六、非目标重申（PRD 原文）

1. 不重新打分、不改 mba 现有评分逻辑：dashboard 是纯展示层。
2. 第一期单品牌先行，不做多品牌对比视图（接口已预留 `comparison`）。
3. 不做历史数据回填：从上线日起积累；健康度"曲线"需至少两份报告才有意义，
   一期只展示最新一次报告的"快照 ＋ Δ"。

## 七、给 T2 / T3 / T4 的输入清单

- **T2（数据源接入，trend #319）**：
  1. 舆情采集器 → 输出 `sentiment` 段（`daily_volume` 近 7 天滚动、`top_events` Top3）；
     源可配置，失败时该段写 `null`。
  2. 竞品追踪 → 输出 `competitors` 段（`watch_list` 可配置、`events` Top5）。
  3. 聚合脚本 → 从最新报告产物抽取 `health` 段（可复用 PRD-023 抽取逻辑：
     Score Matrix 表尾 ＋ Mean 列），合并三段写出 `data/deck.json`。
- **T3（看板实现，trend #324）**：按 §四 实现单页 HTML，只读 `data/deck.json`；
  图表用 chart.js（与报告同版本 CDN）；实现 §四 的更新时间条与过期提示。
- **T4（自动刷新与告警，trend #326）**：定时任务——舆情每日、竞品每周、
  报告产出事件触发健康度段刷新（即重跑聚合脚本）；告警规则初版：
  综合评分下降超阈值 / 负面舆情声量突增 → 飞书推送；只推异动不推常规更新。
  阈值先宽松，跑两周按真实异动回调（PRD 风险预案）。

## 八、验收对接（PRD §验收标准 → 本设计覆盖）

| PRD 验收项 | 本设计对应 |
|---|---|
| 打开 URL 三区块齐全、"上次更新时间"明确 | §三指标清单 ＋ §四状态条 |
| 舆情/竞品自动刷新 | §五 `updated_at` ＋ §七 T4 |
| 构造评分骤降，飞书收到异动告警 | §七 T4 告警规则 |
| 管理层连续 7 天打开（或明确反馈不用每天看） | T5 试用（本 T1 不覆盖） |
