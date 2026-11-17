#!/bin/bash
#SBATCH --job-name=yzl-289-U-focused
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-focused-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
pids=()
for run in "$@"; do
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/audit/u-focused.sh" "$run" > "$root/audit/focused-$(basename "$run").log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
exit "$rc"
