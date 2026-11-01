from pathlib import Path
import json,hashlib,base64,subprocess,shlex,datetime
b=Path('work/YUZE-LU/121');manifests={m:json.loads((b/'delivery-300mhz'/m/'final-native.json').read_text())for m in ('M','V','S','T')}
for m,d in manifests.items():
 assert d['passed'] and d['native_leaf_accepted'] and d['implementation_count']==1
 assert d['native_routing_layers']==['metal'+str(i)for i in range(1,11)] and len(d['final_files'])==6
request=base64.b64encode(json.dumps(manifests).encode()).decode()
q=r'''from pathlib import Path
import sys,json,hashlib,base64,datetime
manifests=json.loads(base64.b64decode(sys.argv[1]));files={};proof={}
base='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/'
for macro,d in manifests.items():
 checks={}
 for kind,row in d['gate_receipts'].items():
  contents={}
  for field,hfield in [('path','sha256'),('report_path','report_sha256')]:
   path=row[field];assert path.startswith(base);p=Path(path);value=p.read_bytes();h=hashlib.sha256(value).hexdigest();assert h==row[hfield],(macro,kind,field,h)
   r=dict(bytes=len(value),sha256=h)
   if len(value)<3000000:r['base64']=base64.b64encode(value).decode()
   files[path[len(base):]]=r;contents[field]=json.loads(value)
  r=contents['path'];v=contents['report_path'];assert r['passed'] and v['passed'] and v['source_receipt_sha256']==d['source_receipt_sha256']
  if kind=='physical':assert all(v['checks'].values()) and v['timing']['passed']
  elif kind=='drc':assert v['full_deck']['total_items']==0 and not v['native_report'].strip()
  elif kind=='formal':assert v['strict_native_lec']['passed'] and all(v['strict_native_lec']['checks'].values())
  elif kind=='final-function':assert set(v['initial_runs'])=={'all-ones','random-121','random-122'} and all(x['result']['passed']for x in v['initial_runs'].values())
  else:raise AssertionError(kind)
  checks[kind]=True
 assert set(checks)=={'physical','drc','formal','final-function'}
 proof[macro]=dict(passed=True,source_receipt_sha256=d['source_receipt_sha256'],checks=checks)
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,proof=proof,passed=True,scope='Actual remote completed M/V/S/T gate receipt and report bytes, same-source binding, individual verdicts. Not a new six-final-artifact or geometry audit. R and overall goal incomplete.')))
'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)+' '+shlex.quote(request)]))
out=b/'review-20261028/four-macro-gate-audit-843';assert not out.exists()
raw={n:base64.b64decode(r['base64'])for n,r in d['files'].items()if 'base64'in r}
for n,value in raw.items():assert len(value)==d['files'][n]['bytes'] and hashlib.sha256(value).hexdigest()==d['files'][n]['sha256']
out.mkdir()
for n,value in raw.items():
 p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value)
for r in d['files'].values():r.pop('base64',None)
(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
print('843 actual remote gate audit PASS',list(d['proof']),'raw',len(raw),'hashed',len(d['files']))
