#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
base=${NATIVE_STAGE:?frozen input stage};bank=${SRAM_BANK:?qualified bank}
verilator=${VERILATOR:-verilator};coverage_tool=${COVERAGE_TOOL:-$(dirname "$verilator")/verilator_coverage}
kind=${KIND:?0..4};layout=${LAYOUT:?0five or1directed};out=${1:?output}
mkdir -p "$out";out=$(cd "$out" && pwd)
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
types=(U F C P J);family=five;if [[ $layout == 1 ]]; then family=recovery;fi
target="$family/${types[$kind]}";ctrl="$repo/project/control_rtl_min_v0_1";boot="$repo/project/control_boot_v1"
five="$repo/project/control_five_boot_v1";recovery="$repo/project/control_recovery_boot_v1";matrix="$repo/project/control_matrix_v1"
native="$base/native-p/staged/native";pj="$base/native-p/staged/pj/project/rtl"
if [[ $kind == 1 || $kind == 2 || $kind == 4 ]]; then native="$base/cfj/staged/native";pj="$base/cfj/staged/pj/project/rtl";fi
pu="$base/native-p/design";cfj="$base/cfj/design"
python3 -B "$matrix/instrument.py" --out "$out/bench" > "$out/instrument.log"
python3 -B "$matrix/generate.py" --target "$target" "$out/matrix-inputs" > "$out/generate.log"
if [[ $layout == 0 ]]; then
 python3 -B "$five/images.py" --kind "$kind" "$out/legacy-inputs" > "$out/legacy-generate.log"
 legacy_top=tb_five_boot;legacy_modes=7
else
 python3 -B "$recovery/images.py" --kind "$kind" "$out/legacy-inputs" > "$out/legacy-generate.log"
 legacy_top=tb_recovery_boot;legacy_modes=19
fi
"$verilator" --version > "$out/tools.txt";"$coverage_tool" --version >> "$out/tools.txt"
backends=(0 1);seeds=(1:143 2:143 2:144);suites=(matrix legacy)
if [[ ${SMOKE:-0} == 1 ]];then backends=(1);seeds=(1:143);suites=(matrix);fi
extra=();if [[ $kind != 0 ]]; then extra+=("$base/native-p/staged/native/local_s_p.sv");fi
for backend in "${backends[@]}"; do
 for suite in "${suites[@]}"; do
  top=tb_matrix;if [[ $suite == legacy ]];then top=$legacy_top;fi
  dst="$out/$suite/backend-$backend";mkdir -p "$dst"
  "$verilator" --binary --timing --assert --coverage-line --coverage-user --timescale-override 1ns/1ps --x-initial unique --x-assign unique -Wno-fatal \
   --top-module "$top" "-GKIND=$kind" "-GPM_USE_SRAM=$backend" $([[ $suite == matrix ]] && echo "-GLAYOUT=$layout") \
   -j "${BUILD_JOBS:-4}" --Mdir "$dst/obj" -I"$ctrl" -I"$native" \
   "$ctrl"/{mc_min_controller,lc_min_controller,two_local_link}.sv "$boot"/{control_pm,control_boot_manager}.sv \
   "$five"/{native_result_fifo,native_control_endpoint,five_control_top,typed_boot_front,five_boot_top}.sv \
   "$repo/project/control_hetero_boot_v1/hetero_boot_front.sv" \
   "$recovery"/{draining_transport,draining_word_link,recovery_endpoint,recovery_control_top,recovery_engine,recovery_supervisor,recovery_boot_top}.sv \
   "$out/bench/$top.sv" "$matrix/matrix_probe.sv" \
   "$repo/project/control_native_v1/"{pj_native_service,ucf_native_service}.sv \
   "$pu"/{pu_p_group,pu_p_store_control,pu_u_group,pu_compact_e_service}.sv \
   "$cfj"/{block_cfj_cf,block_cfj_j,cfj_s_port,cfj_e_port}.sv \
   "$native"/*.sv "${extra[@]}" "$bank" "$pj"/block_pj_v1/*.sv "$pj/block_v2/block_v2_m.sv" "$pj/block_v1/transaction6k.sv" \
   > "$dst/compile.log" 2>&1
  if [[ $suite == matrix ]];then
   for case in "$out/matrix-inputs"/*/; do
    name=$(basename "$case")
    for seed in "${seeds[@]}"; do
     stem="$dst/$name-init-${seed//:/-}"
     "$dst/obj/V$top" "+ROOT=$case" +STALL=3 "+verilator+coverage+file+$stem.dat" "+verilator+rand+reset+${seed%:*}" "+verilator+seed+${seed#*:}" > "$stem.log" 2>&1
     grep '^PASS matrix-native' "$stem.log";test -s "$stem.dat"
    done
   done
  else
   for ((mode=0;mode<legacy_modes;mode++));do
    for seed in "${seeds[@]}";do
     stem="$dst/mode-$mode-init-${seed//:/-}"
     "$dst/obj/V$top" "+ROOT=$out/legacy-inputs" "+MODE=$mode" "+verilator+coverage+file+$stem.dat" "+verilator+rand+reset+${seed%:*}" "+verilator+seed+${seed#*:}" > "$stem.log" 2>&1
     grep '^PASS .*\(boot\|recovery\)' "$stem.log";test -s "$stem.dat"
    done
   done
  fi
  "$coverage_tool" --write-info "$dst/coverage.info" "$dst"/*.dat > "$dst/coverage.log" 2>&1
 done
done
find "$out" -type f \( -name '*.mem' -o -name '*.log' -o -name '*.json' -o -name '*.txt' -o -name '*.dat' -o -name '*.info' \) -not -path '*/obj/*' -print0 | sort -z | xargs -0 sha256sum > "$out/result.sha256"
