#!/usr/bin/env bash
#SBATCH --job-name=yzl-ctl162-gates
#SBATCH --partition=c96
#SBATCH --cpus-per-task=48
#SBATCH --time=12:00:00
set -euo pipefail
root=$1
source_root=$2
producer=$3
out=$4
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -ge 48
mkdir -p "$out"
python3 "$root/project/experiments/control_v1/bundle_source.py" --verify "$root" > "$out/source-verification.json"
python3 - "$out" <<'PY'
from pathlib import Path
import json,sys
m=dict(s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines())
available=int(m['MemAvailable'].split()[0])*1024
Path(sys.argv[1]+'/memory-admission.json').write_text(json.dumps(dict(available_bytes=available,workers=3,initial_forecast_gib_per_worker=48,guard_gib=16,headroom=1.2)))
assert available>(3*48*1.2+16)*1024**3
PY
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
python3 "$root/project/experiments/control_v1/gate_queue.py" "$root" "$source_root" "$producer" "$out" "$image"
