#!/bin/bash
set -euo pipefail
mode=${1:?h20/h50/h80}
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
c=$root/candidate-S-hold08-v3
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$c" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 "$1/f-eco-v3.py" "$2" "$3"' bash "$root" "$c" "$mode" > "$c/f-eco-${mode}-v3-worker.log" 2>&1
