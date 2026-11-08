#!/usr/bin/env bash
#SBATCH --job-name=yzl-native-lef
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;configs=$2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
python3 project/experiments/upper_router/odb_lef.py "$2" "$1/views"
' bash "$task" "$configs"
