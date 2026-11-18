#!/bin/bash
#SBATCH --job-name=yzl-289-C-review
#SBATCH --partition=debug,c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:20:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/root-C43-review-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 "$root/audit/root-C43-disposition-verify-v2.py"
