"""Collect actual fixed-PG six-file indices and layout images for five new leaves."""
from pathlib import Path
import json,subprocess,shlex,hashlib,concurrent.futures
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');out=repo/'work/YUZE-LU/162/block-delivery-r256-c285';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();leaves=[]
for folder in [b/'r256-fixed-pg-271/2371/delivery']:
 r=json.loads((folder/'receipt.json').read_text());assert r['passed']and r['native_leaf_qualified']
 d=json.loads((folder/'delivery.json').read_text());assert sha(folder/'delivery.json')==r['outputs']['delivery.json']and d['passed']and d['native_leaf_accepted']
 assert set(d['final_files'])=={'6_final.'+s for s in ['v','sdc','def','odb','spef','gds']}
 for f in d['final_files'].values():assert sha(f['path'])==f['sha256']
 for key in ['original_delivery','fresh_physical_receipt','fresh_timing_receipt']:assert sha(d[key])==d[key+'_sha256']
 image=folder/'layout.png';assert sha(image)==d['image_sha256']
 row=dict(d,delivery=dict(path=str(folder/'delivery.json'),sha256=sha(folder/'delivery.json')),receipt=dict(path=str(folder/'receipt.json'),sha256=sha(folder/'receipt.json')),image=dict(path='images/'+d['top']+'.png',remote=str(image),sha256=sha(image)),pins=dict(path=str(folder/'pins.json'),sha256=sha(folder/'pins.json')))
 assert row['pins']['sha256']==d['pins_sha256'];leaves.append(row)
print(json.dumps(dict(passed=True,leaves=leaves,individually_qualified_types=1,whole_system_qualified=False,captured_at=time.time(),scope='Genuinely qualified actual C8 new fixed-PG type. R new fixedPG and all composed-system gates remain separate unfinished tasks; no composed qualification.')))
'''
compile(q,'leaf_index260','exec')
d=json.loads(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));out.mkdir();(out/'images').mkdir()
def receive(row):
 p=out/row['image']['path'];subprocess.run(['scp','-o','ConnectTimeout=10','yuzelu@10.129.166.172:'+row['image']['remote'],str(p)],check=True,stdout=subprocess.DEVNULL);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['image']['sha256']
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:list(pool.map(receive,d['leaves']))
(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(leaves=len(d['leaves']),six_file_bytes=sum(f['bytes']for r in d['leaves']for f in r['final_files'].values()),index=str(out/'index.json'),whole_system_qualified=False)))
