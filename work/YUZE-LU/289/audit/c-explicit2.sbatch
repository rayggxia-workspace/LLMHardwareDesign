#!/bin/bash
#SBATCH -J yzl-C-explicit2
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n2
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-explicit2-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit
pids=()
for name in C-v14-genericadder-distributed-parallel-synthproof C-v15-genericadder-onehot-v2-synthproof; do
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 "$1/c-explicit-state.py" "$1/$2"' _ "$root" "$name" > "$root/$name/explicit-command.log" 2>&1 &
 pids+=("$!")
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
