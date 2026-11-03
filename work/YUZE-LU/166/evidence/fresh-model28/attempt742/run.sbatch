#!/bin/bash
#SBATCH --job-name=yzl-r166-stage742
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
export SINGULARITYENV_SLURM_JOB_ID="${SLURM_JOB_ID}" SINGULARITYENV_SLURM_STEP_ID="${SLURM_STEP_ID}" SINGULARITYENV_SLURMD_NODENAME="${SLURMD_NODENAME}"
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "${1}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 -c '"'"'import os,runpy,sys;cc=os.sched_getaffinity(0);assert len(cc)==15 and 64 in cc;os.sched_setaffinity(0,cc-{64});assert len(os.sched_getaffinity(0))==14;sys.argv=['"'"'"'"'"'"'"'"'project/experiments/r_local_state/netlist_queue.py'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'--source-test'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt738/netlist-profile'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'--netlist'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/flow/results/nangate45/r166_1024/base/6_final.v'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'--capacity'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'1024'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'--case-parallelism'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'14'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'--fresh'"'"'"'"'"'"'"'"'];runpy.run_path(sys.argv[0],run_name='"'"'"'"'"'"'"'"'__main__'"'"'"'"'"'"'"'"')'"'"'; exec bash /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt743/run.sbatch /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt743'
