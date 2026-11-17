#!/bin/bash
set -euo pipefail
mode=${1:?mode};attempt=${2:-v3}
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
candidate=$root/candidate-S-${mode}-${attempt}
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$candidate" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 "$1/f-parent.py" "$2"' bash "$root" "$candidate" > "$candidate/f-parent-worker.log" 2>&1
