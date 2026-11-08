#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
base=${NATIVE_STAGE:?pinned five-type input staging}
bank=${SRAM_BANK:?qualified bank model}
verilator=${VERILATOR:-verilator}
kind=${KIND:?0 U,1 F,2 C,3 P,4 J}
layout=${LAYOUT:?0 five-type homogeneous or1 recovery directed}
out=${1:?result directory}
mkdir -p "$out";out=$(cd "$out" && pwd)
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
types=(U F C P J);family=five
if [[ $layout == 1 ]]; then family=recovery; fi
target="$family/${types[$kind]}"
ctrl="$repo/project/control_rtl_min_v0_1";boot="$repo/project/control_boot_v1"
five="$repo/project/control_five_boot_v1";recovery="$repo/project/control_recovery_boot_v1"
native="$base/native-p/staged/native";pj="$base/native-p/staged/pj/project/rtl"
if [[ $kind == 1 || $kind == 2 || $kind == 4 ]]; then native="$base/cfj/staged/native";pj="$base/cfj/staged/pj/project/rtl"; fi
pu="$base/native-p/design";cfj="$base/cfj/design"
python3 -B "$repo/project/control_task_compiler_v1/generate.py" --target "$target" "$out/inputs" > "$out/generate.log"
"$verilator" --version > "$out/tools.txt"
backends=(0 1);variants=(0 1 2);seeds=(1:143 2:143 2:144)
if [[ ${SMOKE:-0} == 1 ]]; then backends=(1);variants=(0);seeds=(1:143);fi
extra=()
if [[ $kind != 0 ]]; then extra+=("$base/native-p/staged/native/local_s_p.sv");fi
for backend in "${backends[@]}"; do
 dst="$out/backend-$backend";mkdir -p "$dst"
 "$verilator" --binary --timing --assert --timescale-override 1ns/1ps --x-initial unique --x-assign unique -Wno-fatal \
  --top-module tb_compiled_native "-GKIND=$kind" "-GLAYOUT=$layout" "-GPM_USE_SRAM=$backend" -j "${BUILD_JOBS:-4}" --Mdir "$dst/obj" \
  -I"$ctrl" -I"$native" "$ctrl"/{mc_min_controller,lc_min_controller,two_local_link}.sv \
  "$boot"/{control_pm,control_boot_manager}.sv \
  "$five"/{native_result_fifo,native_control_endpoint,five_control_top,typed_boot_front,five_boot_top}.sv \
  "$repo/project/control_hetero_boot_v1/hetero_boot_front.sv" \
  "$recovery"/{draining_transport,draining_word_link,recovery_endpoint,recovery_control_top,recovery_engine,recovery_supervisor,recovery_boot_top}.sv \
  "$repo/project/control_task_compiler_v1/tb_compiled_native.sv" \
  "$repo/project/control_native_v1/"{pj_native_service,ucf_native_service}.sv \
  "$pu"/{pu_p_group,pu_p_store_control,pu_u_group,pu_compact_e_service}.sv \
  "$cfj"/{block_cfj_cf,block_cfj_j,cfj_s_port,cfj_e_port}.sv \
  "$native"/*.sv "${extra[@]}" "$bank" "$pj"/block_pj_v1/*.sv "$pj/block_v2/block_v2_m.sv" "$pj/block_v1/transaction6k.sv" \
  > "$dst/compile.log" 2>&1
 for variant in "${variants[@]}"; do
  for seed in "${seeds[@]}"; do
   log="$dst/case-$variant-init-${seed//:/-}.log"
   "$dst/obj/Vtb_compiled_native" "+ROOT=$out/inputs/$variant" "+CASE=$variant" "+STALL=$variant" "+verilator+rand+reset+${seed%:*}" "+verilator+seed+${seed#*:}" > "$log" 2>&1
   grep '^PASS compiled-native' "$log"
  done
 done
done
find "$out" -type f \( -name '*.mem' -o -name '*.log' -o -name '*.json' -o -name '*.txt' -o -name '*.bin' \) -not -path '*/obj/*' -print0 | sort -z | xargs -0 sha256sum > "$out/result.sha256"
