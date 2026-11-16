#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-last1184
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:07:00
set -euo pipefail
root=$(pwd -P)
seed=$(sed -n 's/^run=//p' "$1")
diagnosis=$(sed -n 's/^run=//p' "$2")
test "$(sed -n 's/^routing=//p' "$2")" = "$seed"
case "$seed" in "$root"/mix.*) ;; *) exit 2 ;; esac
input="$root/precheck-final"
run=$(mktemp -d "$root/last.XXXXXXXX")
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json"
printf 'run=%s\nlayout=%s\nthis_round_seed=%s\n' "$run" "$input" "$seed"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
cd "$run"
cmp "$input/graph.txt" "$seed/graph.txt"
cp "$input/graph.txt" .
awk -F '\t' '$2 == "available" {print $1}' "$diagnosis/causes.tsv" > target.txt
g++ -O3 -std=c++17 "$root/close-available.cpp" -o close
./close graph.txt "$seed/paths.txt" target.txt paths.txt
python3 -B "$root/verify-top.py" verify "$input/derived-spec.json" paths.txt routes.json --original "$orig" --escape "$input/lower-evidence.json"
python3 -B - "$seed/routes.json" routes.json <<'PY'
import json,sys
a,b=[json.load(open(p)) for p in sys.argv[1:]]
assert a['context']==b['context'] and all(x['geometry_check']['passed'] for x in (a,b))
assert set(a['routes'])<=set(b['routes'])
print('retained_this_round={}'.format(len(a['routes'])))
PY
sha256sum graph.txt paths.txt paths.txt.initial routes.json
