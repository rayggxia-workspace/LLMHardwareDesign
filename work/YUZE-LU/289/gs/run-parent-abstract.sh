#!/bin/bash
set -euo pipefail
role=${1:?role};mode=${2:?mode};attempt=${3:-v3}
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
c=$root/candidate-${role}-${mode}-${attempt}
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$c" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 "$1/parent-abstract.py" "$2" "$3"' bash "$root" "$role" "$c" > "$c/parent-abstract-v3-worker.log" 2>&1
