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
DESC='【中文】把任意品牌交给一组可配置的"评委"做一次可复盘的品牌影响力审计: 并行调研创始叙事、产品定位、渠道、社区、视觉、竞品、舆情,再由可换的人物评委 panel 独立打分——默认 5 人(傅盛 / Steve Jobs / 李可佳 / 吴俊东 / 张一鸣),另有 9 套行业 panel(汽车 / 安全 / AI 应用 / 教育 / 中英 VC / 消费 / 出海 / 奢侈品),共 10 套内置 panel、43 位评委,全部可运行。支持 --panel / --industry / --panel-add / --panel-drop,输出 Markdown + HTML 报告,含雷达图、异议热力图、影响力构造图、90 天行动建议。适合创始人、品牌/增长团队、投资人、竞品研究、AI 产品发布前复盘。

[EN] Turn any brand into a replayable influence audit: parallel research across founder narrative, positioning, distribution, community, identity, competitors, and sentiment, followed by a swappable judge panel — the default 5 judges or one of 9 industry panels (auto / security / AI-apps / education / VC EN&CN / consumer / cross-border / luxury), 10 built-in panels and 43 judges in all, via --panel / --industry / --panel-add / --panel-drop. Outputs versioned Markdown + HTML reports with radar charts, dissent heatmaps, influence maps, and 90-day brand moves.

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
    print('[sync-mba-desc] no JSON in response (first 500 chars):', file=sys.stderr)
    print(raw[:500], file=sys.stderr)
    sys.exit(1)

try:
    obj, _ = json.JSONDecoder().raw_decode(raw[start:])
except json.JSONDecodeError as e:
    print(f'[sync-mba-desc] JSON parse failed: {e}', file=sys.stderr)
    print('[sync-mba-desc] raw response (first 500 chars):', file=sys.stderr)
    print(raw[:500], file=sys.stderr)
    sys.exit(1)

if not obj.get('success'):
    print('[sync-mba-desc] API returned success=false', file=sys.stderr)
    print(json.dumps(obj.get('errors'), ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

# 防御性提取：botlearn API 结构若变了，告诉用户具体哪一层缺
try:
    s = obj['data']['skill']
    version = s['version']
    source_url = s['sourceUrl']
    description = s['description']
except (KeyError, TypeError) as e:
    print(f'[sync-mba-desc] unexpected API response shape (missing {e}); raw response keys: {list(obj.keys())}', file=sys.stderr)
    print(json.dumps(obj, ensure_ascii=False, indent=2)[:800], file=sys.stderr)
    sys.exit(1)

print(f"[sync-mba-desc] OK · version={version} · sourceUrl={source_url}")
print('[sync-mba-desc] live description:')
print('---')
print(description)
print('---')
PY
