#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-focus77
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:27:00
set -euo pipefail
root=$(pwd -P)
plan=$(sed -n 's/^run=//p' "$1")
input=$(sed -n 's/^layout=//p' "$1")
shift
prior=/public/home/yuzelu/PingyangHuang/hpy-pr276-scarce1184.fOd5vRE3
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json"
run=$(mktemp -d "$root/clean.XXXXXXXX")
printf 'run=%s\nlayout=%s\nplan=%s\nparams=%s\n' "$run" "$input" "$plan" "$*"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1 FOCUS_PLAN="$plan"
cd "$run"
test ! -e paths.txt
options=$(sed -n 's/^run=//p' "$prior/probes-118268.log")
cp "$input/graph.txt" "$input/access.tsv" .
if cmp -s "$input/graph.txt" "$prior/precheck-final/graph.txt"; then
    cp "$options/path-options.tsv" .
else
    python3 -B "$root/rebase-options.py" "$prior/precheck-final/graph.txt" graph.txt "$options/path-options.tsv" > path-options.tsv
fi
python3 -B - "$input/derived-spec.json" <<'PY'
import json,sys
s=json.load(open(sys.argv[1])); assert len(s['nets'])==1184
assert not any(s.get(k) for k in ('routes','pre_routes','existing_routes','seed_routes'))
PY
features=()
if [[ ${FOCUS_STEMS:-0} == 1 ]]; then features+=("$root/focus-route.inc"); fi
python3 -B "$root/build-focus.py" "$root/route-scarce.cpp" focus.cpp "${features[@]}"
g++ -O3 -std=c++17 -Wall -Wextra -Wno-unused-variable -I "$root" focus.cpp -o maze
/usr/bin/time -f 'elapsed=%e max_rss=%M' ./maze graph.txt access.tsv path-options.tsv paths.txt "$@"
python3 -B "$root/verify-top.py" verify "$input/derived-spec.json" paths.txt routes.json --original "$orig" --escape "$input/lower-evidence.json"
sha256sum graph.txt paths.txt paths.txt.initial routes.json priority-entries.tsv focus.cpp
