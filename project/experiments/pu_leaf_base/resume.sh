#!/usr/bin/env bash
set -euo pipefail
root=$1
candidate=$2
mode=$3
hold_target=${4:-0.005}
extra=()
if [[ ${5:-} == post-hold ]]; then extra=(--post-hold-repair); fi
if [[ -n ${6:-} ]]; then extra+=(--via-access-layer "$6"); fi
cpus=${SLURM_CPUS_PER_TASK:?}
tmp=$root/tmp-$SLURM_JOB_ID
mkdir -p "$tmp"
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu --pwd "$root/source" \
    --env "TMPDIR=$tmp,OMP_NUM_THREADS=$cpus,OPENBLAS_NUM_THREADS=1" \
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
    bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 -B "$@"' bash \
    project/experiments/pu_leaf_base/resume.py "$candidate" "$root/resume-$SLURM_JOB_ID" "$cpus" "$mode" --hold-target "$hold_target" "${extra[@]}"
