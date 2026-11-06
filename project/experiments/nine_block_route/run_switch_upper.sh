#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
repo="$PWD"
native="${1:?routed switch native results}"
profile="${2:?c0 or nine}"
seed="${SLURM_ARRAY_TASK_ID:-2}"
placements=(east north channel)
placement="${placements[seed % 3]}"
case="$repo/upper-${SLURM_ARRAY_JOB_ID:-${SLURM_JOB_ID:?}}-$seed-$profile"
if [[ "$profile" == c0 ]]; then top=qwen_c0_receive; else top=qwen_nine_transport; fi
src="$repo/project/experiments/nine_block_route"
python3 -B "$src/bind_switch.py" inputs "$native/switch.lef" \
    "$native/flow/results/nangate45/$top/base/6_final.gds" "$case" "$profile" "$placement"
python3 -B "$src/escape.py" "$case" "$seed" --compact
python3 -B "$src/validate_escape.py" "$case/escape-$seed.json"
python3 -B - "$case/escape-$seed-audit.json" <<'PY'
import json
import sys
with open(sys.argv[1]) as handle:
    if not json.load(handle)["passes_coupon_geometry"]:
        sys.exit("Upper route incomplete or rule errors present")
PY
python3 -B "$src/export_escape.py" "$case/escape-$seed.json"
cp "$case/escape-$seed.json" "$case/route.json"
mkdir "$case/tmp"
export TMPDIR="$case/tmp"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
    --bind /public/home/yuzelu
    --env "QT_QPA_PLATFORM=offscreen,COUPON_AUDIT=$case,TMPDIR=$TMPDIR"
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; klayout -b -r "$1"' _ "$src/check_gds.py"
(cd "$case"; sha256sum *.json *.def upper-only.gds > SHA256SUMS)
