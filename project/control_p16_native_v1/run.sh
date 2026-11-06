#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?usage: run.sh OUTPUT_DIRECTORY}
native=${NATIVE_STAGE:?set NATIVE_STAGE to the verified native input directory}
bank=${SRAM_BANK:?set SRAM_BANK to the SRAM bank model}
verilator=${VERILATOR:-verilator}
mkdir -p "$out"
cd "$out"
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1
printf '%s  %s\n' 6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7 "$bank" | sha256sum -c
(cd "$native" && sha256sum -c "$repo/project/control_p16_native_v1/upstream.sha256") | tee inputs.log
ctrl="$repo/project/control_rtl_min_v0_1"
trial="$repo/project/control_p16_native_v1"
service="$repo/project/control_native_v1"
p="$native/pj/project/rtl"
p16="$repo/project/rtl/block_pj_v1"
for name in block_p16 pj_feed_hold pj_mem_port pj_sram_client; do
  cmp "$p16/$name.sv" "$p/block_pj_v1/$name.sv"
done
python3 "$trial/images.py" "$PWD/images" > image.words
mapfile -t words < image.words
"$verilator" --version | tee tool.txt
python3 --version | tee -a tool.txt
# Use the same SRAM implementations and P16 sources as the upstream acceptance.
"$verilator" --binary --timing --assert --timescale-override 1ns/1ps -Wno-fatal \
  --top-module tb_p16_pair -j "${BUILD_JOBS:-4}" --Mdir "$PWD/obj" \
  -I"$ctrl" -I"$native/native" \
  "$ctrl"/{lc_min_controller,mc_min_controller,tb_network_pm}.sv \
  "$trial"/{tb_p16_local,tb_p16_pair}.sv "$service"/{pj_native_service,ucf_native_service,stored_link}.sv \
  "$native"/native/{block_feed_loader,block_feed_s16k,block_feed_s16k_sram,block_local_s_arbiter,block_local_s_macro,p4,block_v2_g}.sv \
  "$p16"/{block_p16,pj_feed_hold,pj_mem_port,pj_sram_client}.sv "$p/block_v2/block_v2_m.sv" \
  "$p/block_v1/transaction6k.sv" "$bank" > compile.log 2>&1
for mode in normal stalled reset; do
  stall=0 reset_trial=0
  if [[ $mode != normal ]]; then stall=1; fi
  if [[ $mode == reset ]]; then reset_trial=1; fi
  ./obj/Vtb_p16_pair "+MOTHER=images/mother.mem" "+MWORDS=${words[0]}" \
    "+LOCAL0=images/local0.mem" "+WORDS0=${words[1]}" \
    "+LOCAL1=images/local1.mem" "+WORDS1=${words[2]}" \
    "+STALL=$stall" "+RESET_TRIAL=$reset_trial" | tee "$mode.log"
done
sha256sum images/*.mem normal.log stalled.log reset.log tool.txt inputs.log > result.sha256
