#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
root=$base/snapshots/146
archive=/public/home/yuzelu/project-circuit/source-issue143-146.tar.gz
test "$(sha256sum "$archive" | cut -d' ' -f1)" = 4f1a4b2b05b29000aeb8ead82c31cac5469699524632617399297a3a47de9fa6
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
bash -n "$root/project/experiments/block_v2/remote_r_deferred_gates.sh"
bash -n "$root/project/experiments/block_v2/remote_r_final_gates.sh"
sbatch --parsable --nodes=1 --dependency=afterok:94507:94509 --exclude=node[19-24] --output="$base/run146-%j.out" --error="$base/run146-%j.err" "$root/project/experiments/block_v2/remote_r_deferred_gates.sh" "$root" "$base/outputs/146"
