from pathlib import Path
import json,hashlib,base64,subprocess,shlex,tarfile
base='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121'
q=r'''from pathlib import Path
import json,hashlib
b=Path(BASE);rows=[]
for n in ('826','827','828','829'):
 r=b/('block-v1-20261101-'+n);files={name:hashlib.sha256((r/name).read_bytes()).hexdigest()for name in ('manifest.json','node-queue.json','src/project/experiments/block_v1/dispatch.py','src/project/experiments/block_v1/native_node_queue.py')}
 m=json.loads((r/'manifest.json').read_text());assert m['run_id']==r.name and hashlib.sha256((r/'source.tar').read_bytes()).hexdigest()==m['source_archive_sha256']
 rows.append(dict(run_id=r.name,files=files,source_commit=m['source_commit'],source_archive_sha256=m['source_archive_sha256']))
print(json.dumps(rows))'''.replace('BASE',repr(base))
rows=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
folder=Path('work/YUZE-LU/121/review-20261028/admission-830');assert not folder.exists()
for row in rows:
 n=row['run_id'].rsplit('-',1)[1]
 for remote_name,filename in [('manifest.json','stage'+n+'-manifest.json'),('node-queue.json','node-queue-'+n+'.json')]:assert hashlib.sha256((folder.parent/filename).read_bytes()).hexdigest()==row['files'][remote_name]
 with tarfile.open('.local/issue121/source'+('826'if n=='826'else'827')+'.tar')as tar:
  m=json.load(tar.extractfile('bundle-manifest.json'));assert row['source_commit']==m['source_commit']
  for name in ('project/experiments/block_v1/dispatch.py','project/experiments/block_v1/native_node_queue.py'):
   v=next(v for v in m['files']if v['path']==name);raw=tar.extractfile(name).read();assert raw==subprocess.check_output(['git','cat-file','blob',v['git_blob']])and hashlib.sha256(raw).hexdigest()==row['files']['src/'+name]
config=dict(schema='revision300-admission/1',base=base,max_allocations=8,interval_seconds=60,runs=[dict(run_id=r['run_id'],files=r['files'])for r in rows]);raw=(json.dumps(config,indent=2)+'\n').encode()
controller=base+'/admission-20261101-830';wrapper=base+'/block-v1-20261101-827/src/project/experiments/block_v1/revision300_r_read_admission.py'
sha=lambda name:hashlib.sha256(subprocess.check_output(['git','show','747d700e8136a93788eb6eaa28c83c11302c9c71:project/experiments/block_v1/'+name])).hexdigest()
q=r'''from pathlib import Path
import json,hashlib,base64,subprocess,time,os
r=Path(CONTROLLER);assert not r.exists();r.mkdir();raw=base64.b64decode(CONFIG);assert hashlib.sha256(raw).hexdigest()==CONFIG_SHA;(r/'config.json').write_bytes(raw)
wrapper=Path(WRAPPER);assert hashlib.sha256(wrapper.read_bytes()).hexdigest()==WRAPPER_SHA
common=wrapper.parent/'revision300_admission.py';assert hashlib.sha256(common.read_bytes()).hexdigest()==COMMON_SHA
log=(r/'controller.log').open('ab');p=subprocess.Popen(['python3','-u',str(wrapper),str(r/'config.json'),str(r)],stdout=log,stderr=log,start_new_session=True)
(r/'controller.pid').write_text(str(p.pid)+'\n');time.sleep(2);assert p.poll()is None
proc=Path('/proc')/str(p.pid);cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode();assert str(wrapper)in cmd and str(r)in cmd
uid=next(v for v in (proc/'status').read_text().splitlines()if v.startswith('Uid:'));assert all(int(v)==os.getuid()for v in uid.split()[1:])
print(json.dumps(dict(pid=p.pid,config_sha256=CONFIG_SHA,wrapper_sha256=WRAPPER_SHA,common_sha256=COMMON_SHA,command=cmd,scope='Only826/827/828/829; immutable receipts/dependencies, no retry/cancel/EDA on login controller, common issue cap8 including old/pending/unknown. Original controllers untouched.')))
'''
for key,value in sorted([('CONTROLLER',controller),('CONFIG',base64.b64encode(raw).decode()),('CONFIG_SHA',hashlib.sha256(raw).hexdigest()),('WRAPPER',wrapper),('WRAPPER_SHA',sha('revision300_r_read_admission.py')),('COMMON_SHA',sha('revision300_admission.py'))],key=lambda v:-len(v[0])):q=q.replace(key,repr(value))
proof=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
folder.mkdir();(folder/'config.json').write_bytes(raw);(folder/'deployment.json').write_bytes((json.dumps(dict(passed=True,rows=rows,actual=proof),indent=2)+'\n').encode());print(json.dumps(proof))
