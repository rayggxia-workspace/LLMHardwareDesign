#!/bin/bash
#SBATCH --job-name=yzl-r166-package734
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --mem=0
#SBATCH --exclude=node16,node19,node20,node21,node25,node26
set -euo pipefail
cd "${1}"
sha256sum -c FILES.sha256 > source-check.log
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif | sha256sum -c -
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "${1}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; exec python3 project/experiments/r_local_state/qualify_package.py --capacity 1024 --physical /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical --evaluation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt733/evaluation --functional /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt723/netlist-queue --geometry /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt720/results --mapped /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt014/results/1024 --mapping-proof /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt047/preroute-lec'
