# PRD-021/T1：mba 插件市场 marketplace.json（草稿 v1）

> T1 只出设计稿：下方为 `marketplace.json` 全文。T2 落地时原样写入
> `.claude-plugin/marketplace.json`，并新建 `source` 指向的 `./plugins/mba`
> 插件目录（该目录当前尚不存在，T2 新建）。

## 版本说明

- 插件版本 `0.6.1` 为插件独立版本号，与仓库 `package.json`（当前 `0.4.0`）不强制同步；
  插件按自身节奏发版时单独递增。
- `license` 填 `MIT`；T2 落地前确认仓库根目录已补 `LICENSE` 文件（当前缺失）。

## marketplace.json

```json
{"$schema":"https://anthropic.com/claude-code/marketplace.schema.json","description":"Metric Brand Auditor：多智能体品牌影响力审计 skill（/mba <brand>）","name":"mba-marketplace","owner":{"name":"zhanglunet","url":"https://github.com/zhanglunet/mba"},"plugins":[{"description":"多智能体并行调研 + 5 人评委 panel 独立打分，把品牌影响力拆成可打分、可比较、可复盘的版本化报告：雷达图 + 异议热力图 + 影响力构造图 + 90 天行动建议。`/mba <brand>` 一行触发，EVOLUTION 模式追踪品牌随时间演化。","homepage":"https://mbabrand.com","keywords":["brand-audit","multi-agent","competitive-intelligence","marketing-strategy"],"license":"MIT","name":"mba","source":"./plugins/mba","version":"0.6.1"}]}```
