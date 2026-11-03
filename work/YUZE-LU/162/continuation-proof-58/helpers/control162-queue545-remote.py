from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';record=b/'route-selection-102/sready545-s-local-controlled-searches';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
template=json.loads((b/'route-selection-102/sready540-s-translated-full-upper/tasks.json').read_text())['tasks'];assert len(template)==7
for seed,scale,window in [(5450,'256',None),(5451,'64','64')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-5400.json').read_text().replace('/upper-candidates/5400/','/upper-candidates/'+str(seed)+'/'))
 for old in template:
  spec=json.loads(json.dumps(old['spec']));assert spec['source_root']==str(b/'source-537')
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5400/','/upper-candidates/'+str(seed)+'/').replace('acceptance-5400.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];assert a[a.index('--reuse-placement')+1]==str(root/'cap-candidates/5380')and a[a.index('--seed')+1]=='4661'and a[a.index('--route-ordinary-congestion-scale')+1]=='64'and '--route-ordinary-search-margin'not in a
   a[a.index('--route-ordinary-congestion-scale')+1]=scale
   if window:a+=['--route-ordinary-search-margin',window]
  p=b/'dynamic-03/node5/pending'/(Path(old['path']).stem.replace('sready540','sready545').replace('5400',str(seed))+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Two controlled full seven-stage chains from actual5380 S-only placement:5450 differs5400 only ordinary congestion scale64->256;5451 differs5400 only ordinary margin0->64. Both parameters exercised by actual525 regression; actual5380 reconstructed all pins, constrained endpoints exact, low/base/high necessary violations0, current453 function and actual473/480 event audit passed. Same frozen source537, same345instances/23fixed native views/all states, sameRNG4661 and finite-resource/electrical budgets, no hardware changes or relaxed gates. Queue before exact-owned older359 fixed-pool replacement;16active trials and finite64attempt dynamic refill each, node5 4x16 ceiling and real memory gate unchanged. No success inferred from queue admission.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=[5450,5451])))
