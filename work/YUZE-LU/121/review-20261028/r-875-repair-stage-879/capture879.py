from pathlib import Path
import base64, datetime, hashlib, json, shlex, subprocess, tarfile
q = r'''from pathlib import Path
import base64,datetime,hashlib,json,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');r=b/'block-v1-20261101-875'
paths=[r/n for n in ('manifest.json','node-queue.json','dispatch-state.json','stage-identity-proof.json','node-queue-state.json')if (r/n).is_file()]
paths += [p for p in (r/'tasks/native-node-queue').glob('*')if p.is_file()]
files={}
for p in paths:
 data=p.read_bytes();assert len(data)<3000000
 files[str(p.relative_to(b))]=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),base64=base64.b64encode(data).decode())
m=json.loads((r/'src/bundle-manifest.json').read_text())
actual={row['path']:hashlib.sha256((r/'src'/row['path']).read_bytes()).hexdigest()for row in m['files']}
job=str(json.loads((r/'dispatch-state.json').read_text())['tasks']['native-node-queue']['job_id']);assert job=='94497'
sacct=subprocess.check_output(['sacct','-X','-j',job,'--format=JobIDRaw,State,ExitCode,Elapsed,NodeList','-n','-P'],universal_newlines=True)
assert job+'|RUNNING|'in sacct or job+'|COMPLETED|0:0|'in sacct
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_source_sha256=actual,actual_source_archive_sha256=hashlib.sha256((r/'source.tar').read_bytes()).hexdigest(),sacct=sacct)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
raw={n:base64.b64decode(row['base64'])for n,row in d['files'].items()}
for n,data in raw.items():assert hashlib.sha256(data).hexdigest()==d['files'][n]['sha256']and len(data)==d['files'][n]['bytes']
archive=Path('.local/issue121/source875.tar')
assert hashlib.sha256(archive.read_bytes()).hexdigest()==d['actual_source_archive_sha256']=='bd15f0bff5ccd3545c4d46a747a81931e3e386ef8b8787ce15246693ca141ba3'
with tarfile.open(archive)as tar:
 m=json.load(tar.extractfile('bundle-manifest.json'));assert m['source_commit']=='836fed0cca1e5552ac6844f2652025286a681710'
 assert d['actual_source_sha256']=={r['path']:r['sha256']for r in m['files']}
 batch=subprocess.check_output(['git','cat-file','--batch'],input=''.join(r['git_blob']+'\n'for r in m['files']).encode());offset=0
 for row in m['files']:
  end=batch.index(b'\n',offset);header=batch[offset:end].split();assert header[0].decode()==row['git_blob'];size=int(header[2]);offset=end+1
  assert batch[offset:offset+size]==tar.extractfile(row['path']).read();offset+=size+1
 assert offset==len(batch)
prefix='block-v1-20261101-875/'
for remote,local in [('node-queue.json','node-queue-875.json'),('manifest.json','stage875-manifest.json')]:
 assert raw[prefix+remote]==(Path('work/YUZE-LU/121/review-20261028')/local).read_bytes()
proof=json.loads(raw[prefix+'stage-identity-proof.json']);assert proof['passed']and proof['source_commit']==m['source_commit']
queue=json.loads(raw[prefix+'node-queue.json']);assert queue['node_cpus']==96 and len(queue['tasks'])==6 and all(t['cpus']==16 for t in queue['tasks'])
out=Path('work/YUZE-LU/121/review-20261028/r-875-repair-stage-879');assert not out.exists();out.mkdir()
for n,data in raw.items():
 p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);d['files'][n].pop('base64')
d.update(source_commit=m['source_commit'],source_git_blobs_verified=len(m['files']),actual_remote_source_and_archive_verified=True,actual_job='94497',diagnostic_completed=False,physical_acceptance=False,scope='Actual immutable875 source/queue/argv identity and Slurm handle. Six source-bound retained-pad stack-via shards from94 R candidates, six16CPU slots. No original828 edit or final qualification; candidate results pending.')
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print('879',len(raw),'raw files',len(m['files']),'sourceGit',d['sacct'])
