#!/usr/bin/env bash
# Single-core solver and geometry audit. Run multiple candidate/seed pairs as a Slurm array.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
source_dir="${1:?pass the directory containing trial scripts}"
layout_job="${2:?pass the verified-input layout job id}"
id="${SLURM_ARRAY_TASK_ID:?}"
layout=$((id / 4))
seed=$((id % 4))
in="case-$layout_job-$layout"
work="escape-${SLURM_ARRAY_JOB_ID:?}-$id"
mkdir "$work"
cp "$in"/{coupon.def,inputs.json} "$work/"
python3 "$source_dir/escape.py" "$work" "$seed"
python3 "$source_dir/validate_escape.py" "$work/escape-$seed.json"
python3 "$source_dir/reservations.py" "$work/inputs.json"
if python3 -c 'import json,sys; raise SystemExit(not json.load(open(sys.argv[1]))["passes_coupon_geometry"])' "$work/escape-$seed-audit.json"; then
    python3 "$source_dir/export_escape.py" "$work/escape-$seed.json"
fi
sha256sum "$work"/* > "$work/SHA256SUMS"
