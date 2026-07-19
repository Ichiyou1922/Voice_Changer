#!/usr/bin/env bash
# Seed-VC のゼロショット/話者別 fine-tune プロファイルを GUI で選んで起動する。
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$DIR/scripts/voice_clone_launcher.py" "$@"
