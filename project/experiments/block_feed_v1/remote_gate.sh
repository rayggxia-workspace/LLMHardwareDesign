#!/usr/bin/env bash
#SBATCH --job-name=yzl-feed-gate
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=12:00:00
set -euo pipefail
root=$1
operation=$2
source_folder=$3
out=$4
shift 4
test -f "$root/source-manifest.json"
test -f "$root/project/experiments/block_feed_v1/qualify.py"
case "$operation" in seal|physical|drc|function|formal|formal-join|deliver|geometry|escape) ;; *) exit 2 ;; esac
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -eq 16
mkdir -p "$(dirname "$out")"
python3 -c 'from pathlib import Path; import json; m=dict(s.split(":",1) for s in Path("/proc/meminfo").read_text().splitlines()); a=int(m["MemAvailable"].split()[0])*1024; print(json.dumps(dict(available_bytes=a,forecast_gib=192,headroom=1.2,node_guard_gib=16))); assert a>=(192*1.2+16)*1024**3' > "$(dirname "$out")/memory-$operation-$SLURM_JOB_ID.json"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
actual=$(sha256sum "$image")
test "${actual%% *}" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
 --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 "$image" \
 bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/block_feed_v1/qualify.py" "$2" --source "$3" --out "$4" "${@:5}"' \
 bash "$root" "$operation" "$source_folder" "$out" "$@"
