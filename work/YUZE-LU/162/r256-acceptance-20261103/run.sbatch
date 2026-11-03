#!/bin/bash
#SBATCH --job-name=yzl-r256-accept
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=0
#SBATCH --time=0
set -euo pipefail
cd "$1"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
hostname > NODE.txt
scontrol show job "$SLURM_JOB_ID" > SLURM.txt
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$1" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec python3 work/YUZE-LU/162/r256-acceptance-20261103/run.py'
