#!/bin/bash
set -euo pipefail
role=${1:?}; mode=${2:?}; attempt=${3:-v3}
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
candidate=$root/candidate-${role}-${mode}-${attempt}
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 "$1/formal.py" "$2" "$3"' bash "$root" "$role" "$candidate" > "$candidate/formal-worker.log" 2>&1
