#!/bin/bash
#SBATCH --job-name=yzl-sram-generate
#SBATCH --partition=c64
#SBATCH --cpus-per-task=16
#SBATCH --mem=0
#SBATCH --time=12:00:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/generate-006
echo '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif' | sha256sum -c -
export PATH=/public/software/singularity-ce-4.3.4/bin:$PATH
singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env SLURM_JOB_ID="$SLURM_JOB_ID" --env SLURM_CPUS_PER_TASK=16 --env OPENBLAS_NUM_THREADS=1 --env S_SRAM_OFFLINE=/public/home/yuzelu/opt/eda/issue155-offline-v2 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; bash source/project/experiments/s_sram/provision_generate.sh "$PWD/source" "$PWD" --internal-pins'
