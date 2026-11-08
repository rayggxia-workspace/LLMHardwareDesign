#!/usr/bin/env bash
#SBATCH --job-name=yzl-identity-check
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen,ROUTER_IDENTITY_CONTROLS="$task/controls.json" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif klayout -b -r project/experiments/upper_router/native_identity_controls.py
