#!/usr/bin/env bash
#SBATCH --job-name=yzl-feed-pnr
#SBATCH --partition=c96
#SBATCH --cpus-per-task=32
#SBATCH --time=12:00:00
set -euo pipefail
source_root=$1
output_root=$2
mapping_root=$3
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -eq 32
mkdir -p "$output_root"
# RealMemory is a1MiB scheduler placeholder: use actual node memory admission.
# Native route/formal peak budget192GiB/task,20% headroom and16GiB node guard.
python3 -c 'from pathlib import Path; import json; m=dict(s.split(":",1) for s in Path("/proc/meminfo").read_text().splitlines()); a=int(m["MemAvailable"].split()[0])*1024; n=2 if a>=(2*192*1.2+16)*1024**3 else 1 if a>=(192*1.2+16)*1024**3 else 0; print(json.dumps(dict(available_bytes=a,parallel=n,per_task_gib=192,headroom=1.2,node_guard_gib=16))); assert n>0' > "$output_root/memory-admission.json"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
sha256sum "$image" > "$output_root/image.sha256"
read -r actual _ < "$output_root/image.sha256"
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
srun --ntasks=1 --cpus-per-task=32 --cpu-bind=cores \
 singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$source_root" \
 --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 "$image" \
 bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/block_feed_v1/physical_queue.py" --root "$1" --out "$2" --mapping "$3"' \
 bash "$source_root" "$output_root" "$mapping_root"
