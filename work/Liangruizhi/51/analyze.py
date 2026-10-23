"""Descriptive policy envelope over the already frozen sweep; no new designs."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('runs',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    raw=a.runs.read_bytes();runs=json.loads(raw);groups=defaultdict(lambda:defaultdict(list))
    for r in runs:groups[(r['fixture'],r['lanes'],r['consumer_cost'])][r['placement']].append(r)
    pairs=[]
    for key,placements in sorted(groups.items()):
        near=min(placements['near'],key=lambda x:(x['cycles'],x['name']))
        shared=min(placements['shared'],key=lambda x:(x['cycles'],x['name']))
        pairs.append(dict(fixture=key[0],lanes=key[1],consumer_cost=key[2],near=near['name'],shared=shared['name'],
            near_cycles=near['cycles'],shared_cycles=shared['cycles'],
            cycle_reduction_fraction=(shared['cycles']-near['cycles'])/shared['cycles'],
            boundary_wire_saved=shared['traffic']['wire']-near['traffic']['wire']))
    result={'schema':'issue51-policy-envelope/1','runs_sha256':hashlib.sha256(raw).hexdigest(),
        'scope':'post-sweep descriptive best among the same two windows and two scheduling policies; not global optimum/acceptance',
        'pairs':pairs,'summary':{'pairs':len(pairs),'near_faster':sum(x['near_cycles']<x['shared_cycles'] for x in pairs),
        'near_slower':sum(x['near_cycles']>x['shared_cycles'] for x in pairs),
        'minimum_cycle_reduction':min(x['cycle_reduction_fraction'] for x in pairs),
        'maximum_cycle_reduction':max(x['cycle_reduction_fraction'] for x in pairs)}}
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result['summary']))

if __name__=='__main__':main()
