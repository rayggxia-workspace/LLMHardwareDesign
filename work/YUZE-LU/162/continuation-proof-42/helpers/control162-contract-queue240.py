import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-239';out=b/'r256-scene-regression-240';p=b/'dynamic-06/node7/pending/00-a-sready240-r256-contract.json';assert not p.exists()and not out.exists()
spec=dict(script='run.py',source_root=str(source),forecast_gib=16,requires=[],args=['--model','r256_contract','--verify-only','--out',str(out)])
p.write_text(json.dumps(spec));print(json.dumps(dict(queued=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
for family,numbers in [('233',[2330,2333]),('237',[2371])]:
 for n in numbers:
  root=b/('r256-native-'+family)/str(n);receipt=root/'native/receipt.json'
  if receipt.exists():
   r=json.loads(receipt.read_text());print(n,'producer',r['passed'],'last',r.get('commands',[])[-1]if r.get('commands')else None)
  else:
   logs=sorted((root/'native/pnr').glob('[0-9][0-9]-*.log'));print(n,'running',[(p.name,p.read_text().splitlines()[-3:])for p in logs[-1:]])
for n in [2292,2294,2295]:
 p=b/'r256-fixed-pg-235'/str(n)/'delivery/delivery.json'
 print('PG',n,{k:v for k,v in json.loads(p.read_text()).items()if k in ['passed','minimum_setup_ns','minimum_hold_ns']}if p.exists()else'waiting')
'''
compile(q,'contract_queue240','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=35).decode())
