#!/usr/bin/env bash
#SBATCH --job-name=yzl-nine-topo
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
root=$2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
task=$1;root=$2;r=project/experiments/upper_router
python3 "$r/assembly_inventory.py" "$root/attempt17/base.json" "$root/attempt17/library.json" "$root/attempt26/native/native.gds" "$task/inventory.json"
export ROUTER_NATIVE_INVENTORY=$task/inventory.json ROUTER_NATIVE_GDS=$root/attempt26/native/native.gds ROUTER_TOPOLOGY_OUT=$task/topology
klayout -b -r "$r/native_topology.py"
' bash "$task" "$root"
