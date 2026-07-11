#!/usr/bin/env bash
# Print a brand report HTML to PDF with all <details> force-expanded.
#
# Why: report.html uses <details> to collapse heavy sections (dissent walk-throughs,
# Citations). When printed, closed-by-default details would lose their bodies in the
# PDF. This script:
#   1. Copies report.html → report.print.html (intermediate)
#   2. Force-adds `open` to every <details>
#   3. Runs headless Chrome → report.pdf (overwrites existing)
#
# Usage:
#   scripts/print_report.sh <brand-slug>
#
# Brand dir resolves to published/reports/<slug>/. The previous report.pdf is
# overwritten in place; if you want a baseline copy, snapshot it yourself before
# running.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <brand-slug>" >&2
  exit 2
fi

SLUG="$1"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRAND_DIR="$REPO_ROOT/published/reports/$SLUG"

if [ ! -d "$BRAND_DIR" ]; then
  echo "[print] brand dir not found: $BRAND_DIR" >&2
  exit 1
fi

SRC_HTML="$BRAND_DIR/report.html"
PRINT_HTML="$BRAND_DIR/report.print.html"
OUT_PDF="$BRAND_DIR/report.pdf"

if [ ! -f "$SRC_HTML" ]; then
  echo "[print] $SRC_HTML missing" >&2
  exit 1
fi

# Cross-platform Chromium/Chrome discovery (E2-6). Prefers the Chromium this
# environment preinstalls for Playwright ($PLAYWRIGHT_BROWSERS_PATH, e.g.
# /opt/pw-browsers), so PDF generation works on Linux/CI — not only macOS.
find_chrome() {
  local pb="${PLAYWRIGHT_BROWSERS_PATH:-}"
  if [ -n "$pb" ]; then
    [ -x "$pb/chromium" ] && { echo "$pb/chromium"; return 0; }
    local c
    for c in "$pb"/chromium-*/chrome-linux/chrome "$pb"/chromium-*/chrome-linux/headless_shell; do
      [ -x "$c" ] && { echo "$c"; return 0; }
    done
  fi
  for name in chromium chromium-browser google-chrome-stable google-chrome; do
    if command -v "$name" >/dev/null 2>&1; then command -v "$name"; return 0; fi
  done
  local mac="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  [ -x "$mac" ] && { echo "$mac"; return 0; }
  return 1
}

if ! CHROME="$(find_chrome)"; then
  echo "[print] no Chromium/Chrome found. Tried \$PLAYWRIGHT_BROWSERS_PATH/chromium, chromium, chromium-browser, google-chrome[-stable], and macOS Chrome.app." >&2
  exit 1
fi
echo "[print] using browser: $CHROME"

cp "$SRC_HTML" "$PRINT_HTML"
perl -i -pe 's|<details>|<details open>|g' "$PRINT_HTML"

# Older reports baked in `details[open] summary { display: none }` — that hides
# the section title (and only the title) in PDF. Strip just that rule; leave
# the rest of the print CSS alone so we don't accidentally break layout.
perl -i -pe 's|details\[open\]\s*summary\s*\{\s*display:\s*none;?\s*\}||g' "$PRINT_HTML"

OPEN_COUNT=$(grep -c '<details open>' "$PRINT_HTML" || true)
echo "[print] $SLUG — forced open: $OPEN_COUNT <details>"

"$CHROME" \
  --headless \
  --disable-gpu \
  --no-pdf-header-footer \
  --virtual-time-budget=15000 \
  --run-all-compositor-stages-before-draw \
  --print-to-pdf="$OUT_PDF" \
  "file://$PRINT_HTML" 2>&1 | tail -3

PAGES=$(pdfinfo "$OUT_PDF" 2>/dev/null | awk -F: '/^Pages/ {gsub(/ /,"",$2); print $2}')
echo "[print] wrote $OUT_PDF (${PAGES:-?} pages)"
