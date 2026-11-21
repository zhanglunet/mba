# 32 · 上游标准版本跟踪机制（PRD-098/T4）

> trend issue：zhanglunet/mba#273；PRD：`adopted/PRD-098-mba-openui-alignment.md` §4。
> 定稿：2026-11-21。配套脚本：`scripts/check_standard_updates.py`；快照：`docs/standards-snapshot.json`。

## 1. 跟踪对象（上游标准源）

| 编号 | 来源 | 用途 | 抓取面 |
|---|---|---|---|
| S1 | thesysdev/openui（MIT）——仓库 README + releases | PRD-098 T1 拆解的生成式 UI 标准（组件/协议/渲染契约）本源 | GitHub API：`repos/thesysdev/openui` 的 `pushed_at` + README SHA + 最新 release tag |
| S2 | Claude Code 官方文档《Extend Claude with skills》（code.claude.com/docs/en/skills） | SKILL.md frontmatter 六字段可移植集口径（PRD-094/199 同源） | 页面 `Updated` 标注 + frontmatter 字段表关键行 |
| S3 | Cursor 官方文档《Plugins reference》（cursor.com/docs/reference/plugins） | `.cursor-plugin` 插件规范口径 | 页面提交清单关键行 |
| S4 | anthropics/claude-plugins-official README | marketplace.json 第三方淘汰等分发面变更（2026-11-21 已捕一次：转 directory/manage） | README SHA |

## 2. 检查频率与责任人（验收要求的约定）

| 项 | 约定 |
|---|---|
| **例行检查** | 每月 1 号（UTC 月初），由当月值班维护者执行 `python3 scripts/check_standard_updates.py --check` 并把结果贴进本文件的「检查记录」节 |
| **即时检查** | S1 有 release / 官方文档页大改（社区渠道看到）时随时加跑 |
| **责任人** | 例行=当月值班；即时=发现者。均记名（检查记录节按"日期 + 执行人 + 结果"登记） |
| **CI 辅助** | 无专用 workflow（省 private 分钟）；脚本本地可跑、`--check` 非零退出码可直接接任何调度器 |

## 3. 变更评估 → 排期流程（文档化）

标准变更确认后，按下列四步走（沿用 PRD-098 已有口径，不新发明流程）：

1. **登记**：在本文件「检查记录」节记一条（日期/来源/变更点原文链接）。
2. **影响评估**：把变更映射到 T1 拆解条目（组件/协议/渲染契约）与 PRD-094 checklist 条目——每条标"对齐/部分/缺失"三态与影响面（同 T2 差距报告口径）。
3. **排期**：按影响 × 成本排序（同 #272 口径：高影响低成本先行）；进 PRD-098 的后续批次或新开 PRD，逐项带 PRD-081 回归门禁（test_genui_e2e.py，当前 91/91 基线）。
4. **收口**：改造合入后把本文件「检查记录」对 应条目标"已消化"，并更新快照（`--update-snapshot`）。

## 4. 脚本用法

```bash
# 例行检查：与上次快照比对，变更则 exit 1 并打印变更面（无变更 exit 0）
python3 scripts/check_standard_updates.py --check

# 首次建快照 / 确认消化后更新基线
python3 scripts/check_standard_updates.py --update-snapshot
```

- 零第三方依赖（urllib/hashlib 标准库）；网络不可达时 exit 2（inconclusive，非阻断）。
- 快照字段：每来源的 `content_sha256`、`fetched_at`、`head`（S1 为 pushed_at+release tag，S2/S3/S4 为页面标记行）。

## 5. 检查记录

| 日期 | 执行人 | 来源 | 结果 |
|---|---|---|---|
| 2026-11-21 | 张路代理 | S1/S4 | **首次建快照**；S1 无 release、README 与 10-20 口径一致；S4 捕获 marketplace.json 第三方淘汰变更（已升 PRD-094 checklist v1.1 消化，见该文件 v1.1 注记） |
