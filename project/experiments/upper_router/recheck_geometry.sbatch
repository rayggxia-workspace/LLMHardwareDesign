#!/usr/bin/env bash
#SBATCH --job-name=yzl-nine-geometry
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;root=$2;previous=$3
mkdir "$task/backend"
for name in bindings.json upper.def upper.odb odb-geometry.tsv;do cp "$previous/$name" "$task/backend/$name";done
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen,ROUTER_HANDOFF="$task/backend",ROUTER_NATIVE_GDS="$root/attempt26/native/native.gds" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif klayout -b -r project/experiments/upper_router/physical_readback.py
