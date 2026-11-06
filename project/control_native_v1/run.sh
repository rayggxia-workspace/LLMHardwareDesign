#!/usr/bin/env bash
set -euo pipefail
base=$(cd "${1:?bundle directory}" && pwd)
out=${2:?output directory}
kind=${3:--1}
mkdir -p "$out"
cd "$out"
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1
runtime=()
verilator=${VERILATOR:-verilator}
if [[ -n ${SLURM_JOB_ID:-} ]]; then
  runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
  verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
fi
bank=${SRAM_BANK:-/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v}
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
sha256sum "$base"/design/*.sv "$base"/design/*.py "$base"/staged/sources.json > source-sha256.txt
ctrl="$base/staged/project/control_rtl_min_v0_1"
native="$base/staged/native"
pj="$base/staged/pj/project/rtl"
"${runtime[@]}" "$verilator" --version | tee tool.txt
python3 --version | tee -a tool.txt
"${runtime[@]}" "$verilator" --binary --timing --assert --timescale-override 1ns/1ns \
  -Wno-fatal --top-module tb_native_pair "-GSINGLE_KIND=$kind" \
  -j "${SLURM_CPUS_PER_TASK:-4}" --Mdir "$PWD/obj" \
  -I"$ctrl" -I"$native" "$native/native_r.vlt" \
  "$ctrl"/{lc_min_controller,mc_min_controller,tb_network_pm}.sv \
  "$base"/design/*.sv "$native"/*.sv "$bank" \
  "$pj"/block_pj_v1/*.sv "$pj/block_v2/block_v2_m.sv" "$pj/block_v1/transaction6k.sv" \
  > compile.log 2>&1
run_case() {
  local name=$1 stall=$2 fault=$3 reset_trial=$4
  local flags=() words=()
  if [[ $fault == 1 ]]; then flags+=(--fault); fi
  python3 "$base/design/images.py" "$base/staged" "$name" --kind "$kind" "${flags[@]}" > "$name.words"
  mapfile -t words < "$name.words"
  "${runtime[@]}" "./obj/Vtb_native_pair" \
    "+MOTHER=$name/mother.mem" "+MWORDS=${words[0]}" \
    "+LOCAL0=$name/local0.mem" "+WORDS0=${words[1]}" \
    "+LOCAL1=$name/local1.mem" "+WORDS1=${words[2]}" "+STALL=$stall" "+FAULT=$fault" "+RESET_TRIAL=$reset_trial"
}
cases=("normal 0 0 0")
if [[ $kind == -1 ]]; then cases+=("stalled 1 0 0" "fault 0 1 0" "stalled-fault 1 1 0" "reset 1 0 1"); fi
pids=()
for item in "${cases[@]}"; do
  read -r name stall fault reset_trial <<< "$item"
  run_case "$name" "$stall" "$fault" "$reset_trial" > "$name.log" 2>&1 &
  pids+=("$!")
done
result=0
for pid in "${pids[@]}"; do
  wait "$pid" || result=1
done
tail -n 5 ./*.log | tail -n 32
exit "$result"
