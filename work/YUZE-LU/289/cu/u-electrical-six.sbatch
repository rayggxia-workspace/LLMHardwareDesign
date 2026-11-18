#!/bin/bash
#SBATCH -J yzl-289-U-elec
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 6
#SBATCH -c 8
#SBATCH --time=10:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/u-postroute-%j.log
set -uo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for fraction in 33 50 67; do
 for drive in 4 8; do
  srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-u-electrical.sh" "$fraction" "$drive" &
  pids+=("$!")
 done
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
