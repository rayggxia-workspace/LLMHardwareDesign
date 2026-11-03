#!/bin/bash
#SBATCH --job-name=yzl-r166-stage738
#SBATCH --partition=c96
#SBATCH --nodelist=node15
#SBATCH --cpus-per-task=15
#SBATCH --time=0
#SBATCH --mem=0
#SBATCH --exclude=node16,node19,node20,node21,node25,node26
set -euo pipefail
cd "${1}"
sha256sum -c FILES.sha256 > source-check.log
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif | sha256sum -c -
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "${1}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; export SLURM_CPUS_PER_TASK=15; exec python3 project/experiments/r_local_state/netlist_profile.py --physical /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical --source-build /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt672/netlist-test --baseline /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt010/results/1024/init-0.json --output-groups 64 --separate-optimization'
