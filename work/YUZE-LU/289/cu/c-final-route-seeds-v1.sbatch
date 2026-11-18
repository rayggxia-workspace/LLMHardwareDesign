#!/bin/bash
#SBATCH -J yzl-289-Cfinal
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n6
#SBATCH -c8
#SBATCH --time=06:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-final-seeds-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
sing=/public/software/singularity-ce-4.3.4/bin/singularity
srun --exclusive -N1 -n1 -c8 "$sing" exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 "$image" bash "$r/run-c-final-sizes-prepare-v1.sh"
pids=()
for seed in 0 1 2 3 4 5;do
 srun --exclusive -N1 -n1 -c8 "$sing" exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 "$image" bash "$r/run-c-final-route-seed-v1.sh" "$seed" > "$r/c-final-seeds-${SLURM_JOB_ID}-${seed}.log" 2>&1 &
 pids+=("$!")
done
rc=0;for p in "${pids[@]}";do wait "$p" || rc=1;done;exit "$rc"
