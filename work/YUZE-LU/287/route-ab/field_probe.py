import json,pathlib,subprocess,concurrent.futures,hashlib
P=pathlib.Path;root=P(__file__).resolve().parent
binary=P('/public/home/yuzelu/PingyangHuang/issue-199-field-xXrAwSOn/job-98267/field_row')
Z={'M10':(10.09,12.09),'M11':(12.89,14.89),'M12':(15.69,17.69),'V10':(12.09,12.89),'V11':(14.89,15.69)}
jobs=[];index={}
for label,path in [('A',root/'A-mapped.json'),('B',P('/public/home/yuzelu/project-circuit/side-top-pressure-20261117/route-fixed.json'))]:
 routes=json.loads(path.read_text())['routes'];names=sorted(routes);groups={};scene=[]
 for i,name in enumerate(names):
  r=routes[name];boxes=set()
  def box(layer,a,b):
   z0,z1=Z[layer];boxes.add((min(a[0],b[0])/2000-1,min(a[1],b[1])/2000-1,z0,max(a[0],b[0])/2000+1,max(a[1],b[1])/2000+1,z1))
  for s in r['segments']:box(s['layer'],s['a'],s['b'])
  for v in r['via10']:
   for layer in ('M10','V10','M11'):box(layer,v['at'],v['at'])
  for v in r['via11']:
   for layer in ('M11','V11','M12'):box(layer,v,v)
  boxes=sorted(boxes);nodes=[tuple((b[k]+b[k+3])/2 for k in range(3)) for b in boxes];scene.append((boxes,nodes))
  pins=[v['pin'] for v in r['via10']]
  if any(p.startswith('P') for p in pins):continue
  group='CU' if all(p.split('.')[0] in ('C0','U0') for p in pins) else 'GS'
  length=sum(abs(s['a'][0]-s['b'][0])+abs(s['a'][1]-s['b'][1]) for s in r['segments'])/2000
  groups.setdefault(group,[]).append((length,i,name,pins))
 directory=root/('field-'+label);directory.mkdir(exist_ok=True);field=directory/'field.in'
 with field.open('w') as f:
  print(3.9,len(scene),file=f)
  for boxes,nodes in scene:
   print(len(boxes),len(nodes),file=f)
   for b in boxes+nodes:print(*b,file=f)
 for group,rows in groups.items():
  rows.sort()
  for tag,idx in [('median',len(rows)//2),('longest',len(rows)-1)]:
   length,i,name,pins=rows[idx];jobs.append((directory,i));index[label+'-'+group+'-'+tag]={'net':name,'master':i,'length_um':length,'pins':pins,'field':str(field),'field_sha256':hashlib.sha256(field.read_bytes()).hexdigest()}
(root/'field-probe-index.json').write_text(json.dumps({'solver_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'samples':index,'scope':'Upper-only research dielectric, actual routes and M10 pads; P geometry retained; not full lower coupling or STA.'},indent=2))
def run(job):
 d,i=job
 with (d/f'row-{i}.json').open('w') as f,(d/f'row-{i}.log').open('w') as log:
  rc=subprocess.call([str(binary),str(d/'field.in'),str(i),'2',str(104729+4099*i),str(1<<18)],stdout=f,stderr=log)
 return {'case':str(d),'master':i,'exit':rc}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(run,jobs))
(root/'field-probe-status.json').write_text(json.dumps(results,indent=2));assert all(r['exit']==0 for r in results)
