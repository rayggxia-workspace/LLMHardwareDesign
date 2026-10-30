#!/usr/bin/env bash
#SBATCH --job-name=yzl-bv2-gates
#SBATCH --partition=c96
#SBATCH --cpus-per-task=96
#SBATCH --time=12:00:00
set -euo pipefail
root=$1
raw=$2
out=$3
test -f "$root/source-manifest.json"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
python3 "$root/project/experiments/block_v2/gate_queue.py" --root "$root" --raw "$raw" --out "$out"
