from pathlib import Path
import json,hashlib,tarfile,subprocess,shlex
base='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121';remote=base+'/block-v1-20261101-826'
archive=Path('.local/issue121/source826.tar');digest=hashlib.sha256(archive.read_bytes()).hexdigest()
with tarfile.open(archive)as tar:commit=json.load(tar.extractfile('bundle-manifest.json'))['source_commit']
queue=dict(schema='block-v1-node-queue/1',node_cpus=96,default_task_cpus=16,memory_guard_gib=16,state_path=remote+'/node-queue-state.json',tasks=[])
for mode,report,memory in [('revision300-test-r','revision300-rtl-test.json',16),('revision300-map-r','revision300-rtl-map.json',64),('revision300-bench-r-revised','revision300-vr-benchmark.json',16),('revision300-bench-r-extended','revision300-vr-benchmark.json',16),('revision300-occupancy-r-revised','revision300-lane-occupancy.json',16),('revision300-occupancy-r-extended','revision300-lane-occupancy.json',16)]:
 after=[]
 if '-occupancy-'in mode:after=['revision300-bench-r-'+mode.rsplit('-',1)[1]]
 queue['tasks'].append(dict(id=mode,mode=mode,cwd=remote+'/tasks/'+mode,source=remote+'/src',cpus=16,memory_gib=memory,report=report,after=after,receipts=[],memory_basis='One revised shared-bank-read R only: fresh three-init numerical checks, mapping, two public schedules and two internal occupancy checks. Six16CPU slots; occupancy has a genuine per-variant fresh public report dependency, other four start independently and refill immediately. Test16GiB/map64GiB forecasts with1.2 margin plus16GiB guard/liveRSS. Original404 terminal GRT failure preserved; no old physical qualification inherited. No changes to other members or M/S/T/V.'))
manifest=dict(run_id='block-v1-20261101-826',base_nodes=6,max_nodes=8,elastic=True,source_commit=commit,source_archive_sha256=digest,tasks=[dict(id='native-node-queue',partition='c96',cpus=96,memory='0',minutes=0,after=[],argv=['bash',remote+'/src/project/experiments/block_v1/worker.sh',remote+'/src','native-node-queue'])])
folder=Path('work/YUZE-LU/121/review-20261028');files=[(archive,'source.tar')]
for name,d in [('node-queue-826.json',queue),('stage826-manifest.json',manifest)]:
 p=folder/name;assert not p.exists();p.write_bytes((json.dumps(d,indent=2)+'\n').encode());files.append((p,'node-queue.json'if name.startswith('node')else'manifest.json'))
subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','test ! -e '+remote+' && mkdir '+remote+' && mkdir '+remote+'/src'],check=True)
for p,n in files:subprocess.run(['scp','-q',str(p),'yuzelu@10.129.166.172:'+remote+'/'+n],check=True)
bindings={n:hashlib.sha256(p.read_bytes()).hexdigest()for p,n in files}
q=r'''from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
r=Path(REMOTE);expected=BINDINGS
for n,h in expected.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h,n
m=json.loads((r/'manifest.json').read_text());q=json.loads((r/'node-queue.json').read_text());assert r.name==m['run_id']and m['source_commit']==COMMIT and m['source_archive_sha256']==expected['source.tar']
assert m['tasks'][0]['argv']==['bash',str(r/'src/project/experiments/block_v1/worker.sh'),str(r/'src'),'native-node-queue']
assert q['state_path']==str(r/'node-queue-state.json')and all(t['source']==str(r/'src')and t['cwd']==str(r/'tasks'/t['id'])for t in q['tasks'])
with tarfile.open(str(r/'source.tar'))as t:assert json.load(t.extractfile('bundle-manifest.json'))['source_commit']==COMMIT;t.extractall(str(r/'src'))
sys.path.insert(0,str(r/'src/project/experiments/block_v1'));from native_node_queue import validate;validate(q,r.parent)
proof=dict(passed=True,source_commit=COMMIT,actual_remote_sha256=expected,run_directory_and_manifest_same=True,queue_and_argv_paths_exact=True)
(r/'stage-identity-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('IDENTITY_GUARD_PASS',r.name,flush=True)
subprocess.run(['python3',str(r/'src/project/experiments/block_v1/dispatch.py'),str(r/'manifest.json'),'--submit'],check=True,cwd=str(r))
'''.replace('REMOTE',repr(remote)).replace('BINDINGS',repr(bindings)).replace('COMMIT',repr(commit))
Path('.local/issue121/826stage-remote.py').write_text(q,encoding='utf-8')
subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],check=True)
