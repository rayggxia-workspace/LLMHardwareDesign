#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
r=$root/runs/C-v17-closure-r24-x16
out=$root/c-donly-probe
mkdir -p "$out";cd "$out"
libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$r/config.mk" | tail -1)
sing=/public/software/singularity-ce-4.3.4/bin/singularity
img=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
for script in c-unshare-hold c-plan-d-delay c-apply-d-delay;do
 "$sing" exec --cleanenv --bind /public/home/yuzelu --env "CU_LIBS=$libs,CU_SEED=$r/flow/results/nangate45/c-overlay-current/base,CU_HOLD_MARGIN=0.04,CU_CELL_DELAY=0.025" "$img" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/$script.tcl" > "$script.log" 2>&1
done