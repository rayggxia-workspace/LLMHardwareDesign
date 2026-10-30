import hashlib,json,shlex,subprocess,tarfile
from pathlib import Path
run='block-v1-20261030-460';base='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121';remote=base+'/'+run
archive=Path('.local/issue121/source460.tar');digest=hashlib.sha256(archive.read_bytes()).hexdigest()
with tarfile.open(archive)as tar:commit=json.load(tar.extractfile('bundle-manifest.json'))['source_commit']
queue=json.loads(Path('work/YUZE-LU/121/review-20261028/node-queue-422.json').read_bytes())
queue['state_path']=remote+'/node-queue-state.json'
for t in queue['tasks']:
 t['cwd']=remote+'/tasks/'+t['id'];t['source']=remote+'/src'
 for d in t['receipts']:d['path']=d['path'].replace('block-v1-20261030-421','block-v1-20261030-459')
 t['memory_basis']='Seven NEW replay-fetch pipeline V occupancy and finite SV/model measurements; required actual459 numerical/public/extended/composition/latency and264bit/130bit proofs plus unchanged348 group proof. New latency and actual bytes/stalls must be measured; no old422 qualification transfer. One c96 six16CPU slots dynamic refill, each32GiB forecast times1.2 plus16GiB nodeguard/liveRSS; no accepted M/S/T repeat, no cancellation, no physical qualification transfer.'
manifest=dict(run_id=run,base_nodes=6,max_nodes=8,elastic=True,source_commit=commit,source_archive_sha256=digest,tasks=[dict(id='native-node-queue',partition='c96',cpus=96,memory='0',minutes=0,after=[],argv=['bash',remote+'/src/project/experiments/block_v1/worker.sh',remote+'/src','native-node-queue'])])
folder=Path('work/YUZE-LU/121/review-20261028')
for name,value in [('node-queue-460.json',queue),('stage460-manifest.json',manifest)]:
 p=folder/name;assert not p.exists();p.write_bytes((json.dumps(value,indent=2)+'\n').encode())
def ssh(command):subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172',command],check=True)
ssh('test ! -e '+remote+' && mkdir '+remote+' && mkdir '+remote+'/src')
for local,name in [(archive,'source.tar'),(folder/'node-queue-460.json','node-queue.json'),(folder/'stage422-manifest.json','manifest.json')]:subprocess.run(['scp','-q',str(local),'yuzelu@10.129.166.172:'+remote+'/'+name],check=True)
check="from pathlib import Path;import hashlib;assert hashlib.sha256(Path('source.tar').read_bytes()).hexdigest()=='"+digest+"'"
validate="import json,sys;from pathlib import Path;sys.path.insert(0,'src/project/experiments/block_v1');from native_node_queue import validate;validate(json.loads(Path('node-queue.json').read_text()),Path.cwd().parent)"
ssh('cd '+remote+' && python3 -c '+shlex.quote(check)+' && tar -xf source.tar -C src && python3 -c '+shlex.quote(validate)+' && python3 src/project/experiments/block_v1/dispatch.py manifest.json --submit')
