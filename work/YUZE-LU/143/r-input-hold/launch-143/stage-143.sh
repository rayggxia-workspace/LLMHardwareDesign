#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
root=$base/snapshots/143
archive=/public/home/yuzelu/project-circuit/source-issue143-143.tar.gz
test "$(sha256sum "$archive" | cut -d' ' -f1)" = e07d867c1f4764dccf3c72deaf79cadbfb0b23040da01cf75796631de374bff2
test ! -e "$root"
mkdir "$root"
tar -xzf "$archive" -C "$root"
python3 - "$root" <<'PY'
import hashlib,json,sys
from pathlib import Path
r=Path(sys.argv[1]);m=json.loads((r/'source-manifest.json').read_text())
for name,row in m['files'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==row['sha256']
print(json.dumps(dict(source_verified=True,commit=m['commit'])))
PY
bash -n "$root/project/experiments/block_v2/remote_r_function_compute.sh"
sbatch --parsable --nodes=1 --nodelist=node26 --exclude=node[19-24] --output="$base/run143-%j.out" --error="$base/run143-%j.err" "$root/project/experiments/block_v2/remote_r_function_compute.sh" "$root" "$base/outputs/139/pnr/r" "$base/outputs/143/function-r"
