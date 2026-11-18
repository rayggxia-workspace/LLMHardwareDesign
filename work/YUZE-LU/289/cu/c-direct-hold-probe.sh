#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
r=$root/runs/C-v16-genericadder-cached
out=$root/studies/C-direct-hold-v1
mkdir -p "$out";cd "$out"
test ! -e STARTED || exit 2
date -Is > STARTED
libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$r/config.mk" | tail -1)
for script in c-cached-closure-edit c-direct-setup c-direct-delay-plan;do
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "CU_LIBS=$libs,CU_SEED=$r/flow/results/nangate45/c-overlay-current/base,CU_RESULTS=$out,RESULTS_DIR=$out,CU_RESET_N=32,CU_TRACE_X=16,CU_HOLD_MARGIN=0.01,CU_CELL_DELAY=0.025" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/$script.tcl" > "$script.log" 2>&1
done