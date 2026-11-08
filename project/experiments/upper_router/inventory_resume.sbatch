#!/usr/bin/env bash
#SBATCH --job-name=yzl-route-input
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%6
#SBATCH --time=0
set -euo pipefail
task=$1
packages=$2
kind=$(python3 -c 'import sys; print(["P","U","C","F","J"][int(sys.argv[1])])' "$SLURM_ARRAY_TASK_ID")
native=$packages/$kind
test -f "$native.stage.json"
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env "OMP_NUM_THREADS=10,ROUTER_NATIVE_ODB=$native/native/6_final.odb,ROUTER_INVENTORY_TSV=$task/$kind-inventory.tsv" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -threads 10 -exit project/experiments/upper_router/native_inventory.tcl'
python3 "$task/source/project/experiments/upper_router/native_inventory.py" --tsv "$task/$kind-inventory.tsv" "$native" "$task/$kind-inventory.json"
