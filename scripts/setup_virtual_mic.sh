#!/usr/bin/env bash
# Discord に選ばせる仮想マイクを PipeWire (PulseAudio 互換層) 上に作る.
#   vc_sink : 変換済み音声の書き込み先 (seed-vc GUI の出力デバイス)
#   vc_mic  : vc_sink.monitor を remap した仮想ソース (Discord の入力デバイス)
# monitor を直接使わず remap するのは, monitor ソースを入力候補に出さない
# アプリ (Discord 等) からも通常のマイクとして見えるようにするため.
set -euo pipefail

if ! pactl list short sinks | awk '{print $2}' | grep -qx vc_sink; then
    pactl load-module module-null-sink sink_name=vc_sink \
        sink_properties=device.description=VC_Sink
fi

if ! pactl list short sources | awk '{print $2}' | grep -qx vc_mic; then
    pactl load-module module-remap-source master=vc_sink.monitor \
        source_name=vc_mic source_properties=device.description=VC_Mic
fi

echo "--- sinks ---"
pactl list short sinks | grep vc_sink
echo "--- sources ---"
pactl list short sources | grep vc_mic
