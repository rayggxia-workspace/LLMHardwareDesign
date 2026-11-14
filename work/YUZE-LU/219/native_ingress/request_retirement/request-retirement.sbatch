#!/usr/bin/env bash
set -euo pipefail
cd "$1"
rtl=$2
request=$3
handoff=$4
kv=$5
vocab=$6
locals=$7
framework=$8
router=$9
out="$PWD/run-$SLURM_JOB_ID"
mkdir -p "$out"
export PYTHONPATH="$(dirname "$PWD"):$framework:$router"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
"$py" -B request_phase_bindings.py "$request" "$handoff" "$kv" "$vocab" "$locals" "$out/bindings"
for test in test_native_request_index_gate test_native_phase_page_sequence; do
    bash "$tool" "$vlt" --binary --timing --assert -Wno-fatal --top-module "$test" \
      -j "$SLURM_CPUS_PER_TASK" --Mdir "$out/$test" \
      native_request_index_gate.sv test_native_request_index_gate.sv \
      "$rtl"/rtl/block_local_native/native_retired_token_index.sv \
      "$rtl"/rtl/mother_control_native/native_{request_sequence,token_sequence,phase_page_sequence}.sv \
      "$rtl"/experiments/mother_control_native/test_native_phase_page_sequence.sv > "$out/$test.build.log" 2>&1
    bash "$tool" "$out/$test/V$test" | tee "$out/$test.log"
done
sha256sum "$out"/bindings/phase-bindings.* "$out"/test_native*.log
