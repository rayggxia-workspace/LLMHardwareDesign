#!/bin/bash
set -euo pipefail
kind=$1
case "$kind" in distributed|distributed-parallel) ;; *) exit 2;; esac
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
src=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C
old=$root/runs/C-v11-resynth-$kind
run=$root/runs/C-v12-resynth-macropdn-$kind
oldres=$old/flow/results/nangate45/c-overlay-current/base
test -s "$oldres/1_synth.odb"
test -s "$oldres/1_synth.sdc"
grep -q 'make: Leaving directory' "$old/synth.log"
mkdir -p "$run"
cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$old/loader-candidate.sv" "$old/input.sdc" .
sed "s@$old@$run@g" "$old/config.mk" > config.mk
printf '\nexport PDN_TCL = %s/c-macro-pdn.tcl\nexport POST_PDN_TCL = %s/c-post-pdn.tcl\n' "$root" "$root" >> config.mk
res=$run/flow/results/nangate45/c-overlay-current/base
mkdir -p "$res"
cp "$oldres"/1* "$res/"
sha256sum "$oldres/1_synth.odb" "$res/1_synth.odb" loader-candidate.sv "$root/c-macro-pdn.tcl" "$root/c-post-pdn.tcl" > transition-source-sha256.txt
source /OpenROAD-flow-scripts/env.sh
export CU_OUTPUT_PORTS=$root/C-outputs.txt
python3 "$root/manifest.py" "$run"
args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8)
make "${args[@]}" floorplan > floorplan.log 2>&1
make "${args[@]}" place > place.log 2>&1
export CU_SNAPSHOT_ODB=$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb CU_SNAPSHOT_OUT=$run/geometry-reference.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-reference.log 2>&1
export CU_SNAPSHOT_ODB=$res/3_place.odb CU_SNAPSHOT_OUT=$run/geometry-prects.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-prects.log 2>&1
python3 "$root/compare-signal-geometry.py" geometry-reference.tsv geometry-prects.tsv geometry-prects-contract.json
make "${args[@]}" cts > cts.log 2>&1
export CU_SNAPSHOT_ODB=$res/4_cts.odb CU_SNAPSHOT_OUT=$run/geometry-postcts.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-postcts.log 2>&1
python3 "$root/compare-signal-geometry.py" geometry-reference.tsv geometry-postcts.tsv geometry-postcts-contract.json
make "${args[@]}" do-grt > grt.log 2>&1
make "${args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${args[@]}" do-finish > finish.log 2>&1
make "${args[@]}" do-gds > gds.log 2>&1
bash "$root/signoff-v4.sh" "$run"
bash "$root/lec-v3.sh" "$run" "$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb"
