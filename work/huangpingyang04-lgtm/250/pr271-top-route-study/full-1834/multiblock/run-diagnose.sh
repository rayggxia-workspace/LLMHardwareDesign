#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-diagnose
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:13:00
set -euo pipefail
root=$(pwd -P)
top_log=$1
top=$(sed -n 's/^run=//p' "$top_log")
variant=$(sed -n 's/^variant=//p' "$top_log")
spec="$root/$variant"
run=$(mktemp -d "$root/diagnose.XXXXXXXX")
cd "$run"
export TMPDIR="$run"
printf 'diagnose_run=%s\n' "$run"
g++ -std=c++17 -O3 -Wall -Wextra -Wno-unused-variable "$root/diagnose-maze.cpp" -o diagnose-maze
workers=${SLURM_CPUS_PER_TASK:-1}
pids=()
for ((shard=0; shard<workers; shard++)); do
    ./diagnose-maze "$spec/graph.txt" "$top/paths.txt" "$shard" "$workers" > "part-$shard.tsv" &
    pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
head -1 part-0.tsv > unresolved.tsv
for file in part-*.tsv; do tail -n +2 "$file"; done | sort -n >> unresolved.tsv
python3 -B - "$spec/derived-spec.json" "$top/routes.json" <<'PY' > counts.json
from collections import Counter
import csv
import json
import sys

with open(sys.argv[1]) as src:
    nets = json.load(src)['nets']
with open(sys.argv[2]) as src:
    result = json.load(src)
assert result['geometry_check']['passed']
with open('unresolved.tsv') as src:
    rows = list(csv.DictReader(src, delimiter='\t'))
    reasons = {nets[int(r['net_index'])]['id']: r['reason'] for r in rows}
assert len(reasons) == len(rows)
assert set(reasons) == set(result['failed'])
print(json.dumps(dict(Counter(reasons.values())), sort_keys=True))
PY
cat counts.json
sha256sum "$spec/graph.txt" "$top/paths.txt" "$root/diagnose-maze.cpp" unresolved.tsv counts.json
