#!/usr/bin/env bash
set -euo pipefail
run=$1
root=$2
src=$3
stage=$4
pair=$SLURM_ARRAY_TASK_ID
kinds=(c c f f j j)
variants=(compact room compact room compact room)
cd "$run"
out="$run/$pair"
python3.12 "$src/project/experiments/cfj_leaf_base/physical.py" "$src" "$root" "$out" "${kinds[pair]}" "${variants[pair]}"
cpus=$SLURM_CPUS_PER_TASK
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'set -eu; source /OpenROAD-flow-scripts/env.sh; make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$1/config.mk" WORK_HOME="$1/flow" NUM_CORES="$2" "$3"' bash "$out" "$cpus" "$stage"
