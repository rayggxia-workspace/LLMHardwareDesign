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
run=$root/runs/$block-v10-ctsdelay-newG-$mode-seed$seed
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
printf '\nexport CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none -balance_levels -root_buf BUF_X32 -buf_list {BUF_X8 BUF_X16 BUF_X32}\n' >> config.mk
printf '\nexport SKIP_CTS_REPAIR_TIMING = 0\n' >> config.mk
res=$run/flow/results/nangate45/$lower-overlay-current/base
mkdir -p "$res"
cp "$src/flow/results/nangate45/$lower-overlay-current/base/3_place.odb" "$src/flow/results/nangate45/$lower-overlay-current/base/3_place.sdc" "$res/"
sha256sum "$res/3_place.odb" "$res/3_place.sdc" "$src/config.mk" "$src/input.sdc" > source-sha256.txt
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
printf '\n' >> "$res/3_place.sdc"
cat "$run/io-contract.sdc" >> "$res/3_place.sdc"
printf '\nexport SDC_FILE = %s/3_place.sdc\n' "$res" >> config.mk
export CU_OUTPUT_PORTS=$root/$block-outputs.txt
source /OpenROAD-flow-scripts/env.sh
bash "$root/rebase-g-v9.sh" "$run" "$src/flow/results/nangate45/c-overlay-current/base/3_place.odb" "$res/3_place.odb"
make_args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES="$cores")
python3 "$root/manifest.py" "$run"
# Rebuild CTS accounting for the existing Liberty macro clock insertion models.
test "$block" = C || exit 2
export CU_SNAPSHOT_ODB=$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb
export CU_SNAPSHOT_OUT=$run/geometry-reference.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-reference.log 2>&1
export CU_SNAPSHOT_ODB=$res/3_place.odb
export CU_SNAPSHOT_OUT=$run/geometry-prects.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-prects.log 2>&1
cmp "$run/geometry-reference.tsv" "$run/geometry-prects.tsv"
make "${make_args[@]}" do-cts > cts.log 2>&1
export CU_SNAPSHOT_ODB=$res/4_cts.odb
export CU_SNAPSHOT_OUT=$run/geometry-postcts.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-postcts.log 2>&1
cmp "$run/geometry-reference.tsv" "$run/geometry-postcts.tsv"
make "${make_args[@]}" do-grt > grt.log 2>&1
make "${make_args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${make_args[@]}" do-finish > finish.log 2>&1
make "${make_args[@]}" do-gds > gds.log 2>&1
date -Is > BACKEND_ARTIFACTS_CREATED_NOT_SIGNED_OFF

s1=0; bash "$root/signoff-v4.sh" "$run" || s1=$?
s2=0; bash "$root/lec-v3.sh" "$run" "$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb" || s2=$?
printf 'signoff=%s lec=%s\n' "$s1" "$s2" > validation-exit-status.txt
test "$s1" -eq 0 -a "$s2" -eq 0
