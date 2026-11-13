#!/usr/bin/env bash
set -euo pipefail
run=$1
src=$2
index=$SLURM_ARRAY_TASK_ID
reuse=${3:-}
export SINGULARITYENV_SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK
export SINGULARITYENV_SLURM_JOB_ID=$SLURM_JOB_ID
exec srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'set -euo pipefail;source /OpenROAD-flow-scripts/env.sh; extra=(); if [[ -n "$4" ]];then extra+=(--reuse-synth "$4/$3");fi; python3 -B "$1/project/experiments/mother_control_v1/physical.py" --out "$2/$3" --candidate "$3" "${extra[@]}" --generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation' bash "$src" "$run" "$index" "$reuse"
