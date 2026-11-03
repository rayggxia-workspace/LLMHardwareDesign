"""Read current physical gates compactly; no task mutation."""
import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';seeds=set()
for name in ['s-ready-upper-source140.json','s-ready-capacity-upper-source140.json','s-ready-capacity-refill-source140.json','s-ready-cap-proof141-refill-source140.json','s-ready-congestion-source142.json','s-ready-congestion-followup-source142.json','s-ready-halo-routes-source142.json','s-ready-cache-source143.json','s-ready-cache-refill-source143.json','s-ready-history-product-source144.json','s-ready-history-product-refill-source144.json','s-ready-segment-source145.json','s-ready-openroad-source156.json','s-ready-openroad-halo-source156.json','s-ready-openroad-source157.json','s-ready-internal-channel-openroad-source157.json','s-ready-clear-placement-openroad-source157.json','s-ready-local-density-openroad-source157.json','s-ready-fastroute24phase-source172.json','s-ready-cpp-shortwire-source172.json','s-ready-cpp-weighted-local-source172.json','s-ready-balanced-fast-source172.json','s-ready-balanced-cpp-source172.json','s-ready-exact-fast-source172.json','s-ready-exact-cpp-source172.json','s-ready-initial-order-source213.json','s-ready-cugr24phase-source172.json','s-ready-cpp-localdensity-source172.json']:
 p=b/'route-selection-102'/name
 if not p.exists():continue
 for task in json.loads(p.read_text())['tasks']:
  s=task['spec'];a=s['args']
  if s['script']=='system_upper.py'and'--seed'in a:seeds.add(int(a[a.index('--seed')+1]))
done=[];progress=[]
for seed in sorted(seeds):
 p=c/'upper-candidates'/str(seed)
 for stage in ['route','geometry','pg-audit','timing/low','timing/base','timing/high','delivery','delivery-after-final-receipts']:
  r=p/stage/'receipt.json'
  if r.exists():
   d=json.loads(r.read_text());done.append(dict(seed=seed,stage=stage,passed=d.get('passed'),error=d.get('error'),whole=d.get('whole_system_qualified')))
 if seed not in [1411,1413,1431,1441,1443,1447,1460,1412,1454,1440,1452,1510,1432,1433,1444,1493,1491,1494,1450,1410,1514,1445,1446]:
  rounds=[];conflicts=[]
  for log in (p/'route').glob('trial-*/router.log'):
   with log.open('rb')as f:f.seek(max(0,log.stat().st_size-9000));lines=f.read().decode(errors='replace').splitlines()
   parsed=[]
   for line in lines:
    try:parsed.append(json.loads(line))
    except ValueError:pass
   rr=[d['round']for d in parsed if'round'in d];cc=[d['conflict_nodes']for d in parsed if'conflict_nodes'in d]
   if rr:rounds.append(max(rr))
   if cc:conflicts.append(cc[-1])
  if rounds:progress.append(dict(seed=seed,round_min=min(rounds),round_max=max(rounds),best_recent_conflicts=min(conflicts)if conflicts else None))
queues=[]
for fam,node in [(5,2),(2,3),(5,4),(3,5),(2,6),(2,7),(4,25),(2,26)]:
 p=b/('dynamic-%02d'%fam)/('node'+str(node))/'queue-state.json';d=json.loads(p.read_text());queues.append(dict(node=node,active=len(d['active']),slots=d['slots'],cpus_per_slot=d['cpus_per_slot'],memory_rejections=sum(not v['admitted']for v in d.get('memory_admissions',[]))))
print(json.dumps(dict(completed_physical_gates=done,queues=queues,progress=progress)))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
