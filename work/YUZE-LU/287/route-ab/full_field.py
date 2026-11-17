"""All non-P routed nets; reuse exact scenes, never sample the target list."""
import concurrent.futures,gzip,hashlib,json,pathlib,subprocess,time
P=pathlib.Path;root=P(__file__).resolve().parent
binary=P('/public/home/yuzelu/PingyangHuang/issue-199-field-xXrAwSOn/job-98267/field_row')
source=P('/public/home/yuzelu/project-circuit/issue287-route-ab-20261117')
spec=json.loads(P('/public/home/yuzelu/project-circuit/side-top-pressure-20261117/spec.json').read_text())
nets={n['id']:n for n in spec['nets']};jobs=[]
for label,path in [('A',source/'A-mapped.json'),('B',P('/public/home/yuzelu/project-circuit/side-top-pressure-20261117/route-fixed.json'))]:
 routes=json.loads(path.read_text())['routes'];scene=source/('field-'+label)/'field.in'
 for i,name in enumerate(sorted(routes)):
  r=routes[name];pins=[v['pin'] for v in r['via10']]
  if any(p.startswith('P') for p in pins):continue
  n=nets[name];assert set(pins)==set([n['driver']]+n['sinks'])
  jobs.append(dict(scheme=label,net=name,master=i,driver=n['driver'],sinks=n['sinks'],group='CU' if all(p.split('.')[0] in ('C0','U0') for p in pins) else 'GS',length_um=sum(abs(s['a'][0]-s['b'][0])+abs(s['a'][1]-s['b'][1]) for s in r['segments'])/2000,via10=len(r['via10']),via11=len(r['via11']),scene=str(scene),scene_sha256=hashlib.sha256(scene.read_bytes()).hexdigest()))
assert sum(j['scheme']=='A' for j in jobs)==306
assert sum(j['scheme']=='B' for j in jobs)==340
(root/'inventory.json').write_text(json.dumps(jobs,indent=2))
def run(j):
 key=j['scheme']+'-'+j['net'];dest=root/(key+'.summary.json')
 if dest.exists():return json.loads(dest.read_text())
 start=time.time()
 with (root/(key+'.log')).open('wb') as log:
  p=subprocess.run([str(binary),j['scene'],str(j['master']),'8',str(104729+4099*j['master']),str(1<<18)],stdout=subprocess.PIPE,stderr=log)
 with gzip.open(root/(key+'.raw.json.gz'),'wb') as f:f.write(p.stdout)
 out=dict(j,exit=p.returncode,elapsed_s=time.time()-start,raw_sha256=hashlib.sha256(p.stdout).hexdigest())
 if p.returncode==0:
  r=json.loads(p.stdout);i=r['master'];v=r['values'];total,sigma=v[i]
  out.update(self_fF=total,sigma_fF=sigma,relative_sigma=sigma/total,ground_fF=-r['ground'][0],coupling_signed_fF=-sum(x[0] for k,x in enumerate(v) if k!=i),conservation_error_fF=sum(x[0] for x in v)+r['ground'][0],walks=r['walks'],coupling_row=v)
 dest.write_text(json.dumps(out));return out
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for k,result in enumerate(pool.map(run,jobs),1):
  print(json.dumps(dict(done=k,total=len(jobs),net=result['net'],scheme=result['scheme'],exit=result['exit'])),flush=True)
results=[json.loads((root/(j['scheme']+'-'+j['net']+'.summary.json')).read_text()) for j in jobs]
(root/'all-results.json').write_text(json.dumps(results))
assert all(r['exit']==0 for r in results)
print('ALL_646_COMPLETE',flush=True)
