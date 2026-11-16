from collections import Counter
from pathlib import Path
import sys

import lower_rules as geo


root=Path.cwd()
pre=root/'precheck-first'
dest=Path(sys.argv[1]); dest.mkdir()
previous=geo.read(pre/'lower-evidence.json')
s=geo.read(pre/'derived-spec.json')
assert len(s['nets'])==1184
records={r['pin']:r for r in previous['rebound']}
per_block={}
checked=set()
new=[]
for folder in map(Path,sys.argv[2:]):
    proof=geo.read(folder/'fanout-verified.json')
    assert geo.sha(folder/'paths.txt')==proof['paths_sha256']
    b=proof['block']; assert b not in per_block
    assert proof['layout_sha256']==previous['placement_sha256']
    per_block[b]={k:v for k,v in proof.items() if k!='paths'}
    checked.add(b)
    for r in proof['paths']:
        pin=r['pin']; assert pin.split('/')[0]==b
        assert s['pins'][pin]==[r['extension_from']]
        s['pins']['frozen_escape_source/'+pin]=[r['old_m10']]
        s['pins'][pin]=[r['new_m10']]
        records[pin]=r
        new.append(r)
assert checked=={'U0','C0','P0','P1','P2','mc','sw'}
assert sum(p['checked_old_paths'] for p in per_block.values())==len(previous['rebound'])
previous['rebound']=list(records.values())
previous['endpoint_count']=len(records)
previous['route_count']=len({r['net'] for r in records.values()})
previous['clean_1184_fanout']={'existing_geometry_rechecked':sum(x['checked_old_paths'] for x in per_block.values()),
    'new_endpoints':len(new),'new_ids':new,'new_by_block':dict(Counter(r['block'] for r in new)),
    'previous_access_failed_nets_helped':len({r['net'] for r in new if r['prior_access_failure']}),'per_block':per_block}
geo.write(dest/'lower-evidence.json',previous)
s['context']['lower_escape_overlay_sha256']=geo.sha(dest/'lower-evidence.json')
geo.write(dest/'derived-spec.json',s)
print('verified_fanouts',len(new),'blocks',dict(Counter(r['block'] for r in new)))
