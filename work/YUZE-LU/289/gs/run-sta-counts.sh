#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
role=${1:?}; mode=${2:?}; attempt=${3:-v3}
candidate=$root/candidate-$role-$mode-$attempt
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "GS_ROLE=$role,GS_CANDIDATE=$candidate,OMP_NUM_THREADS=8" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/sta-counts-v2.tcl" > "$candidate/independent-sta-worker.log" 2>&1
