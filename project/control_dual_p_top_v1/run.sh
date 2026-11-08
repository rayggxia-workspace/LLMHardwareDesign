#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?output directory}
base=${NATIVE_STAGE:?locked native-p staging directory}
bank=${SRAM_BANK:?qualified SRAM model}
verilator=${VERILATOR:-verilator}
mkdir -p "$out"
out=$(cd "$out" && pwd)
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
ctrl="$repo/project/control_rtl_min_v0_1"
top="$repo/project/control_dual_p_top_v1"
native="$base/staged/native"
pj="$base/staged/pj/project/rtl"
python3 -B "$repo/project/control_p16_native_v1/images.py" "$out/images" > "$out/image.words"
mapfile -t words < "$out/image.words"
"$verilator" --version > "$out/tools.txt"
"$verilator" --binary --timing --assert --timescale-override 1ns/1ps -Wno-fatal \
  --top-module tb_dual_p_control_top -j "${BUILD_JOBS:-4}" --Mdir "$out/obj" \
  -I"$ctrl" -I"$native" "$ctrl"/{lc_min_controller,mc_min_controller,two_local_link,tb_network_pm}.sv \
  "$top"/{dual_p_control_top,p_control_endpoint,p_word_link,tb_dual_p_control_top}.sv \
  "$repo/project/control_native_v1/"{pj_native_service,ucf_native_service,stored_link}.sv \
  "$repo/project/control_r4_v0_1/p_stored_ack_guard.sv" \
  "$base/design/"{pu_p_group,pu_p_store_control}.sv "$native"/*.sv "$bank" \
  "$pj"/block_pj_v1/*.sv "$pj/block_v2/block_v2_m.sv" "$pj/block_v1/transaction6k.sv" \
  > "$out/compile.log" 2>&1
for mode in 0 1 2 3 4; do
  "$out/obj/Vtb_dual_p_control_top" "+MODE=$mode" \
    "+MOTHER=$out/images/mother.mem" "+MWORDS=${words[0]}" \
    "+LOCAL0=$out/images/local0.mem" "+WORDS0=${words[1]}" \
    "+LOCAL1=$out/images/local1.mem" "+WORDS1=${words[2]}" > "$out/mode-$mode.log" 2>&1
  grep '^PASS dual-p-top' "$out/mode-$mode.log"
done
(cd "$out" && sha256sum compile.log tools.txt mode-*.log images/*.mem > result.sha256)
