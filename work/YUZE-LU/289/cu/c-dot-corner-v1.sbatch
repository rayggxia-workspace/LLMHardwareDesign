#!/bin/bash
#SBATCH -J yzl-289-C-corner
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n6
#SBATCH -c8
#SBATCH --time=16:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-corner-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for spec in 'left 2' 'left 4' 'left 6' 'bottom 2' 'bottom 4' 'bottom 6';do
 read -r orientation depth <<< "$spec"
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-c-dot-corner-v1.sh" "$orientation" "$depth" > "$root/c-corner-${SLURM_JOB_ID}-${orientation}-${depth}.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"