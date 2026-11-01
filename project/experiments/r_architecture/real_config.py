"""Real Qwen3.5 GDN strip dimensions; synthetic integer coefficients, no accuracy claim."""
from pathlib import Path
import json,hashlib,subprocess,concurrent.futures
from workloads import create
ROOT=Path.cwd();OUT=ROOT/'results';OUT.mkdir(exist_ok=False);corpus=OUT/'corpus';corpus.mkdir()
model=dict(model='Qwen3.5-4B',source='docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md section 7.2/7.3',key_dimension=128,value_dimension=128,value_heads=32,recurrent_layers=24,convolution_taps=4,tested_unit='one key-128 by value-8 state strip, not full head or full layer',full_layer_state_elements=32*128*128,full_layer_two_version_bytes=2*4*32*128*128,all_24_layers_two_version_bytes=24*2*4*32*128*128,numeric_provenance='synthetic fixed-point inputs; real configuration dimensions only')
(OUT/'REAL_CONFIG.json').write_text(json.dumps(model,indent=2)+'\n')
cases=[create(corpus/('Qwen35-GDN-key128-value8-t%d.bin'%t),0,1024,1,t,2026110157+t)for t in [1,16]];(corpus/'MANIFEST.json').write_text(json.dumps(dict(cases=cases),indent=2)+'\n')
BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt022/results')
def run(task):
 arch,cap,case=task;binary=BASE/('a%d_%d'%(arch,cap))/'obj/Vresearch_top';dest=OUT/('a%d_%d_'%(arch,cap)+Path(case['path']).stem+'.json')
 with(dest.with_suffix('.log')).open('w')as f:r=subprocess.run([str(binary),str(corpus/case['path']),str(dest),'40','16','cache'],stdout=f,stderr=subprocess.STDOUT)
 row=dict(binary=str(binary),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),input_sha256=case['sha256'],workload=case['path'],exit=r.returncode);row.update(json.loads(dest.read_text())if dest.exists()else{});return row
with concurrent.futures.ThreadPoolExecutor(max_workers=12)as pool:rows=list(pool.map(run,[(a,c,k)for a,c in [(0,2048),(1,256),(1,512),(1,1024),(1,2048),(2,0)]for k in cases]))
(OUT/'RESULTS.json').write_text(json.dumps(rows,indent=2)+'\n');assert all(x['exit']==0 for x in rows)
