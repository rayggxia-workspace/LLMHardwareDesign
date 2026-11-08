#!/usr/bin/env bash
#SBATCH --job-name=yzl-plan-route
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;root=$2;ir=$3;plan=$4
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
task=$1;root=$2;ir=$3;plan=$4;r=project/experiments/upper_router
python3 "$r/resource_library.py" "$task/source/work/YUZE-LU/230/inputs.json" "$root/attempt02" "$root/attempt01/packages" "$task/library.json" --services "$task/source/work/YUZE-LU/230/resource-services.json"
python3 "$r/flow.py" "$ir" "$plan" "$task/library.json" "$root/attempt26/spec.json" "$task/flow" --gap-dbu 160000 --alignment-dbu 16000 --via-resistance-ohm .08
' bash "$task" "$root" "$ir" "$plan"
