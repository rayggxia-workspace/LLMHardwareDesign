#!/usr/bin/env bash
set -euo pipefail
base=${1:?staged CFJ bundle}
bench=${2:?pinned native exchange testbench}
out=${3:?result directory}
bank=${SRAM_BANK:?qualified SRAM bank model}
verilator=${VERILATOR:-verilator}
mkdir -p "$out"
out=$(cd "$out" && pwd)
ctrl="$base/staged/project/control_rtl_min_v0_1"
native="$base/staged/native"
pj="$base/staged/pj/project/rtl"
sources=("$base"/design/*.sv)
if [[ -n ${MUTANT_CF:-} ]]; then
  filtered=()
  for source in "${sources[@]}"; do
    [[ $source == */block_cfj_cf.sv ]] || filtered+=("$source")
  done
  sources=("${filtered[@]}" "$MUTANT_CF")
fi
"$verilator" --binary --timing --assert --timescale-override 1ns/1ps -Wno-fatal \
  --top-module tb_cfj_exchange -j "${BUILD_JOBS:-4}" --Mdir "$out/obj" \
  -I"$native" -I"$ctrl" -I"$base/design" "$native/native_r.vlt" \
  "$bench" "${sources[@]}" "$native"/*.sv "$bank" \
  "$pj"/block_pj_v1/*.sv "$pj/block_v2/block_v2_m.sv" "$pj/block_v1/transaction6k.sv" > "$out/compile.log" 2>&1
"$out/obj/Vtb_cfj_exchange" > "$out/run.log" 2>&1
grep '^PASS' "$out/run.log"
(cd "$out" && sha256sum compile.log run.log > result.sha256)
