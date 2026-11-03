#!/bin/bash
#SBATCH --job-name=yzl-r166-farm721
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --mem=0
#SBATCH --exclude=node16,node19,node20,node21,node25,node26
set -euo pipefail
cd "${1}"
sha256sum -c FILES.sha256 > source-check.log
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif | sha256sum -c -
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "${1}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; exec python3 project/experiments/r_local_state/netlist_farm.py --stage prepare --capacity 1024 --source-test /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt672/netlist-test --netlist /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/flow/results/nangate45/r166_1024/base/6_final.v --physical /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical --worker-attempt /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt722 --reuse-identical-build'
