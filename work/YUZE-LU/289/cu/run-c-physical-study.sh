#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
mode=$1;value=$2
out=$root/studies/C-${mode}-v1-${value}
mkdir -p "$out";cd "$out"
test ! -e STARTED || exit 2
date -Is > STARTED
cfg=$root/runs/C-v18-donly-m0.04-d0.025/config.mk
libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$cfg" | tail -1)
if [ "$mode" = capacity ];then
 source=$root/runs/C-v18-donly-m0.04-d0.025/flow/results/nangate45/c-overlay-current/base
 odb=$source/4_cts.odb;sdc=$source/4_cts.sdc
else
 source=$root/runs/C-v16-genericadder-cached/flow/results/nangate45/c-overlay-current/base
 odb=$source/3_place.odb;sdc=$source/3_place.sdc
fi
test -s "$odb";test -s "$sdc"
sha256sum "$odb" "$sdc" "$root/c-$mode-study.tcl" > inputs.sha256
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "CU_LIBS=$libs,CU_SOURCE_ODB=$odb,CU_SOURCE_SDC=$sdc,CU_VALUE=$value,RESULTS_DIR=$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/c-$mode-study.tcl"