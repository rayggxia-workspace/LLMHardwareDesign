#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-scarcegroup
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:24:00
set -euo pipefail
root=$(pwd -P)
seed_log=$1
probe_log=$2
shift 2
seed=$(sed -n 's/^run=//p' "$seed_log")
probes=$(sed -n 's/^run=//p' "$probe_log")
input="$root/precheck-final"
run=$(mktemp -d "$root/group.XXXXXXXX")
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json"
printf 'run=%s\nlayout=%s\nthis_round_seed=%s\nparams=%s\n' "$run" "$input" "$seed" "$*"
grep -Eq '^clean nets=1184 M11=0 M12=0 V11=0 restored=0$|^this_round_seed=' "$seed_log"
case "$seed" in "$root"/*) ;; *) exit 2 ;; esac
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1 GROUP_PROBES="$probes/path-options.tsv"
cd "$run"
cmp "$input/graph.txt" "$seed/graph.txt"
cp "$input/graph.txt" .
sed -e '/^#include <chrono>/a #include <cstdlib>\n#include "group-priority.inc"' \
    -e 's/auto ids=order_by_span(nets);/const auto ids=group_priority(nets,order);/' \
    -e '/if(order==1)reverse(ids.begin(),ids.end());/d' \
    -e '/if(order==2)iota(ids.begin(),ids.end(),0);/d' \
    "$root/group-repair.cpp" > group-scarce.cpp
g++ -O3 -std=c++17 -Wall -Wextra -Wno-unused-variable -I "$root" group-scarce.cpp -o maze
/usr/bin/time -f 'elapsed=%e max_rss=%M' ./maze graph.txt "$seed/paths.txt" paths.txt "$@"
python3 -B "$root/verify-top.py" verify "$input/derived-spec.json" paths.txt routes.json --original "$orig" --escape "$input/lower-evidence.json"
python3 -B - "$seed/routes.json" routes.json <<'PY'
import json,sys
a,b=[json.load(open(p)) for p in sys.argv[1:]]
assert all(x['geometry_check']['passed'] for x in (a,b)) and a['context']==b['context']
assert set(a['routes'])<=set(b['routes'])
print('retained_this_round={}'.format(len(a['routes'])))
PY
sha256sum graph.txt paths.txt paths.txt.initial routes.json group-scarce.cpp "$root/group-priority.inc"
