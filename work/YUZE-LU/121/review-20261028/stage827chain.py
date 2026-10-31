from pathlib import Path
import json,hashlib,tarfile,subprocess,shlex,copy
base='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121';folder=Path('work/YUZE-LU/121/review-20261028');archive=Path('.local/issue121/source827.tar')
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
with tarfile.open(archive)as tar:commit=json.load(tar.extractfile('bundle-manifest.json'))['source_commit']
def stage(number,queue,fixture=False):
 run='block-v1-20261101-'+str(number);remote=base+'/'+run;queue['state_path']=remote+'/node-queue-state.json'
 for t in queue['tasks']:t.update(cwd=remote+'/tasks/'+t['id'],source=remote+'/src')
 manifest=dict(run_id=run,base_nodes=6,max_nodes=8,elastic=True,source_commit=commit,source_archive_sha256=digest,tasks=[dict(id='native-node-queue',partition='c96',cpus=96,memory='0',minutes=0,after=[],argv=['bash',remote+'/src/project/experiments/block_v1/worker.sh',remote+'/src','native-node-queue'])])
 files=[(archive,'source.tar')]
 for name,data,remote_name in [('node-queue-'+str(number)+'.json',queue,'node-queue.json'),('stage'+str(number)+'-manifest.json',manifest,'manifest.json')]:
  p=folder/name;assert not p.exists();p.write_bytes((json.dumps(data,indent=2)+'\n').encode());files.append((p,remote_name))
 subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','test ! -e '+remote+' && mkdir '+remote+' && mkdir '+remote+'/src'],check=True)
 for p,n in files:subprocess.run(['scp','-q',str(p),'yuzelu@10.129.166.172:'+remote+'/'+n],check=True)
 expected={n:hashlib.sha256(p.read_bytes()).hexdigest()for p,n in files}
 q=r'''from pathlib import Path
import json,hashlib,tarfile,sys,subprocess
r=Path(REMOTE);expected=EXPECTED
for n,h in expected.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h
m=json.loads((r/'manifest.json').read_text());q=json.loads((r/'node-queue.json').read_text())
assert r.name==m['run_id']and m['source_commit']==COMMIT and m['source_archive_sha256']==expected['source.tar']
assert m['tasks'][0]['argv']==['bash',str(r/'src/project/experiments/block_v1/worker.sh'),str(r/'src'),'native-node-queue']
assert q['state_path']==str(r/'node-queue-state.json')and all(t['source']==str(r/'src')and t['cwd']==str(r/'tasks'/t['id'])for t in q['tasks'])
with tarfile.open(str(r/'source.tar'))as t:assert json.load(t.extractfile('bundle-manifest.json'))['source_commit']==COMMIT;t.extractall(str(r/'src'))
if FIXTURE:
 (r/'tasks').mkdir(exist_ok=True)
 subprocess.run(['cp','-a',str(r.parent/'block-v1-20261029-258/tasks/revision300-constraints-control'),str(r/'tasks/revision300-constraints-control')],check=True)
sys.path.insert(0,str(r/'src/project/experiments/block_v1'));from native_node_queue import validate;validate(q,r.parent)
(r/'stage-identity-proof.json').write_text(json.dumps(dict(passed=True,source_commit=COMMIT,actual_remote_sha256=expected,run_directory_and_manifest_same=True,queue_and_argv_paths_exact=True),indent=2)+'\n')
subprocess.run(['python3',str(r/'src/project/experiments/block_v1/dispatch.py'),str(r/'manifest.json')],check=True,cwd=str(r))
'''
 for key,value in [('REMOTE',remote),('EXPECTED',expected),('COMMIT',commit),('FIXTURE',fixture)]:q=q.replace(key,repr(value))
 subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],check=True)
def blank():return dict(schema='block-v1-node-queue/1',node_cpus=96,default_task_cpus=16,memory_guard_gib=16,tasks=[])
queue=blank();requirements=[]
for t in json.loads((folder/'node-queue-826.json').read_bytes())['tasks']:
 requirements.append(dict(path=base+'/block-v1-20261101-826/tasks/'+t['id']+'/receipt.json',mode=t['mode'],reports=[t['report']],producer_state=base+'/block-v1-20261101-826/node-queue-state.json',producer_task=t['id']))
mode='revision300-route-r';queue['tasks'].append(dict(id=mode,mode=mode,cpus=16,memory_gib=192,report='revision300-native-flow.json',after=[],receipts=requirements,memory_basis='Single shared-bank-read R after all six826 source-bound checks. All six physical stages fresh, unchanged state capacity/numerics/latency, minimum2330um retains404 footprint to avoid automatic shrink. Actual404 GRT RSS20GiB, forecast192GiB retains headroom for built-in nativeLEC with1.2 margin+16GiB guard. No duplicate implementations or old failing checkpoint inheritance. Default6x16 but only this P&R dependency is ready.'))
stage(827,queue)
queue=json.loads((folder/'node-queue-405.json').read_bytes())
for t in queue['tasks']:
 t['memory_basis']='One shared-read R:827 fresh native stages then828 independent final gates; six16CPU dynamic slots, physical64/fullGDS64/function128/formal192/geometry64GiB forecasts with1.2 margin+16GiB guard/liveRSS. Formal follows function; delivery follows every gate plus whole-signal geometry. Actual dependencies/RAM only reduce concurrency; no404/405 qualification transfer.'
 for d in t['receipts']:
  for k in ('path','producer_state'):
   if k in d:d[k]=d[k].replace('block-v1-20261030-404','block-v1-20261101-827')
 if t['id']=='revision300-delivery-r':t['after'].append('revision300-signal-connectivity-r')
queue['tasks'].insert(4,dict(id='revision300-signal-connectivity-r',mode='revision300-signal-connectivity-r',cpus=16,memory_gib=96,report='revision300-signal-connectivity.json',after=['revision300-final-source-r'],receipts=[],memory_basis='Read-only complete R wire/via/pin connectivity, exact all-normal DEF coverage including native RECT complement. Native404 about1.12million nets before read-port repair;96GiB forecast with1.2 margin+16GiB guard/liveRSS,16CPU. No logical-net-membership surrogate or deleted geometry.'))
stage(828,queue,fixture=True)
queue=json.loads((folder/'node-queue-406.json').read_bytes())
for t in queue['tasks']:
 t['memory_basis']='One newly accepted shared-read R829 all-port geometry then three output loads and base/high finite all-port piRC in six16CPU immediate-refill slots. Geometry128GiB/STA64GiB forecasts with1.2 margin+16GiB guard/liveRSS. Genuine828 full geometry prerequisite, no404/405 qualification transfer; failed high STA preserved separately from experiment completion.'
 for d in t['receipts']:
  for k in ('path','producer_state'):
   if k in d:d[k]=d[k].replace('block-v1-20261030-405','block-v1-20261101-828')
stage(829,queue)
