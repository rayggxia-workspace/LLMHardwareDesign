#!/bin/bash
#SBATCH --job-name=yzl-r166-stage724
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=0
#SBATCH --mem=0
#SBATCH --exclude=node16,node19,node20,node21,node25,node26
set -euo pipefail
cd "${1}"
sha256sum -c FILES.sha256 > source-check.log
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif | sha256sum -c -
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "${1}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; set -e; python3 project/experiments/r_local_state/check_native_tool_source.py --root /public/home/yuzelu/opt/eda/r166-openroad-gc-cache-2eba27b2-offline01 --archives /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/native-diagnostic; python3 project/experiments/r_local_state/final_stage.py --capacity 1024 --physical /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical --stage native --checker-root /public/home/yuzelu/opt/eda/r166-openroad-gc-cache-2eba27b2-offline01 --checker-source-recheck /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt724/TOOL_SOURCE_RECHECK.json'
