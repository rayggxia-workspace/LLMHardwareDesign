#!/usr/bin/env bash
# Run in an isolated task directory populated with the fixed #194 inputs.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen
mkdir -p "$PWD/tmp"
export TMPDIR="$PWD/tmp"
src="$PWD/project/experiments/nine_block_route"

if [[ "${1:-}" == audit ]]; then
    python3 "$src/qwen_candidate.py" inputs "audit-${SLURM_JOB_ID:?}" audit
    exit
fi

cases=(pair mixed wide gdn)
id="${SLURM_ARRAY_TASK_ID:?}"
seed=$((id % 2 + 2))
case="${cases[id / 2]}"
work="$PWD/route-${SLURM_ARRAY_JOB_ID:?}-$id-$case"
python3 "$src/qwen_candidate.py" inputs "$work" "$case"
python3 "$src/escape.py" "$work" "$seed"
python3 "$src/validate_escape.py" "$work/escape-$seed.json"
python3 - "$work/escape-$seed-audit.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    proof = json.load(f)
if not proof["passes_coupon_geometry"]:
    sys.exit("Incomplete or invalid geometry. See the per-net audit.")
PY
python3 "$src/export_escape.py" "$work/escape-$seed.json"
cp "$work/escape-$seed.json" "$work/route.json"
python3 - "$work" "$PWD/inputs/native-gds.json" <<'PY'
import json
from pathlib import Path
import sys

work = Path(sys.argv[1])
sources = json.loads(Path(sys.argv[2]).read_text())
bindings = json.loads((work / "case-binding.json").read_text())
used = {block for ends in bindings["endpoints"].values() for block, _ in ends}
(work / "gds-inputs.json").write_text(json.dumps({block: sources[block[0]] for block in sorted(used)}))
PY

export COUPON_AUDIT="$work"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
    --bind /public/home/yuzelu
    --env "QT_QPA_PLATFORM=offscreen,COUPON_AUDIT=$COUPON_AUDIT,TMPDIR=$TMPDIR"
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; klayout -v; klayout -b -r "$1"' _ "$src/check_gds.py"
(cd "$work"; sha256sum *.json *.def upper-only.gds > SHA256SUMS)
