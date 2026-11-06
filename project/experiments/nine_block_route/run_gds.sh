#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export QT_QPA_PLATFORM=offscreen
base="$PWD"
i="${SLURM_ARRAY_TASK_ID:?}"
run="gds-${SLURM_ARRAY_JOB_ID:?}-$i"
mkdir "$run"
seed=2
cp "escape-97881-$i/inputs.json" "$run/inputs.json"
cp "escape-97881-$i/escape-$seed.json" "$run/route.json"
if [[ "$i" == 26 ]]; then
  python3 - "$run/route.json" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
d=json.loads(p.read_text())
d["routes"]={k:v for k,v in d["routes"].items() if k.startswith("p_gate")}
assert len(d["routes"])==34
p.write_text(json.dumps(d))
PY
fi
python3 - "$run" "$i" <<'PY'
import json,sys
from pathlib import Path
d=dict(C0="../issue-188-ucf16/accepted-ucf16-01/C16/6_final.gds",
       U0="../issue-188-ucf16/accepted-ucf16-01/U16/6_final.gds",
       P0="../issue-187-p16-j16/139-p-final-gates/final/P/flow/results/nangate45/block_p16/base/6_final.gds")
need={"10":["C0","U0"],"26":["P0"],"30":["P0","C0","U0"]}[sys.argv[2]]
(Path(sys.argv[1])/"gds-inputs.json").write_text(json.dumps({n:str(Path(d[n]).resolve()) for n in need}))
PY
export COUPON_AUDIT="$base/$run"
if command -v klayout >/dev/null; then
  klayout -v
  klayout -b -r "$base/check_gds.py"
else
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
    --env "QT_QPA_PLATFORM=offscreen,COUPON_AUDIT=$COUPON_AUDIT" \
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
    bash -c 'source /OpenROAD-flow-scripts/env.sh; klayout -v; klayout -b -r "$1"' _ "$base/check_gds.py"
fi
(cd "$run"; sha256sum *.json upper-only.gds > SHA256SUMS)
