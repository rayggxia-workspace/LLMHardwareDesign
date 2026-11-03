from pathlib import Path
import json,hashlib,time,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';q=b/'dynamic-06/node26';record=b/'route-selection-102/sready549-s-local-direction-cost-grid';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
job=subprocess.check_output(['scontrol','show','job','96222','-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in job and 'JobName=yzl-ctl162-rec237n26'in job and 'JobState=PENDING'in job and 'NumCPUs=96'in job and 'ReqNodeList=node26 'in job
assert not(q/'queue-state.json').exists()
for p in(q/'pending').glob('*.json'):assert(q/'results'/p.name).exists(),str(p)
for folder in ['r256-ordinary-window-regression-525','r256-padding-program-events-473','r256-padding-program-event-audit-480']:assert json.loads((b/folder/'receipt.json').read_text())['passed']
template=json.loads((b/'route-selection-102/sready540-s-translated-full-upper/tasks.json').read_text())['tasks'];assert len(template)==7
for i,(cost,scale)in enumerate((c,s)for c in ['8','32']for s in ['16','64','256']):
 seed=5490+i;config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-5400.json').read_text().replace('/upper-candidates/5400/','/upper-candidates/'+str(seed)+'/'))
 for old in template:
  spec=json.loads(json.dumps(old['spec']));assert spec['source_root']==str(b/'source-537')
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5400/','/upper-candidates/'+str(seed)+'/').replace('acceptance-5400.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];assert a[a.index('--reuse-placement')+1]==str(root/'cap-candidates/5380')and a[a.index('--seed')+1]=='4661'and a[a.index('--route-ordinary-congestion-scale')+1]=='64'and '--route-ordinary-search-margin'not in a
   a[a.index('--route-ordinary-congestion-scale')+1]=scale
   if '--route-nonpreferred-cost'in a:a[a.index('--route-nonpreferred-cost')+1]=cost
   else:a+=['--route-nonpreferred-cost',cost]
   a+=['--route-ordinary-search-margin','64']
  p=q/'pending'/(Path(old['path']).stem.replace('sready540','sready549').replace('5400',str(seed))+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,parent_details_before=job,parent_job=96222,new_parent_jobs=0,whole_system_qualified=False,scope='Prepare exactly six independent16CPU current453/S5380 complete seven-stage candidate chains for existing own eighth96CPU pending node26, whose queue had no unfinished tasks and has not started. Six-row bounded search grid nonpreferred cost8/32 x ordinary congestion16/64/256, same margin64 andRNG4661/h256/adaptive, not a single-variable comparison to5400. Every parameter is supported by actual525 regression; final real edge/short/resource/geometry/nativeXOR/PG/threeRC300MHz/current453function/joint acceptance remains unchanged. All345fixed instances/23 native masks, S-only5380 reconstructed placement and all states unchanged. Actual473/480 event audit prerequisite retained. No running task cancelled, no extra allocation, foreign/R tasks untouched. Existing controller admits at most6x16 only when real aggregate forecast*1.2+16GiB fits MemAvailable and refills next eligible work as steps end; parent remains Resources-pending and queued candidates are not execution/results.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=list(range(5490,5496)),existing_pending_job=96222,new_jobs=0)))
