#!/usr/bin/env bash
set -euo pipefail
base=${1:?staged campaign directory}
out=${2:?result directory}
bank=${SRAM_BANK:?qualified SRAM bank model}
verilator=${VERILATOR:-verilator}
jobs=${BUILD_JOBS:-4}
mkdir -p "$out"
out=$(cd "$out" && pwd)
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
"$verilator" --version > "$out/tool.txt"
python3 --version >> "$out/tool.txt"

run_bundle() {
  local bundle=$1 kind=$2 name=$3
  local ctrl="$bundle/staged/project/control_rtl_min_v0_1"
  local native="$bundle/staged/native" pj="$bundle/staged/pj/project/rtl"
  local dst="$out/$name"
  local initial_flags=()
  if [[ ${THREE_INITIAL_STATES:-0} == 1 ]]; then initial_flags+=(--x-initial unique --x-assign unique); fi
  mkdir -p "$dst"
  "$verilator" --binary --timing --assert --timescale-override 1ns/1ps \
    -Wno-fatal --top-module tb_native_pair "-GSINGLE_KIND=$kind" "${initial_flags[@]}" \
    -j "$jobs" --Mdir "$dst/obj" -I"$ctrl" -I"$native" -I"$bundle/design" \
    "$native/native_r.vlt" "$ctrl"/{lc_min_controller,mc_min_controller,tb_network_pm,two_local_link}.sv \
    "$bundle"/design/*.sv "$native"/*.sv "$bank" "$pj"/block_pj_v1/*.sv \
    "$pj/block_v2/block_v2_m.sv" "$pj/block_v1/transaction6k.sv" > "$dst/compile.log" 2>&1
  local cases=("normal 0 0 0")
  if [[ $kind == -1 ]]; then
    cases+=("stalled 1 0 0" "reset 1 0 1")
    if [[ $name != duplex ]]; then cases+=("fault 0 1 0" "stalled-fault 1 1 0"); fi
  fi
  for item in "${cases[@]}"; do
    local mode stall fault reset
    read -r mode stall fault reset <<< "$item"
    local path="$dst/$mode" flags=()
    [[ $fault == 0 ]] || flags+=(--fault)
    python3 "$bundle/design/images.py" "$bundle/staged" "$path" --kind "$kind" "${flags[@]}" > "$path.words"
    local words=()
    mapfile -t words < "$path.words"
    local seeds=(default)
    [[ ${THREE_INITIAL_STATES:-0} == 1 ]] && seeds=(1:143 2:143 2:144)
    for seed in "${seeds[@]}"; do
      local init=() logfile="$path.log"
      if [[ $seed != default ]]; then
        init=("+verilator+rand+reset+${seed%:*}" "+verilator+seed+${seed#*:}")
        logfile="$path-seed-${seed//:/-}.log"
      fi
    "$dst/obj/Vtb_native_pair" "+MOTHER=$path/mother.mem" "+MWORDS=${words[0]}" \
      "+LOCAL0=$path/local0.mem" "+WORDS0=${words[1]}" \
      "+LOCAL1=$path/local1.mem" "+WORDS1=${words[2]}" \
      "+STALL=$stall" "+FAULT=$fault" "+RESET_TRIAL=$reset" "${init[@]}" > "$logfile" 2>&1
    grep "^PASS native" "$logfile"
    done
  done
}
case "${CAMPAIGN:-all}" in
  p) run_bundle "$base/native-p" 3 native-p ;;
  u) run_bundle "$base/native-u" -1 native-u ;;
  ue) run_bundle "$base/native-u-e" -1 native-u-e ;;
  cfj) run_bundle "$base/cfj" -1 cfj-pair; run_bundle "$base/cfj" 1 cfj-f; run_bundle "$base/cfj" 2 cfj-c; run_bundle "$base/cfj" 4 cfj-j ;;
  duplex) run_bundle "$base/duplex" -1 duplex ;;
  *) echo 'Set CAMPAIGN to p, u, cfj, or duplex' >&2; exit 2 ;;
esac
find "$out" -type f \( -name '*.mem' -o -name '*.log' -o -name '*.txt' \) -not -path '*/obj/*' -print0 | sort -z | xargs -0 sha256sum > "$out/result.sha256"
