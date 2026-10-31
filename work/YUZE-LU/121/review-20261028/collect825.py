from pathlib import Path
import subprocess,shlex,json,base64,hashlib,tarfile
q=r'''from pathlib import Path
import json,hashlib,base64,datetime,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');r=b/'block-v1-20261030-404';p=r/'tasks/revision300-route-r'
receipt=json.loads((p/'receipt.json').read_text());assert receipt['passed'] is False
paths=[p/'receipt.json']+[p/n for n in receipt['outputs']]+[r/n for n in ('manifest.json','node-queue.json','node-queue-state.json','dispatch-state.json')]
files={};large={};changed={}
for f in dict.fromkeys(paths):
 h=hashlib.sha256()
 with f.open('rb')as s:
  for chunk in iter(lambda:s.read(1024*1024),b''):h.update(chunk)
 row=dict(bytes=f.stat().st_size,sha256=h.hexdigest());key=str(f.relative_to(b))
 if p in f.parents and str(f.relative_to(p)) in receipt['outputs']:
  old=receipt['outputs'][str(f.relative_to(p))]
  if old!=row['sha256']:
   assert f.name=='node-queue-child.log';changed[key]=dict(receipt_sha256=old,captured_sha256=row['sha256'])
 if row['bytes']<3000000:row['base64']=base64.b64encode(f.read_bytes()).decode();files[key]=row
 else:large[key]=row
m=json.loads((r/'src/bundle-manifest.json').read_text());sources={v['path']:hashlib.sha256((r/'src'/v['path']).read_bytes()).hexdigest()for v in m['files']}
sacct=subprocess.check_output(['sacct','-X','-j','93555','--format=JobID,State,ExitCode,Elapsed,End,NodeList','-n','-P'],universal_newlines=True)
assert '93555|FAILED|1:0|'in sacct
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_server_large=large,actual_source_sha256=sources,post_receipt_log_appends=changed,sacct=sacct)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
out=Path('work/YUZE-LU/121/review-20261028/r-404-grt-failure-825');assert not out.exists()
with tarfile.open('.local/issue121/source404.tar')as t:
 m=json.load(t.extractfile('bundle-manifest.json'));assert d['actual_source_sha256']=={r['path']:r['sha256']for r in m['files']}
 raw=subprocess.check_output(['git','cat-file','--batch'],input=''.join(r['git_blob']+'\n'for r in m['files']).encode());pos=0
 for row in m['files']:
  end=raw.index(b'\n',pos);header=raw[pos:end].split();assert header[0].decode()==row['git_blob'];n=int(header[2]);pos=end+1
  assert raw[pos:pos+n]==t.extractfile(row['path']).read();pos+=n+1
 assert pos==len(raw)
 for name,row in d['files'].items():
  if not name.endswith('/receipt.json'):continue
  receipt=json.loads(base64.b64decode(row['base64']))
  assert receipt['source_commit']==m['source_commit']
  for name,h in receipt['inputs'].items():
   if '/__pycache__/'not in name:assert hashlib.sha256(t.extractfile(name).read()).hexdigest()==h
d.update(source_commit=m['source_commit'],archive_git_blobs_verified=len(m['files']),actual_native_passed=False,final_acceptance=False,failure='GRT-0116: final total congestion 786830; global router terminated after extra iteration61 naturally; no timeout/cancel/OOM',scope='Unmodified original404 terminal failure, all receipt outputs hashed remotely and archived sources Git verified; failed ODB remains on authorized server.')
out.mkdir()
for name,row in d['files'].items():
 raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
print(d['sacct'],len(d['files']),len(d['actual_server_large']),d['archive_git_blobs_verified'])
