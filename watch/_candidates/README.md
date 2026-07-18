# watch/_candidates/ — 每日自动发现的舆情候选(暂存区,待人工核验)

`Watch Discover` workflow(`.github/workflows/watch-discover.yml`)每日跑
`fetch_candidate.py discover`,把 Google News RSS 发现、且尚未入库的候选事件写到
本目录的 `<date>.md`,并开一个 PR 待审。

**这里的文件是暂存草稿,不是正式事件流**:

- **判断字段(dim / severity / direction / lens_map)是 TODO**,由人工/评委核验后才定
  —— 脚本不做自动打分(docs/15 §边界:direction 是显式标注,不假装客观)。
- **反捏造**:标题 / 日期 / URL 均取自源 feed,脚本从不编造 quote。
- 本目录不含 `events.yaml`,`validate_watch.py` 只扫 `watch/*/events.yaml`,故**不校验**这里。

**核验流程**:把合规候选 → 补齐判断字段 → 粘进 `watch/<slug>/events.yaml` →
删掉本候选文件 → 跑 `python3 scripts/watch-tools/validate_watch.py`。全是噪音则直接关 PR。

手动发现(任何有网环境):

```bash
python3 scripts/watch-tools/fetch_candidate.py discover --brand kimichat --days 7 --limit 12
```
