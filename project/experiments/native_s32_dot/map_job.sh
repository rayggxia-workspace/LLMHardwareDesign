#!/usr/bin/env bash
#SBATCH --job-name=yzl-dot32-map
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root"
sha256sum -c source.sha256 > source-check.log
scontrol show job "$SLURM_JOB_ID" > allocation.txt
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c > tools.log
pids=()
tops=(dot_s32_s128)
if [ "${NATIVE32_MAP_TOP:-both}" = both ];then tops+=(dot_s32_core);fi
for rows in 1 2 4;do
 for top in "${tops[@]}";do
  srun --exact -n1 -c10 --cpu-bind=cores bash \
   "$root/source/project/experiments/native_s32_dot/map_rank.sh" "$root" "$rows" "$top" \
   > "map-$top-$rows.log" 2>&1 &
  pids+=("$!")
 done
done
failed=0
for pid in "${pids[@]}";do wait "$pid" || failed=1;done
exit "$failed"
