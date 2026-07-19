#!/usr/bin/env bash
# V1 zero-shot real-time pipeline．custom checkpoint は下流で拒否する．
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$DIR/seed-vc/configs/inuse"
if [ ! -f "$DIR/seed-vc/configs/inuse/zero-shot.json" ]; then
    cp "$DIR/config/gui_config.json" "$DIR/seed-vc/configs/inuse/zero-shot.json"
fi
exec "$DIR/scripts/run_voice_changer.sh" --pipeline-mode zero-shot "$@"
