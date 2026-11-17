#!/bin/bash
#SBATCH -J yzl-289-C-cluster2
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 6
#SBATCH -c 8
#SBATCH --time=04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cluster-v2-%j.log
set -uo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
pids=()
for size in 4 8 16; do
 for weight in 3 10; do
  srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 "$root/c-cluster-run-v2.py" "$size" "$weight" &
  pids+=("$!")
 done
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
