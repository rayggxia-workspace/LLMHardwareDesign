#!/usr/bin/env bash
#SBATCH --job-name=yzl-native-topo
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%6
#SBATCH --time=0
set -euo pipefail
task=$1
root=$2
kind=$(python3 -c 'import sys;print(["P","U","C","F","J"][int(sys.argv[1])])' "$SLURM_ARRAY_TASK_ID")
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env "OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen,ROUTER_NATIVE_INVENTORY=$root/attempt02/$kind-inventory.json,ROUTER_NATIVE_GDS=$root/attempt01/packages/$kind/native/6_final.gds,ROUTER_TOPOLOGY_OUT=$task/$kind" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 klayout -b -r project/experiments/upper_router/native_topology.py
