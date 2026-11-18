#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
for role in G S; do
 if [[ $role == G ]]; then
  odb=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/flow/results/nangate45/c-overlay-current/base/4_cts.odb
  master=block_v2_g
 else
  odb=/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01/flow/results/nangate45/f-native-frame/base/6_final.odb
  master=local_s_base
 fi
 srun --jobid=119542 --exclusive -n1 -c2 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env AUDIT_PARENT_ODB="$odb",AUDIT_MASTER="$master",AUDIT_MASTER_OUT="$root/$role-parent-master.tsv" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1/export_master.tcl"' bash "$root" > "$root/$role-parent-export.log" 2>&1
 done
