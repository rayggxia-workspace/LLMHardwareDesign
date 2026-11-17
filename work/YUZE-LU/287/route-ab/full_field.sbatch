#!/bin/bash
#SBATCH --job-name=yzl-ab-allnets
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --time=02:00:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue287-route-ab-all-20261117
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 full_field.py
