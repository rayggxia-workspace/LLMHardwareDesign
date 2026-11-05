from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';record=b/'route-selection-102/sready555-s-local-direction-controls';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
template=json.loads((b/'route-selection-102/sready540-s-translated-full-upper/tasks.json').read_text())['tasks'];assert len(template)==7
for seed,cost,folder in [(5550,'8','dynamic-05/node2'),(5551,'32','dynamic-04/node25')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-5400.json').read_text().replace('/upper-candidates/5400/','/upper-candidates/'+str(seed)+'/'))
 for old in template:
  spec=json.loads(json.dumps(old['spec']));assert spec['source_root']==str(b/'source-537')
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5400/','/upper-candidates/'+str(seed)+'/').replace('acceptance-5400.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];assert a[a.index('--reuse-placement')+1]==str(root/'cap-candidates/5380')and a[a.index('--seed')+1]=='4661'and a[a.index('--route-ordinary-congestion-scale')+1]=='64'and '--route-ordinary-search-margin'not in a
   if '--route-nonpreferred-cost'in a:a[a.index('--route-nonpreferred-cost')+1]=cost
   else:a+=['--route-nonpreferred-cost',cost]
  p=b/folder/'pending'/(Path(old['path']).stem.replace('sready540','sready555').replace('5400',str(seed))+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Two separate current453/S5380 full seven-stage direction controls vs5400: only nonpreferred cost2->8 or32; same actual placement/RNG4661/h256/adaptive/ordinary64/no window. Actual525 exercised all direction costs including finite-resource branch; physical wire budgets and all final source gates unchanged. Queue before exact-own old359 fixed pools3730/3733 replacement, after actual2/1 failed trials without refill; no old-trial infeasibility claim. Preserve all prior outputs/source/spec and parent allocations, current453 and foreign/R tasks. New finite64attempt pools each16active dynamic refill and real memory admission unchanged.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=[5550,5551])))
