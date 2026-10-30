#!/usr/bin/env bash
#SBATCH --job-name=yzl-bv2-rsmall
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
set -euo pipefail
root=$1
out=$2
mapping=$3
clock_profile=${4:-standard}
test "$clock_profile" = standard || test "$clock_profile" = strong || test "$clock_profile" = wide-strong
test "$SLURM_CPUS_PER_TASK" -eq 16
test -f "$root/source-manifest.json"
test -f "$mapping/block_v1_r/receipt.json"
mkdir -p "$out"
# Measured previous native R peak ~30GB; 64GiB is a forecast, not a hard bound.
python3 -c 'from pathlib import Path; import json; m=dict(s.split(":",1)for s in Path("/proc/meminfo").read_text().splitlines()); a=int(m["MemAvailable"].split()[0])*1024; print(json.dumps(dict(available_bytes=a,forecast_gib=64,headroom=1.2,guard_gib=16,basis="Original R MaxRSS29988144KiB, new compact forecast64GiB; record actual"))); assert a>(64*1.2+16)*1024**3' > "$out/memory-admission.json"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
 --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 "$image" \
 /usr/bin/time -v bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh
 extra=(--r-compact-floorplan)
 if [[ "$4" == strong ]]; then extra+=(--r-strong-clock); fi
 if [[ "$4" == wide-strong ]]; then extra=(--r-strong-clock); fi
 exec python3 "$1/project/experiments/block_v2/physical.py" --top block_v1_r --mapping "$3" --out "$2/pnr/r" --input-receivers --placement-mode geometric --fanout-mode partition --refine-partition-placement --placement-hold-margin 0.0 "${extra[@]}"' \
 bash "$root" "$out" "$mapping" "$clock_profile" > "$out/r-worker.log" 2>&1
