#!/bin/bash
#SBATCH -J yzl-289-cu-recover
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/recovery-%j.log
set -uo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for kind in proof original parallel U C pg; do
 srun --exclusive -N1 -n1 -c8 bash "$root/recovery-worker.sh" "$kind" > "$root/recovery-${SLURM_JOB_ID}-${kind}.log" 2>&1 &
 pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
