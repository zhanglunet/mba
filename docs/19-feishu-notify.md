# 19 · 飞书群推送(Feishu Notify)

> Status: 实现落地 · Last verified 2026-07-13
> 品牌监控 / 舆情信号有变化时,自动推送到飞书群。

## 一句话

合并 PR 到 `main` 时,若改动了**舆情事件**(`watch/**`)或**评分**(`site/reports-meta.yaml`),
GitHub Action 会 diff 出变化、拼成一张飞书卡片,POST 到飞书自定义机器人 webhook,进群。

- 触发点:`push` 到 `main`(即合并 PR),仅当 `watch/**` 或 `site/reports-meta.yaml` 改动
- 脚本:[`scripts/notify_feishu.py`](../scripts/notify_feishu.py)
- 工作流:[`.github/workflows/notify-feishu.yml`](../.github/workflows/notify-feishu.yml)
- 反捏造:卡片内容**全部取自仓库文件**(事件标题/引用/URL、真实评分),无任何 LLM 生成

## 推送门槛(避免刷屏)

与首页卡片「建议重审」**同口径**,只推三类:

| 类别 | 条件 | 数据源 |
|---|---|---|
| 📮 新增舆情信号 | 本次新增、`severity` 为 **P0/P1** 的事件(P2/P3 不单独刷群,docs/15 §5.2) | `watch/<slug>/events.yaml` |
| 🔁 建议重审 | 品牌**新命中**触发规则:base 未命中、head 命中(R1 P0≥1 / R2 P1≥3 / R3 加权 4·2·0.5 ≥6,只数未消费事件;单一真源 [`evaluate_triggers.py`](../scripts/watch-tools/evaluate_triggers.py)) | 同上 |
| 📈 评分变动 | `score_normalized` 变化(含新品牌首审) | `site/reports-meta.yaml` |

卡片头部颜色:有 P0 事件或建议重审 → 红,否则橙。一次 push 聚合成**一张**卡片,不逐条刷屏。

## 配置(3 步)

1. **建飞书机器人**:目标群 → 设置 → 群机器人 → 添加「自定义机器人」→ 复制 webhook URL。
   (可选)勾选「签名校验」,复制密钥 —— 安全性更高,推荐。
2. **配 GitHub secret**:仓库 Settings → Secrets and variables → Actions → New repository secret:
   - `FEISHU_WEBHOOK` = webhook URL(**必需**)
   - `FEISHU_SIGN_SECRET` = 签名密钥(**可选**,勾了签名校验才配)
3. 完成。下次合并涉及 `watch/**` 或 `reports-meta.yaml` 的 PR 即自动推送。
   未配 `FEISHU_WEBHOOK` 时工作流直接跳过、不报错(非阻断)。

## 本地预览 / 调试

不 POST,只打印将要发送的卡片 JSON(拿任意两个提交做 diff):

```bash
python3 scripts/notify_feishu.py --base <old-sha> --head <new-sha> --dry-run
```

真发一条(需本机 export `FEISHU_WEBHOOK`,可选 `FEISHU_SIGN_SECRET`):

```bash
export FEISHU_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxxx'
python3 scripts/notify_feishu.py --base HEAD^ --head HEAD
```

## 签名算法(与飞书一致)

配了 `FEISHU_SIGN_SECRET` 时,POST body 顶层加 `timestamp` + `sign`:

```
string_to_sign = f"{timestamp}\n{secret}"
sign = base64( HMAC-SHA256(key=string_to_sign, msg="") )
```

## 卡片长这样(示例,真实数据)

```
MBA 品牌监控更新 · 2026-07-13 · 3 项
🔁 建议重审
  • 爱马仕 — 未消费 P0×0 / P1×3(R2:P1≥3、R3:加权7.5≥6) [信号 →]
📮 新增舆情信号(P0/P1)
  • 🟠 P1 利好 ▲ · 爱马仕 · W5 资本市场 · 2025-02-14
    爱马仕 2024 全年营收 +15% 至 €15.2B…  [原文链接]
  • 🟠 P1 利好 ▲ · 联想集团 · W5 资本市场 · 2026-05-25
    联想 2025/26 财年史上最佳…  [原文链接]
```

## 边界 / 已知限制

- **只在 CI(合并到 main)触发**。直接改文件不 commit、或改动只在 PR 分支上、未合并,不推送。
- 需要完整 git 历史(`fetch-depth: 0`)才能 `git show <before>:<path>` 取旧版本;工作流已配。
- `github.event.before` 在首次 push / force-push 可能是全 0,脚本会退回 `head^`;再无有效 base 则跳过。
- 事件必须有可解析的 `date`(ISO)才计入触发评估(与 `evaluate_triggers` 一致)。
- 若想改成「MCP live server 实时下发」而非 CI,另有一条路:扩展 `packages/mcp-server/src/notify/`
  加飞书 channel(由 `record_watch_event` / `trigger_evolution` 触发)。本期按 CI 方案落地。
