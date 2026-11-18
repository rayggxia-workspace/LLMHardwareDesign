#!/bin/bash
set -euo pipefail
role=${1:?G/S}; mode=${2:?mode}; attempt=${3:-v3}
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
candidate=$root/candidate-${role}-${mode}-${attempt}
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$candidate" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 "$1/qualify-v2.py" "$2" "$3"' bash "$root" "$role" "$candidate" > "$candidate/qualification-v2-worker.log" 2>&1
