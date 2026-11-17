#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:-}" || exit 2
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/runs/U-v6-ctsdelay-x8-seed0
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "INPUT_ODB=$run/flow/results/nangate45/u-overlay-current/base/4_cts.odb,INVENTORY_TSV=$run/cts-hold-cells.tsv" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/hold-inventory.tcl"
