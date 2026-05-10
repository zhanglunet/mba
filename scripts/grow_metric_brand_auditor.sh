#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${WORKSPACE:-/Users/john/mba}"
BOTLEARN="${BOTLEARN:-$WORKSPACE/skills/botlearn/bin/botlearn.sh}"
SKILL_NAME="${SKILL_NAME:-metric-brand-auditor}"
SKILL_URL="${SKILL_URL:-https://www.botlearn.ai/skillhunt/v2/s/metric-brand-auditor}"
DEMO_URL="${DEMO_URL:-https://mbabrand.com/reports/lenovo/}"
SITE_URL="${SITE_URL:-https://mbabrand.com}"
POST_CHANNEL="${POST_CHANNEL:-skill-bazaar-zh}"
OUT_DIR="${OUT_DIR:-/private/tmp/mba-growth}"

usage() {
  cat <<'EOF'
Usage:
  scripts/grow_metric_brand_auditor.sh metrics
  scripts/grow_metric_brand_auditor.sh wish
  scripts/grow_metric_brand_auditor.sh update-metadata
  scripts/grow_metric_brand_auditor.sh draft-post
  scripts/grow_metric_brand_auditor.sh post-update --execute
  scripts/grow_metric_brand_auditor.sh comment-feedback <post_id> --execute
  scripts/grow_metric_brand_auditor.sh run

What this script does:
  - Improves real conversion: metadata, assessment wish, useful community copy.
  - Never loops install/uninstall or fabricates installs.
  - Defaults to dry-run for community writes unless --execute is passed.
EOF
}

require_botlearn() {
  if [ ! -x "$BOTLEARN" ]; then
    echo "BotLearn CLI not found or not executable: $BOTLEARN" >&2
    exit 1
  fi
}

skill_json() {
  local out
  if ! out="$(bash "$BOTLEARN" skill-info "$SKILL_NAME" 2>&1)"; then
    printf '%s\n' "$out" >&2
    echo "BotLearn request failed. Check network/auth, then retry." >&2
    exit 1
  fi
  printf '%s\n' "$out"
}

metric_summary() {
  skill_json | node -e '
let d = "";
process.stdin.on("data", c => d += c);
process.stdin.on("end", () => {
  let r;
  try {
    r = JSON.parse(d);
  } catch (err) {
    console.error("Could not parse BotLearn JSON response.");
    process.exit(1);
  }
  if (!r.success) {
    console.error(r.error || "BotLearn returned success=false.");
    process.exit(1);
  }
  const s = r.data || {};
  const rows = [
    ["name", s.name],
    ["version", s.version],
    ["installs", s.installCount],
    ["activeInstalls", s.activeInstalls],
    ["executionCount", s.executionCount],
    ["completionCount", s.completionCount],
    ["reviewCount", s.reviewCount],
    ["ratingAvg", s.ratingAvg],
    ["assessmentWishCount", s.assessmentWishCount],
    ["archiveFiles", Array.isArray(s.fileIndex) ? s.fileIndex.length : ""],
    ["archiveUrl", s.latestArchiveUrl],
  ];
  for (const [k, v] of rows) console.log(`${k}: ${v ?? ""}`);
});
'
}

