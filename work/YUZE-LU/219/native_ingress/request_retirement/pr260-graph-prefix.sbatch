#!/usr/bin/env bash
set -euo pipefail
cd "$1"
pr260="$2"
source_manifest="$3"
cp "$source_manifest" "tlm-graph-source-$SLURM_JOB_ID.json"
python3 -B - "$source_manifest" "tlm-graph-prefix-$SLURM_JOB_ID.json" <<'PY'
import json,sys
from pathlib import Path
source,output=map(Path,sys.argv[1:])
v=json.loads(source.read_bytes())
v['cases']['graph-prefix']={**v['cases'].pop('request-128'),'mode':'checkpoint','checkpoint_pages':4}
output.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
PY
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
bash "$tool" "$py" -B "$pr260/run_native_tlm_cases.py" "tlm-graph-prefix-$SLURM_JOB_ID.json" "tlm-graph-prefix-$SLURM_JOB_ID"
find "tlm-graph-prefix-$SLURM_JOB_ID" -maxdepth 3 -type f -printf '%f\n'
