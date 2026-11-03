import subprocess,shlex
q=r'''from pathlib import Path
import json,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359';record=b/'route-selection-102/sready393-native-budget-refill';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();audit=b/'r256-reset53-final-function-audit-392/receipt.json';assert json.loads(audit.read_text())['passed']
template=[r for r in json.loads((b/'route-selection-102/sready389-measured-route-budget/tasks.json').read_text())['tasks']if '-3890'in Path(r['path']).name];assert len(template)==7;rows=[]
for seed,cost,scale,queue in [(3930,32,0,'dynamic-07/node7'),(3931,8,1,'dynamic-02/node6')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-3890.json').read_text().replace('/upper-candidates/3890/','/upper-candidates/'+str(seed)+'/'))
 for row in template:
  spec=json.loads(json.dumps(row['spec']))
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/3890/','/upper-candidates/'+str(seed)+'/').replace('acceptance-3890.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];a[a.index('--seed')+1]=str(seed);a[a.index('--route-nonpreferred-cost')+1]=str(cost);a+=['--route-congestion-scale',str(scale)];spec['requires']+=[str(audit)]
  p=b/queue/'pending'/(Path(row['path']).stem.replace('sready389','sready393').replace('3890',str(seed))+'.json');assert not p.exists();t=p.with_suffix('.tmp');t.write_text(json.dumps(spec));t.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,actual_new_final_program_audit_sha256=sha(audit),whole_system_qualified=False,scope='Natural dynamic refill only. Node7 actual current8program three-initial run completed and frees fourth16CPU slot; node6 independent candidate awaits natural completion of retained old3441 bounded congestion diagnostic. Two actual reset53 current345instance measured native/input finite-budget variants (direction32; direction8/congestion1) retain all original seven route/geometry/PG/threeRC300MHz/joint gates. No extra allocations, no steps cancelled, no foreign/R changes. Native23 types remain fixed. Actual function success is not system physical qualification.'),indent=2));print(json.dumps(dict(queued=len(rows),record=str(record))))
'''
compile(q,'refill393','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
