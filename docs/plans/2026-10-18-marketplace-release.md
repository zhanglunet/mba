# 官方市场发布材料清单（PRD-021/T4，trend #119）

> 日期：2026-10-18 · 对应版本：0.6.1（与 `plugins/mba/.claude-plugin/plugin.json` 对齐）
> 目标：材料一次备齐，打开提交入口即可逐项粘贴，"可直接提交"。

## 一、一句话描述

中文（与 `plugin.json` 的 description 逐字一致，T1 已定稿）：

> 多智能体并行调研 + 5 人评委 panel 独立打分，把品牌影响力拆成可打分、可比较、可复盘的版本化报告：雷达图 + 异议热力图 + 影响力构造图 + 90 天行动建议。`/mba <brand>` 一行触发，EVOLUTION 模式追踪品牌随时间演化。

English:

> Multi-agent parallel research + a 5-judge panel scoring independently — brand influence as versioned, scorable, comparable audit reports: radar charts, dissent heatmaps, influence-structure graphs, and 90-day action plans. Trigger with `/mba <brand>`; EVOLUTION mode tracks brands over time.

## 二、分类

官方 manifest schema（`$schema: https://anthropic.com/claude-code/marketplace.schema.json`）
**没有 category 字段**——分类只在提交表单里出现。提交时按表单实际选项选择，
建议方向：Developer Tools / Productivity（备选：Marketing & Research）。
**不要在 manifest 里自创 category 字段**，会破坏 schema 校验（T1 验收项）。

## 三、关键词

正式 4 个（与 `plugin.json` / `marketplace.json` 逐字一致，T1 已定稿）：

`brand-audit` · `multi-agent` · `competitive-intelligence` · `marketing-strategy`

候选补充（提交表单若允许更多关键词时再加，不动仓库文件）：
`brand-influence`、`sentiment-monitoring`、`competitive-analysis`、`china-market`

## 四、截图 / demo 素材

### 可复用（已有，零成本）

| 素材 | 位置 | 用途 |
|---|---|---|
| 网站首页（24 品牌 · 产业筛选 · 舆情信号） | `docs/screenshots/site-home.png`（README 已引用） | 主截图：产品长什么样 |
| 创始人晚餐亮点 | `docs/screenshots/founder-dinner.png`（README 已引用） | 特色功能截图 |
| 品牌报告样例 | `docs/screenshots/report-lenovo.png` | 输出物样例：版本化报告 |
| 原理图 | `docs/screenshots/how-it-works.png` | 工作原理说明 |
| 知识星图 live demo | https://mbabrand.com/starmap.html | 可交互 demo 链接 |
| 创始人晚餐 | https://mbabrand.com/collabs/ | 可交互 demo 链接 |

### 需新制（提交前补拍）

| 素材 | 说明 | 状态 |
|---|---|---|
| 插件安装录屏/GIF | `claude plugin install mba --marketplace zhanglunet/mba` 一条命令装上 | ☐ 待制 |
| `/mba <brand> --quick --no-judges` 运行效果截图 | T3 已在干净环境跑通，补一张终端截图即可 | ☐ 待制 |

## 五、README 徽章（本 PR 已加）

README 顶部新增一行（纯加法，不动现有内容）：

```markdown
[![plugin](https://img.shields.io/badge/plugin-0.6.1-blue)](plugins/mba) [![marketplace](https://img.shields.io/badge/marketplace-manifest-7c3aed)](.claude-plugin/marketplace.json) [![demo](https://img.shields.io/badge/demo-mbabrand.com-D97757)](https://mbabrand.com)
```

说明：
- plugin 版本徽章 `0.6.1`：与 `plugin.json` version 对齐；**发版 bump 版本时同步改徽章**。
- marketplace 徽章：指向 `.claude-plugin/marketplace.json`，证明官方格式已就位。
- demo 徽章：指向 https://mbabrand.com，可交互素材入口。
- 已有徽章（npm / license）不动。

## 六、提交 checklist

> 背景：Anthropic 官方目录（anthropics/claude-plugins-official）**不收外部 PR**
> （开了会被机器人自动关闭）；当前（2026-10）外部提交走开发者门户
> claude.ai/directory/manage（需付费 Claude 账号），分"单 MCP connector"和
> "plugin bundle（含 skill 的 GitHub 仓库）"两条路径。mba 走 **plugin bundle** 路径。
> PRD 非目标已明确：第一期先在自己仓库把格式做对，本清单备到"可提交"即止，
> 真正点提交按钮是后面的事。

- [x] 一句话描述（中英）定稿 —— 本文档 §一
- [x] 关键词 4 个定稿（与 manifest 一致） —— 本文档 §三
- [x] 分类口径确定（schema 无该字段，表单项再选） —— 本文档 §二
- [x] 复用截图/demo 清单 —— 本文档 §四（6 项现成）
- [x] README 徽章行 —— 本 PR 已加（§五）
- [x] `marketplace.json` 通过官方 schema 校验 —— T1（#239）已完成
- [x] 干净环境一条命令安装并跑通 `--quick --no-judges` —— T3（#247）已完成
- [ ] 补拍 2 项新素材（安装 GIF、运行截图） —— §四"需新制"
- [ ] 仓库根目录补 `LICENSE` 文件（MIT） —— **待办，不在本 PR 范围**：
  `marketplace.json` 声明 license 为 MIT，但根目录尚无 LICENSE 文件；
  提交审核前补上（内容与 `packages/mcp-server/LICENSE` 一致即可）。
- [ ] 登录 claude.ai/directory/manage，选 plugin bundle 路径，按表单粘贴 §一–§四材料，
  等待自动校验 → 安全扫描 → 人工审核。

## 七、自查结果

"可直接提交" = 材料侧齐备。当前状态：**齐备（材料侧）**。

- 描述/关键词/分类/徽章：✅ 本 PR 落定
- 复用素材：✅ 6 项现成可用
- 待提交前补：新截图 2 项（§四）、根目录 LICENSE（§六）——均为提交动作前置项，
  不影响本 PR 的"材料齐全"结论，已在 checklist 中明确标出。
