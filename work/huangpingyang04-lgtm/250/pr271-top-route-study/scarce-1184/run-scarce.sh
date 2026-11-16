#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-scarce
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:27:00
set -euo pipefail
root=$(pwd -P)
options=$(sed -n 's/^run=//p' "$1"); shift
input="$root/precheck-final"
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json"
run=$(mktemp -d "$root/clean.XXXXXXXX")
printf 'run=%s\nlayout=%s\nparams=%s\n' "$run" "$input" "$*"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
cd "$run"
test ! -e paths.txt
python3 -B - "$options/options.json" "$input/access-summary.json" <<'PY'
import json,sys
a,p=[json.load(open(x)) for x in sys.argv[1:]]
assert a['nets']==p['nets']==1184 and a['targets']==1674 and p['terminals']==2858
assert a['initial_top']==p['empty_top_segments']=={'M11':0,'M12':0,'V11':0}
PY
printf '%s  %s\n' 15ae015489975cdf12b4bd22a60f4fed9f7c00473a61bc589eb0d8c20c51dcc5 "$input/graph.txt" | sha256sum -c
cp "$input/graph.txt" "$input/access.tsv" "$options/path-options.tsv" .
source="$root/route-scarce.cpp"
if [[ ${SCARCE_LOCAL:-0} == 1 ]]; then
    sed -e 's/span!=md(n.pins.front(),n.pins\[j\])/span<0||span>md(n.pins.front(),n.pins[j])/' "$source" > route-near.cpp
    source=route-near.cpp
fi
g++ -O3 -std=c++17 -Wall -Wextra -Wno-unused-variable -I "$root" "$source" -o maze
/usr/bin/time -f 'elapsed=%e max_rss=%M' ./maze graph.txt access.tsv path-options.tsv paths.txt "$@"
python3 -B "$root/verify-top.py" verify "$input/derived-spec.json" paths.txt routes.json --original "$orig" --escape "$input/lower-evidence.json"
sha256sum graph.txt access.tsv path-options.tsv paths.txt paths.txt.initial routes.json "$source" "$root/trunk-engine.cpp"
