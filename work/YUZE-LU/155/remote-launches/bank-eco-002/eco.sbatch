#!/bin/bash
#SBATCH --job-name=yzl-sram-bankeco
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH --time=02:00:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-eco-002
echo '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif' | sha256sum -c -
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env SLURM_JOB_ID="$SLURM_JOB_ID" --env OMP_NUM_THREADS=4 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 run.py'
