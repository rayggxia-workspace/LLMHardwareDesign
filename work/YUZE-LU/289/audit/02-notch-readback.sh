#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
c=$root/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4-repair3-notch
printf 'read_db {%s/candidate.odb}\ndrt::check_drc_cmd {%s/audit/native-readback/notch.rpt} 0 0 0 0 independent_readback\n' "$c" "$root" > "$root/audit/native-readback/notch.tcl"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1"' bash "$root/audit/native-readback/notch.tcl" > "$root/audit/native-readback/notch.log" 2>&1
