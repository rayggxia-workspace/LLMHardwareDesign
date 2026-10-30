#!/usr/bin/env bash
#SBATCH --job-name=yzl-bv2-retain
#SBATCH --partition=c96
#SBATCH --cpus-per-task=32
#SBATCH --time=02:00:00
set -euo pipefail
root=$1
out=$2
test "$SLURM_CPUS_PER_TASK" -eq 32
test -f "$root/source-manifest.json"
mkdir -p "$out"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
for model in s t; do
 if [ "$model" = s ]; then
  prefix=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees
  delivery=$prefix/issue130-m-feed-qualify43-20261030/results/delivery-s/native
  geometry=$prefix/issue130-m-feed-qualify43-20261030/results/delivery-s/geometry
  source_dir=$prefix/issue130-m-feed-qualify42-20261030/results/source-s
 else
  prefix=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121
  delivery=$prefix/block-v1-20261029-256/tasks/revision300-delivery-t
  geometry=$prefix/block-v1-20261029-256/tasks/revision300-geometry-t
  source_dir=$prefix/block-v1-20261028-249/tasks/revision300-final-source-t
 fi
 srun --exclusive --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" "$image" \
  python3 "$root/project/experiments/block_v2/audit_retained.py" --macro "$model" --delivery "$delivery" --source "$source_dir" --geometry "$geometry" --out "$out/retained-$model" > "$out/$model-worker.log" 2>&1 &
done
status=0
for pid in $(jobs -p); do wait "$pid" || status=1; done
exit "$status"
