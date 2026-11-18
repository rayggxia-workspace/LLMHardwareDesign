#!/bin/bash
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --job-name=yzl-C40-clock6
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C40-clock-graft-fast-v1/matrix-%j.log
set -euo pipefail
pids=()
for seed in 0 1 2 3 4 5;do srun --exclusive -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C40-clock-graft-fast-v1/run.sh "$seed" >/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C40-clock-graft-fast-v1/seed${seed}-worker.log 2>&1 & pids+=( $! );done
rc=0;for p in "${pids[@]}";do wait "$p" || rc=1;done;exit "$rc"
