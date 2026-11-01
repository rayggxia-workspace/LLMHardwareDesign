from pathlib import Path
import hashlib,json,shlex,subprocess,tarfile
number='870';run='block-v1-20261101-'+number;base='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121';remote=base+'/'+run;archive=Path('.local/issue121/source870.tar');digest=hashlib.sha256(archive.read_bytes()).hexdigest()
with tarfile.open(archive)as tar:commit=json.load(tar.extractfile('bundle-manifest.json'))['source_commit']
queue=dict(schema='block-v1-node-queue/1',node_cpus=96,default_task_cpus=16,memory_guard_gib=16,state_path=remote+'/node-queue-state.json',tasks=[])
for mode,report,memory in [('revision300-r-alternate-vias-'+str(i),'revision300-r-vias.json',64)for i in range(6)]:
 queue['tasks'].append(dict(id=mode,mode=mode,cwd=remote+'/tasks/'+mode,source=remote+'/src',cpus=16,memory_gib=memory,memory_basis='Six independent source-bound copy checks from64 actualR851/857 alternate vias. Different nets from866314 corners/53 M2 pairs;55 reverseM4 and9 existing-bend candidates. All original828 files unchanged. Six16CPU slots; each64GiB forecast,1.2 margin plus16GiB guard/liveRSS,503.5GiB physical node. Actual DRC and precise DEF delta required, no final qualification',report=report,after=[],receipts=[dict(path=base+'/block-v1-20261101-851/tasks/revision300-r-current-neighborhood/receipt.json',mode='revision300-r-current-neighborhood',reports=['revision300-r-current-neighborhood.json']),dict(path=base+'/block-v1-20261101-857/tasks/revision300-r-topology/receipt.json',mode='revision300-r-topology',reports=['revision300-r-topology.json','via-candidate-plan.json'])]))
manifest=dict(run_id=run,base_nodes=6,max_nodes=8,elastic=True,source_commit=commit,source_archive_sha256=digest,tasks=[dict(id='native-node-queue',partition='c96',cpus=96,memory='0',minutes=0,after=[],argv=['bash',remote+'/src/project/experiments/block_v1/worker.sh',remote+'/src','native-node-queue'])])
folder=Path('work/YUZE-LU/121/review-20261028');queuefile=folder/'node-queue-870.json';manifestfile=folder/'stage870-manifest.json'
for p,d in [(queuefile,queue),(manifestfile,manifest)]:assert not p.exists();p.write_bytes((json.dumps(d,indent=2)+'\n').encode())
assert manifest['run_id']==run and manifest['tasks'][0]['argv'][1].startswith(remote+'/src/')
assert queue['state_path'].startswith(remote+'/')and all(t['cwd'].startswith(remote+'/tasks/')and t['source']==remote+'/src'for t in queue['tasks'])
files=[(archive,'source.tar'),(queuefile,'node-queue.json'),(manifestfile,'manifest.json')]
subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','test ! -e '+remote+' && mkdir '+remote+' && mkdir '+remote+'/src'],check=True)
for p,n in files:subprocess.run(['scp','-q',str(p),'yuzelu@10.129.166.172:'+remote+'/'+n],check=True)
bindings={n:hashlib.sha256(p.read_bytes()).hexdigest()for p,n in files}
q=r'''from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
r=Path(REMOTE);expected=BINDINGS
for n,h in expected.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h,n
m=json.loads((r/'manifest.json').read_text());q=json.loads((r/'node-queue.json').read_text());assert r.name==m['run_id'] and m['source_commit']==COMMIT and m['source_archive_sha256']==expected['source.tar']
assert m['tasks'][0]['argv']==['bash',str(r/'src/project/experiments/block_v1/worker.sh'),str(r/'src'),'native-node-queue']
assert q['state_path']==str(r/'node-queue-state.json') and all(t['source']==str(r/'src')and t['cwd']==str(r/'tasks'/t['id'])for t in q['tasks'])
with tarfile.open(str(r/'source.tar'))as t:assert json.load(t.extractfile('bundle-manifest.json'))['source_commit']==m['source_commit'];t.extractall(str(r/'src'))
sys.path.insert(0,str(r/'src/project/experiments/block_v1'));from native_node_queue import validate;validate(q,r.parent)
proof=dict(passed=True,actual_remote_sha256=expected,run_directory_and_manifest_same=True,actual_archive_source_commit_matches=True,queue_and_argv_paths_exact=True,source_commit=m['source_commit'],scope='Crossfile source/run/argv identity guard before any dispatch;460 wrong manifest is not reused.')
(r/'stage-identity-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('IDENTITY_GUARD_PASS',r.name,flush=True)
subprocess.run(['python3',str(r/'src/project/experiments/block_v1/dispatch.py'),str(r/'manifest.json'),'--submit'],check=True,cwd=str(r))
'''.replace('REMOTE',repr(remote)).replace('BINDINGS',repr(bindings)).replace('COMMIT',repr(commit))
Path('.local/issue121/870stage-remote.py').write_text(q,encoding='utf-8');subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],check=True)
