#!/bin/bash
#SBATCH -J yzl-289-U-wiremap
#SBATCH -p debug
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 2
#SBATCH --time=00:20:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-wire-%j.log
set -euo pipefail
srun /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-map-markers.py
