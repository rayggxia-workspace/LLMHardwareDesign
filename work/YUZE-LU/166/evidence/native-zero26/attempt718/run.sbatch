#!/bin/bash
#SBATCH --job-name=yzl-r166-stage718
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=0
#SBATCH --mem=0
#SBATCH --exclude=node16,node19,node20,node21,node25,node26
set -euo pipefail
cd "${1}"
sha256sum -c FILES.sha256 > source-check.log
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif | sha256sum -c -
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "${1}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; exec python3 project/experiments/r_local_state/resume_native_short.py --source /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt697/physical --diagnosis /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt708/native-complete --fixed-clock-proof /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt714/clock-route-probe --hook-proof /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt715/short-hook-probe --placement /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt716/pg-placement-probe'
