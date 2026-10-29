#!/usr/bin/env bash
#SBATCH --job-name=yzl-feed-fix
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=12:00:00
set -euo pipefail
source_root=$1
native=$2
out=$3
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -eq 16
mkdir -p "$(dirname "$out")"
python3 -c 'from pathlib import Path; import json; m=dict(s.split(":",1) for s in Path("/proc/meminfo").read_text().splitlines()); a=int(m["MemAvailable"].split()[0])*1024; print(json.dumps(dict(available_bytes=a,forecast_gib=192,headroom=1.2,node_guard_gib=16))); assert a>=(192*1.2+16)*1024**3' > "$(dirname "$out")/memory-admission-$SLURM_JOB_ID.json"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
actual=$(sha256sum "$image")
test "${actual%% *}" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$source_root" \
 --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 "$image" \
 bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/block_feed_v1/repair.py" --source "$2" --out "$3"' \
 bash "$source_root" "$native" "$out"
