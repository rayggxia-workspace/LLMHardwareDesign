#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
old=$root/runs/U-v6-ctsdelay-x8-seed0
run=$root/runs/U-v7-macropdn-x8-seed0
mkdir -p "$run"
test ! -e "$run/STARTED" || exit 2
date -Is > "$run/STARTED"
python3 "$root/verify-pdn-boundary.py"
cp "$old/config.mk" "$run/config.mk"
res=$run/flow/results/nangate45/u-overlay-current/base
mkdir -p "$res"
cp "$root/u-macro-pdn-v1/pdn-connected.odb" "$res/4_cts.odb"
cp "$old/flow/results/nangate45/u-overlay-current/base/4_cts.sdc" "$res/4_cts.sdc"
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$run" --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$PWD
python3 "$root/manifest.py" "$run"
args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8)
make "${args[@]}" do-grt > grt.log 2>&1
make "${args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${args[@]}" do-finish > finish.log 2>&1
make "${args[@]}" do-gds > gds.log 2>&1
a=0; bash "$root/signoff-v4.sh" "$run" || a=$?
b=0; bash "$root/lec-v3.sh" "$run" /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/U/flow/results/nangate45/u-overlay-current/base/4_cts.odb || b=$?
test "$a" -eq 0 -a "$b" -eq 0
'
