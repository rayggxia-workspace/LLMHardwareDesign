#!/bin/bash
#SBATCH --job-name=yzl-C-S-M9-gds
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-S-M9-gds-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif klayout -b -r /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/c-v27-s-m9-gds.py
