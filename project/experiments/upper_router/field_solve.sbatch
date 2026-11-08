#!/usr/bin/env bash
#SBATCH --job-name=yzl-field-rc
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
 --env OMP_NUM_THREADS=10 \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
task=$1;root=$2;kind=$3
for walks in 262144 1048576 4194304; do
 out=$task/$kind/walks-$walks
 if python3 project/experiments/upper_router/field_solve.py "$root/attempt20/$kind/field" "$root/attempt23/build" "$root/attempt23/controls" "$out" --threads 10 --walks "$walks"; then
  printf "%s\n" "$out" > "$task/$kind/selected-run.txt"
  exit 0
 fi
 # Retry numerical failures only; truncated input/program errors are fatal.
 test -f "$out/solve.json"
done
exit 2
' bash "$task" "$root" "$kind"
