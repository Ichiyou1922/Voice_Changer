#!/usr/bin/env bash
# seed-vc リアルタイム GUI を仮想マイク構成で起動する.
#   入力: システムデフォルトのマイク (PULSE_SOURCE で上書き可)
#   出力: vc_sink (PULSE_SINK で固定) -> vc_mic として Discord から見える
# 初回のみ config/gui_config.json を seed-vc の設定として配置する
# (GUI 上での変更は configs/inuse/config.json に保存され, 以後そちらが優先).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$DIR/scripts/setup_virtual_mic.sh"

mkdir -p "$DIR/seed-vc/configs/inuse"
if [ ! -f "$DIR/seed-vc/configs/inuse/config.json" ]; then
    cp "$DIR/config/gui_config.json" "$DIR/seed-vc/configs/inuse/config.json"
fi

cd "$DIR/seed-vc"
PULSE_SINK=vc_sink exec .venv/bin/python real-time-gui.py "$@"
