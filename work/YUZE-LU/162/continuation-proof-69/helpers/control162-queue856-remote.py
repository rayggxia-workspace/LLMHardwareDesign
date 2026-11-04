from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-854';record=b/'route-selection-102/sready855-native-prefix-fullchains';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
assert (source/'freeze-import.json').exists()
def put(folder,name,spec):
 p=b/folder/'pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=b/'r256-native-prefix-regression-855'
template=[x for x in json.loads((b/'route-selection-102/sready589-zero-pattern-controlled/tasks.json').read_text())['tasks']if '-5890'in Path(x['path']).stem];assert len(template)==7
for seed,weight,folder in [(8560,'all','dynamic-08/node6'),(8561,'after-native','dynamic-03/node5')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-5890.json').read_text().replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/'))
 for old in template:
  spec=json.loads(json.dumps(old['spec']));assert spec['source_root']==str(b/'source-587');spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/').replace('acceptance-5890.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];assert '--route-ordinary-zero-pattern'in a and '--bidirectional-two-terminal'in a and a[a.index('--route-heuristic-weight')+1]=='256';assert a[a.index('--route-nonpreferred-cost')+1]=='2';assert a[a.index('--route-congestion-scale')+1]=='1';a[a.index('--route-congestion-scale')+1]='1';a+=['--route-weighted-bidirectional','--route-trace-phases','--route-ordinary-endpoint-escape','--route-ordinary-zero-maze','16384','--route-native-prefix-first','--route-pin-access',weight];a[a.index('--seed')+1]='4662';spec['forecast_gib']=64;spec['requires']+=[str(reg/'receipt.json'),str(b/'r256-maze-legacy45-byte-audit-858/receipt.json')]
  put(folder,Path(old['path']).stem.replace('sready589','sready855').replace('5890',str(seed)),spec)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Source854 default-off native-prefix-first, globally matched pin-access all/after-native, original finite-resource search and all final gates retained. All57cases/35negative plus51 actual byte replays required before fullscene admission. All16 active64attempts/16CPU/64GiB outer4GiB child, actual memory1.2+16 guard. Freeze native paths only after zero conflicts; native success is never full success. All selected original paths, failed attempts, raw sources retained. Node6 free slot after848/855; only own5451 node5 may be replaced after fresh identity guard.8 parents unchanged, c64 4x16/c96 6x16 dynamic refill. No system pass until all original7 stages independently pass.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=[8560,8561])))
