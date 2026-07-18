# Discord ボイスチェンジャー 開発プラン

作成日: 2026-07-18

> **2026-07-18 更新**: ユーザー判断によりスコープをトラック A（seed-vc リアルタイム）のみに
> 確定．トラック B（STT + Irodori-TTS）は実施しない．実測結果は文末の「進捗と実測」参照．

## 結論（要約）

当初構想の「STT → clone TTS」パイプラインは，**リアルタイム会話用のボイスチェンジャーとしては成立しない可能性が高い**．
最大の理由は遅延で，Irodori-TTS はストリーミング推論に対応しておらず（公式 README に記載なし，2026-07-18 確認），
発話終了を待ってから文字起こし→音声生成を行うため，発話終了から音声出力まで数秒単位の遅れが避けられない．

そこで本プランでは 2 トラック構成を推奨する:

- **トラック A（リアルタイム会話・主軸）**: seed-vc によるリアルタイム zero-shot 声質変換．
  参照音声 1〜30 秒でクローンでき，RTX 3060 Laptop (6GB) での公式実測が全体遅延 ~430ms．
  本機の RTX 4050 Laptop (6GB) は同クラスであり成立する見込み（**本機では未実測**．Phase 1 で最初に検証する）．
- **トラック B（高品質・非リアルタイム，オプション）**: 当初構想の VAD + STT (kotoba-whisper) +
  Irodori-TTS．完全にターゲット声質になり源音声の癖もノイズも残らない利点があるため，
  読み上げ・クリップ生成・「交互に話す」運用向けの副次モードとして残す．

## 環境（実測済み，2026-07-18）

以下は本マシンでコマンド実行して確認した値:

- GPU: NVIDIA GeForce RTX 4050 Laptop, VRAM 6141MiB（ほぼ全量空き），Driver 580.173.02 / CUDA 13.0（`nvidia-smi`）
- 音声: PipeWire 1.0.5（PulseAudio 互換層あり），48kHz/float32/2ch，入出力は Roland FANTOM-06/07/08（`pactl info`）
- Python 3.12.3，ffmpeg・pw-cli インストール済み，RAM 30GiB（`python3 --version` / `which` / `free -h`）
- リポジトリはほぼ空（LICENSE, README.md, 空の reference/ のみ）

## 当初構想（STT → clone TTS）の評価

### 脆弱性・品質面の問題

1. **遅延（致命的）**: パイプラインの構造上，(a) 発話終了の検知（VAD のハングオーバー ~0.5–1s），
   (b) STT 推論，(c) TTS 生成，が直列に積み上がる．Irodori-TTS の生成速度は
   RTX 5070 Ti + Ryzen 7 9700X で 5 秒クリップに約 3 秒という実測報告がある（GIGAZINE, 2026-05）．
   RTX 4050 はこれより演算性能が低いため更に遅くなると推測される（本機未実測）．
   合計すると発話終了から出力開始まで最短でも 3〜5 秒以上となり，会話の応酬には使えない．
2. **パラ言語情報の全損**: 抑揚・感情・笑い・間・言い淀み・非言語音（笑い声，相槌のトーン）は
   テキストを経由した時点で失われ，TTS が独自に再生成した抑揚に置き換わる．
   「声だけ変えて自分の演技を通す」用途には原理的に合わない．
3. **STT 誤認識の伝播**: 誤字がそのまま音声化される．ゲーム用語・固有名詞・スラングに弱い
   （kotoba-whisper でもオノマトペ連続で混乱するというレビュー報告あり）．
4. **日本語 TTS の読み誤り**: 漢字の同形異音語の読み分けはテキストだけでは決定できない．
5. **Irodori-TTS の制約（一次資料・レビュー確認済み）**: 1 回の生成は約 30 秒まで．日本語のみ対応．
   ストリーミング生成の記載なし．

### 利点（残す価値がある理由）

