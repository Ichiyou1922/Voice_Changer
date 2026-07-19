#!/usr/bin/env bash
# V1 fine-tuned real-time pipeline．checkpoint，YAML，固定 prompt を必須にする．
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$DIR/seed-vc/configs/inuse"
if [ ! -f "$DIR/seed-vc/configs/inuse/fine-tuned.json" ]; then
    cp "$DIR/config/gui_config.json" "$DIR/seed-vc/configs/inuse/fine-tuned.json"
fi
exec "$DIR/scripts/run_voice_changer.sh" --pipeline-mode fine-tuned "$@"
