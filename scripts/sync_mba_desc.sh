#!/usr/bin/env bash
# 把 metric-brand-auditor 在 BotLearn skillhunt 上的 description / sourceUrl
# 重新对齐到本仓库的 source-of-truth。
#
# 为什么需要它:`botlearn skill-republish` 每次 bump 版本会用 SKILL.md frontmatter
# 重新覆盖 BotLearn 上的 description,导致网站/GitHub 链接每次都掉。这个脚本是
# republish 后的"二次修正",把 marketplace 文案钉死。
#
# 用法:
#   bash scripts/sync_mba_desc.sh
#
# 何时跑:
#   - 每次 `botlearn skill-republish metric-brand-auditor ...` 之后
#   - 修了下面的 DESC / SOURCE_URL 之后

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BOTLEARN_BIN="$REPO_ROOT/skills/botlearn/bin/botlearn.sh"
SKILL_NAME="metric-brand-auditor"

if [ ! -x "$BOTLEARN_BIN" ]; then
  echo "[sync-mba-desc] botlearn CLI not found at $BOTLEARN_BIN"
  echo "[sync-mba-desc] hint: skills/botlearn/ is gitignored — install via setup first"
  exit 1
fi

SOURCE_URL='https://mbabrand.com'

# Marketplace description — source of truth. 改这里就够。
DESC='【中文】把任意品牌交给一组可配置的"评委"做一次可复盘的品牌影响力审计: 并行调研创始叙事、产品定位、渠道、社区、视觉、竞品、舆情,再由默认 5 人 panel(傅盛 / Steve Jobs / 李可佳 / 吴俊东 / 张一鸣)或行业 panel 独立打分。支持 --panel / --industry / --panel-add / --panel-drop,输出 Markdown + HTML 报告,含雷达图、异议热力图、影响力构造图、90 天行动建议。适合创始人、品牌/增长团队、投资人、竞品研究、AI 产品发布前复盘。

[EN] Turn any brand into a replayable influence audit: parallel research across founder narrative, positioning, distribution, community, identity, competitors, and sentiment, followed by a configurable judge panel. Use the default 5-judge panel or switch via --panel / --industry / --panel-add / --panel-drop. Outputs versioned Markdown + HTML reports with radar charts, dissent heatmaps, influence maps, and 90-day brand moves.

官网 / Website: https://mbabrand.com/
样例报告 / Sample: https://mbabrand.com/reports/lenovo/
GitHub: https://github.com/zhanglunet/mba'

echo "[sync-mba-desc] syncing $SKILL_NAME ..."
LOG="$(mktemp -t sync-mba-desc.XXXXXX)"
trap "rm -f $LOG" EXIT

# botlearn CLI returns exit=1 even on API success — don't trust exit code,
# parse JSON success field instead.
bash "$BOTLEARN_BIN" skill-update "$SKILL_NAME" \
  --source-url="$SOURCE_URL" \
  --desc="$DESC" >"$LOG" 2>&1 || true

# 提取并打印线上当前状态
python3 - "$LOG" <<'PY'
import json, sys
raw = open(sys.argv[1]).read()
start = raw.find('{')
if start < 0:
    print('[sync-mba-desc] no JSON in response:')
    print(raw[:500])
    sys.exit(1)
obj, _ = json.JSONDecoder().raw_decode(raw[start:])
if not obj.get('success'):
    print('[sync-mba-desc] API returned success=false')
    print(json.dumps(obj.get('errors'), ensure_ascii=False))
    sys.exit(1)
s = obj['data']['skill']
print(f"[sync-mba-desc] OK · version={s['version']} · sourceUrl={s['sourceUrl']}")
print('[sync-mba-desc] live description:')
print('---')
print(s['description'])
print('---')
PY
