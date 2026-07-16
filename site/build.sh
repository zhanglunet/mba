#!/usr/bin/env bash
# MBA 站点构建脚本 —— Cloudflare Pages 调用
#
# 行为:
#   1. 不动 site/index.html(已经在仓库里)
#   2. 读 site/published-reports.txt
#   3. 把白名单里每个 brand 的 report.html 拷到 site/reports/<brand>/index.html
#   4. 拷过去的同时把 published/reports/<brand>/ 下的图片等静态资源一并搬过去(若存在)
#
# 输出目录 = site/  (Cloudflare Pages 的 build output directory)
#
# 本地用法:
#   bash site/build.sh
#
# Cloudflare Pages 设置:
#   Build command:           bash site/build.sh
#   Build output directory:  site
#   Root directory:          (空,默认仓库根)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE_DIR="$REPO_ROOT/site"
SRC_DIR="$REPO_ROOT/published/reports"
WHITELIST="$SITE_DIR/published-reports.txt"
OUT_DIR="$SITE_DIR/reports"

echo "[mba-build] repo:      $REPO_ROOT"
echo "[mba-build] whitelist: $WHITELIST"

# 清理上次产物(只清 site/reports/,不动 site/index.html)
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# Agent-facing JSON 端点 —— site/api/*.json 是给 agent 调用的结构化产物。
# 默认从 git 仓库里读已生成的 site/api/*(committed),build 时如果 python3 + pyyaml
# 在 build env 里可用,会重新生成一次以保证和源文件同步。
if command -v python3 >/dev/null 2>&1; then
  if python3 -c "import yaml" 2>/dev/null \
     || pip install --quiet pyyaml >/dev/null 2>&1 \
     || pip3 install --quiet pyyaml >/dev/null 2>&1; then
    echo "[mba-build] regenerating site/api/* from sources"
    python3 "$REPO_ROOT/scripts/build_agents_api.py" || \
      echo "[mba-build] WARN: build_agents_api.py failed — using committed site/api/*"
    echo "[mba-build] generating watch timeline pages"
    rm -rf "$SITE_DIR/watch"
    python3 "$REPO_ROOT/scripts/build_watch_pages.py" || \
      echo "[mba-build] WARN: build_watch_pages.py failed — watch pages skipped"
    echo "[mba-build] generating watch cockpits"
    python3 "$REPO_ROOT/scripts/build_watch_cockpit.py" || \
      echo "[mba-build] WARN: build_watch_cockpit.py failed — cockpits skipped"
    echo "[mba-build] generating knowledge star map"
    python3 "$REPO_ROOT/scripts/build_starmap.py" || \
      echo "[mba-build] WARN: build_starmap.py failed — using committed site/starmap.html"
    echo "[mba-build] generating per-brand star maps"
    rm -rf "$SITE_DIR/starmap"
    python3 "$REPO_ROOT/scripts/build_brand_starmap.py" || \
      echo "[mba-build] WARN: build_brand_starmap.py failed — per-brand star maps skipped"
    echo "[mba-build] generating founder dimension pages"
    rm -rf "$SITE_DIR/founders"
    python3 "$REPO_ROOT/scripts/build_founder_pages.py" || \
      echo "[mba-build] WARN: build_founder_pages.py failed — founder pages skipped"
  else
    echo "[mba-build] no PyYAML in build env — using committed site/api/*"
  fi
else
  echo "[mba-build] no python3 in build env — using committed site/api/*"
fi

if [ ! -f "$WHITELIST" ]; then
  echo "[mba-build] no whitelist file — only homepage will be published"
  exit 0
fi

published_count=0
missing_count=0

while IFS= read -r line || [ -n "$line" ]; do
  # 跳过空行 + 注释
  trimmed="$(echo "$line" | sed -E 's/^[[:space:]]+//;s/[[:space:]]+$//')"
  case "$trimmed" in
    ''|\#*) continue ;;
  esac

  slug="$trimmed"
  src_html="$SRC_DIR/$slug/report.html"
  dest_dir="$OUT_DIR/$slug"

  if [ ! -f "$src_html" ]; then
    echo "[mba-build] WARN: $slug listed but $src_html missing — skipping"
    missing_count=$((missing_count + 1))
    continue
  fi

  mkdir -p "$dest_dir"
  cp "$src_html" "$dest_dir/index.html"

  # 一并拷该 brand 目录下的静态资源(图片 / PDF,不拷 _raw / reviews / versions)。
  # report.pdf 由 scripts/print_report.sh 就地生成并覆盖(forced-open <details>),
  # 不再有 expanded.pdf 中间产物。report.print.html 仅是 PDF 渲染源,也不上线。
  while IFS= read -r asset; do
    rel="${asset#$SRC_DIR/$slug/}"
    mkdir -p "$dest_dir/$(dirname "$rel")"
    cp "$asset" "$dest_dir/$rel"
  done < <(
    find "$SRC_DIR/$slug" -maxdepth 2 -type f \
      \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \
         -o -name "*.svg" -o -name "*.webp" -o -name "*.gif" \
         -o -name "*.pdf" \) \
      ! -path "*/versions/*" \
      ! -path "*/_raw/*" \
      ! -path "*/reviews/*" \
      2>/dev/null
  )

  # 发布 EVOLUTION 版本快照(versions/*.html)——首页卡片的「版本演化」导航点开的正是这些历史版本。
  # 只发 .html(自包含),不发 versions/*.md 原稿。当前版本仍是 /reports/<slug>/(report.html)。
  if compgen -G "$SRC_DIR/$slug/versions/*.html" >/dev/null 2>&1; then
    mkdir -p "$dest_dir/versions"
    cp "$SRC_DIR/$slug"/versions/*.html "$dest_dir/versions/"
    echo "[mba-build]   + $(ls "$SRC_DIR/$slug"/versions/*.html | wc -l | tr -d ' ') version snapshot(s)"
  fi

  echo "[mba-build] published: $slug"
  published_count=$((published_count + 1))
done < "$WHITELIST"

echo "[mba-build] done — published=$published_count missing=$missing_count"
