# _raw/ — SpaceX 审计留痕说明（诚实缺口记录）

> 本 README 写于 **2026-07-12（事后补档）**。原则：**只如实记录缺口，不伪造从未
> 存在的中间产物**（反捏造纪律，见仓库 CLAUDE.md 坑 #3）。

## 1. v1（FRESH · 2026-07-12）：调研中间产物未落库

参照完整留痕形态（如 `published/reports/qianxin/_raw/` 的
`dimension_1..7_*.md` + `synthesis.md`），SpaceX v1 审计的逐维度调研笔记与合成稿
**当时未写入本目录**。这些中间产物已不存在，无法事后重建——事后"补写"等于伪造
留痕，故本目录不放任何冒充 v1 过程稿的文件。

**v1 证据链以报告快照的 Sources 段为准**：`versions/v1_2026-07-12.md` 的
`## Sources`（8 条公开来源：Wikipedia×2、Sacra、Morningstar×3、Forbes、ElectroIQ）。

## 2. v1 勘误历史（如实记入）

- v1 初版 Signal 段曾**误写「作为未上市公司」**——事实上 SpaceX 已于 2026-06-12
  以史上最大 IPO 登陆纳斯达克（NASDAQ: SPCX，募资约 750 亿美元）。
- 错误于**发布同日（2026-07-12）发现并勘误**：勘误框保留于
  `versions/v1_2026-07-12.md` 的 Signal 段（「**勘误 2026-07-12**：v1 初版此处误写
  『作为未上市公司』……」）及 Legal 段口径说明。
- 处理方式：IPO 信号**未回改 v1 评分**，而是录入 `watch/spacex/events.yaml`
  （3 条事件，全部 CNBC，URL 内嵌日期自证），由**同日 EVOLUTION v2** 按事件流
  规则消化——这也是 v1 与 v2 同日（2026-07-12）的原因。

另记一处 v1 快照的次要不一致（按快照不可改写原则保留原样，不回改）：
Origin 段行文写作「马斯克与蒂尔给 10」，与 Score Matrix（**安德森** 10 / 蒂尔 10；
马斯克非评委）不符，应为「安德森」笔误；矩阵各行均值与各评委总分均自洽，以矩阵为准。

## 3. v2（EVOLUTION · 2026-07-12）：delta 证据 = 3 条 CNBC watch 事件

v2 无新增外部调研，全部增量证据来自 `watch/spacex/events.yaml`（`consumed_by: v2`）：

| 事件 id | severity | 摘要 |
|---|---|---|
| `2026-06-11-spacex-001` | P1 | IPO 定价募资约 750 亿美元，史上最大 IPO |
| `2026-06-12-spacex-002` | P1 | 首日收约 $161（+19%），市值约 2.1 万亿美元（NASDAQ:SPCX） |
| `2026-06-15-spacex-003` | P2 | 上市后首个完整交易日再涨约 20% |

消费明细（含 URL 与驱动的镜头变化）见本目录 `watch_consumption_v2.md`；
定向重打分记录见 `../reviews/v2_rescores.md`。

## 4. 本目录现有文件

- `README.md`（本文件）— 缺口与勘误历史的诚实记录
- `watch_consumption_v2.md` — v2 消费的 watch 事件清单与镜头变化对照

逐评委留痕（2026-07-12 事后整合 v1+v2，AI in-character 模拟标注齐全）见
`../reviews/{paulg,naval,pmarca,pthiel,rhoffman}.md`。
