"""Compare independently checked, paired top-metal runs by logical net and local region."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(path):
    fields = {}
    for line in path.read_text().splitlines():
        key, separator, value = line.partition('=')
        if separator and key in {'slurm_job', 'slurm_step', 'node', 'params'}:
            fields[key] = value
    return fields


def region(point, windows):
    x,y = point
    for name,(l,b,r,t) in windows.items():
        if l<=x<=r and b<=y<=t:
            return name
    raise AssertionError('Supplemental candidate used outside all regions')


root, original = map(Path, sys.argv[1:])
spec = read(root/'input/derived-spec.json')
metadata = read(root/'candidate-regions.json')
routes = {a:read(root/a/'routes.json') for a in 'AB'}
arms = {a:log(root/a/'route.log') for a in 'AB'}
assert arms['A']['slurm_job']==arms['B']['slurm_job'] and arms['A']['slurm_step']!=arms['B']['slurm_step']
assert arms['A']['node']==arms['B']['node'] and arms['A']['params']==arms['B']['params']
assert routes['A']['candidate_sha256'] is None and routes['B']['candidate_sha256']==sha(root/'local-edges.tsv')
assert routes['A']['spec_sha256']==routes['B']['spec_sha256'] and routes['A']['context']==routes['B']['context']
assert all(r['geometry_check']['passed'] for r in routes.values())
with (original/'nets.tsv').open() as stream:
    families = {r['net_id']:r['family'] for r in csv.DictReader(stream,delimiter='\t')}
netset = {n['id'] for n in spec['nets']}
assert netset==set(families) and len(netset)==1184
assert Counter(families.values())=={'packet':1031,'decode.index.transport':153}
for a in 'AB':
    assert set(routes[a]['routes'])|set(routes[a]['failed'])==netset
    assert not set(routes[a]['routes'])&set(routes[a]['failed'])
    assert len(routes[a]['routes'])==routes[a]['geometry_check']['nets_checked']
    assert 'clean nets=1184 M11=0 M12=0 V11=0 restored=0' in (root/a/'route.log').read_text()
    assert 'upstream_matched=24' in (root/a/'route.log').read_text()
    arms[a]['timing']={k:float(v) for k,v in (p.split('=') for p in (root/a/'timing.txt').read_text().split())}
    arms[a]['geometry']=routes[a]['geometry_check']
    arms[a]['routed']=len(routes[a]['routes'])
    arms[a]['unrouted']=len(routes[a]['failed'])
    arms[a]['paths_sha256']=sha(root/a/'paths.txt')
    arms[a]['routes_sha256']=sha(root/a/'routes.json')
    arms[a]['log_sha256']=sha(root/a/'route.log')
    arms[a]['stage_trace']=[line for line in (root/a/'route.log').read_text().splitlines()
                            if line.startswith(('trunks placed=','short_branches','complete_before_repair=','repair tried=','done '))]

idsa, idsb = (set(routes[a]['routes']) for a in 'AB')
b_only, a_only = idsb-idsa, idsa-idsb
ox,oy = metadata['origin_dbu']; step=metadata['access_step_dbu']; pitch=21*step
wire_arcs = set(); via_arcs = set()
for line in (root/'local-edges.tsv').read_text().splitlines():
    x,y,l,xx,yy,ll=map(int,line.split())
    a=(ox+x*step,oy+y*step); b=(ox+xx*step,oy+yy*step)
    if l==ll: wire_arcs.add((l,*sorted((a,b))))
    else: via_arcs.add(a)
assert len(wire_arcs)==metadata['wire_arcs'] and len(via_arcs)==metadata['via11_arcs']
windows={}
for item in metadata['regions']:
    name=','.join(map(str,item['center_um']))
    l,b,r,t=item['lattice_bounds']; windows[name]=(ox+l*step,oy+b*step,ox+r*step,oy+t*step)


def touch_regions(route):
    hits=set()
    for s in route['segments']:
        x,y=s['a']; xx,yy=s['b']
        for name,(l,b,r,t) in windows.items():
            if max(x,xx)>=l and min(x,xx)<=r and max(y,yy)>=b and min(y,yy)<=t:
                hits.add(name)
    return hits


def extra_uses(net,route):
    access=[]
    for name in (net['driver'],*net['sinks']):
        for l,b,r,t in spec['pins'][name]:
            margin=spec['technology']['access_radius']
            access.append((l-margin,b-margin,r+margin,t+margin))
    def during_pin_access(a,b):
        x,y=a; xx,yy=b
        return any(l<=min(x,xx) and max(x,xx)<=r and bot<=min(y,yy) and max(y,yy)<=top for l,bot,r,top in access)
    uses=Counter(); symbols=Counter(); wire_len=0
    for s in route['segments']:
        a,b=tuple(s['a']),tuple(s['b']); layer=int(s['layer'][-1])-1
        if (layer,*sorted((a,b))) not in wire_arcs or during_pin_access(a,b): continue
        parallel=(a[1]-oy if layer==0 else a[0]-ox)
        if parallel%pitch:
            uses[region(a,windows)]+=1
            symbols['shifted_wire']+=1
            wire_len+=abs(a[0]-b[0])+abs(a[1]-b[1])
        else:
            symbols['split_primary_segment']+=1
    for p in route['via11']:
        if tuple(p) in via_arcs and not during_pin_access(p,p):
            uses[region(p,windows)]+=1
            symbols['nonuniform_via11']+=1
    return uses,symbols,wire_len


direct_regions=Counter(); passes_through=Counter(); direct_ids=[]; all_b_direct=0
with (root/'net-comparison.tsv').open('w') as stream:
    out=csv.writer(stream,delimiter='\t',lineterminator='\n')
    out.writerow(['net_id','family','driver','sinks','routed_A','routed_B','B_supplemental_wire_length_dbu',
                  'B_supplemental_via11','B_supplemental_regions_um','B_route_crosses_test_regions_um'])
    for n in spec['nets']:
        identifier=n['id']; fa=families[identifier]
        present=identifier in idsb
        uses,symbols,wire_len=Counter(),Counter(),0
        touched=set()
        if present:
            route=routes['B']['routes'][identifier]
            uses,symbols,wire_len=extra_uses(n,route)
            touched=touch_regions(route)
        all_b_direct+=bool(uses)
        if identifier in b_only:
            direct_regions.update(uses.keys())
            passes_through.update(touched)
            if uses:
                direct_ids.append({'id':identifier,'driver':n['driver'],'sinks':n['sinks'],'regions_um':sorted(uses),
                                   'shifted_wire_length_dbu':wire_len,'supplemental_via11':symbols['nonuniform_via11']})
        out.writerow([identifier,fa,n['driver'],','.join(n['sinks']),int(identifier in idsa),int(present),wire_len,
                      symbols['nonuniform_via11'],';'.join(sorted(uses)) or '-',';'.join(sorted(touched)) or '-'])

ids = [arms[a]['slurm_job']+'.'+arms[a]['slurm_step'] for a in 'AB']
receipt = subprocess.check_output(['sacct','-nP','-j',arms['A']['slurm_job'],'-o','JobID,State,Elapsed,ExitCode,NodeList'],
                                  universal_newlines=True)
slurm = {v[0]:dict(zip(('state','elapsed','exit','node'),v[1:])) for v in (line.split('|') for line in receipt.splitlines())}
assert all(slurm[n]['state']=='COMPLETED' and slurm[n]['exit']=='0:0' for n in ids)
print(json.dumps({'server_root':str(root),'jobs':slurm,'arm':arms,'candidate_regions':metadata,
                  'A_only':len(a_only),'B_only':len(b_only),'B_minus_A':len(idsb)-len(idsa),'common':len(idsa&idsb),
                  'B_only_by_family':dict(Counter(families[n] for n in b_only)),
                  'A_only_by_family':dict(Counter(families[n] for n in a_only)),
                  'B_only_direct_supplemental':len(direct_ids),'B_only_direct_regions':dict(direct_regions),
                  'B_only_passing_regions':dict(passes_through),'all_B_direct_supplemental':all_b_direct,
                  'B_only_direct_samples':direct_ids[:16],
                  'inputs':{f:sha(root/'input'/f) for f in ('graph.txt','derived-spec.json','lower-evidence.json','access.tsv')},
                  'comparison_sha256':sha(root/'net-comparison.tsv')},sort_keys=True,indent=2))