- 出力は完全にターゲット話者の声質になり，源話者の声質の漏れ（VC 系で起きる）が無い．
- マイクノイズ・環境音が完全に消える．
- Irodori-TTS は MIT ライセンス・日本語特化・zero-shot クローン（参照音声 10〜30 秒）で，
  この用途のモデルとしての選定自体は妥当．

### 計算資源

- kotoba-whisper-v2.0-faster (CTranslate2/float16) + Irodori-TTS 500M–600M の同時常駐が
  6GB に収まるかは**未検証**．モデルサイズからは収まる見込みだが，Phase 3 冒頭で実測する．
- トラック B は交互運用なので，収まらない場合は STT/TTS を排他ロードする逃げ道がある．

## 推奨アーキテクチャ

### トラック A: seed-vc リアルタイム声質変換（主軸）

```
マイク (FANTOM) → seed-vc real-time GUI/サーバ → PipeWire 仮想ソース → Discord
```

- seed-vc（Plachtaa/seed-vc, GPL 系ではなく… ライセンスは導入時に要確認）は
  zero-shot VC で参照音声 1〜30 秒からクローン可能．公式が RTX 3060 Laptop で
  実測・推奨パラメータを公開しており，全体遅延 ~430ms（アルゴリズム ~380ms + デバイス ~100ms）．
  推奨 VRAM 6GB+ で本機と一致する．
- 品質が不足した場合の代替: w-okada VCClient v.2（RVC / Beatrice v2 対応，Linux はソースから実行）．
  RVC はターゲット話者ごとの学習が必要（クローンの手軽さは落ちる）が品質・安定性の実績が大きい．
  Beatrice v2 は低遅延・低負荷だがライセンスがプロプライエタリ．

### トラック B: VAD + STT + Irodori-TTS（オプション・後回し）

```
マイク → Silero VAD（発話区間検出）→ faster-whisper (kotoba-whisper-v2-faster)
      → テキスト → Irodori-TTS（参照音声でクローン）→ PipeWire 仮想ソース → Discord
```

- 位置づけ: リアルタイム会話ではなく「高品質モード」（一言ずつの応酬，読み上げ，録画素材）．
- 遅延目標は「発話終了から 3–5 秒」を許容する運用前提．

### 共通基盤: 音声ルーティング（OBS 的なマイク横取り）

PipeWire の仮想デバイスで実現する（PipeWire 1.0.5 実測済みの環境で標準的な手法）:

1. `pactl load-module module-null-sink media.class=Audio/Source/Virtual sink_name=vc_mic ...`
   で仮想マイクを作成．
2. 変換パイプラインの出力を仮想マイクに書き込む（アプリからは `vc_mic` の monitor / Virtual Source として見える）．
3. Discord の入力デバイスに仮想マイクを選択する．

Discord のデスクトップ版 (Linux) が仮想ソースを認識するかは Phase 0 で実機確認する．

## フェーズ計画（各フェーズ末に実機検証）

リスクの大きい順に潰す．**Phase 1 が本プラン最大の検証点**（6GB で seed-vc の推論時間 <
ブロック時間を満たせるか）で，ここが崩れたら代替（RVC/Beatrice）へ切り替える．

- **Phase 0: 音声ルーティング基盤**
  PipeWire 仮想マイク作成スクリプト．検証: `ffmpeg`/`pw-cat` でトーンを流し込み，
  Discord（またはまず `pavucontrol`/録音アプリ）で仮想マイクから聞こえることを確認．
- **Phase 1: seed-vc リアルタイム成立性の実測**
  seed-vc をソースから導入し，real-time GUI をチューニング（diffusion steps 4–10，
  CFG rate 0.0 等の公式推奨から開始）．計測項目: ブロックあたり推論時間 vs ブロック時間，
  体感遅延，VRAM 使用量，品質（自分の参照音声でクローン）．
  **判定基準: 推論時間 < ブロック時間を安定して満たし，遅延 ~500ms 台なら採用．**
