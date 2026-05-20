#!/usr/bin/env bash
# 从YouTube视频下载字幕
# 用法: ./download_subtitles.sh <YouTube_URL> [输出目录]
# 优先下载人工字幕，无人工字幕则下载自动生成字幕
# 语言优先级：中文 > 英文 > 其他
#
# 调试: DEBUG=1 ./download_subtitles.sh <URL>  # 显示 yt-dlp 完整 stderr

set -euo pipefail

URL="${1:-}"
OUTPUT_DIR="${2:-.}"
DEBUG="${DEBUG:-0}"

if [ -z "$URL" ]; then
    echo "用法: ./download_subtitles.sh <YouTube_URL> [输出目录]"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
MARKER="$(mktemp -t ytdlp-subtitles.XXXXXX)"
ERRLOG="$(mktemp -t ytdlp-subtitles-err.XXXXXX)"
trap 'rm -f "$MARKER" "$ERRLOG"' EXIT

find_new_subtitle() {
    find "$OUTPUT_DIR" -type f \( -name "*.srt" -o -name "*.vtt" \) -newer "$MARKER" 2>/dev/null | head -1
}

# 跑 yt-dlp 并捕获 stderr 到 $ERRLOG；exit code 不为 0 时打 warn，
# DEBUG=1 时把完整 stderr 打回当前 stderr。
run_ytdlp() {
    local label="$1"; shift
    if yt-dlp "$@" 2>"$ERRLOG"; then
        return 0
    else
        local code=$?
        echo "[warn] yt-dlp attempt failed: ${label} (exit ${code})" >&2
        if [ "$DEBUG" = "1" ]; then
            echo "[warn] --- yt-dlp stderr ---" >&2
            cat "$ERRLOG" >&2
            echo "[warn] --- end stderr ---" >&2
        else
            echo "[warn] rerun with DEBUG=1 to see yt-dlp stderr" >&2
        fi
        return "$code"
    fi
}

echo ">>> 检查可用字幕..."
if yt-dlp --list-subs --no-download "$URL" 2>"$ERRLOG" | tail -20; then
    :
else
    echo "[warn] --list-subs failed; continuing to attempt download anyway" >&2
fi

echo ""
echo ">>> 尝试下载人工字幕（中文优先）..."

# 尝试1: 人工中文字幕
if run_ytdlp "manual zh" --write-subs --sub-langs "zh-Hans,zh-Hant,zh,zh-CN,zh-TW" --sub-format srt --skip-download -o "$OUTPUT_DIR/%(title)s" "$URL"; then
    FOUND=$(find_new_subtitle)
    if [ -n "$FOUND" ]; then
        echo "✅ 下载成功: $FOUND"
        exit 0
    fi
fi

# 尝试2: 人工英文字幕
echo ">>> 无中文人工字幕，尝试英文..."
if run_ytdlp "manual en" --write-subs --sub-langs "en,en-US,en-GB" --sub-format srt --skip-download -o "$OUTPUT_DIR/%(title)s" "$URL"; then
    FOUND=$(find_new_subtitle)
    if [ -n "$FOUND" ]; then
        echo "✅ 下载成功: $FOUND"
        exit 0
    fi
fi

# 尝试3: 自动生成字幕（中文优先）
echo ">>> 无人工字幕，尝试自动生成字幕..."
if run_ytdlp "auto zh/en" --write-auto-subs --sub-langs "zh-Hans,zh,en" --sub-format srt --skip-download -o "$OUTPUT_DIR/%(title)s" "$URL"; then
    FOUND=$(find_new_subtitle)
    if [ -n "$FOUND" ]; then
        echo "✅ 自动字幕下载成功: $FOUND"
        exit 0
    fi
fi

echo "❌ 未找到任何可用字幕（如怀疑是网络 / cookie / 区域问题，重跑 DEBUG=1 看 stderr）"
exit 1
