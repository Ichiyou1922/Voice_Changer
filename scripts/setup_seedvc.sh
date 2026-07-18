#!/usr/bin/env bash
# seed-vc の実行環境を構築する (初回のみ実行. 済んでいれば再実行しても壊れない).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

[ -d seed-vc ] || git clone --depth 1 https://github.com/Plachtaa/seed-vc.git

cd seed-vc
[ -d .venv ] || uv venv --python 3.10 .venv

# requirements.txt は torch を nightly cu126 と 2.4.0 固定で二重指定しており
# そのままでは依存解決に失敗するため, nightly 行を除外して 2.4.0 (cu121) を使う
grep -v "nightly/cu126" requirements.txt > /tmp/seedvc_req_filtered.txt
uv pip install -p .venv/bin/python -r /tmp/seedvc_req_filtered.txt

# uv 配布の Python 3.10 は Tk 9.0 同梱で, FreeSimpleGUI 5.1.1 は Tcl 9 で削除された
# 旧 trace API を呼んで起動時に TclError になるため, TkVersion 分岐を持つ 5.2 以上へ更新
uv pip install -p .venv/bin/python -U "FreeSimpleGUI>=5.2"

.venv/bin/python -c "import torch; assert torch.cuda.is_available(); print('setup ok:', torch.__version__)"
