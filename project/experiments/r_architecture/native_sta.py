from pathlib import Path
import subprocess,json,hashlib,os,concurrent.futures,re
B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');P=Path(__file__).resolve().parent;O=Path.cwd()/'results';O.mkdir(exist_ok=False)
def run(item):
 label,source,top=item;d=O/label;d.mkdir();src=B/source/'mapped.v';data=src.read_text();net=d/'input.v';net.write_text(re.sub(r'\bwire signed\b','wire',data));empty=d/'classified.tcl';empty.write_text('set state_q {}; set state_d {}; set operand_d {}\n');env=os.environ.copy();env.update(INPUT_NETLIST=str(net),INPUT_TOP=top,INPUT_SDC=str(P/'physical.sdc'),INPUT_CLASSIFICATION=str(empty))
 with(d/'sta.log').open('w')as f:r=subprocess.run(['openroad','-exit',str(P/'sta_probe.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT)
 receipt=dict(candidate=label,exit=r.returncode,passed=r.returncode==0,source_mapped_v=str(src),mapped_v_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),log_sha256=hashlib.sha256((d/'sta.log').read_bytes()).hexdigest(),scope='zero-wire pin-load arithmetic timing only; no integrated physical qualification');(d/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:rows=list(pool.map(run,[('C-N','attempt055/unit/c_wide_native','c_wide_native'),('C-E','attempt037/results/c_wide_e','c_wide_e'),('C-M','attempt009/results/c_wide_m','c_wide_m'),('C-finish','attempt009/results/c_finish','c_finish')]))
(O/'STA_RECEIPTS.json').write_text(json.dumps(rows,indent=2)+'\n');assert all(r['passed']for r in rows)
