#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-mix
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:18:00
set -euo pipefail
root=$(pwd -P)
run=$(mktemp -d "$root/mix.XXXXXXXX")
input="$root/precheck-final"
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json"
printf 'run=%s\nlayout=%s\n' "$run" "$input"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
args=()
for log in "$@"; do
    case "$log" in clean-*.log|group-*.log) ;; *) exit 2 ;; esac
    dir=$(sed -n 's/^run=//p' "$log")
    case "$dir" in "$root"/clean.*|"$root"/group.*) ;; *) exit 2 ;; esac
    cmp "$dir/graph.txt" "$input/graph.txt"
    grep -Eq '^clean nets=1184 M11=0 M12=0 V11=0 restored=0$|^this_round_seed=' "$log"
    args+=("$dir")
done
cd "$run"
mapfile -t sorted < <(python3 -B - "${args[@]}" <<'PY'
import json,sys
a=[(p,json.load(open(p+'/routes.json'))) for p in sys.argv[1:]]
assert all(r['geometry_check']['passed'] for _,r in a)
assert all(r['context']==a[0][1]['context'] for _,r in a)
assert all(len(r['routes'])+len(r['failed'])==1184 for _,r in a)
for p,r in sorted(a,key=lambda item:len(item[1]['routes']),reverse=True): print(p)
PY
)
test "${#sorted[@]}" -eq "$#"
seed=${sorted[0]}
printf 'this_round_seed=%s\n' "$seed"
alternatives=()
for donor in "${sorted[@]:1}"; do printf 'candidate_source=%s\n' "$donor"; alternatives+=("$donor/paths.txt"); done
cp "$input/graph.txt" .
g++ -O3 -std=c++17 "$root/select-maze.cpp" -o select
./select graph.txt "$seed/paths.txt" selected.paths 16 "${alternatives[@]}"
g++ -O3 -std=c++17 "$root/close-available.cpp" -o close
seq 0 1183 > targets.txt
./close graph.txt selected.paths targets.txt paths.txt
python3 -B "$root/verify-top.py" verify "$input/derived-spec.json" paths.txt routes.json --original "$orig" --escape "$input/lower-evidence.json"
python3 -B - "$seed/routes.json" routes.json <<'PY'
import json,sys
a,b=[json.load(open(p)) for p in sys.argv[1:]]
assert a['context']==b['context'] and all(x['geometry_check']['passed'] for x in (a,b))
assert set(a['routes'])<=set(b['routes'])
print('retained_this_round={}'.format(len(a['routes'])))
PY
sha256sum graph.txt selected.paths paths.txt paths.txt.initial routes.json
