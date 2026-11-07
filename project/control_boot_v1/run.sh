#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?result directory}
base=${NATIVE_STAGE:?locked native-p staging directory}
bank=${SRAM_BANK:?qualified OpenRAM model}
verilator=${VERILATOR:-verilator}
mkdir -p "$out"
out=$(cd "$out" && pwd)
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
ctrl="$repo/project/control_rtl_min_v0_1"
top="$repo/project/control_dual_p_top_v1"
boot="$repo/project/control_boot_v1"
native="$base/staged/native"
pj="$base/staged/pj/project/rtl"
python3 -B "$boot/images.py" "$out/images" > "$out/image.args"
mapfile -t args < "$out/image.args"
"$verilator" --version > "$out/tools.txt"
for backend in 0 1; do
  dst="$out/backend-$backend"
  mkdir -p "$dst"
  "$verilator" --binary --timing --assert --timescale-override 1ns/1ps --x-initial unique --x-assign unique -Wno-fatal \
    --top-module tb_control_boot "-GPM_USE_SRAM=$backend" -j "${BUILD_JOBS:-4}" --Mdir "$dst/obj" \
    -I"$ctrl" -I"$native" "$ctrl"/{lc_min_controller,mc_min_controller,two_local_link}.sv \
    "$top"/{dual_p_control_top,p_control_endpoint,p_word_link}.sv \
    "$boot"/{control_pm,control_boot_manager,control_boot_top,tb_control_boot}.sv \
    "$repo/project/control_native_v1/"{pj_native_service,ucf_native_service,stored_link}.sv \
    "$repo/project/control_r4_v0_1/p_stored_ack_guard.sv" \
    "$base/design/"{pu_p_group,pu_p_store_control}.sv "$native"/*.sv "$bank" \
    "$pj"/block_pj_v1/*.sv "$pj/block_v2/block_v2_m.sv" "$pj/block_v1/transaction6k.sv" \
    > "$dst/compile.log" 2>&1
  for mode in 0 1 2 3 4 5; do
    for seed in 1:143 2:143 2:144; do
      log="$dst/mode-$mode-init-${seed//:/-}.log"
      "$dst/obj/Vtb_control_boot" "+MODE=$mode" "${args[@]}" "+verilator+rand+reset+${seed%:*}" "+verilator+seed+${seed#*:}" > "$log" 2>&1
      grep '^PASS control-boot' "$log"
    done
  done
done
find "$out" -type f \( -name '*.mem' -o -name '*.log' -o -name '*.json' -o -name '*.txt' \) -not -path '*/obj/*' -print0 | sort -z | xargs -0 sha256sum > "$out/result.sha256"
