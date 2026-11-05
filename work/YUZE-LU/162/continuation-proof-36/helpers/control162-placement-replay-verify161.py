"""Verify original trial bytes; append a receipt only when all comparisons pass."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391/cap-capacity-candidates';rows=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for old,new in [(1580,1604),(1602,1620),(1610,1621),(1611,1622)]:
 a=c/str(old);d=c/str(new)
 if not(d/'receipt.json').exists():print('unfinished',new);continue
 for folder in (a,d):
  receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed'];assert receipt['outputs']['placement-search.json']==sha(folder/'placement-search.json')
  for i in range(16):assert receipt['outputs']['electrical-placement-'+str(i)+'.txt']==sha(folder/('electrical-placement-'+str(i)+'.txt'))
  assert receipt['outputs']['electrical-placement-input.txt']==sha(folder/'electrical-placement-input.txt')
 assert(a/'electrical-placement-input.txt').read_bytes()==(d/'electrical-placement-input.txt').read_bytes()
 for i in range(16):assert(a/('electrical-placement-'+str(i)+'.txt')).read_bytes()==(d/('electrical-placement-'+str(i)+'.txt')).read_bytes()
 original=json.loads((a/'placement-search.json').read_text())['electrical_refinement'];result=json.loads((d/'placement-search.json').read_text())['electrical_refinement'];trials=result['independent_trials'];key=(lambda r:r['metrics'][0])if old==1580 else(lambda r:(r['metrics'][5],r['metrics'][0]));expected=min(trials,key=key);assert expected['seed']==result['selected_seed']
 if old==1580:
  p=json.loads((a/'placement.json').read_text());q=json.loads((d/'placement.json').read_text())
  assert p==q
 else:assert expected['metrics'][5]==0
 rows.append(dict(original=old,replay=new,identical_inputs=True,byte_identical_trial_outputs=16,independent_selection_verified=True,selected_seed=result['selected_seed'],metrics=expected['metrics'],source_receipts={str(p/'receipt.json'):sha(p/'receipt.json')for p in (a,d)}))
report=dict(time=time.time(),pairs=rows,complete=len(rows)==4,passed=len(rows)==4,whole_system_qualified=False)
if report['passed']:
 path=b/'route-selection-102/sready161-replay-verification.json'
 if path.exists():
  old=json.loads(path.read_text());assert old['passed']and old['pairs']==rows
 else:
  temp=path.with_suffix('.tmp');assert not temp.exists();temp.write_text(json.dumps(report,indent=2));temp.rename(path)
 report['receipt']=str(path);report['receipt_sha256']=sha(path)
print(json.dumps(report))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
