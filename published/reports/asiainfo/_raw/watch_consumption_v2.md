# v2 消费的 watch 事件清单（EVOLUTION · 2026-07-12）

本文件为 2026-07-12 事后整理的消费留痕：硬字段（id / severity / 一句话 / URL）逐字照录自
`watch/asiainfo/events.yaml`（`consumed_by: v2` 的 7 条）；「驱动的镜头变化」对照 `../report.md`
§What changed since v1 与 `../reviews/v2_rescores.md`，不引入两者之外的新判断。

## 事件清单（按 severity 排列）

| 事件 id | Severity | Direction | 一句话（events.yaml title 照录） | URL |
|---------|----------|-----------|----------------------------------|-----|
| `2025-04-07-asiainfo-006` | P0 | neg | 亚信安全被中国移动子公司禁入采购三年(起因约 60 万元项目) | https://finance.sina.com.cn/tech/roll/2025-04-07/doc-inesincs1400808.shtml |
| `2026-03-24-asiainfo-010` | P1 | mixed | 2025 年报:营收 63.02 亿(−5.2%),核心系统 −8.9%、智能数据运营 +34.1% | https://finance.eastmoney.com/a/202603243681838932.html |
| `2025-07-01-asiainfo-007` | P2 | pos | 跻身中国「大模型应用交付供应商」六强 | https://www.asiainfo.com/zh_cn/content_4884.html |
| `2025-08-05-asiainfo-008` | P2 | pos | 盈利预喜:预计全年利润优于上年,AI 大模型交付爆发式增长 | https://www.stcn.com/article/detail/2932591.html |
| `2025-08-22-asiainfo-009` | P2 | neutral | 亚信安全 2025 年半年度报告披露 | https://stockmc.xueqiu.com/202508/688225_20250822_RBL3.pdf |
| `2026-04-11-asiainfo-011` | P2 | neutral | 亚信安全 2025 年年度报告披露(已并表亚信科技) | http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESH_STOCK/2026/2026-4/2026-04-11/12080670.PDF |
| `2024-08-22-asiainfo-004` | P3 | pos | 财经媒体正面解读:投资周期波谷下的韧性叙事 | https://finance.sina.cn/stock/relnews/hk/2024-08-22/detail-incknxxa1698695.d.html |

注：`006` 的处罚公示原文待回溯，事件以财经媒体报道为据（report.md §What-changed 与
events.yaml note 均已如实标注）。

## 各事件驱动的镜头变化（对照 report.md §What changed since v1）

- **`2025-04-07-asiainfo-006`（P0）→ Leverage ↓ 主驱动**：Leverage 均值 6.0→5.2，除黄仁勋外
  五位评委各降 1（周/张/任/马/纳）。同时构成 Signal 的恶化面——周鸿祎 Signal 6→5 的直接理由
  （「政企客户买安全买的是责任，连采购资格都守不住」）。该事件发生于 2025-04、早于 v1 审计日，
  属 v1 调研窗漏掉的既有公开信号，由 watch 流回填，故触发同日重审。
- **`2026-03-24-asiainfo-010`（P1）→ Signal 锚点更新**：以 2025 年报（63.02 亿、−5.2% 收窄、
  智能数据运营 +34.1% 占 12.8%）替换 v1 的 2024 年报锚（66.46 亿、−15.8%）。黄仁勋 Signal
  6→7 的主要证据；lens_map 亦含 leverage——黄仁勋维持 Leverage 6 的「二曲线」证据之一。
- **`2025-07-01-asiainfo-007`（P2）→ Signal 改善面**：「AI 新赌注」兑现的证据（大模型应用交付
  六强）；同时是黄仁勋维持 Leverage 6 的理由（「AI 交付六强与 +34.1% 的二曲线，正在给这条
  旧杠杆接上新杠杆」）。
- **`2025-08-05-asiainfo-008`（P2）→ Signal 改善面**：盈利预喜（预计全年利润优于上年，AI 大
  模型交付爆发式增长）。
- **`2025-08-22-asiainfo-009`（P2）→ 语境事件**：亚信安全侧法定披露，列入 Signal 证据清单，
  不单独驱动分数变化。
- **`2026-04-11-asiainfo-011`（P2）→ 语境事件**：2024-11 完成对亚信科技的控制并表（「一个
  亚信」资本层面落地）。触及 identity，但仅为 v1 已计入的重组叙事的执行进度，双品牌对外叙事
  未变，品牌层无新证据——**Identity 不重打**。
- **`2024-08-22-asiainfo-004`（P3）→ 韧性叙事语境**：背景语境，不上卡片，不驱动分数变化。

**净效果**：Leverage 6.0→5.2（主驱动 `006`）；Signal 均值 5.8 持平但方向性分裂（黄仁勋 6→7 ↑
vs 周鸿祎 6→5 ↓）；Origin / Category / Identity 未重审（↔）。总分 178→173（5.93→5.77）。
