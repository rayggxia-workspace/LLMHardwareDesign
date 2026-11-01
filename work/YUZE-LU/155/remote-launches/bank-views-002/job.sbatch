#!/bin/bash
#SBATCH --job-name=yzl-sram-views
#SBATCH --partition=c64
#SBATCH --cpus-per-task=1
#SBATCH --mem=0
#SBATCH --time=00:15:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-002
echo '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif' | sha256sum -c -
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env SLURM_JOB_ID="$SLURM_JOB_ID" --env SLURM_CPUS_PER_TASK=1 --env OMP_NUM_THREADS=1 --env OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash run.sh
