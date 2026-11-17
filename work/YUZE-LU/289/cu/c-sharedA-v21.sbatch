#!/bin/bash
#SBATCH -J yzl-289-C-shareA
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH --time=16:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-shareA-%j.log
set -euo pipefail
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/run-c-sharedA-v21.sh cached-shared-A