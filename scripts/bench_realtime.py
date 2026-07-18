"""seed-vc リアルタイム推論のブロックあたり処理時間を GUI 無しで実測する.

real-time-gui.py の custom_infer を README 推奨パラメータ
(block_time=0.18s, crossfade=0.04s, extra_ce=2.5s, extra_right=0.02s,
 diffusion_steps=10, max_prompt=3.0) で反復実行し, 所要時間と VRAM を報告する.
判定基準: 推論時間 < block_time (180ms) を安定して満たすこと.
"""

import argparse
import contextlib
import importlib.util
import io
import os
import statistics
import sys
import time

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEEDVC_DIR = os.path.join(REPO_DIR, "seed-vc")
REF_WAV = os.path.join(REPO_DIR, "reference", "clone.wav")

# real-time-gui.py は cwd 依存 (sys.path.append(os.getcwd())) なので先に移動する
os.chdir(SEEDVC_DIR)
sys.path.insert(0, SEEDVC_DIR)

import librosa  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "rtg", os.path.join(SEEDVC_DIR, "real-time-gui.py")
)
rtg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rtg)  # __main__ ガードにより GUI は起動しない

rtg.device = torch.device("cuda")

args = argparse.Namespace(checkpoint_path=None, config_path=None, fp16=True, gpu=0)
model_set = rtg.load_models(args)
sr = model_set[-1]["sampling_rate"]
zc = sr // 50

BLOCK_TIME = 0.18
CROSSFADE = 0.04
EXTRA_CE = 2.5
EXTRA_RIGHT = 0.02
MAX_PROMPT = 3.0

block_frame = int(round(BLOCK_TIME * sr / zc)) * zc
block_frame_16k = 320 * block_frame // zc
crossfade_frame = int(round(CROSSFADE * sr / zc)) * zc
sola_buffer_frame = min(crossfade_frame, 4 * zc)
sola_search_frame = zc
extra_frame = int(round(EXTRA_CE * sr / zc)) * zc
extra_frame_right = int(round(EXTRA_RIGHT * sr / zc)) * zc
input_len = (
    extra_frame + crossfade_frame + sola_search_frame + block_frame + extra_frame_right
)
input_res_len = 320 * input_len // zc
skip_head = extra_frame // zc
skip_tail = extra_frame_right // zc
return_length = (block_frame + sola_buffer_frame + sola_search_frame) // zc

ref_wav, _ = librosa.load(REF_WAV, sr=sr)
src_16k, _ = librosa.load(
    os.path.join(SEEDVC_DIR, "examples", "source", "yae_0.wav"), sr=16000
)
src_16k = np.tile(src_16k, int(np.ceil(input_res_len / len(src_16k))))[:input_res_len]
input_wav_res = torch.from_numpy(src_16k).float().to(rtg.device)

print(
    f"model_sr={sr} block_frame={block_frame} ({block_frame/sr*1000:.0f}ms) "
    f"input_res_len={input_res_len} skip_head={skip_head} return_length={return_length}"
)


def run_once(cfg_rate, diffusion_steps):
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        out = rtg.custom_infer(
            model_set,
            ref_wav,
            os.path.basename(REF_WAV),
            input_wav_res,
            block_frame_16k,
            skip_head,
            skip_tail,
            return_length,
            diffusion_steps,
            cfg_rate,
            MAX_PROMPT,
        )
    torch.cuda.synchronize()
    return (time.perf_counter() - t0) * 1000, out


for cfg_rate, steps in [(0.7, 10), (0.0, 10), (0.0, 6), (0.0, 4)]:
    for _ in range(5):  # warmup (初回は prompt 前計算とカーネル初期化を含む)
        run_once(cfg_rate, steps)
    times = [run_once(cfg_rate, steps)[0] for _ in range(30)]
    ok = "OK" if np.percentile(times, 95) < BLOCK_TIME * 1000 else "NG"
    print(
        f"cfg={cfg_rate} steps={steps}: mean={statistics.mean(times):.1f}ms "
        f"median={statistics.median(times):.1f}ms p95={np.percentile(times, 95):.1f}ms "
        f"max={max(times):.1f}ms vs block {BLOCK_TIME*1000:.0f}ms -> {ok}"
    )

print(
    f"VRAM allocated peak: {torch.cuda.max_memory_allocated()/2**20:.0f}MiB, "
    f"reserved: {torch.cuda.max_memory_reserved()/2**20:.0f}MiB"
)
