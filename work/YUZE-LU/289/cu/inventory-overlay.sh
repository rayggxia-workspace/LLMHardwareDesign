#!/bin/bash
set -euo pipefail
block=$1
case "$block" in C|U) ;; *) exit 2;; esac
lower=$(printf '%s' "$block" | tr '[:upper:]' '[:lower:]')
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
src=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/$block/flow/results/nangate45/$lower-overlay-current/base/4_cts.odb
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "INPUT_ODB=$src,INVENTORY_TSV=$root/$lower-overlay-inventory.tsv" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/inventory.tcl"