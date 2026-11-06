#!/usr/bin/env bash
#SBATCH --job-name=yzl-compact-ge
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-5%6
#SBATCH --time=08:00:00
set -euo pipefail
root=$1
results=$2
adjustment=
case "${3:-first}:${SLURM_ARRAY_TASK_ID:?}" in
  first:0) model=g; side=180; bands=2; margin=12; density=.91 ;;
  first:1) model=g; side=200; bands=2; margin=14; density=.86 ;;
  first:2) model=g; side=190; bands=3; margin=12; density=.90 ;;
  first:3) model=e_compact; side=340; bands=2; margin=16; density=.86 ;;
  first:4) model=e_compact; side=380; bands=3; margin=16; density=.83 ;;
  first:5) model=e_compact; side=390; bands=4; margin=16; density=.83 ;;
  followup:0) model=g; side=220; bands=2; margin=14; density=.72 ;;
  followup:1) model=g; side=220; bands=3; margin=14; density=.72 ;;
  followup:2) model=g; side=240; bands=2; margin=16; density=.68 ;;
  followup:3) model=g; side=240; bands=3; margin=16; density=.68 ;;
  followup:4) model=e_compact; side=380; bands=2; margin=16; density=.83 ;;
  followup:5) model=e_compact; side=390; bands=3; margin=16; density=.83 ;;
  upper:0) model=g; side=200; bands=2; margin=14; density=.86; adjustment=.15 ;;
  upper:1) model=g; side=200; bands=2; margin=14; density=.86; adjustment=.00 ;;
  upper:2) model=g; side=210; bands=2; margin=14; density=.78; adjustment=.15 ;;
  upper:3) model=g; side=210; bands=3; margin=14; density=.78; adjustment=.15 ;;
  *) exit 2 ;;
esac
out="$results/${model}-${side}-bands${bands}${adjustment:+-upper${adjustment}}"
mkdir "$out"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r digest _ < <(sha256sum "$image")
test "$digest" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
srun --exclusive --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
 --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" --env OPENBLAS_NUM_THREADS=1 "$image" \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
exp="$1/project/experiments/block_v2"; rtl="$1/project/rtl/block_v2"; out=$2
model=$3; side=$4; bands=$5; margin=$6; density=$7; cpus=$8
upper=()
if [[ -n "${9:-}" ]]; then upper=(--upper-adjustment "$9"); fi
export PYTHONDONTWRITEBYTECODE=1
if [[ "$model" == g ]]; then
 python3 "$exp/run_rtl.py" --model g --out "$out/rtl"
else
 mkdir "$out/rtl"
 /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --binary --timing \
   -j "$cpus" --x-initial unique --x-assign unique --top-module tb_e_compact \
   --Mdir "$out/rtl/obj" "$rtl/block_v2_e.sv" "$rtl/block_v2_e_compact.sv" "$exp/tb_e_compact.sv" \
   > "$out/rtl/build.log" 2>&1
 for run in 1:143 2:143 2:144; do
   "$out/rtl/obj/Vtb_e_compact" "+verilator+rand+reset+${run%:*}" "+verilator+seed+${run#*:}" > "$out/rtl/$run.log"
 done
 python3 - "$out/rtl" <<PY
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1])
sources=[Path("project/rtl/block_v2")/name for name in ("block_v2_e.sv","block_v2_e_compact.sv")]
sources.append(Path("project/experiments/block_v2/tb_e_compact.sv"))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
logs=sorted(out.glob("*:*.log"))
assert len(logs)==3 and all("PASS compact E" in log.read_text() for log in logs)
(out/"receipt.json").write_text(json.dumps(dict(passed=True,model="e_compact",runs=[dict(log=log.name,sha256=sha(log)) for log in logs],source_sha256={str(p):sha(p) for p in sources})))
PY
fi
python3 "$exp/map.py" --model "$model" --rtl-receipt "$out/rtl/receipt.json" --out "$out/mapping/block_v2_$model"
python3 "$exp/physical.py" --top "block_v2_$model" --mapping "$out/mapping" --out "$out/pnr" \
 --side "$side" --pin-bands "$bands" --density "$density" --core-margin "$margin" --cpus "$cpus" --input-receivers "${upper[@]}"
' bash "$root" "$out" "$model" "$side" "$bands" "$margin" "$density" "$SLURM_CPUS_PER_TASK" "$adjustment" > "$out/worker.log" 2>&1
