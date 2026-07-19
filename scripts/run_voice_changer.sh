#!/usr/bin/env bash
# seed-vc リアルタイム GUI を仮想マイク構成で起動する.
#   入力: システムデフォルトのマイク (PULSE_SOURCE で上書き可)
#   出力: vc_sink (PULSE_SINK で固定) -> vc_mic として Discord から見える
# GUI 設定の初期化と保存先は各 pipeline の専用 launcher が管理する．
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$DIR/scripts/setup_virtual_mic.sh"
"$DIR/scripts/apply_seedvc_profile_ui_patch.sh"

cd "$DIR/seed-vc"
PULSE_SINK=vc_sink exec .venv/bin/python real-time-gui.py "$@"
