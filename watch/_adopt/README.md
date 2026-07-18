# watch/_adopt/ — 采纳事件的暂存折叠区(合并即清空)

两条路径会在这里放 `*.yaml`(**扁平事件列表,每条带 `slug`**;JSON 亦是合法 YAML):

1. **前台 triage 页「✅ 提 PR」**(docs/16 §2.6):你在 `/watch/triage.html` 打勾采纳 →
   经 GitHub 预填新文件深链创建 `triage-<ts>.yaml`。
2. **LLM 预分类自动 PR**(docs/16 §2.7):`watch-discover` 跑 `classify_candidates.py`,
   把高置信 keep 项写成 `auto-<date>.yaml`,自动开「建议入库」PR。

两者都由 **`.github/workflows/watch-adopt.yml`**(PR 触发,`paths: watch/_adopt/**`)调
`scripts/watch-tools/fold_adopt.py` **折入** `watch/<slug>/events.yaml`(重算 id 尾号防撞、删暂存、
跑 `validate_watch`),并回推 PR 分支。**维护者只审最终 `events.yaml` diff 再合并** —— 合并是人工闸门。

反捏造:标题/日期/URL 逐字取自源 feed;`dim/severity/direction/lens` 是 model-judged 分类
(triage 页人工打勾 / LLM 预分类),**不改任何审计分数**;合并入库后才由评委在 EVOLUTION 消费。

本目录平时应为空(只有本 README)——暂存文件在 PR 合并/折叠后即被删除。
