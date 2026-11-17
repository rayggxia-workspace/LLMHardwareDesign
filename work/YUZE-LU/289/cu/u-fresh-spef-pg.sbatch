#!/bin/bash
#SBATCH -J yzl-289-U-spefpg
#SBATCH -p debug,c96,c64
#SBATCH -N 1
#SBATCH -n 4
#SBATCH -c 8
#SBATCH --time=00:30:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/u-spefpg-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for spec in f50-h2-u1.2 f50-h2-u1.4 f67-h3-u1.2 f67-h3-u1.4;do
 srun --exclusive -N1 -n1 -c8 bash "$root/u-fresh-spef-pg.sh" "$spec" > "$root/u-spefpg-${SLURM_JOB_ID}-$spec.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"