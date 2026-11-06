#!/usr/bin/env bash
set -euo pipefail
run=$1
pair=$SLURM_ARRAY_TASK_ID
out="$run/$pair"
result=$(find "$out/flow/results" -name 6_final.odb -printf '%h\n')
[[ -n "$result" && -s "$result/6_final.gds" ]]
export SINGULARITYENV_CFJ_FINAL_ODB="$result/6_final.odb"
export SINGULARITYENV_CFJ_NATIVE_GDS="$result/6_final.gds"
export SINGULARITYENV_CFJ_ENDPOINTS="$out/endpoints.tsv"
export SINGULARITYENV_CFJ_OVERLAY_DIR="$out"
cpus=$SLURM_CPUS_PER_TASK
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'set -eu; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1/endpoints.tcl"; klayout -b -r "$1/overlay.py"' \
 bash "$2"
