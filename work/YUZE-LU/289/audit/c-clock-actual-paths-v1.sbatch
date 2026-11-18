#!/bin/bash
#SBATCH -J yzl-C-clock-paths
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n3
#SBATCH -c8
#SBATCH -t 00:15:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-clock-actual-paths-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
pids=()
for k in 4 7 9; do
 srun --exclusive -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/audit/c-clock-actual-paths-v1.sh" "$k" &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"