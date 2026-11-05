"""Capture completed local-cost oracles, strict FastRoute probes and actual full scene."""
from pathlib import Path
import ast,subprocess,shlex,json,hashlib,base64,shutil,sys
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-37';assert not out.exists()
p=home/'control162-collect-proof36.py';tree=ast.parse(p.read_text(encoding='utf-8'));q=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets)))
q=q.replace('[160,161,165]','[170,171,172]')
start=q.index("for name in ['sready160-measured-budget-placement'");end=q.index('for seed in [1600',start)
q=q[:start]+'''for p in (b/'route-selection-102/sready170-fastroute-reprobe').rglob('*.json'):one(p)
for name in ['s-ready-local-density-bounds165.json','sready165-local-density-native-cap-config.json','sready165-default-replay-verification.json','s-ready-local-density-openroad-source157.json','sready171-fastroute24um-probe.json','sready172-fastroute24um-phase-probe.json','s-ready-fastroute24phase-source172.json']:
 p=b/'route-selection-102'/name;one(p)
 if not p.exists():continue
 d=json.loads(p.read_text());rows=d.get('tasks',[])
 if 'path'in d:rows=rows+[d]
 for row in rows:
  f=Path(row['path']);one(f);queue=f.parent.parent
  for t in [queue/'commands'/f.name,queue/'results'/f.name,queue/(f.stem+'.log')]:one(t);active.add(t)
for name in ['00-j-sready170-fastroute-probe.json','00-j-sready171-fastroute24um-probe.json','00-j-sready172-fastroute24um-phase-probe.json']:
 queue=b/'dynamic-05/node4'
 for t in [queue/'pending'/name,queue/'commands'/name,queue/'results'/name,queue/(Path(name).stem+'.log')]:one(t)
for folder in ['router-fastroute-preflight-170','router-fastroute24-preflight-171','router-fastroute24phase-preflight-172']:
 for p in (b/folder).rglob('*'):
  if p.is_file()and p.suffix in ['.json','.log','.tcl','.def','.lef','.rpt','.tsv']:one(p)
'''+q[end:]
q=q.replace('[1600,1601,1602,1603,1604,1610,1611,1620,1621,1622,1700,1701,1702,1703,1704]','[1700,1701,1702,1703,1704]')
q=q.replace("['measured-placement-native-residual-160','measured-placement-native-pin-load-160','clear-placement-native-residual-161','clear-placement-native-pin-load-161','local-density-native-residual-165','local-density-native-pin-load-165']","['local-density-native-residual-165','local-density-native-pin-load-165']")
q=q.replace('[1630,1631]','[1690,1691,1770]').replace("'sready163clear-acceptance-'+str(seed)","('sready177fast-'if seed==1770 else'sready169local-')+'acceptance-'+str(seed)")
q=q.replace('Measured native/pin placement budgets, exact64 trial-byte replays and default placement identity, clear1620/21/22 necessary bounds, actual1630/31 full physical queues, actual local-congestion165 source and diagnostic queues. Not joint qualification.',
 'Completed64 C++ versus direct Python local-density cost oracles, exact16 old-default trial bytes/placement identity, all five actual native-ground/input-pin bounds, nine previous mature routes plus1770 FastRoute full original seven gates. Preserve170 global congestion and171 off-grid failure;172 actual three detailed-route/strict original grid/checkerboard/flood plus9 negative checks pass. No joint qualification.')
compile(q,'collect_actual_proof37','exec')
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 blob=base64.b64decode(encoded);assert hashlib.sha256(blob).hexdigest()==row['sha256']and len(blob)==row['bytes'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob);copied+=1
helpers=[]
names=['control162-local-density-diagnostic164.py','control162-local-density-compare166.py','control162-local-density166.json','control162-local-cut-diagnostic167.py','control162-local-cut167.json','control162-default-replay-verify166.py','control162-local-density-native-status166.py','control162-local-density-routes169.py','control162-local-route-status169.py','control162-extend-collectors169.py','control162-read-fastroute-reference170.py','control162-openroad-fastroute-reference170/index.json','control162-fastroute-probe-launch170.py','control162-fastroute-finer-probe171.py','control162-fastroute-failure171.py','control162-fastroute-phase-probe172.py','control162-fastroute-full177.py','control162-probe-summary.py','control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py','control162-collect-proof37.py']
for name in names:
 p=out/'helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(home/name,p);helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
test=json.loads(subprocess.check_output([sys.executable,str(home/'control162-residual-budget-test160.py')],encoding='utf-8'));assert test['passed'];test['tested_module_sha256']=hashlib.sha256((repo/'project/experiments/control_v1/placement_residual_budget.py').read_bytes()).hexdigest();p=out/'helpers/actual-local-budget-regression.json';p.write_text(json.dumps(test,indent=2)+'\n');helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
d['helpers']=helpers;d['copied_count']=copied;(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-37/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
