#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-clean1184
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:27:00
set -euo pipefail
root=$(pwd -P)
input=$1; shift
run=$(mktemp -d "$root/clean.XXXXXXXX")
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json"
printf 'run=%s\nlayout=%s\nparams=%s\n' "$run" "$input" "$*"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
cd "$run"
test ! -e paths.txt
python3 -B - "$input/access-summary.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['nets']==1184 and x['terminals']==2858 and x['prior_44_checked']==44
assert x['empty_top_segments']=={'M11':0,'M12':0,'V11':0}
PY
printf '%s  %s\n' 9c28df8dccacb06ce71a65ffc1141755a1a443e1f732a7a21f3d45abc0e80c61 "$root/cugr-maze-route.inc" | sha256sum -c
cp "$input/graph.txt" "$input/access.tsv" .
g++ -std=c++17 -O3 -Wall -Wextra -Wno-unused-variable "$root/route-trunks.cpp" -o maze
/usr/bin/time -f 'elapsed=%e max_rss=%M' ./maze graph.txt access.tsv paths.txt "$@"
python3 -B "$root/verify-top.py" verify "$input/derived-spec.json" paths.txt routes.json --original "$orig" --escape "$input/lower-evidence.json"
sha256sum graph.txt access.tsv paths.txt paths.txt.initial routes.json "$root/route-trunks.cpp" "$root/trunk-engine.cpp"
