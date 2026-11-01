#!/usr/bin/env bash
#SBATCH --job-name=yzl-ctl162-initial
#SBATCH --partition=c96
#SBATCH --cpus-per-task=32
#SBATCH --time=12:00:00
set -euo pipefail
root=$1
out=$2
models=${3:-c endpoint}
mode=${4:-physical}
read -ra model_list <<< "$models"
flags=()
if [ "$mode" = physical ]; then flags+=(--physical); fi
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -ge 32
test "$((${#model_list[@]}*16))" -le "$SLURM_CPUS_PER_TASK"
mkdir -p "$out"
python3 "$root/project/experiments/control_v1/bundle_source.py" --verify "$root" > "$out/source-verification.json"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
python3 - "$out" <<'PY'
from pathlib import Path
import json,sys
m=dict(s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines())
available=int(m['MemAvailable'].split()[0])*1024
Path(sys.argv[1]+'/memory-admission.json').write_text(json.dumps(dict(available_bytes=available,workers=2,initial_forecast_gib_per_worker=48,guard_gib=16,headroom=1.2)))
assert available>(2*48*1.2+16)*1024**3
PY
pids=()
for model in "${model_list[@]}"; do
 srun --exclusive --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
  singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
  --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 --env SLURM_JOB_ID="$SLURM_JOB_ID" "$image" \
  /usr/bin/time -v bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; root=$1; model=$2; out=$3; shift 3; python3 "$root/project/experiments/control_v1/run.py" --model "$model" --out "$out/$model" "$@"' \
  bash "$root" "$model" "$out" "${flags[@]}" > "$out/$model-worker.log" 2>&1 &
 pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
