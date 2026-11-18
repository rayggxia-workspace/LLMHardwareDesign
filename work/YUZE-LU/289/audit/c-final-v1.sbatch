#!/bin/bash
#SBATCH -J yzl-C-final-lec
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
set -euo pipefail
test "$#" = 2
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
test ! -e "$2"
mkdir "$2"
cp "$1" "$2/source-manifest.json"
cp "$root/audit/c-final-v1.py" "$root/audit/c-formal.py" "$root/audit/c-control-packed-v3.py" "$root/audit/c-liberty-truth.py" "$2/"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$2" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 c-final-v1.py "$1"' _ "$2"
