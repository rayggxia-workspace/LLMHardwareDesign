from pathlib import Path
import base64,hashlib,json,shlex,subprocess,tarfile
q=r'''from pathlib import Path
import base64,hashlib,json,datetime
r=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-857');p=r/'tasks/revision300-r-topology'
receipt=json.loads((p/'receipt.json').read_text());assert receipt['passed']
files={};large={}
for n in ['receipt.json']+list(receipt['outputs']):
 v=(p/n).read_bytes();row=dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest())
 if len(v)<3000000:row['base64']=base64.b64encode(v).decode();files[n]=row
 else:large[n]=row
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_server_large=large)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
raw={n:base64.b64decode(row['base64'])for n,row in d['files'].items()}
for n,v in raw.items():assert len(v)==d['files'][n]['bytes']and hashlib.sha256(v).hexdigest()==d['files'][n]['sha256']
receipt=json.loads(raw['receipt.json']);assert receipt['passed']and receipt['source_commit']=='ae2502efb532caa6f143b758d66f8ae3eac505c1'
with tarfile.open('.local/issue121/source857.tar')as tar:
 for n,h in receipt['inputs'].items():
  if '/__pycache__/'not in n:assert hashlib.sha256(tar.extractfile(n).read()).hexdigest()==h
for n,h in receipt['outputs'].items():assert d['files'].get(n,d['actual_server_large'].get(n))['sha256']==h
report=json.loads(raw['revision300-r-topology.json']);assert report['passed']and report['original_inputs_unchanged']and not report['physical_qualified']
out=Path('work/YUZE-LU/121/review-20261028/r-857-topology-862');assert not out.exists();out.mkdir()
for n,v in raw.items():
 p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v);d['files'][n].pop('base64')
d.update(all_receipt_inputs_and_outputs_verified=True,source_archive_proof='../r-857-repair-stage-860/index.json',physical_acceptance=False)
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode())
print('862',len(raw),'raw',report)
print('NS',json.loads(raw['ns-exact-net.json']))
plan=json.loads(raw['via-candidate-plan.json']);print('via selected',len(plan['selected']),'skipped',len(plan['skipped']));print('first',plan['selected'][:2])
