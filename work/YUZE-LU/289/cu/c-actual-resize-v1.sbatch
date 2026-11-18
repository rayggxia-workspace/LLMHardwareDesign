#!/bin/bash
#SBATCH -J yzl-289-C-drive
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n3
#SBATCH -c8
#SBATCH --time=00:30:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-actual-resize-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for strength in 8 16 32;do
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-c-actual-resize-v1.sh" "$strength" > "$root/c-actual-resize-${SLURM_JOB_ID}-X$strength.log" 2>&1 &
 pids+=("$!")
done
rc=0;for p in "${pids[@]}";do wait "$p" || rc=1;done;exit "$rc"
