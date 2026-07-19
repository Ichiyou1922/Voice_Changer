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
./scripts/run_voice_clone_gui.sh
```

起動ランチャーで **Voice clone profile** を選び、`Start Voice Changer` を押す。標準の
`Seed-VC Zero-shot (realtime)` は、これまでと同じ参照音声だけで使うモードである。

`run_voice_changer.sh` が以下を自動で行う:

- PipeWire 上に仮想シンク `vc_sink` と仮想マイク `vc_mic` を作成（`scripts/setup_virtual_mic.sh`）
- 推奨パラメータ（`config/gui_config.json`）を初回のみ seed-vc に配置
- GUI の出力先を `PULSE_SINK=vc_sink` で仮想シンクに固定して起動

GUI が開いたら:

1. `reference audio` に自分で置いた参照音声（`reference/clone.wav`）のパスを設定する
2. **Start Voice Conversion** を押す
3. Discord の設定 → 音声・ビデオ → 入力デバイスで **VC_Mic** を選ぶ

仮想デバイスは再起動で消えるが，`run_voice_changer.sh` が毎回作り直すので操作は不要．

## より高い声質一致度: Fine-tuned realtime profile

リアルタイム性を維持したまま品質を上げるには、Seed-VC の **real-time tiny** モデルを
対象話者のクリーンな音声で fine-tune する。公式 README でも、この tiny 用 YAML が
リアルタイム変換向けの fine-tune 構成として指定されている。V2 や offline 用の大きな
モデルはこの GUI のストリーミング経路には対応しないため、プロファイルには登録しない。

### 用意する音声

クローン対象本人の同意を得た、単一話者のクリーンな音声だけを使う。

- 形式は wav、flac、mp3、m4a、opus、ogg に対応する。
- 1 ファイルは **1〜30 秒**にする。範囲外のファイルは Seed-VC が学習対象から除外する。
- 公式上の最低条件は話者あたり **1 発話**である。ただし、これは学習が開始できる最低値であり、品質を保証する長さではない。
- 総音声量の公式な推奨値は公開されていない。このリポジトリでは、まず 5〜15 分程度の発話を 20〜60 個の短いファイルに分けて試すことを推奨する。これは運用上の開始値であり、本機で品質を実測した値ではない。
- BGM、効果音、複数人の会話、強い残響、クリッピングを含めない。発話内容と録音条件に幅を持たせると、特定の言い回しだけに偏るのを抑えやすい。

例えば、学習用音声をリポジトリ外の `/path/to/target-voice` に置く。

```
/path/to/target-voice/
├── 001.wav
├── 002.wav
└── ...
```

### 必要な VRAM

fine-tune 用の必要 VRAM は Seed-VC 公式が固定値を公開していない。
公式の学習コマンドは `--batch-size 2` を例示し、GPU メモリに応じて変更するよう指定している。

本リポジトリで実測済みなのは、推論時の VRAM ピーク約 920 MiB だけであり、学習時の VRAM は未計測である。
推論に 6GB で足りても、勾配とオプティマイザ状態を保持する fine-tune が 6GB で成立する保証にはならない。

- **16GB 以上を推奨**する。公式が「100 steps を T4 で約 2 分」と示すため、T4 相当の環境を最初の実行先にするのが安全である。
- **6GB で試す場合**は、必ず `--batch-size 1` から始める。最初の数 step で CUDA out of memory が出たら、batch size をさらに下げる選択肢はないため、VRAM の大きい GPU または Colab の GPU ランタイムへ切り替える。
- 学習開始直後に `nvidia-smi` で VRAM 使用量を確認し、推論 GUI やゲームなど他の GPU 利用を停止する。

根拠となる学習仕様は [Seed-VC 公式 README](https://github.com/Plachtaa/seed-vc/blob/main/README.md) を参照する。
NVIDIA T4 のメモリ容量は [NVIDIA の仕様](https://www.nvidia.com/en-us/data-center/tesla-t4/) で 16GB とされている。

### 学習コマンド

以下は real-time tiny モデルを、`/path/to/target-voice` の音声で fine-tune するコマンドである。
6GB GPU を想定して batch size を 1 にしている。
16GB 以上で余裕があることを確認できた場合だけ、`--batch-size 2` を試す。

```bash
cd seed-vc
.venv/bin/python train.py \
  --config configs/presets/config_dit_mel_seed_uvit_xlsr_tiny.yml \
  --dataset-dir /path/to/target-voice \
  --run-name target-voice-realtime \
  --batch-size 1 \
  --max-steps 1000 \
  --max-epochs 1000 \
  --save-every 250 \
  --num-workers 0
