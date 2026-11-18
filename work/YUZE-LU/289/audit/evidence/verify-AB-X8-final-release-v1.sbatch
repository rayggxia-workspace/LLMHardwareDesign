#!/bin/bash
#SBATCH --job-name=yzl-X8-releasecheck
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/AB-X8-release-check-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/verify-AB-X8-final-release-v1.py
