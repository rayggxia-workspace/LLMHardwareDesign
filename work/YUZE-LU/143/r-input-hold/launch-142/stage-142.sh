#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
source_dir=$base/snapshots/142
archive=/public/home/yuzelu/project-circuit/source-issue143-142.tar.gz
test "$(sha256sum "$archive" | cut -d' ' -f1)" = 212046334855725d08c37018ac1723760bc4ea70b4e243950ce6ae18ce3c7255
test ! -e "$source_dir"
mkdir -p "$source_dir"
tar -xzf "$archive" -C "$source_dir"
python3 - "$source_dir" <<'PY'
import json,hashlib,sys
from pathlib import Path
r=Path(sys.argv[1]);m=json.loads((r/'source-manifest.json').read_text())
for p,v in m['files'].items(): assert hashlib.sha256((r/p).read_bytes()).hexdigest()==v['sha256'],p
print(json.dumps(dict(source_verified=True,commit=m['commit'])))
PY
bash -n "$source_dir/project/experiments/block_v2/remote_r_geometry_diagnostic.sh"
test -s "$base/outputs/139/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/6_final.odb"
test -s "$base/outputs/139/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/6_final.sdc"
test -s "$base/outputs/139/pnr/r/flow/logs/nangate45/bv1_block_v1_r/base/6_final_lec_check.log"
sbatch --parsable --exclude=node[19-24] --nodes=1 --nodelist=node26 --job-name=yzl-bv2-rgeomdiag --cpus-per-task=16 --output="$base/run142-%j.out" --error="$base/run142-%j.err" "$source_dir/project/experiments/block_v2/remote_r_geometry_diagnostic.sh" "$source_dir" "$base/outputs/142" "$base/outputs/139/pnr/r" "$base/outputs/129" final-gds