update_metadata() {
  # NOTE: keep this body in sync with metric-brand-auditor/SKILL.md frontmatter
  # description / category. If they drift, this function will silently revert the
  # marketplace listing the next time it runs. v0.2.15 is the current cutoff.
  local desc
  desc="【中文】零依赖上手:装完直接 \`/mba <brand> --quick --no-judges\` 跑一份单视角品牌速读 —— 只用 WebSearch + WebFetch,不需要 Mac host、不需要 Wuying 云浏览器、不需要预装 5 个 perspective skill。先验证管线再加重。

满意了再升级:去掉 \`--no-judges\` 召回 5 位评委(傅盛 / Steve Jobs / 李可佳 / 吴俊东 / 张一鸣)独立打分;去掉 \`--quick\` 加上 Wuying leg 抓 X / 小红书 / Bilibili / 中文媒体的真实信号。完整管线输出版本化 Markdown + HTML 报告,含雷达图、异议热力图、影响力构造图、90 天行动建议。适合创始人、品牌/增长团队、投资人、竞品研究、AI 产品发布前复盘。

网站:$SITE_URL/
样例报告:$DEMO_URL
GitHub:https://github.com/zhanglunet/mba"

  bash "$BOTLEARN" skill-update "$SKILL_NAME" \
    --display-name="乔布斯教你做品牌" \
    --category=ai-agents \
    --tags=brand-audit,competitive-intelligence,founder-story,marketing-strategy,multi-agent \
    --source-url="$SITE_URL" \
    --desc="$desc"
}

wish_assessment() {
  bash "$BOTLEARN" skill-wish "$SKILL_NAME"
}

draft_post() {
  mkdir -p "$OUT_DIR"
  local body="$OUT_DIR/metric-brand-auditor-update.md"
  cat > "$body" <<EOF
## metric-brand-auditor v0.2.15 更新

我把 **乔布斯教你做品牌 / metric-brand-auditor** 做了一轮安装转化和首跑成功率的优化。

这次主要修了三个被低分评论反复点名的漏点:

- 装完跑不动 → SKILL.md 里所有 \`~/mba/\` 和 \`ssh <MAC_USER>@<MAC_HOST>\` 硬编码全部
  改成 \`\${SKILL_DIR}\` / \`\${REPORTS_DIR}\` / \`\${PERSPECTIVES_PATH}\` 等可解析符号,
  非 Mac 环境也能直接跑
- description 第一段改成「零依赖上手 \`/mba <brand> --quick --no-judges\`」,把最便宜的
  试跑姿势放在门面,不用先备 Wuying 云浏览器
- category 从 \`research\` 迁到 \`ai-agents\`,从 470 个 skill 的噪音桶进 3 个 skill
  的精准 filter
- 公开报告 (mbabrand.com) footer 加 BotLearn 安装反向链接
- 跑完且通过质量门时,prompt host agent 在 BotLearn 留 review

适合场景:

- 创始人想知道品牌影响力靠什么建立
- 增长/品牌团队要找叙事、渠道、社区、视觉和竞品里的短板
- 投资或竞品研究需要一份可复盘的审计报告
- AI 产品发布前做一次品牌 sanity check

详情页: $SKILL_URL
样例报告: $DEMO_URL
EOF
  echo "$body"
}

post_update() {
  local execute="${1:-}"
  local body
  body="$(draft_post)"
  echo "Post draft: $body"
  if [ "$execute" != "--execute" ]; then
    echo "Dry run. Re-run with: $0 post-update --execute"
    return 0
  fi

  local skill_id
  skill_id="$(skill_json | node -e 'let d="";process.stdin.on("data",c=>d+=c);process.stdin.on("end",()=>process.stdout.write(JSON.parse(d).data.id));')"
  bash "$BOTLEARN" post "$POST_CHANNEL" \
    "metric-brand-auditor v0.2.15: 修硬编码 / 加 review nudge / 改进分类" \
    "$(cat "$body")" \
    --skill "$skill_id" \
    --sentiment positive \
    --depth usage
}

comment_feedback() {
  local post_id="${1:-}"
  local execute="${2:-}"
  if [ -z "$post_id" ]; then
    echo "Missing post_id" >&2
    usage
    exit 1
  fi

  mkdir -p "$OUT_DIR"
  local body="$OUT_DIR/comment-$post_id.md"
  cat > "$body" <<'EOF'
谢谢这篇反馈,我已经按这里指出的安装阻力发了 v0.2.11 -> v0.2.15。

已处理:
- v0.2.13 加了 Prerequisites & Graceful Degradation 章节,首次运行先 self-check
- v0.2.14 把 ~/mba/ 和 ssh <MAC_USER>@<MAC_HOST> 硬编码全改成 ${SKILL_DIR} 等符号,
  非 Mac 环境也能直接跑(MarsLocal / Nathalie / Lovelace 三条评论指向的根因)
- v0.2.14 description 第一段改成 `--quick --no-judges` 零依赖入口
- v0.2.15 category 从 research 迁到 ai-agents,跳出 470 个 skill 的 general 桶
- v0.2.15 跑完通过质量门后引导 host agent 留 review

还没完全解决的是 5-judge 依赖的自包含问题。下一版考虑补 bootstrap 或 fallback judge 模板。
EOF
  echo "Comment draft: $body"
  if [ "$execute" != "--execute" ]; then
    echo "Dry run. Re-run with: $0 comment-feedback $post_id --execute"
    return 0
  fi
  bash "$BOTLEARN" comment "$post_id" "$(cat "$body")"
}

run_campaign() {
  echo "== Before =="
  metric_summary
  echo
  echo "== Update metadata =="
  update_metadata || true
  echo
  echo "== Assessment wish =="
  wish_assessment || true
  echo
  echo "== Draft post =="
  draft_post
  echo
  echo "== After =="
  metric_summary
}

main() {
  require_botlearn
  cd "$WORKSPACE"
  local cmd="${1:-}"
  case "$cmd" in
    metrics) metric_summary ;;
    wish) wish_assessment ;;
    update-metadata) update_metadata ;;
    draft-post) draft_post ;;
    post-update) shift; post_update "${1:-}" ;;
    comment-feedback) shift; comment_feedback "${1:-}" "${2:-}" ;;
    run) run_campaign ;;
    -h|--help|help|"") usage ;;
    *) echo "Unknown command: $cmd" >&2; usage; exit 1 ;;
  esac
}

main "$@"
