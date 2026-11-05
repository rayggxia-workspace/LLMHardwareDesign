#!/usr/bin/env bash
#SBATCH --job-name=yzl-ctl162-sysroute
#SBATCH --partition=c96
#SBATCH --cpus-per-task=96
#SBATCH --time=08:00:00
set -euo pipefail
root=$1
python3 "$root/project/experiments/control_v1/bundle_source.py" --verify "$root"
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
exec python3 "$root/project/experiments/control_v1/system_sweep.py" "$@" "$image"
