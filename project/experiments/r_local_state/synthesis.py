from pathlib import Path
import os,subprocess,json,hashlib,concurrent.futures,argparse
ROOT=Path.cwd();S=ROOT/'project/rtl/r_local_state';L='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
p=argparse.ArgumentParser();p.add_argument('--capacity',type=int,choices=[256,1024]);p.add_argument('--functional-root',type=Path);p.add_argument('--timing-driven',action='store_true');p.add_argument('--finalize-pipeline',action='store_true');a=p.parse_args()
assert not a.finalize_pipeline or a.capacity==1024
if a.finalize_pipeline:S=ROOT/'project/experiments/r_local_state/experimental_finalize'
capacities=[a.capacity]if a.capacity else[256,1024]
cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=16*len(capacities)
PRE=a.functional_root or Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt010/results')
def run(cap,slot):
 rows=[json.loads((PRE/str(cap)/f'init-{i}.json').read_text())for i in range(3)]
 assert all(row['passed']for row in rows)
 assert all(row['source_sha256']==rows[0]['source_sha256']for row in rows)
 assert all(row.get('finalize_pipeline',0)==int(a.finalize_pipeline)for row in rows),'Functional parameter differs from synthesis'
 r=rows[0]
 assert r['source_sha256']=={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in S.glob('*.sv')}
 out=ROOT/'results'/str(cap);out.mkdir(parents=True,exist_ok=False)
 abc_options=''
 if a.timing_driven:
  assert cap==1024,'Keep the qualified256 implementation frozen'
  with(out/'abc-help.log').open('w')as log:subprocess.run(['yosys','-Q','-T','-p','help abc'],stdout=log,stderr=subprocess.STDOUT,check=True)
  help_text=(out/'abc-help.log').read_text();assert '-constr'in help_text and '-D <picoseconds>'in help_text and 'set_load'in help_text
  # Conservative load at every extracted combinational boundary, matching
  # the original external50fF load. This is synthesis guidance, not an SDC
  # change or a promise that the final routed macro meets timing.
  (out/'abc.constr').write_text('set_driving_cell BUF_X2\nset_load 50\n')
  abc_options=' -constr '+str(out/'abc.constr')+' -D 3000'
 script=f'''read_liberty -lib {L}
read_verilog -sv {S/'r_state_store.sv'} {S/'r_stream_local.sv'}
chparam -set WORDS {cap} r_stream_local
{('chparam -set FINALIZE_PIPELINE 1 r_stream_local'if a.finalize_pipeline else'')}
hierarchy -check -top r_stream_local
proc
opt
synth -top r_stream_local -flatten -noabc
dfflibmap -liberty {L}
abc -liberty {L}{abc_options}
clean
check -assert
stat -liberty {L}
write_json mapped.json
write_verilog -noattr mapped.v
'''
 (out/'map.ys').write_text(script)
 rec={'capacity':cap,'passed':False,'source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in S.glob('*.sv')},'functional_source':[str(PRE/str(cap)/f'init-{i}.json')for i in range(3)]}
 rec['abc_options']=abc_options
 rec['finalize_pipeline']=int(a.finalize_pipeline)
 if a.timing_driven:rec['abc_policy']=dict(delay_target_ps=3000,driving_cell='BUF_X2',load_ff=50,constr_sha256=hashlib.sha256((out/'abc.constr').read_bytes()).hexdigest(),actual_help_sha256=hashlib.sha256((out/'abc-help.log').read_bytes()).hexdigest(),rtl_unchanged=True,final_300mhz_io_gates_unchanged=True,reference='https://yosyshq.readthedocs.io/projects/yosys/en/0.47/cmd/abc.html')
 try:
  with(out/'map.log').open('w')as f:subprocess.run(['taskset','-c',','.join(map(str,cpus[slot*16:(slot+1)*16])),'yosys','-s','map.ys'],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
  rec.update(mapped=True,mapped_json_sha256=hashlib.sha256((out/'mapped.json').read_bytes()).hexdigest())
  with(out/'selection.log').open('w')as f:subprocess.run(['taskset','-c',','.join(map(str,cpus[slot*16:(slot+1)*16])),'python3',str(ROOT/'project/experiments/r_local_state/audit_selection.py'),str(out/'mapped.json'),'--capacity',str(cap),'--out',str(out/'SELECTION.json')],stdout=f,stderr=subprocess.STDOUT,check=True)
  rec['passed']=True
 except Exception as e:rec['error']=str(e)
 (out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=len(capacities))as pool:rr=list(pool.map(lambda x:run(*x),[(cap,slot)for slot,cap in enumerate(capacities)]))
(ROOT/'results/receipt.json').write_text(json.dumps(rr,indent=2)+'\n');assert all(x['passed']for x in rr)