- **Phase 2: Discord E2E**
  seed-vc 出力 → 仮想マイク → Discord 実通話で相手側の聞こえ方を確認．
  常用のための起動スクリプト / systemd user unit 化．
- **Phase 3（オプション）: 高品質モード（トラック B）**
  Irodori-TTS 単体の生成速度・VRAM を本機で実測 → VAD+STT+TTS を utterance 単位で接続．
  STT/TTS の VRAM 同時常駐可否をここで実測．
- **Phase 4（品質不足時のみ）: RVC / Beatrice v2 への切替**
  自声→ターゲットの RVC モデル学習（w-okada の学習環境 or RVC WebUI）．6GB での学習可否も要実測．

## リスクと未検証事項（明示）

| 事項 | 状態 |
|---|---|
| RTX 4050 6GB での seed-vc リアルタイム成立 | 未実測（RTX 3060 の公式実測から見込みあり）— Phase 1 で検証 |
| Linux Discord が PipeWire 仮想ソースを選択可能か | 未実測 — Phase 0 で検証 |
| Irodori-TTS の本機での生成速度・VRAM | 未実測 — Phase 3 で検証 |
| STT+TTS の 6GB 同時常駐 | 未実測 — Phase 3 で検証 |
| seed-vc で日本語音声の品質（学習データの言語分布） | 未確認 — Phase 1 で耳で検証 |
| ゲーム等と GPU を取り合う場合の劣化 | 未検証（w-okada はサーバ分離機構を持つ．seed-vc で問題になれば構成再考） |

## 進捗と実測（2026-07-18，本機 RTX 4050 Laptop 6GB で実施）

- **環境構築**: `scripts/setup_seedvc.sh`（Python 3.10 venv + torch 2.4.0+cu121．
  requirements の torch 二重指定と FreeSimpleGUI の Tk 9.0 非互換への対処を含む）．
- **オフライン変換 E2E**: `inference.py` で examples/source/yae_0.wav →
  reference/clone.wav への変換が成功（出力 11 秒 wav 生成を確認）．
- **リアルタイム成立性（最重要検証点・クリア）**: `scripts/bench_realtime.py` で
  実運転と同じ `custom_infer` 経路を README 推奨設定（block 0.18s, steps=10, cfg=0.7,
  extra_ce=2.5s）でウォームアップ 5 回 + 30 回計測:
  平均 102.5ms / p95 122.6ms / 最大 160.3ms < Block Time 180ms → **成立**．
  steps=4, cfg=0.0 なら平均 65.4ms まで短縮可．VRAM ピークは allocated 920MiB．
  想定全体遅延 ≈ アルゴリズム 380ms（0.18×2+0.02）+ デバイス側 ~100ms ≈ 480ms．
  （なお README が主張する cfg=0.0 での 1.5 倍高速化は本機では再現せず，
  steps=10 では cfg 0.7 と 0.0 で有意差が無かった．）
- **仮想マイク**: `scripts/setup_virtual_mic.sh` で vc_sink + vc_mic を作成し，
  paplay→parecord のループバックで信号到達を確認（捕捉 max -18.1dB）．
- **GUI 起動**: `scripts/run_voice_changer.sh`（出力を PULSE_SINK=vc_sink に固定，
  設定は config/gui_config.json を初回配置）で 30 秒間クラッシュ無しを確認．
- **未検証（ユーザー操作が必要）**: GUI で Start をかけた実運転の音質・体感遅延，
  Discord が vc_mic を入力デバイスとして認識するか，通話相手側での聞こえ方．

## 倫理・規約

- クローン対象は自分の声，または明示的な同意を得た声に限る（Irodori-TTS の利用制限にも
  「同意のない声のクローン・なりすまし禁止」が明記されている）．
- Discord の利用規約でリアルタイム音声改変が制限されていないかは未確認．導入前に確認する．
- 通話相手を欺くなりすまし用途には使わない．
