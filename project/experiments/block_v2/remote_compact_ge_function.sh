#!/usr/bin/env bash
#SBATCH --job-name=yzl-ge-final
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-1%2
#SBATCH --time=04:00:00
set -euo pipefail
root=$1
out=$2
shift 2
case "${SLURM_ARRAY_TASK_ID:?}" in
  0) model=g ;;
  1) model=e_compact ;;
  *) exit 2 ;;
esac
out="$out/$model"
mkdir "$out"
selected=$(python3 - "$model" "$@" <<'PY'
import json,sys
from pathlib import Path
model,*audits=sys.argv[1:]
passed=[]
for directory in audits:
    for candidate in Path(directory).glob(model+"-*-bands*"):
        receipt=candidate/"physical"/"five-macro-physical.json"
        drc=candidate/"full-deck-count.txt"
        native=candidate/"native-whole-drc.rpt"
        if not (receipt.is_file() and drc.is_file() and native.is_file()):
            continue
        if drc.read_text().strip()!="0" or native.stat().st_size:
            continue
        physical=json.loads(receipt.read_text())
        if physical["passed"]:
            width,height=physical["die_um"]
            passed.append((width*height,candidate))
if passed:
    print(min(passed)[1]/"sealed")
PY
)
if [[ -z "$selected" ]]; then
    echo "No $model candidate passed the physical and DRC gates." > "$out/no-candidate.txt"
    exit 1
fi
printf '%s\n' "$selected" > "$out/selected.txt"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r digest _ < <(sha256sum "$image")
test "$digest" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
srun --exclusive --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" \
 --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" --env OPENBLAS_NUM_THREADS=1 "$image" \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export PYTHONDONTWRITEBYTECODE=1
qualify="$1/project/experiments/block_v2/qualify.py"
python3 "$qualify" function --source "$2" --out "$3/function" --cpus "$4"
python3 "$qualify" formal --source "$2" --out "$3/formal" --function "$3/function" --cpus "$4"
' bash "$root" "$selected" "$out" "$SLURM_CPUS_PER_TASK" > "$out/worker.log" 2>&1
