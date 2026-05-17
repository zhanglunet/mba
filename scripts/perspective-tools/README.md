# Perspective Tools

Shared helper scripts for building and checking `*-perspective` skills.

These used to be duplicated under multiple perspective directories. Keep the
single maintained copy here and run commands from the repo root, for example:

```bash
python3 scripts/perspective-tools/merge_research.py jobs-perspective
python3 scripts/perspective-tools/quality_check.py jobs-perspective/SKILL.md
python3 scripts/perspective-tools/srt_to_transcript.py input.srt
scripts/perspective-tools/download_subtitles.sh <YouTube_URL> out/subtitles
```
