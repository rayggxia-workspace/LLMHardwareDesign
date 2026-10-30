#!/usr/bin/env bash
#SBATCH --job-name=yzl-bv2-pnr
#SBATCH --partition=c96
#SBATCH --cpus-per-task=32
#SBATCH --time=12:00:00
set -euo pipefail
root=$1
out=$2
verified=$3
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -eq 32
test -f "$root/source-manifest.json"
mkdir -p "$out"
# Initial conservative budget for the two small E/G candidates; measured RSS
# is retained per worker. Do not copy the 192GiB storage-macro forecast here.
python3 -c 'from pathlib import Path; import json; m=dict(s.split(":",1) for s in Path("/proc/meminfo").read_text().splitlines()); a=int(m["MemAvailable"].split()[0])*1024; print(json.dumps(dict(available_bytes=a,initial_forecast_gib_per_worker=48,workers=2,headroom=1.2,guard_gib=16))); assert a>(2*48*1.2+16)*1024**3' > "$out/memory-admission.json"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
status=0
pids=()
for model in e g; do
 srun --exclusive --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
  singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
  --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 "$image" \
  /usr/bin/time -v bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh
   python3 "$1/project/experiments/block_v2/map.py" --model "$2" --rtl-receipt "$4/$2/receipt.json" --out "$3/mapping/block_v2_$2"
   python3 "$1/project/experiments/block_v2/physical.py" --top "block_v2_$2" --mapping "$3/mapping" --out "$3/pnr/$2" --input-receivers' \
  bash "$root" "$model" "$out" "$verified" > "$out/$model-worker.log" 2>&1 &
 pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
