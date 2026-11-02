from pathlib import Path
import os,subprocess,json,hashlib,concurrent.futures,argparse
ROOT=Path.cwd();S=ROOT/'project/rtl/r_local_state';L='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
p=argparse.ArgumentParser();p.add_argument('--capacity',type=int,choices=[256,1024]);a=p.parse_args()
capacities=[a.capacity]if a.capacity else[256,1024]
cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=16*len(capacities)
PRE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt010/results')
def run(cap,slot):
 rows=[json.loads((PRE/str(cap)/f'init-{i}.json').read_text())for i in range(3)]
 assert all(row['passed']for row in rows)
 assert all(row['source_sha256']==rows[0]['source_sha256']for row in rows)
 r=rows[0]
 assert r['source_sha256']=={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in S.glob('*.sv')}
 out=ROOT/'results'/str(cap);out.mkdir(parents=True,exist_ok=False)
 script=f'''read_liberty -lib {L}
read_verilog -sv {S/'r_state_store.sv'} {S/'r_stream_local.sv'}
chparam -set WORDS {cap} r_stream_local
hierarchy -check -top r_stream_local
proc
opt
synth -top r_stream_local -flatten -noabc
dfflibmap -liberty {L}
abc -liberty {L}
clean
check -assert
stat -liberty {L}
write_json mapped.json
write_verilog -noattr mapped.v
'''
 (out/'map.ys').write_text(script)
 rec={'capacity':cap,'passed':False,'source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in S.glob('*.sv')},'functional_source':[str(PRE/str(cap)/f'init-{i}.json')for i in range(3)]}
 try:
  with(out/'map.log').open('w')as f:subprocess.run(['taskset','-c',','.join(map(str,cpus[slot*16:(slot+1)*16])),'yosys','-s','map.ys'],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
  rec.update(mapped=True,mapped_json_sha256=hashlib.sha256((out/'mapped.json').read_bytes()).hexdigest())
  with(out/'selection.log').open('w')as f:subprocess.run(['taskset','-c',','.join(map(str,cpus[slot*16:(slot+1)*16])),'python3',str(ROOT/'project/experiments/r_local_state/audit_selection.py'),str(out/'mapped.json'),'--capacity',str(cap),'--out',str(out/'SELECTION.json')],stdout=f,stderr=subprocess.STDOUT,check=True)
  rec['passed']=True
 except Exception as e:rec['error']=str(e)
 (out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=len(capacities))as pool:rr=list(pool.map(lambda x:run(*x),[(cap,slot)for slot,cap in enumerate(capacities)]))
(ROOT/'results/receipt.json').write_text(json.dumps(rr,indent=2)+'\n');assert all(x['passed']for x in rr)
