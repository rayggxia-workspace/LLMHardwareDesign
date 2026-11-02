#!/bin/bash
#SBATCH --job-name=yzl-sram-model
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --mem=0
#SBATCH --time=02:00:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/actual-model-002
echo '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif' | sha256sum -c -
export PATH=/public/software/singularity-ce-4.3.4/bin:$PATH
singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env SLURM_JOB_ID="$SLURM_JOB_ID" --env SLURM_CPUS_PER_TASK=4 --env OMP_NUM_THREADS=4 --env OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 source/project/experiments/s_sram/run_actual.py --generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/generate-006/generation --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --out "$PWD/test"'
