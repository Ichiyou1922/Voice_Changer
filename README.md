# Voice_Changer

[seed-vc](https://github.com/Plachtaa/seed-vc) を使った Discord 向けリアルタイムボイスチェンジャー環境．
参照音声（10〜30 秒）を 1 本用意するだけで，学習なし（zero-shot）でその声質に変換して通話に乗せられる．

構成の考え方はどの OS でも同じで，次の 2 つを組み合わせる:

1. **seed-vc のリアルタイム GUI** — マイク入力をブロック単位（既定 0.18 秒）で変換して出力する．
2. **仮想オーディオデバイス** — GUI の出力を「仮想マイク」に流し，Discord の入力デバイスとして選ぶ．

検証状況: **Ubuntu（本リポジトリの環境: Ubuntu + RTX 4050 Laptop 6GB + PipeWire 1.0.5）でのみ動作を実測済み**．
Windows / macOS の手順は seed-vc 公式 README と各ツールの公式ドキュメントに基づくもので，本リポジトリでは未検証．

## 必要なもの（共通）

- Python 3.10（seed-vc 公式の推奨バージョン）
- 参照音声: クリーンな単一話者の wav（10〜30 秒程度）．各自で用意して `reference/clone.wav` に置く
  （音声ファイルはリポジトリに含まれない．git 管理外）
- リアルタイム変換には NVIDIA GPU（6GB VRAM で十分．実測 VRAM ピークは約 920MiB）を強く推奨．
  CPU のみでのリアルタイム変換は現実的でない
- 初回起動時に Hugging Face からモデル（`seed-uvit-tat-xlsr-tiny`）が自動ダウンロードされる（要ネット接続）

## Ubuntu（実測済み）

依存: `git`, [`uv`](https://docs.astral.sh/uv/), NVIDIA ドライバ（CUDA 12 対応），PipeWire（22.04 以降は標準）．

```bash
git clone https://github.com/Ichiyou1922/Voice_Changer.git
cd Voice_Changer
./scripts/setup_seedvc.sh   # seed-vc の clone + venv 構築（初回のみ，数分）
./scripts/run_voice_changer.sh
```

`run_voice_changer.sh` が以下を自動で行う:

- PipeWire 上に仮想シンク `vc_sink` と仮想マイク `vc_mic` を作成（`scripts/setup_virtual_mic.sh`）
- 推奨パラメータ（`config/gui_config.json`）を初回のみ seed-vc に配置
- GUI の出力先を `PULSE_SINK=vc_sink` で仮想シンクに固定して起動

GUI が開いたら:

1. `reference audio` に自分で置いた参照音声（`reference/clone.wav`）のパスを設定する
2. **Start Voice Conversion** を押す
3. Discord の設定 → 音声・ビデオ → 入力デバイスで **VC_Mic** を選ぶ

仮想デバイスは再起動で消えるが，`run_voice_changer.sh` が毎回作り直すので操作は不要．

## Windows（未検証）

仮想マイクに [VB-CABLE](https://vb-audio.com/Cable/) を使う（seed-vc 公式 README でも案内されている方法）．

1. [Python 3.10](https://www.python.org/downloads/) と [Git](https://git-scm.com/) をインストール
2. VB-CABLE をインストールして再起動（`CABLE Input` / `CABLE Output` というデバイスが生える）
3. PowerShell で:

```powershell
git clone https://github.com/Plachtaa/seed-vc.git
cd seed-vc
py -3.10 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python real-time-gui.py
```

   ※ requirements.txt 先頭の torch nightly (cu126) 行で依存解決に失敗する場合は，その 3 行を削除して
   `torch==2.4.0` 系（ファイル後半に記載）を使う．本リポジトリの Ubuntu セットアップも同じ対処をしている．

4. GUI で Input Device に実マイク，**Output Device に `CABLE Input`** を選択
5. reference audio に各自で用意した参照音声の wav を指定して Start
6. Discord の入力デバイスに **`CABLE Output`** を選ぶ

## macOS（未検証）

- 対応は Apple Silicon (M シリーズ) のみ．依存インストールは `pip install -r requirements-mac.txt` を使う
  （他は Windows と同じ流れ）．
- 仮想マイクには [BlackHole](https://github.com/ExistentialAudio/BlackHole)（2ch 版）を使い，
  GUI の Output Device に BlackHole，Discord の入力に BlackHole を選ぶ．
- `real-time-gui.py` 起動時に `ModuleNotFoundError: No module named '_tkinter'` が出る場合は
  Tkinter 付きの Python を入れ直す（seed-vc 公式 README のトラブルシュートに詳細あり）．
- **注意**: GPU (MPS) での実時間性能は未検証．ブロックあたりの推論時間が Block time を超えると
  音が途切れる．その場合は Block time を上げる（遅延は増える）．

## 使い方のポイント（全 OS 共通）

GUI 右下の **Inference time (ms) が Block time (ms) を下回っている**ことが途切れないための絶対条件．
超えている場合は次の順で調整する:

| 操作 | 効果 |
|---|---|
| Diffusion steps を下げる（10 → 6 → 4） | 推論時間がほぼ比例して短縮．品質は徐々に低下 |
| Block time を上げる（0.18 → 0.25 …） | 途切れは解消するが遅延が増える（遅延 ≈ Block time × 2 + right context + デバイス遅延） |
| Extra context (right) は最小（0.02）のまま | 上げると丸ごと遅延に加算される |

- 参照音声を差し替えるとき: GUI の reference audio パスを変えるだけでよい（次のブロックから反映，再起動不要）
- 変換を使わないときは **Stop** を押す．無音中も推論は毎ブロック走り続けるため，
  つけっぱなしは GPU の熱で PC 全体が遅くなる（Ubuntu 実測: GPU が電力上限 35W に張り付き
  CPU が最大 2.6GHz にクロック制限された）
- 疎通確認には Input listening モード（変換なしで素通し）が使える

本機（RTX 4050 Laptop 6GB）での実測値: ブロック推論 平均 102ms（steps=10）/ 65ms（steps=4），
全体遅延の想定 ≈ 480ms，VRAM ピーク 920MiB．計測スクリプトは `scripts/bench_realtime.py`．

## リポジトリ構成

```
config/gui_config.json        # GUI の推奨初期設定（Ubuntu 用パス込み）
reference/                    # 参照音声の置き場（各自で wav を配置．git 管理外）
scripts/setup_seedvc.sh       # seed-vc 環境構築（Ubuntu）
scripts/setup_virtual_mic.sh  # PipeWire 仮想マイク作成（Ubuntu）
scripts/run_voice_changer.sh  # 起動ランチャ（Ubuntu）
scripts/bench_realtime.py     # ブロック推論時間のヘッドレス実測
PLAN.md                       # 設計判断と実測記録
```

## 倫理・ライセンス

- クローンしてよいのは自分の声か，明示的な同意を得た人の声のみ．なりすまし・欺瞞目的での使用禁止
- seed-vc は GPL-3.0（コード）．本リポジトリは Apache-2.0（LICENSE 参照）
