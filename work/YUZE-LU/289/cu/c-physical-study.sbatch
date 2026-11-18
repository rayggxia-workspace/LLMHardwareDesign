#!/bin/bash
#SBATCH -J yzl-289-C-study
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n6
#SBATCH -c8
#SBATCH --time=04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-study-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for spec in 'capacity 0.0' 'capacity 0.10' 'capacity 0.20' 'routability 0.40' 'routability 0.45' 'routability 0.50';do
 read -r mode value <<< "$spec"
 srun --exclusive -N1 -n1 -c8 bash "$root/run-c-physical-study.sh" "$mode" "$value" > "$root/c-study-${SLURM_JOB_ID}-${mode}-${value}.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"