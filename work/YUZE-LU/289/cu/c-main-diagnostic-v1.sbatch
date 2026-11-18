#!/bin/bash
#SBATCH -J yzl-289-C-mainRC
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n2
#SBATCH -c8
#SBATCH --time=04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-main-diagnostic-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for mode in rcx notch;do
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-c-main-diagnostic-v1.sh" "$mode" > "$root/c-main-${SLURM_JOB_ID}-${mode}.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"
