# 项目周报 · Weekly Reports

面向非技术读者的每周开发进展报告：解决了哪些问题、交付了哪些功能、沉淀了哪些方法论。

| 周期 | 报告 | 里程碑 |
|---|---|---|
| 截至 2026-07-12 | [2026-07-12.md](2026-07-12.md) | v0.4.1→v0.4.3 三连发 · 评委深化收官(42/43) · Brand Watch 舆情监控全线上线 |
| 截至 2026-07-05 | [2026-07-05.md](2026-07-05.md) | v0.4.0 发布 · 品牌演化追踪闭环 · 10 份行业报告 |

> 网页版同步发布于 [mbabrand.com/weekly.html](https://mbabrand.com/weekly.html)（最新一期 +
> **历史周报时间线**）；每期另有独立存档页 `mbabrand.com/weekly/<日期>.html`，永久可链。

## 如何新增一份周报

Markdown 是唯一事实源，网页由脚本从它生成，两边不会跑偏。

```bash
# 1. 生成骨架（日期默认今天），并自动在上表追加一行
python3 scripts/new_weekly.py new 2026-07-12 --milestone "本周里程碑"

# 2. 填写 docs/weekly/2026-07-12.md（照着 TEMPLATE.md 的结构写）

# 3. 重生成全部网页：site/weekly.html（最新期 + 时间线）+ site/weekly/<日期>.html 存档页
python3 scripts/new_weekly.py publish

# 4. 提交 docs/weekly/*.md + site/weekly.html + site/weekly/
```

模板见 [`TEMPLATE.md`](TEMPLATE.md)。写作要点：**非技术语言**、用"痛点 → 解决后状态"的句式、聚焦业务价值。

## 自动生成（2026-07-12 起）

CCR Routine「**MBA 周报自动生成**」（`trig_01MDmKcmf1mrvkoo1kKW4JzK`）每周日
20:00（北京时间）自动开新会话：收集本周 main 合并记录 → 按 TEMPLATE 撰写（非技术语言、
诚实记账、数字从仓库实际核实）→ `publish` 重生成全部页面 → 开 PR **供人工审阅后合并**；
本周无合并提交则静默跳过。自动生成的是草稿，把关仍在人。
