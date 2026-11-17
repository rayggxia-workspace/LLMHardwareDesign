import json,copy,pathlib,traceback,hashlib,csv,statistics
from check import verify,digest
from geometry import segment_shape,via_shapes
P=pathlib.Path;root=P(__file__).resolve().parent
b=P('/public/home/yuzelu/project-circuit/side-top-pressure-20261117')
old=P('/public/home/yuzelu/PingyangHuang/hpy-cu-p0-gate-top.2Ovvdrcq/landing-closure.xh8Q7CUU')
bs=json.loads((b/'spec.json').read_text());br=json.loads((b/'route-fixed.json').read_text());am=json.loads((root/'A-mapped.json').read_text())
out={}
for label,spec,result in [('B-full',bs,br)]:
 try:out[label]=verify(spec,result)
 except Exception as e:out[label]={'passed':False,'error':str(e),'trace':traceback.format_exc()}
# A: only C/U checked; P copper retained as obstacles, not electrically qualified.
spec=copy.deepcopy(bs);spec['nets']=[n for n in bs['nets'] if all(p.split('.')[0] in ('C0','U0') for p in [n['driver'],*n['sinks']])]
active={p for n in spec['nets'] for p in [n['driver'],*n['sinks']]};spec['pins']={p:bs['pins'][p] for p in active}
routes=am['routes'];targets={n['id'] for n in spec['nets']};ob=[]
for name,r in routes.items():
 if name in targets:continue
 for s in r['segments']:
  layer,rect=segment_shape(s['layer'],s['a'],s['b'],spec['technology']);ob.append({'layer':layer,'rect':rect})
 for v in r['via10']:
  for layer,rect in via_shapes('via10',v['at'],spec['technology']):ob.append({'layer':layer,'rect':rect})
 for v in r['via11']:
  for layer,rect in via_shapes('via11',v,spec['technology']):ob.append({'layer':layer,'rect':rect})
spec['obstacles']=ob
res=copy.deepcopy(br);res['routes']={n:routes[n] for n in targets};res['spec_sha256']=digest(spec);res['context']=spec['context'];res['failed']={};res['status']='geometry_complete'
(root/'A-cu-audit-spec.json').write_text(json.dumps(spec))
try:out['A-CU-with-P-obstacles']=verify(spec,res)
except Exception as e:out['A-CU-with-P-obstacles']={'passed':False,'error':str(e),'trace':traceback.format_exc()}
out['lengths']={}
for label,rs in [('A',routes),('B',br['routes'])]:
 groups={}
 for name,r in rs.items():
  pins=[x['pin'] for x in r['via10']]
  if any(p.startswith('P') for p in pins):continue
  g='CU' if all(p.split('.')[0] in ('C0','U0') for p in pins) else 'GS'
  groups.setdefault(g,[]).append(sum(abs(s['a'][0]-s['b'][0])+abs(s['a'][1]-s['b'][1]) for s in r['segments'])/2000)
 for g,values in groups.items():
  values.sort();out['lengths'][label+'-'+g]={'count':len(values),'min_um':values[0],'median_um':statistics.median(values),'p90_um':values[round(.9*(len(values)-1))],'max_um':values[-1]}
f=json.loads(P('/public/home/yuzelu/project-circuit/algo2-current-blocks-20261116/physical-binding/F0-macro-components.json').read_text())['endpoints']
out['F_S_existing_drivers']={k:v.get('parent_physical_terms') for k,v in f.items() if k in ['F0.S.req_valid']+['F0.S.req_data[%d]'%i for i in range(32)]}
out['scope']='Geometry and endpoint preflight only; no new RC/STA. P retained as static metal obstacles.'
(root/'audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
