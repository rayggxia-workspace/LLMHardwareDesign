"""Cross-reference every admitted original terminal to its archived M10 conductor."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import runpy
import sys


root=Path.cwd()
mod=runpy.run_path(str(root/'refresh-fanout.py'))
geo=mod['geo']
origin=root.parent/'hpy-pr271-top-hsVf4b/inputs'
original=geo.read(origin/'top-1184-no-u0-dma/algorithm2-input.json')
current=geo.read(root/'precheck-final/derived-spec.json')
overlay=geo.read(root/'precheck-final/lower-evidence.json')
assert original['nets']==current['nets'] and len(original['nets'])==1184
floor=geo.read(origin/'placement.json')
source_pins=defaultdict(set)
for n in original['nets']:
    for p in [n['driver'],*n['sinks']]: source_pins[p.split('/')[0]].add(p)
moved={r['pin']:r for r in overlay['rebound']}
audit=Counter(); unmatched=defaultdict(list); receipts={}
for block, pins in sorted(source_pins.items()):
    _,src,plan=mod['info'](block,overlay)
    _,native=mod['offset_shapes'](src,floor['placement_dbu'][block],plan['area'])
    for p in pins:
        terminal,=original['pins'][p]
        owners=native[tuple(terminal)]
        if len(owners)!=1 or -1 in owners:
            unmatched[block].append({'pin':p,'owners':sorted(owners)})
            continue
        if p in moved:
            assert moved[p]['native_owner'] in owners and moved[p]['old_m10']==terminal
            assert current['pins'][p]==[moved[p]['new_m10']]
        else:
            assert original['pins'][p]==current['pins'][p]
        audit[block]+=1
    receipts[block]={'archive_sha256':geo.sha(src),'matched':audit[block],'requested':len(pins)}
print(json.dumps({'unique_terminal_pins':sum(map(len,source_pins.values())),
                  'unique_native_ownership_confirmed':sum(audit.values()),'unmatched':dict(unmatched),
                  'by_block':receipts,'placement_sha256':geo.sha(origin/'placement.json')},sort_keys=True,indent=2))
