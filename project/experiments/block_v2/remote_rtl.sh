#!/usr/bin/env bash
#SBATCH --job-name=yzl-bv2-rtl
#SBATCH --partition=c96
#SBATCH --cpus-per-task=32
#SBATCH --time=02:00:00
set -euo pipefail
root=$1
out=$2
test -n "${SLURM_JOB_ID:-}"
models=${3:-e g}
read -ra model_list <<< "$models"
test "$((${#model_list[@]}*16))" -le "$SLURM_CPUS_PER_TASK"
test -f "$root/source-manifest.json"
mkdir -p "$out"
python3 -c 'from pathlib import Path; import json; m=dict(s.split(":",1) for s in Path("/proc/meminfo").read_text().splitlines()); a=int(m["MemAvailable"].split()[0])*1024; print(json.dumps(dict(available_bytes=a,forecast_gib=16,guard_gib=16))); assert a>(16*1.2+16)*1024**3' > "$out/memory-admission.json"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
expected=49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
read -r actual _ < <(sha256sum "$image")
test "$actual" = "$expected"
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
status=0
pids=()
for model in "${model_list[@]}"; do
 srun --exclusive --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
  singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
  --env OMP_NUM_THREADS=1 --env OPENBLAS_NUM_THREADS=1 "$image" \
  bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/block_v2/run_rtl.py" --model "$2" --out "$3/$2"' \
  bash "$root" "$model" "$out" > "$out/$model-worker.log" 2>&1 &
 pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
