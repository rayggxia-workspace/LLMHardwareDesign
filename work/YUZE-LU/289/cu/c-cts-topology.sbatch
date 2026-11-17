#!/bin/bash
#SBATCH -J yzl-289-C-clocks
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n5
#SBATCH -c8
#SBATCH --time=02:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-clock-study-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for mode in no_balance no_insert neither;do
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-c-cts-topology.sh" "$mode" > "$root/c-clock-study-${SLURM_JOB_ID}-$mode.log" 2>&1 &
 pids+=("$!")
done
for d in 0.33 0.35;do
 srun --exclusive -N1 -n1 -c8 bash "$root/run-c-physical-study.sh" routability "$d" > "$root/c-clock-study-${SLURM_JOB_ID}-density$d.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"