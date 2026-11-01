from pathlib import Path
import base64, hashlib, json, shlex, subprocess, tarfile
q=r'''from pathlib import Path
import base64,datetime,hashlib,json,subprocess,sys
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');r=b/'block-v1-20261101-851'
task=r/'tasks/revision300-r-current-neighborhood';receipt=json.loads((task/'receipt.json').read_text());assert receipt['passed']
sacct=subprocess.check_output(['sacct','-X','-j','94488','--format=JobIDRaw,State,ExitCode,Elapsed,NodeList','-n','-P'],universal_newlines=True);assert '94488|COMPLETED|0:0|'in sacct
paths=[r/n for n in ('manifest.json','node-queue.json','dispatch-state.json','node-queue-state.json','stage-identity-proof.json')]
paths+=[task/'receipt.json']+[task/n for n in receipt['outputs']]
files={};large={}
for p in dict.fromkeys(paths):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for v in iter(lambda:f.read(1024*1024),b''):h.update(v)
 row=dict(bytes=p.stat().st_size,sha256=h.hexdigest());name=str(p.relative_to(b))
 if row['bytes']<3000000:row['base64']=base64.b64encode(p.read_bytes()).decode();files[name]=row
 else:large[name]=row
sys.path.insert(0,str(r/'src/project/experiments/block_v1'));from revision300_v_clearance_corners import generate
report=json.loads((task/'revision300-r-current-neighborhood.json').read_text());assert report['passed']and report['source_native_count']==584 and report['original_inputs_unchanged']
plan=generate(report,task/'neighborhood.tsv',task/'net-aliases.tsv',task/'layer-dimensions.tsv')
offgrid=[p for p in plan['selected']if any(v%10 for v in p['bbox_dbu'])]
plan['rejected'] += [dict(index=p['index'],reason='not-on-frozen10DBU-grid')for p in offgrid]
plan['selected']=[p for p in plan['selected']if p not in offgrid];plan['shards']=sorted({p['shard']for p in plan['selected']})
m=json.loads((r/'src/bundle-manifest.json').read_text());actual={v['path']:hashlib.sha256((r/'src'/v['path']).read_bytes()).hexdigest()for v in m['files']}
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_server_large=large,actual_source_sha256=actual,actual_archive_sha256=hashlib.sha256((r/'source.tar').read_bytes()).hexdigest(),sacct=sacct,actual_clearance_plan=plan)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
raw={n:base64.b64decode(row['base64'])for n,row in d['files'].items()}
for n,v in raw.items():assert len(v)==d['files'][n]['bytes']and hashlib.sha256(v).hexdigest()==d['files'][n]['sha256']
archive=Path('.local/issue121/source851.tar');assert hashlib.sha256(archive.read_bytes()).hexdigest()==d['actual_archive_sha256']=='f34d360eda64390281398b06a7ae8e26a2ca4427d2f6407f4c7e76bb7c7f437e'
with tarfile.open(archive)as tar:
 m=json.load(tar.extractfile('bundle-manifest.json'));assert d['actual_source_sha256']=={v['path']:v['sha256']for v in m['files']}
 batch=subprocess.check_output(['git','cat-file','--batch'],input=''.join(v['git_blob']+'\n'for v in m['files']).encode());pos=0
 for v in m['files']:
  end=batch.index(b'\n',pos);header=batch[pos:end].split();assert header[0].decode()==v['git_blob'];size=int(header[2]);pos=end+1
  assert batch[pos:pos+size]==tar.extractfile(v['path']).read();pos+=size+1
 assert pos==len(batch)
 prefix='block-v1-20261101-851/tasks/revision300-r-current-neighborhood/'
 receipt=json.loads(raw[prefix+'receipt.json']);assert receipt['passed']and receipt['source_commit']==m['source_commit']
 for path,h in receipt['inputs'].items():
  if '/__pycache__/'not in path:assert hashlib.sha256(tar.extractfile(path).read()).hexdigest()==h
 for name,h in receipt['outputs'].items():
  row=d['files'].get(prefix+name,d['actual_server_large'].get(prefix+name));assert row and row['sha256']==h,(name,h)
report=json.loads(raw[prefix+'revision300-r-current-neighborhood.json'])
assert report['source_receipt_sha256']=='759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b'
assert report['original_inputs_unchanged']and report['source_native_count']==584
out=Path('work/YUZE-LU/121/review-20261028/r-851-neighborhood-858');assert not out.exists();out.mkdir()
for n,v in raw.items():
 p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v);d['files'][n].pop('base64')
d.update(source_commit=m['source_commit'],source_git_blobs_verified=len(m['files']),all_inputs_and_stable_outputs_verified=True,physical_acceptance=False,scope='Actual terminal read-only851 all584 marker neighborhoods. Complete source/receipt/output binding; scalar-clearance plan proposes candidates only, no repair or physical qualification.')
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode())
(out/'clearance-plan.json').write_bytes((json.dumps(d['actual_clearance_plan'],indent=2)+'\n').encode())
from collections import Counter
print('858',len(raw),'raw',len(d['actual_server_large']),'large',len(m['files']),'sourceGit',d['sacct']);print('plan',len(d['actual_clearance_plan']['selected']),'shards',dict(Counter(v['shard']for v in d['actual_clearance_plan']['selected'])),'skipped',len(d['actual_clearance_plan']['skipped']),'rejected',len(d['actual_clearance_plan']['rejected']))
