#!/bin/bash
#SBATCH -J yzl-289-C-grtplace
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n5
#SBATCH -c8
#SBATCH --time=16:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-grtplace-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for spec in 'rudy 2 5' 'grt 2 5' 'grt 1.5 5' 'grt 2.5 5' 'grt 2 7';do
 read -r method inflation weight <<< "$spec"
 srun --exclusive -N1 -n1 -c8 bash "$root/run-c-grt-placement-v3.sh" "$method" "$inflation" "$weight" > "$root/c-grtplace-${SLURM_JOB_ID}-${method}-${inflation}-${weight}.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"