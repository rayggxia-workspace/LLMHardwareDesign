#!/bin/bash
#SBATCH --job-name=yzl-289-U-odbapi
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-odbapi-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -python -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/u-odb-probe.py'
