set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
python3 source/project/experiments/s_sram/inspect_final.py --physical /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/physical-011/implementation --out "$PWD/audit" > audit-launch.log 2>&1 &
audit_pid=$!
OMP_NUM_THREADS=4 python3 source/project/experiments/s_sram/run_actual.py --physical /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/physical-011/implementation --generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-003/generation --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --out "$PWD/function" > function-launch.log 2>&1 &
function_pid=$!
set +e
wait "$audit_pid"; audit_rc=$?
wait "$function_pid"; function_rc=$?
printf 'audit=%s function=%s\n' "$audit_rc" "$function_rc"
test "$audit_rc" -eq 0 && test "$function_rc" -eq 0
