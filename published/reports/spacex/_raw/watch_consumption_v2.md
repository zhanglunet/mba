# SpaceX v2 watch 事件消费清单（EVOLUTION · 2026-07-12）

> 事后补档（2026-07-12），逐条对照 `watch/spacex/events.yaml`（`consumed_by: v2`）
> 与 `report.md`；不含事件流之外的新增事实。v2 无新增外部调研——delta 证据即下列
> 3 条事件（全部 CNBC，日期以 URL 内嵌自证）。

## 消费的事件（3 条）

| # | 事件 id | severity | dim | lens_map | 一句话 |
|---|---|---|---|---|---|
| 1 | `2026-06-11-spacex-001` | P1 | W5 | signal, leverage | IPO 定价 $135/股、约 5.556 亿股，募资约 750 亿美元——史上最大 IPO（约为沙特阿美 2019 纪录的三倍），纳斯达克挂牌前夜 |
| 2 | `2026-06-12-spacex-002` | P1 | W5 | signal, identity | 纳斯达克首日收于约 $161（+19%），市值约 2.1 万亿美元（NASDAQ:SPCX） |
| 3 | `2026-06-15-spacex-003` | P2 | W5 | signal | 上市后首个完整交易日再涨约 20%，后市延续 |

原文 URL（与 `report.md` Sources v2 增量一致）：

1. `2026-06-11-spacex-001` — "SpaceX raising $75 billion in record-setting IPO as Nasdaq debut awaits"
   <https://www.cnbc.com/2026/06/11/spacex-raises-75-billion-in-record-setting-ipo-ahead-of-nasdaq-debut.html>
2. `2026-06-12-spacex-002` — "SpaceX IPO takeaways: SPCX closes at $161, jumping 19% after record debut"
   <https://www.cnbc.com/2026/06/12/spacex-ipo-spcx-live-updates.html>
3. `2026-06-15-spacex-003` — "SpaceX stock jumps 20% in first full day of trading after record debut"
   <https://www.cnbc.com/2026/06/15/spacex-stock-record-ipo-debut.html>

## 驱动的镜头变化（对照 `report.md`）

| Lens | v1 → v2 | 驱动事件 | 结果 |
|---|---|---|---|
| Signal | 8.6 → **9.2**（↑0.6，主驱动） | `001` + `002` 主驱动，`003` 后市延续 | 格雷厄姆 8→9、安德森 9→10、霍夫曼 8→9；纳瓦尔/蒂尔△ 持 9（「定价不是现金流」/「共识到场不加分」）——v1「估值信号未被公开市场验证」的保留失效 |
| Identity | 6.8 → **7.0**（↑0.2，分歧加深） | `002`（lens_map 含 identity） | 格雷厄姆 6→7（治理稀释票）；霍夫曼持 6（计价器放大票）；蒂尔△持 8（市场为「创始人抵押」定价）；纳瓦尔/安德森持 7——仍是全卷唯一低于 8 的维度 |
| Leverage | 9.0（↔，重审后一致维持） | `001`（lens_map 含 leverage）触发重审 | 五位评委一致拒绝为募资本身加分（安德森 2007 语系：募资是保险，不是成就）；杠杆仍是可复用制造 + Starlink 现金飞轮 |
| Origin / Category | 未重审（↔） | 无事件触及 | 按 EVOLUTION 规则保留 v1 分数 |

**总分**：215 → **219 / 250**（8.60 → **8.76**，↑0.16）。
逐评委重打分见 `../reviews/v2_rescores.md`；逐评委 v1+v2 整合留痕见
`../reviews/{paulg,naval,pmarca,pthiel,rhoffman}.md`。
