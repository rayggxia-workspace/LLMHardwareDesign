#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
r=$root/runs/C-v18-donly-m0.04-d0.025
mkdir -p "$r/remaining-cts"
libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$r/config.mk" | tail -1)
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "CU_LIBS=$libs,CU_SEED=$r/flow/results/nangate45/c-overlay-current/base,CU_OUT=$r/remaining-cts" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/c-remaining-cts.tcl"