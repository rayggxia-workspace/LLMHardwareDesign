#!/usr/bin/env bash
#SBATCH --job-name=yzl-route-package
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;delivery=$2;index=$3
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;delivery=$2;index=$3;r=project/experiments/upper_router;out=$task/handoff
python3 "$r/package_delivery.py" build "$delivery" "$index" "$task/source.tar" "$out"
openroad -no_init -threads 10 -exit "$out/load_odb.tcl" > "$out/load-odb.log" 2>&1
openroad -no_init -threads 10 -exit "$out/load_def.tcl" > "$out/load-def.log" 2>&1
openroad -no_init -threads 10 -exit "$out/load_timing.tcl" > "$out/load-timing.log" 2>&1
python3 "$r/package_delivery.py" verify "$out"
' bash "$task" "$delivery" "$index"
