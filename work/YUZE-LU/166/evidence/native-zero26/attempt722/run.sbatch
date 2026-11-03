#!/bin/bash
#SBATCH --job-name=yzl-r166-farm722
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=0
#SBATCH --mem=0
#SBATCH --exclude=node16,node19,node20,node21,node25,node26
set -euo pipefail
cd "${1}"
sha256sum -c FILES.sha256 > source-check-${SLURM_ARRAY_TASK_ID}.log
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif | sha256sum -c -
exec srun --ntasks=1 --cpus-per-task=16 --cpu-bind=threads /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --env "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID},SLURM_ARRAY_JOB_ID=${SLURM_ARRAY_JOB_ID},SLURM_JOB_ID=${SLURM_JOB_ID},SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK},SLURMD_NODENAME=${SLURMD_NODENAME}" --bind /public/home/yuzelu --pwd "${1}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; exec python3 project/experiments/r_local_state/netlist_farm.py --stage worker --queue /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt721/netlist-queue'
