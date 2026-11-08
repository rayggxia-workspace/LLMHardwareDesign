#!/usr/bin/env bash
#SBATCH --job-name=yzl-flat-seal
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;flat=$2;binding=$3
mkdir "$task/cache"
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen,ROUTER_FLAT_OUT="$flat",ROUTER_FLAT_BINDING="$binding",ROUTER_EQUIVALENCE_CACHE="$task/cache",ROUTER_EQUIVALENCE_RECEIPT="$task" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif klayout -b -r project/experiments/upper_router/physical_equivalence.py
