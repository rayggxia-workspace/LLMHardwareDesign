from pathlib import Path
import subprocess,os,json,concurrent.futures,hashlib,re
BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');P=Path(__file__).resolve().parent;OUT=Path.cwd()/'results';OUT.mkdir(exist_ok=False)
tasks=[('A0',BASE/'attempt001/results/A0-map','block_v1_r')]+[('B'+str(c),BASE/('attempt011/results/'+str(c)),'r_stream')for c in [256,512,1024,2048]]
def run(item):
 name,source,top=item;folder=OUT/name;folder.mkdir();v=(source/'mapped.v').read_text();normalized=re.sub(r'\bwire signed\b','wire',v);net=folder/'input.v';net.write_text(normalized);env=os.environ.copy();env.update(INPUT_NETLIST=str(net),INPUT_TOP=top,INPUT_SDC=str(P/'physical.sdc'));result=dict(candidate=name,passed=False,scope='pre-placement pin-load timing; zero interconnect RC, no physical signoff',mapped_json_sha256=hashlib.sha256((source/'mapped.json').read_bytes()).hexdigest())
 with(folder/'sta.log').open('w')as f:r=subprocess.run(['openroad','-exit',str(P/'sta_probe.tcl')],stdout=f,stderr=subprocess.STDOUT,env=env)
 result.update(passed=r.returncode==0,exit=r.returncode,log_sha256=hashlib.sha256((folder/'sta.log').read_bytes()).hexdigest());(folder/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:rows=list(pool.map(run,tasks))
(OUT/'STA_RECEIPTS.json').write_text(json.dumps(rows,indent=2)+'\n');assert all(x['passed']for x in rows)
