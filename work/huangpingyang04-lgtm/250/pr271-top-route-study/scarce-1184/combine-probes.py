"""Keep the rarer of the whole-connection and near-branch corridor samples."""
from collections import Counter
import csv
import json
from pathlib import Path
import sys


def rows(path):
    with path.open() as stream:
        return {tuple(int(r[k]) for k in ('net_index','pin_index')):
                tuple(int(r[k]) for k in ('sampled_corridors','span'))
                for r in csv.DictReader(stream,delimiter='\t')}


base=rows(Path(sys.argv[1]))
near=rows(Path(sys.argv[2]))
assert len(base)==1674 and set(near)<=set(base)
profile=Counter(); improved_priority=0; short=0
with Path('ranked-options.tsv').open('w') as stream:
    print('net_index\tpin_index\tsampled_corridors\tspan',file=stream)
    for pair,(ways,length) in sorted(base.items()):
        shorter,local_length=near.get(pair,(ways,length))
        assert local_length<=length
        new=min(ways,shorter)
        profile[new]+=1
        improved_priority+=new<ways
        short+=0<local_length<length and local_length<=3000
        print(*pair,new,local_length,sep='\t',file=stream)
report={'nets':1184,'targets':len(base),'sampled_corridors':dict(profile),'near_branch_probes':len(near),
        'raised_priority':improved_priority,'shorter_branch_at_most_600um':short,
        'initial_top':{'M11':0,'M12':0,'V11':0}}
Path('options.json').write_text(json.dumps(report,sort_keys=True)+'\n')
print(report)
