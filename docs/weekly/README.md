# 项目周报 · Weekly Reports

面向非技术读者的每周开发进展报告：解决了哪些问题、交付了哪些功能、沉淀了哪些方法论。

| 周期 | 报告 | 里程碑 |
|---|---|---|
| 截至 2026-07-12 | [2026-07-12.md](2026-07-12.md) | v0.4.1→v0.4.3 三连发 · 评委深化收官(42/43) · Brand Watch 舆情监控全线上线 |
| 截至 2026-07-05 | [2026-07-05.md](2026-07-05.md) | v0.4.0 发布 · 品牌演化追踪闭环 · 10 份行业报告 |

> 网页版同步发布于 [mbabrand.com/weekly.html](https://mbabrand.com/weekly.html)。

## 如何新增一份周报

Markdown 是唯一事实源，网页由脚本从它生成，两边不会跑偏。

```bash
# 1. 生成骨架（日期默认今天），并自动在上表追加一行
python3 scripts/new_weekly.py new 2026-07-12 --milestone "本周里程碑"

# 2. 填写 docs/weekly/2026-07-12.md（照着 TEMPLATE.md 的结构写）

# 3. 生成/更新网页 site/weekly.html
python3 scripts/new_weekly.py publish 2026-07-12

# 4. 提交 docs/weekly/*.md + site/weekly.html
```

模板见 [`TEMPLATE.md`](TEMPLATE.md)。写作要点：**非技术语言**、用"痛点 → 解决后状态"的句式、聚焦业务价值。
