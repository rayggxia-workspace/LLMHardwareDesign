#!/bin/bash
#SBATCH -J yzl-289-loaderorfs
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 6
#SBATCH -c 8
#SBATCH --time=06:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/loader-orfs-%j.log
set -uo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
container=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
sing=/public/software/singularity-ce-4.3.4/bin/singularity
pids=()
kinds=(original distributed-parallel onehot-v2)
for kind in "${kinds[@]}"; do
 srun --exclusive -N1 -n1 -c8 "$sing" exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 "$container" bash "$root/loader-orfs-worker.sh" synth "$kind" &
 pids+=("$!")
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
test "$rc" -eq 0 || exit 1
pids=()
for kind in "${kinds[@]}"; do
 for util in 30 50; do
  srun --exclusive -N1 -n1 -c8 "$sing" exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 "$container" bash "$root/loader-orfs-worker.sh" phys "$kind" "$util" &
  pids+=("$!")
 done
done
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
