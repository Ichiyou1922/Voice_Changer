#!/usr/bin/env bash
# Seed-VC の起動中プロファイル表示を，追跡対象のパッチから適用する．
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEEDVC_DIR="$DIR/seed-vc"
PATCH_FILE="$DIR/patches/seedvc-profile-ui.patch"
TARGET_FILE="$SEEDVC_DIR/real-time-gui.py"

if [ ! -f "$TARGET_FILE" ]; then
    echo "Seed-VC が見つかりません．先に scripts/setup_seedvc.sh を実行してください．" >&2
    exit 1
fi

if grep -q -- "--pipeline-mode" "$TARGET_FILE"; then
    exit 0
fi

if ! git -C "$SEEDVC_DIR" apply --check "$PATCH_FILE"; then
    echo "Seed-VC の版が profile UI パッチと一致しません．パッチを更新してください．" >&2
    exit 1
fi

git -C "$SEEDVC_DIR" apply "$PATCH_FILE"
grep -q -- "--pipeline-mode" "$TARGET_FILE"
