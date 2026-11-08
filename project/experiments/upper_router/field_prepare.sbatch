#!/usr/bin/env bash
#SBATCH --job-name=yzl-field-qual
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
reuse=$2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
task=$1;reuse=$2
python3 project/experiments/upper_router/field/build_native_field.py "$task/build" "$reuse"
python3 project/experiments/upper_router/field_controls.py "$task/build/native_field" "$task/controls"
' bash "$task" "$reuse"
