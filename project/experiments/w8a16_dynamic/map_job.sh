#!/usr/bin/env bash
#SBATCH --job-name=yzl-dyn32-map
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
sha256sum "$image" > tools.sha256
export DYNAMIC_PROOF=${DYNAMIC_PROOF:?frozen accepted proof}
pids=()
# Three independent services, each10 cores; the remaining allocation is not
# reused for unrelated work. No duplicate maps are run to fill CPU slots.
for top in dynamic_s32_merge dynamic_s32_packer dynamic_s32_weight_source; do
 srun --exact -n1 -c10 --cpu-bind=cores \
 bash "$root/source/project/experiments/w8a16_dynamic/map_rank.sh" "$root" "$top" > "$top.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}";do wait "$pid" || failed=1;done
exit "$failed"