```

公式は最短の目安として 100 steps を挙げているが、このコマンドは比較用の中間 checkpoint も残すため 1000 steps にしている。
学習済みモデルの品質、必要な steps、所要時間はデータ量と GPU に依存するため、本機では未測定である。
学習を途中で止めても、同じ `--config` と `--run-name` で再実行すれば Seed-VC が最新 checkpoint から再開する。

長時間ジョブを始める前に、GPU がほかの処理に使われていないこと、空き VRAM、保存先の空き容量を確認する。

```bash
nvidia-smi
df -h . runs
```

fine-tune が終わったら、成果物を次のように配置する（音声・モデルはいずれも git 管理外）。

```
models/seedvc-finetuned/
├── ft_model.pth
└── config_dit_mel_seed_uvit_xlsr_tiny.yml
```

`runs/target-voice-realtime/ft_model.pth` と、同じ学習に使った YAML をコピーする。

```bash
cd ..
mkdir -p models/seedvc-finetuned
cp seed-vc/runs/target-voice-realtime/ft_model.pth \
  models/seedvc-finetuned/ft_model.pth
cp seed-vc/runs/target-voice-realtime/config_dit_mel_seed_uvit_xlsr_tiny.yml \
  models/seedvc-finetuned/config_dit_mel_seed_uvit_xlsr_tiny.yml
```

checkpoint と YAML がそろうと，起動ランチャーの
`Seed-VC Fine-tuned (realtime / higher similarity)` を選べるようになる．
現在のプロファイルでは `reference/clone.wav` を reference 欄の初期値として使う．
fine-tune 専用 GUI で別の音声へ変更でき，選択内容は `configs/inuse/fine-tuned.json` に保存される．
学習データと同じ話者のクリーンな音声を指定する．
fine-tune 後も reference prompt が必要なのは Seed-VC V1 の公式仕様であり，学習済み checkpoint だけで
話者を固定する方式ではない．

起動選択後の経路は次のように分離している．

- `V1 zero-shot realtime`：組み込み tiny checkpoint を使い，GUI で reference 音声を変更できる．custom checkpoint が渡された場合は起動を拒否する．
- `V1 fine-tuned realtime`：fine-tuned checkpoint と対応 YAML を必須にする．reference は fine-tune 専用 GUI で選択し，未指定のまま変換を開始した場合はエラーにする．

GUI 設定も `configs/inuse/zero-shot.json` と `configs/inuse/fine-tuned.json` に分けるため，
reference と性能設定が別 pipeline へ引き継がれることはない．

どちらも V1 tiny のリアルタイム推論なので，Diffusion steps，Inference CFG rate，Block time などの
性能設定は共通である．V2 は Intelligibility CFG，Similarity CFG，Top-p，Temperature，AR style conversion
など別のパラメータを持つが，Seed-VC 公式の real-time GUI には統合されていないため，この選択画面には含めない．

起動した GUI のタイトルと最上部の `Loaded voice clone profile` パネルにも，選択したプロファイル名と
実際に渡した checkpoint を表示する．fine-tuned プロファイルで `Loaded fine-tuned checkpoint:` が
表示されていれば，その checkpoint のロード成功後に GUI が開いている．

モデルは起動時に GPU へロードされるため、変換中の無停止切替はできない。切り替えるときは
Seed-VC GUI を閉じて、ランチャーから別プロファイルで開始する。

GUI を使わない確認・起動もできる。

```bash
./scripts/run_voice_clone_gui.sh --list
./scripts/run_voice_clone_gui.sh --profile seedvc-zero-shot --dry-run
./scripts/run_voice_clone_gui.sh --profile seedvc-finetuned-realtime
```

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
scripts/run_voice_clone_gui.sh # ボイスクローン・プロファイル選択 GUI
scripts/run_seedvc_zero_shot.sh # V1 zero-shot 専用起動経路
scripts/run_seedvc_finetuned.sh # V1 fine-tuned 専用起動経路
scripts/voice_clone_launcher.py # プロファイル検証と Seed-VC 起動
patches/seedvc-profile-ui.patch # Seed-VC 側の経路検証と表示分離
scripts/bench_realtime.py     # ブロック推論時間のヘッドレス実測
PLAN.md                       # 設計判断と実測記録
```

## 倫理・ライセンス

- クローンしてよいのは自分の声か，明示的な同意を得た人の声のみ．なりすまし・欺瞞目的での使用禁止
- seed-vc は GPL-3.0（コード）．本リポジトリは Apache-2.0（LICENSE 参照）
