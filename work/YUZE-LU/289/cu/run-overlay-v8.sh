#!/bin/bash
# Called only inside allocated compute node + ORFS container.
set -euo pipefail
block=$1
seed=${2:-0}
cores=${3:-8}
mode=${4:-x8}
case "$mode" in baseline|x8) ;; *) exit 2;; esac
case "$block" in C|U) ;; *) exit 2;; esac
case "$seed" in 0|1|2) ;; *) exit 2;; esac
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
src=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/$block
lower=$(printf '%s' "$block" | tr '[:upper:]' '[:lower:]')
run=$root/runs/$block-v8-newG-fastroute-$mode-seed$seed
mkdir -p "$run"
cd "$run"
test ! -e STARTED || { echo 'Refusing to overwrite a candidate'; exit 2; }
date -Is > STARTED
cp "$src/config.mk" config.mk
printf '\nexport PRE_GLOBAL_ROUTE_TCL = %s/pre-global-v3.tcl\nexport GRT_SEED = %s\nexport OR_SEED = %s\n' "$root" "$seed" "$seed" >> config.mk
printf '\nexport POST_GLOBAL_ROUTE_TCL = %s/post-global-v5.tcl\n' "$root" >> config.mk
if [ "$block" = C ]; then
 printf '\nexport GLOBAL_ROUTE_ARGS = -verbose -congestion_report_iter_step 5\nexport GLOBAL_ROUTE_USE_CUGR = 0\n' >> config.mk
fi
res=$run/flow/results/nangate45/$lower-overlay-current/base
mkdir -p "$res"
cp "$src/flow/results/nangate45/$lower-overlay-current/base/4_cts.odb" "$src/flow/results/nangate45/$lower-overlay-current/base/4_cts.sdc" "$res/"
sha256sum "$res/4_cts.odb" "$res/4_cts.sdc" "$src/config.mk" "$src/input.sdc" > source-sha256.txt
# Explicit new IO contract, appended to original CTS clock/uncertainty constraints.
cp "$root/provisional-io.sdc" "$run/io-contract.sdc"
python3 - "$root/$block-outputs.txt" "$run/io-contract.sdc" <<'PY'
from pathlib import Path
import sys
ports=Path(sys.argv[1]).read_text().splitlines()
with Path(sys.argv[2]).open('a') as f:
 f.write('\n# Selected route outputs: declared 50 fF standalone acceptance environment.\n')
 for port in ports:
  f.write('set_load 50 [get_ports {'+port+'}]\n')
PY
printf '\n' >> "$res/4_cts.sdc"
cat "$run/io-contract.sdc" >> "$res/4_cts.sdc"
printf '\nexport SDC_FILE = %s/4_cts.sdc\n' "$res" >> config.mk
export CU_OUTPUT_PORTS=$root/$block-outputs.txt
source /OpenROAD-flow-scripts/env.sh
test "$block" = C || { echo 'v6 is the C parent integration flow'; exit 2; }
bash "$root/rebase-g-v8.sh" "$run" "$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb" "$res/4_cts.odb"
make_args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES="$cores")
python3 "$root/manifest.py" "$run"
make "${make_args[@]}" do-grt > grt.log 2>&1
make "${make_args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${make_args[@]}" do-finish > finish.log 2>&1
make "${make_args[@]}" do-gds > gds.log 2>&1
date -Is > BACKEND_ARTIFACTS_CREATED_NOT_SIGNED_OFF

s1=0; bash "$root/signoff-v3.sh" "$run" || s1=$?
s2=0; bash "$root/lec-v2.sh" "$run" || s2=$?
printf 'signoff=%s lec=%s\n' "$s1" "$s2" > validation-exit-status.txt
test "$s1" -eq 0 -a "$s2" -eq 0
