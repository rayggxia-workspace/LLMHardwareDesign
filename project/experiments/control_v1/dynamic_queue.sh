#!/usr/bin/env bash
#SBATCH --job-name=yzl-ctl162-dynamic
#SBATCH --partition=c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH --time=0
#SBATCH --no-requeue
set -euo pipefail
root=$1
out=$2
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
python3 "$root/project/experiments/control_v1/bundle_source.py" --verify "$root" > "$out/source-verification.json"
python3 "$root/project/experiments/control_v1/dynamic_queue.py" "$root" "$out" "$image"
