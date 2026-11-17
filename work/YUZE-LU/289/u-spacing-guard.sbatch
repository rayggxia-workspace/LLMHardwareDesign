#!/bin/bash
#SBATCH -J yzl-289-U-guard
#SBATCH -p c64,c96
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --time=06:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-guard-%j.log
set -euo pipefail
srun /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-spacing-guard.sh
