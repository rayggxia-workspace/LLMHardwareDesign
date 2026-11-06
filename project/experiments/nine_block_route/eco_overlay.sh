#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
run="$base/eco-overlay-${SLURM_JOB_ID:?}"
mkdir "$run"
test "$#" -eq 4
cp "$1" "$run/route.json"
cp "$(dirname "$1")/inputs.json" "$run/"
python3 - "$run" "${@:2}" <<'PY'
import json,sys
from pathlib import Path
paths=dict(zip(("P0","C0","U0"),sys.argv[2:]))
assert set(paths)=={"P0","C0","U0"} and len(sys.argv)==5
p=Path(sys.argv[1])
(p/"gds-inputs.json").write_text(json.dumps({k:str(Path(v).resolve()) for k,v in paths.items()}))
PY
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu
         --env "QT_QPA_PLATFORM=offscreen,COUPON_AUDIT=$run" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; klayout -b -r "$1"' _ "$base/../check_gds.py"
(cd "$run"; sha256sum *.json upper-only.gds > SHA256SUMS)
