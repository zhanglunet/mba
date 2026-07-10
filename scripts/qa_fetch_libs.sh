#!/usr/bin/env bash
# qa_fetch_libs.sh — 为 qa_report_render.mjs --offline-libs 准备确定性的库目录。
#
# 报告用 CDN 加载 Chart.js 4.4.4 + Mermaid 11(见 report.html)。渲染 QA 若在
# render 时依赖 jsdelivr 在线 = flake;此脚本把两个库 npm 装到本地,拼成
# qa_report_render 期望的目录布局,让 CI(和本地无代理浏览器)确定性离线渲染。
#
# 布局(qa_report_render 的 --offline-libs 约定):
#   <dir>/chart.umd.min.js      (chart.js@4.4.4 的 UMD bundle)
#   <dir>/mermaid/<...>         (mermaid@11 的整个 dist,含 chunks/)
#
# 用法:  bash scripts/qa_fetch_libs.sh <target-dir>
set -euo pipefail

DIR="${1:?usage: qa_fetch_libs.sh <target-dir>}"
CHART_VER="4.4.4"
MERMAID_VER="11"

mkdir -p "$DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "[qa-libs] npm i chart.js@${CHART_VER} mermaid@${MERMAID_VER} → $TMP"
npm i --prefix "$TMP" --no-audit --no-fund --silent "chart.js@${CHART_VER}" "mermaid@${MERMAID_VER}"

# Chart.js:npm dist 是 chart.umd.js(与 CDN 的 chart.umd.min.js 功能等价);
# 拷成 qa_report_render 期望的 chart.umd.min.js 名。
cp "$TMP/node_modules/chart.js/dist/chart.umd.js" "$DIR/chart.umd.min.js"

# Mermaid:整个 dist(mermaid.esm.min.mjs + chunks/)拷进 <dir>/mermaid。
rm -rf "$DIR/mermaid"
cp -r "$TMP/node_modules/mermaid/dist" "$DIR/mermaid"

echo "[qa-libs] ready → $DIR (chart $(wc -c <"$DIR/chart.umd.min.js")b, mermaid dist $(ls "$DIR/mermaid" | wc -l) entries)"
