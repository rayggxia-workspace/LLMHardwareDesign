#!/bin/bash
#SBATCH -J yzl-289-U-final
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 6
#SBATCH -c 8
#SBATCH --time=16:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/u-guardant-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for upper in 1.0 1.2 1.4;do
 for pair in '50 2' '67 3';do
  read -r fraction hold <<< "$pair"
  srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-u-guardant-v1.sh" "$fraction" "$hold" "$upper" > "$root/u-guardant-${SLURM_JOB_ID}-f${fraction}-h${hold}-u${upper}.log" 2>&1 &
  pids+=("$!")
 done
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"