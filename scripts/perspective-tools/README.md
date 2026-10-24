# Perspective Tools

Shared helper scripts for building and checking `*-perspective` skills.

These used to be duplicated under multiple perspective directories. Keep the
single maintained copy here and run commands from the repo root, for example:

```bash
python3 scripts/perspective-tools/merge_research.py jobs-perspective
python3 scripts/perspective-tools/quality_check.py jobs-perspective/SKILL.md
python3 scripts/perspective-tools/quality_gate.py --judge jobs   # PRD-151 评委质量门（13 条一页视图）
python3 scripts/perspective-tools/srt_to_transcript.py input.srt
scripts/perspective-tools/download_subtitles.sh <YouTube_URL> out/subtitles
```
- T4（trend #758）：B-1..B-4 / C-1 / C-2 由「人工/待查」转机检（六路齐全非空 / quotes 锚定率 ≥90% / 可复制调用示例 / Boundary 截止标注 / description 触发短语 / tier 追踪表全量一致）；金正样例 satyanadella 13/13 全绿（含补 B-3 调用示例行）。
