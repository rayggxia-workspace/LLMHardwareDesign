#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-probe
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=8
#SBATCH --time=00:21:00
set -euo pipefail
root=$(pwd -P)
input="$root/precheck-final"
run=$(mktemp -d "$root/probes.XXXXXXXX")
printf 'run=%s\n' "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
cd "$run"
printf '%s  %s\n' \
    15ae015489975cdf12b4bd22a60f4fed9f7c00473a61bc589eb0d8c20c51dcc5 "$input/graph.txt" \
    aea700593d0efe238a7021ad2a13756688769e5701742c97ef8772ad89a31aeb "$input/derived-spec.json" \
    95ceae50f78f4e1dd0726ecfd514d291f7e4eed26e5c8c8f5f74749b6c31bcd8 "$input/lower-evidence.json" \
    9c28df8dccacb06ce71a65ffc1141755a1a443e1f732a7a21f3d45abc0e80c61 "$root/cugr-maze-route.inc" | sha256sum -c
g++ -O3 -std=c++17 -Wall -Wextra -Wno-unused-variable "$root/probe-layout.cpp" -o probe
workers=${SLURM_CPUS_PER_TASK:-1}
pids=()
for ((i=0;i<workers;i++)); do
    ./probe "$input/graph.txt" "$i" "$workers" > "part-$i.tsv" &
    pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
head -1 part-0.tsv > path-options.tsv
for f in part-*.tsv; do tail -n +2 "$f"; done | sort -k1,1n -k2,2n >> path-options.tsv
python3 -B - "$input/derived-spec.json" <<'PY' > options.json
import csv,json,sys
from collections import Counter
s=json.load(open(sys.argv[1])); assert len(s['nets'])==1184 and not s['obstacles']
assert not any(s.get(k) for k in ('routes','pre_routes','existing_routes','seed_routes'))
want={(i,j+1) for i,n in enumerate(s['nets']) for j,_ in enumerate(n['sinks'])}
rows=list(csv.DictReader(open('path-options.tsv'),delimiter='\t'))
assert len(rows)==len(want)==1674 and {(int(r['net_index']),int(r['pin_index'])) for r in rows}==want
counts=Counter(int(r['sampled_corridors']) for r in rows)
print(json.dumps({'nets':1184,'targets':len(rows),'sampled_corridors':dict(counts),'initial_top':{'M11':0,'M12':0,'V11':0},
                  'note':'up to three different sampled corridors per branch, on the graph with fixed pins only'},sort_keys=True))
PY
cat options.json
sha256sum path-options.tsv options.json "$root/probe-layout.cpp"
