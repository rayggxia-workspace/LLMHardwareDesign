#!/usr/bin/env bash
#SBATCH --job-name=yzl-ctl162-dynamic
#SBATCH --partition=c96
#SBATCH --cpus-per-task=96
#SBATCH --time=08:00:00
set -euo pipefail
root=$1
source_root=$2
producer=$3
out=$4
shift 4
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -ge 96
python3 "$root/project/experiments/control_v1/bundle_source.py" --verify "$root"
python3 - <<'PY'
from pathlib import Path
m=dict(s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines())
assert int(m['MemAvailable'].split()[0])*1024>(6*48*1.2+16)*1024**3
PY
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
exec python3 "$root/project/experiments/control_v1/multi_gate_queue.py" "$root" "$source_root" "$producer" "$out" "$image" "$@"
