#!/bin/bash
#SBATCH -J yzl-289-U-upper
#SBATCH -p c64,c96
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --time=02:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-upper-%j.log
set -euo pipefail
srun /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-upper-diagnostic.sh
