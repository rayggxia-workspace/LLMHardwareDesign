#!/bin/bash
#SBATCH --job-name=yzl-ab-audit
#SBATCH --partition=debug,c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:25:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue287-route-ab-20261117
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 audit.py
