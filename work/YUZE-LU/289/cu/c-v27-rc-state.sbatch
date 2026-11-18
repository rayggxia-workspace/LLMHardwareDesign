#!/bin/bash
#SBATCH -J yzl-289-C-RCdiag
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH --time=00:30:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-v27-diag-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for mode in rc-state;do
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-c-v27-diag.sh" "$mode" > "$root/c-v27-diag-${SLURM_JOB_ID}-${mode}.log" 2>&1 &
 pids+=("$!")
done
rc=0;for p in "${pids[@]}";do wait "$p" || rc=1;done;exit "$rc"
