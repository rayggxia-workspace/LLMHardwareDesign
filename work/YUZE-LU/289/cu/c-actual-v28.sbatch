#!/bin/bash
#SBATCH -J yzl-289-Cactual
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n6
#SBATCH -c8
#SBATCH --time=16:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-actual-v28-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for iso in 8 16;do
 for hold in 50 100 150;do
  srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-c-actual-v28.sh" "$iso" "$hold" > "$root/c-actual-v28-${SLURM_JOB_ID}-i${iso}-h${hold}.log" 2>&1 &
  pids+=("$!")
 done
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"
