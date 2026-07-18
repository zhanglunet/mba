# watch/_candidates/ — 每日自动发现的舆情候选(暂存区,前台 triage 核验)

`Watch Discover` workflow(`.github/workflows/watch-discover.yml`)每日跑
`fetch_candidate.py discover`,把 Google News RSS 发现、且尚未入库的候选事件写到本目录:

- `<date>.md` —— 人读版草稿(YAML 片段,判断字段留 TODO);
- `<date>.json` —— 结构化版(前台 triage 页数据源,`build_watch_triage.py` 消费)。

候选会**直推 main**(暂存草稿,非审计改分),生产站 `/watch/triage.html` 随即显示。

## 前台 triage(推荐)—— 不必读 PR diff,一键提 PR

打开 **[/watch/triage.html](https://mbabrand.com/watch/triage.html)**:每条候选一张卡片
(标题为中文,取自中文媒体),点 **✓采纳 / ✗丢弃**,可就地选 dim/severity/direction/lens;
选完点 **「✅ 提 PR」**:自动打开 GitHub 预填新文件(`watch/_adopt/<ts>.yaml`),提交即开 PR,
`watch-adopt.yml` 折入 `events.yaml`(重算 id、删暂存、validate),维护者复核 diff 后合并。
也可「复制 YAML」手动粘。`watch/_adopt/` 是折叠前的暂存,合并即清空。

**这里的文件是暂存草稿,不是正式事件流**:

- **判断字段(dim / severity / direction / lens_map)是人工判断**,由你在 triage 页打的勾决定
  —— 脚本不做自动打分(docs/15 §边界:direction 是显式标注,不假装客观)。
- **反捏造**:标题 / 日期 / URL 均取自源 feed,脚本从不编造 quote;triage 页也只呈现源 feed 原文。
- **前台不写库**:triage 页的选择只存在浏览器(localStorage),采纳项必须 commit 进
  `events.yaml` 才生效 —— git 仍是唯一真源,任何访客都改不了审计打分。
- 本目录不含 `events.yaml`,`validate_watch.py` 只扫 `watch/*/events.yaml`,故**不校验**这里。

## 手动发现(任何有网环境)

```bash
python3 scripts/watch-tools/fetch_candidate.py discover --brand kimichat --days 7 --limit 12
# 产出 <date>.md + <date>.json;本地看前台页:python3 scripts/build_watch_triage.py 后开 site/watch/triage.html
```
