#!/bin/bash
#SBATCH -J yzl-289-Ccachetruth
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH --time=00:20:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-final-sizes-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$r/run-c-final-sizes-v1.sh"
