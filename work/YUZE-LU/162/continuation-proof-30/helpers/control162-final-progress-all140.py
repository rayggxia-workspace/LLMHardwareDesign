import subprocess,shlex
q=r'''from pathlib import Path
import json,time,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391'
for candidate in [1390,1391]:
 p=b/'s-ready-composition-01'/str(candidate)/'final-composition';r=p/'receipt.json';print('program',candidate,json.loads(r.read_text()).get('passed')if r.exists()else'active')
 if not r.exists():
  folders=list(p.rglob('Vblock_feed_s_macro.mk'))
  for f in folders:
   folder=f.parent;print('S build cpp,objects',len(list(folder.glob('Vblock_feed_s_macro*.cpp'))),len(list(folder.glob('Vblock_feed_s_macro*.o'))))
for seed in [1410,1411,1412,1413,1430,1431,1432,1433,1440,1441,1442,1443,1444,1445,1446,1447,1448,1449,1450,1451,1452,1453,1454,1460,1461,1462,1480,1481,1482,1490]:
 if seed==1411:print('route',seed,'retired: slow coupled-weight ordering, exact own slot used for passed128-case regression and1460');continue
 if seed==1413:print('route',seed,'retired: slow coupled-weight16 ordering, exact own slot used for1462 after full regression');continue
 if seed in [1431,1441,1443,1447]:print('route',seed,'retired: actual pin-load necessary condition excludes placement1421');continue
 p=base/'upper-candidates'/str(seed);states={};logs=[]
 for name in ['route','geometry','pg-audit','timing/low','timing/base','timing/high','delivery']:
  r=p/name/'receipt.json'
  if r.exists():
   d=json.loads(r.read_text());states[name]=dict(passed=d.get('passed'),error=d.get('error'),whole=d.get('whole_system_qualified'))
 for f in (p/'route').glob('trial-*/router.log'):
  with f.open('rb')as stream:stream.seek(max(0,f.stat().st_size-600));lines=stream.read().decode(errors='replace').splitlines()
  if lines:
   try:logs.append(json.loads(lines[-1]))
   except ValueError:logs.append(dict(error=lines[-1]))
 rounds=[d['round']for d in logs if'round'in d];routed=[d['routed']for d in logs if'routed'in d];conflicts=[d['conflict_nodes']for d in logs if'conflict_nodes'in d]
 print('route',seed,'receipts',states,'rounds',sorted(set(rounds)),'routed_range',(min(routed),max(routed))if routed else None,'conflicts',conflicts,'errors',[d['error']for d in logs if'error'in d])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
