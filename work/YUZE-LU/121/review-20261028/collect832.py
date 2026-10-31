from pathlib import Path
import json,hashlib,base64,subprocess,shlex,tarfile
q=r'''from pathlib import Path
import json,hashlib,base64,datetime,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');r=b/'block-v1-20261101-826';files={};large={}
q=json.loads((r/'node-queue.json').read_text());state=json.loads((r/'node-queue-state.json').read_text())
assert all(state['tasks'][t['id']]['status']=='PASSED'for t in q['tasks'])
paths=[r/n for n in ('manifest.json','node-queue.json','dispatch-state.json','node-queue-state.json','stage-identity-proof.json')]
for t in q['tasks']:
 p=r/'tasks'/t['id'];receipt=json.loads((p/'receipt.json').read_text());assert receipt['passed'];paths+=[p/'receipt.json']+[p/n for n in receipt['outputs']]
for p in dict.fromkeys(paths):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for v in iter(lambda:f.read(1024*1024),b''):h.update(v)
 row=dict(bytes=p.stat().st_size,sha256=h.hexdigest());name=str(p.relative_to(b))
 if row['bytes']<3000000:row['base64']=base64.b64encode(p.read_bytes()).decode();files[name]=row
 else:large[name]=row
m=json.loads((r/'src/bundle-manifest.json').read_text());sources={v['path']:hashlib.sha256((r/'src'/v['path']).read_bytes()).hexdigest()for v in m['files']}
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_server_large=large,actual_source_sha256=sources,sacct=subprocess.check_output(['sacct','-X','-j','94317','--format=JobID,State,ExitCode,Elapsed,NodeList','-n','-P'],universal_newlines=True))))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]));out=Path('work/YUZE-LU/121/review-20261028/r-826-validation');assert not out.exists();raw={n:base64.b64decode(v['base64'])for n,v in d['files'].items()}
with tarfile.open('.local/issue121/source826.tar')as t:
 m=json.load(t.extractfile('bundle-manifest.json'));assert d['actual_source_sha256']=={v['path']:v['sha256']for v in m['files']}
 batch=subprocess.check_output(['git','cat-file','--batch'],input=''.join(v['git_blob']+'\n'for v in m['files']).encode());pos=0
 for row in m['files']:
  end=batch.index(b'\n',pos);header=batch[pos:end].split();assert header[0].decode()==row['git_blob'];n=int(header[2]);pos=end+1;assert batch[pos:pos+n]==t.extractfile(row['path']).read();pos+=n+1
 assert pos==len(batch)
 for n,value in raw.items():
  if not n.endswith('/receipt.json'):continue
  r=json.loads(value);assert r['passed']and r['source_commit']==m['source_commit']
  for path,h in r['inputs'].items():
   if '/__pycache__/'not in path:assert hashlib.sha256(t.extractfile(path).read()).hexdigest()==h
  for path,h in r['outputs'].items():
   key=n.rsplit('/',1)[0]+'/'+path;row=d['files'].get(key,d['actual_server_large'].get(key));assert row and row['sha256']==h,(key,h)
prefix='block-v1-20261101-826/tasks/'
report=lambda mode,name:json.loads(raw[prefix+mode+'/'+name])
mapping=report('revision300-map-r','revision300-rtl-map.json');function=report('revision300-test-r','revision300-rtl-test.json')
assert function['rtl_sha256']==mapping['rtl_sha256']
for v in ('revised','extended'):
 occ=report('revision300-occupancy-r-'+v,'revision300-lane-occupancy.json');bench=report('revision300-bench-r-'+v,'revision300-vr-benchmark.json');assert occ['prior_public_schedule_identity']and occ['rtl_sha256']==bench['rtl_sha256']
 assert list(bench['rtl_sha256'].values())==list(mapping['rtl_sha256'].values())
d.update(source_commit=m['source_commit'],source_git_blobs_verified=len(m['files']),all_inputs_and_actual_outputs_verified=True,actual_rtl_checks_passed=True,public_schedule_identity_to342=True,cell_count=mapping['cell_count'],pretechnology_multipliers=mapping['pretechnology_multipliers'],rtl_sha256=mapping['rtl_sha256'],final_acceptance=False,scope='Six new shared-bank-read R checks; fresh source-bound numerical/mapping/public-cycle/occupancy evidence. Occupancy additionally matches actual342 public schedule, no old qualification transfer. Native827 and all fresh final gates remain required.')
out.mkdir()
for n,v in raw.items():
 row=d['files'][n];assert hashlib.sha256(v).hexdigest()==row['sha256']and len(v)==row['bytes'];row.pop('base64');p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print('832',len(raw),'raw',len(d['actual_server_large']),'large','cells',mapping['cell_count'],'source',m['source_commit']);print(d['sacct'])
