#!/usr/bin/env bash
#SBATCH --job-name=yzl-field-scene
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%6
#SBATCH --time=0
set -euo pipefail
task=$1
root=$2
kind=$(python3 -c 'import sys;print(["P","U","C","F","J"][int(sys.argv[1])])' "$SLURM_ARRAY_TASK_ID")
mkdir "$task/$kind"
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env "OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
task=$1;root=$2;kind=$3
r=project/experiments/upper_router
python3 "$r/rc_graph.py" "$root/attempt05/$kind/spec.json" "$root/attempt05/$kind/routes.json" "$task/$kind/graph.json" --dbu-per-micron 2000 --sheet-resistance-ohm 0.0102 --via-resistance-ohm 0.08
export PYTHONPATH=$PWD/$r
export ROUTER_FIELD_OUT=$task/$kind/field ROUTER_HANDOFF=$root/attempt05/$kind/backend ROUTER_TOPOLOGY=$root/attempt18/$kind ROUTER_RC_GRAPH=$task/$kind/graph.json ROUTER_TECH_LEF=$root/attempt05/$kind/backend/technology/research12.tech.lef
klayout -b -r "$r/field_context.py"
' bash "$task" "$root" "$kind"
