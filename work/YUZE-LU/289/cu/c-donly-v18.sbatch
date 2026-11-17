#!/bin/bash
#SBATCH -J yzl-289-C-donly
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 6
#SBATCH -c 8
#SBATCH --time=16:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-donly-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for margin in 0.02 0.04 0.06;do
 for delay in 0.025 0.030;do
  srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-c-donly-v18.sh" "$margin" "$delay" > "$root/c-donly-${SLURM_JOB_ID}-m${margin}-d${delay}.log" 2>&1 &
  pids+=("$!")
 done
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"