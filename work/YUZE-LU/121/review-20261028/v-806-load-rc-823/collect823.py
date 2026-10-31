from pathlib import Path
import subprocess,shlex,json,hashlib,base64,tarfile
out=Path('work/YUZE-LU/121/review-20261028/v-806-load-rc-823');assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,datetime,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');run=b/'block-v1-20261031-806';files={};large={}
names=['revision300-load-v-'+v for v in ('approved','base','high')]+['revision300-boundary-rc-v-'+v for v in ('base','high')]
for name in names:
 p=run/'tasks'/name;r=json.loads((p/'receipt.json').read_text());assert r['passed']
 for f in [p/'receipt.json']+[p/n for n in r['outputs']]:
  assert f.is_file();f.resolve().relative_to(run.resolve());h=hashlib.sha256()
  with f.open('rb')as s:
   for chunk in iter(lambda:s.read(1024*1024),b''):h.update(chunk)
  row=dict(bytes=f.stat().st_size,sha256=h.hexdigest());key=str(f.relative_to(b))
  if row['bytes']<3000000:row['base64']=base64.b64encode(f.read_bytes()).decode();files[key]=row
  else:large[key]=row
sacct=subprocess.check_output(['sacct','-X','-j','94105','--format=JobID,State,ExitCode,Elapsed,NodeList','-n','-P'],universal_newlines=True).strip();assert '94105|COMPLETED|0:0|'in sacct
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_server_large=large,sacct=sacct)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
Path('.local/issue121/capture823-current.json').write_text(json.dumps(d),encoding='utf-8')
raw={n:base64.b64decode(r['base64'])for n,r in d['files'].items()}
for n,v in raw.items():assert hashlib.sha256(v).hexdigest()==d['files'][n]['sha256']and len(v)==d['files'][n]['bytes']
prefix='block-v1-20261031-806/tasks/';reports={}
with tarfile.open('.local/issue121/source804.tar')as tar:
 m=json.load(tar.extractfile('bundle-manifest.json'));oids=''.join(v['git_blob']+'\n'for v in m['files']).encode();batch=subprocess.check_output(['git','cat-file','--batch'],input=oids);offset=0
 for row in m['files']:
  end=batch.index(b'\n',offset);header=batch[offset:end].split();assert header[0].decode()==row['git_blob']and header[1]==b'blob';size=int(header[2]);offset=end+1;assert batch[offset:offset+size]==tar.extractfile(row['path']).read();offset+=size+1
 assert offset==len(batch)
 for n,v in raw.items():
  if not n.endswith('/receipt.json'):continue
  r=json.loads(v);assert r['passed']and r['source_commit']==m['source_commit']
  for name,h in r['inputs'].items():
   if '/__pycache__/'not in name:assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==h,name
  for name,h in r['outputs'].items():
   key=n.rsplit('/',1)[0]+'/'+name;row=d['files'].get(key,d['actual_server_large'].get(key));assert row and row['sha256']==h,name
  reportname='revision300-boundary-rc.json'if 'boundary-rc'in n else 'revision300-load.json'
  reports[r['mode']]=json.loads(raw[n.rsplit('/',1)[0]+'/'+reportname])
base=Path('work/YUZE-LU/121/review-20261028');native=base/'v-805-delivery-geometry-818/block-v1-20261031-805/tasks'
escape=base/'v-806-interface-821/block-v1-20261031-806/tasks/revision300-escape-v';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary={}
for name,r in reports.items():
 assert r['passed']and r['experiment_completed']and r['macro']=='V'
 assert r['source_delivery']['delivery_receipt_sha256']==sha(native/'revision300-delivery-v/receipt.json')
 assert r['source_delivery']['delivery_report_sha256']==sha(native/'revision300-delivery-v/five-macro-delivery.json')
 assert r['source_escape_receipt_sha256']==sha(escape/'receipt.json')
 timing=r['timing'];flag='declared_pi_boundary_sta_passed'if 'boundary-rc'in name else 'loaded_native_sta_passed';assert r[flag]==timing['passed']
 summary[name]=dict(experiment_completed=True,actual_sta_passed=timing['passed'],timing=timing)
 if 'boundary-rc'in name:
  assert r['approved_budget_and_final_files_unchanged']and r['annotation']['passed']and not r['combined_system_timing_qualified']and not r['calibrated_12layer_rc_qualified']
d.update(source_commit=m['source_commit'],source_git_blobs_verified=len(m['files']),all_inputs_and_actual_outputs_verified=True,same805_delivery_and806_escape_bound=True,actual_sta_results=summary,full_v_accepted=False,scope='Actual five completed sensitivity experiments; receipt passed is separated from actual STA passed. Uncalibrated finite scenarios only, no complete M11/M12 system qualification.')
out.mkdir()
for n,v in raw.items():p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v);d['files'][n].pop('base64')
(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
print('Collected823',len(raw),'raw',len(d['actual_server_large']),'large',d['sacct'])
for n,r in summary.items():print(n,'actual_STA',r['actual_sta_passed'])
