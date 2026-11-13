#!/usr/bin/env bash
set -euo pipefail
root=$1
candidate=$2
cpus=${SLURM_CPUS_PER_TASK:?}
tmp=$root/tmp-$SLURM_JOB_ID
mkdir -p "$tmp"
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu --pwd "$root/source" \
    --env "TMPDIR=$tmp,OMP_NUM_THREADS=$cpus,QT_QPA_PLATFORM=offscreen,PU_OVERLAY=$candidate,PU_OVERLAY_OUT=$root/geometry-$SLURM_JOB_ID" \
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
    bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec klayout -b -r "$1"' bash \
    project/experiments/pu_leaf_base/overlay.py
