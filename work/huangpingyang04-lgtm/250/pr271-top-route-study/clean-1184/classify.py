from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys


root, routing, report=map(Path,sys.argv[1:])
input_dir=root/'precheck-final'
origin=root.parent/'hpy-pr271-top-hsVf4b/inputs'
spec=json.loads((input_dir/'derived-spec.json').read_bytes())
result=json.loads((routing/'routes.json').read_bytes())
assert result['geometry_check']['passed']
with (origin/'top-1184-no-u0-dma/nets.tsv').open() as stream:
    families={r['net_id']:r['family'] for r in csv.DictReader(stream,delimiter='\t')}
assert len(families)==1184 and not set(result['routes'])&set(result['failed'])
assert set(result['routes'])|set(result['failed'])==set(families)
rows=list(csv.DictReader((report/'causes.tsv').open(),delimiter='\t'))
checked={spec['nets'][int(r['index'])]['id'] for r in rows}
assert checked==set(result['failed']) and len(rows)==len(checked)
ox,oy=spec['technology']['origin']
step=spec['technology']['access_pitch']
scale=spec['units']['dbu_per_um'] if isinstance(spec['units'],dict) else 2000
floor=json.loads((origin/'placement.json').read_bytes())['boxes_dbu']
reasons=Counter(); regions=defaultdict(Counter); nearest_blocks=defaultdict(Counter)
standalone=Counter(); blocked_by=Counter()
with (report/'unresolved.tsv').open('w') as stream:
    out=csv.writer(stream,delimiter='\t',lineterminator='\n')
    out.writerow(['net_id','family','driver','sinks','cause','affected_pin','observed_region_x_um','observed_region_y_um','fixed_pins_only','blocking_nets_on_one_candidate'])
    for r in rows:
        net=spec['nets'][int(r['index'])]
        reason=r['status']; reasons[reason]+=1
        standalone[r['standalone_status']]+=1
        if int(r['blocking_nets'])>=0: blocked_by[int(r['blocking_nets'])]+=1
        x,y=int(r['location_x']),int(r['location_y'])
        pin=int(r['failed_pin'])
        name=([net['driver']]+net['sinks'])[pin] if pin>=0 else ''
        location=() if x<0 else (round((ox+x*step)/scale,1),round((oy+y*step)/scale,1))
        if name: regions[reason][name.split('/')[0]]+=1
        elif location: regions[reason][','.join(map(str,location))]+=1
        if location:
            gx,gy=ox+x*step,oy+y*step
            def distance(entry):
                a,b,c,d=entry[1]
                return (max(0,a-gx,gx-c)**2+max(0,b-gy,gy-d)**2, entry[0])
            nearest_blocks[reason][min(floor.items(),key=distance)[0]]+=1
        out.writerow([net['id'],families[net['id']],net['driver'],','.join(net['sinks']),reason,name,
                      *(location or ('','')),r['standalone_status'],r['blocking_nets']])
summary={'requested':1184,'routed':len(result['routes']),'unresolved':len(result['failed']),'breakdown':dict(reasons),
         'families':result['evidence'],'regions':{k:dict(v.most_common(12)) for k,v in regions.items()},
         'approximate_nearest_blocks':{k:dict(v.most_common()) for k,v in nearest_blocks.items()},
         'standalone':dict(standalone),'blocking_histogram':dict(blocked_by),
         'geometry_check':result['geometry_check'],'scope':'fixed final occupancy; channel coordinates are 320um bins of conflicts on one isolated candidate'}
print(json.dumps(summary,sort_keys=True,indent=2))
