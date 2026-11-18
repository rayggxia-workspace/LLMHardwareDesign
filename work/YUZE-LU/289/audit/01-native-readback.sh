#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
c=$root/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4-repair3
mkdir -p "$root/audit/native-readback"
for label in original prepatch; do
 odb="$c/candidate.odb"
 [[ $label != original ]] || odb=/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01/flow/results/nangate45/f-native-frame/base/6_final.odb
 printf 'read_db {%s}\ndrt::check_drc_cmd {%s/audit/native-readback/%s.rpt} 0 0 0 0 independent_readback\n' "$odb" "$root" "$label" > "$root/audit/native-readback/$label.tcl"
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1"' bash "$root/audit/native-readback/$label.tcl" > "$root/audit/native-readback/$label.log" 2>&1
done
