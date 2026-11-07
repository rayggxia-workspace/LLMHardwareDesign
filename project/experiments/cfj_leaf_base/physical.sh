#!/usr/bin/env bash
set -euo pipefail
run=$1
root=$2
src=$3
stage=$4
mode=$5
cts=${6:-default}
control=${7:-services}
guard=${8:-baseline}
pair=$SLURM_ARRAY_TASK_ID
kinds=(c c f f j j)
variants=(compact room compact room compact room)
cd "$run"
out="$run/$pair"
cpus=$SLURM_CPUS_PER_TASK
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
   set -eu
   source /OpenROAD-flow-scripts/env.sh
   extra=()
   if [[ "${10}" == controller64 ]]; then
     # Command-line make variables override the platform defaults; an export
     # in DESIGN_CONFIG alone is overwritten by nangate45/config.mk.
     extra+=("DONT_USE_CELLS=TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4")
   fi
   python3 "$1/project/experiments/cfj_leaf_base/physical.py" "$1" "$2" "$3" "$4" "$5" "$8" "$9" "${10}" "${11}"
   make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$3/config.mk" WORK_HOME="$3/flow" NUM_CORES="$6" "${extra[@]}" "$7"
 ' bash "$src" "$root" "$out" "${kinds[pair]}" "${variants[pair]}" "$cpus" "$stage" "$mode" "$cts" "$control" "$guard"
