#!/bin/bash
#SBATCH -J yzl-C-finalread
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 00:20:00
set -euo pipefail
test "$#" = 3
export C_FINAL_ODB=$1
out=$2
expected=$3
test ! -e "$out"
echo "$expected  $C_FINAL_ODB" | sha256sum -c -
mkdir "$out"
cp /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/c-final-readonly-v2.tcl "$out/check.tcl"
sha256sum "$C_FINAL_ODB" "$out/check.tcl" > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit check.tcl > check.log 2>&1'
sha256sum -c "$out/inputs-before.sha256" > "$out/inputs-unchanged.log"
# Native marker counts must be reviewed against the relevant exact baseline;
# this helper does not label a nonzero native report as a physical pass.
sha256sum "$out/fresh-from-odb.v" "$out/fresh-from-odb.def" "$out/fresh-native.rpt" "$out/check.log" > "$out/outputs.sha256"
