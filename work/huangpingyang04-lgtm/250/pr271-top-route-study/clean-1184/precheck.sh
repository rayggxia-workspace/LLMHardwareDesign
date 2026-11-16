#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-precheck
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:12:00
set -euo pipefail
root=$(pwd -P)
input=$1
dest=$2
mkdir -p "$dest"
test ! -e "$dest/graph.txt"
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
export TMPDIR="$dest" PYTHONDONTWRITEBYTECODE=1
cp "$input/derived-spec.json" "$input/lower-evidence.json" "$dest/"
cd "$dest"
printf 'run=%s\n' "$dest"
python3 -B "$root/verify-top.py" export derived-spec.json graph.txt --original "$orig" --escape lower-evidence.json
g++ -O3 -std=c++17 "$root/access-audit.cpp" -o audit
./audit graph.txt > access.tsv
python3 -B - "$root" "$orig" <<'PY' > access-summary.json
from collections import Counter
import csv, json, sys
from pathlib import Path

root, orig=map(Path,sys.argv[1:])
s=json.load(open('derived-spec.json'))
original=json.load(orig.open())
assert s['nets']==original['nets'] and len(s['nets'])==1184 and not s['obstacles']
assert not any(s.get(k) for k in ('routes','pre_routes','existing_routes','seed_routes'))
assert not Path('paths.txt').exists()
rows=list(csv.DictReader(open('access.tsv'),delimiter='\t'))
expected={(i,j) for i,n in enumerate(s['nets']) for j in range(len(n['sinks'])+1)}
assert len(rows)==len(expected) and {(int(a['net_index']),int(a['pin_index'])) for a in rows}==expected
oldfile=root.parent/'hpy-pr276-toponly.rPq68zlF/causes.m5Ba0Tql/causes.tsv'
prior=[int(a['index']) for a in csv.DictReader(oldfile.open(),delimiter='\t') if a['after'] in ('driver_access','sink_access')]
assert len(set(prior))==44
groups=Counter(); focus=Counter(); names=[]
for a in rows:
    i,j=int(a['net_index']),int(a['pin_index'])
    n=s['nets'][i]; pin=([n['driver']]+n['sinks'])[j]
    exits,near,reserved=(int(a[k]) for k in ('independent_exits','nearby_pins','reserved_exit'))
    issue=('no_exit' if not exits else 'limited' if exits<=2 else 'dense' if near>=6 else 'open')
    groups[issue]+=1
    if i in prior: focus[issue]+=1
    if issue!='open': names.append({'index':i,'net':n['id'],'pin':pin,'status':issue,'exits':exits,'density':near,'reserved':reserved,'old_access_failure':i in prior})
print(json.dumps({'nets':1184,'empty_top_segments':{'M11':0,'M12':0,'V11':0},'terminals':len(rows),
                  'prior_44_checked':len(prior),'terminal_status':dict(groups),'prior_44_terminal_status':dict(focus),
                  'dense_reserved':sum(int(a['reserved_exit']) for a in rows if int(a['nearby_pins'])>=6),
                  'focus':names},sort_keys=True,indent=2))
PY
python3 -B -c 'import json; p=json.load(open("access-summary.json")); p.pop("focus"); print(p)'
sha256sum derived-spec.json lower-evidence.json graph.txt access.tsv access-summary.json
