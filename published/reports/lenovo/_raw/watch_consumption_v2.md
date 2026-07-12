# v2 消费的 watch 事件清单（EVOLUTION · 引擎升级全量重审 · 2026-07-12）

本文件为 v2 审计的消费留痕：硬字段（id / severity / direction / 一句话 / URL）逐字照录自
`watch/lenovo/events.yaml`（3 条全部消费，均已标 `consumed_by: v2`）；「驱动的镜头变化」
对照 `../report.md` §What changed 与 `../reviews/v2_rescores.md`，不引入两者之外的新判断。

## 事件清单（按 severity 排列）

| 事件 id | Severity | Direction | 一句话（events.yaml title 照录） | URL |
|---------|----------|-----------|----------------------------------|-----|
| `2026-05-22-lenovo-001` | P1 | pos | 2025/26 财年年报:营收首破 800 亿美元(831 亿,+20%),归母净利 19.12 亿美元(+38%),史上最佳财年 | https://www.stcn.com/article/detail/3921911.html |
| `2026-06-18-lenovo-002` | P2 | pos | 中标 2026 中央国家机关 6 月打印机批量集采,单包中标台数与金额居全标段首位 | https://www.doit.com.cn/itnews/819020793233477.html |
| `2026-07-12-lenovo-003` | P3 | neutral | 媒体预览 BW 2026 大会:AI 全家桶集中亮相,8 月发布重磅新品 | https://finance.sina.com.cn/tech/roll/2026-07-12/doc-inihpipy5944728.shtml |

三条事件原文均已于 2026-07-12 curl 复核（quote 为源文章标题逐字，quote_type: title）。

## 各事件驱动的镜头变化（对照 report.md §What changed）

- **`2026-05-22-lenovo-001`（P1，lens_map: signal/leverage）→ Signal 主驱动**：史上最佳
  财年（831 亿 +20%、归母净利 19.12 亿 +38%、AI 收入 +105% 占 33%）把 v1 的「财务面好」
  坐实。Signal 均值 5.0 → 6.2（v1 为 50 分制下的同尺度均值），5 评委中傅盛/张一鸣 7、
  李可佳/吴俊东 6、Jobs 独持 5（"财务滞后品味三年"的方法论折价）。同时构成 Leverage 的
  证据面（ISG 扭亏、SSG 连续 20 季双位数，经官方公告交叉核验）。
- **`2026-06-18-lenovo-002`（P2，lens_map: leverage/signal）→ Leverage**：央采 6 月打印机
  批量集采单包台数（2340 台）与金额（超 147.8 万元）双第一，叠加原文载明的 2 月台式机
  1434 台/73.8% 份额——政企渠道信任的硬信号。Leverage 均值 5.0 → 5.4。
- **`2026-07-12-lenovo-003`（P3，lens_map: category/identity）→ Category/Identity 语境**：
  BW 2026 天禧Claw（开箱即用智能体）+ Skills 技能广场 + 天禧AI 4.1 Token 调度 + 8 月新品
  预告。P3 弱信号不单独驱动分数，但与官方公告的 Qira/天禧双名、"maximize value per token"
  原文共同构成 v2 最大的解释权分歧素材（傅盛认方向 vs 李可佳不认成色；Category 3.0 /
  Identity 3.2 基本未动）。8 月新品发布为下一个观察点。

**净效果**：总分 119/250 = 4.76（v1 参考 22/50 = 4.40，归一化同尺度可比）。Signal 与
Leverage 上行由 watch 001/002 驱动；Category/Identity 维持低位由 003 + 官方公告的双名
证据确认。
