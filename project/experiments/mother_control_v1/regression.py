"""Run actual SRAM-integrated mother against finite peers; no Block-RTL claim."""
import argparse,json,os,subprocess,sys,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--netlist',type=Path);p.add_argument('--cells',type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(a.upstream/'project/control_image_v0_1'));import image
 bundle=json.loads((a.upstream/'project/control_image_v0_1/bundles.json').read_text())['bundles'];raw=bytes.fromhex(next(b for b in bundle if b['manifest']['bundle']=='receiver_first_16B')['images_hex']['mother']);parsed=image.parse_image(raw,'mother')
 images={}
 programs={'single':[dict(op='G_CALL',a=0,b=0,c=0),dict(op='G_WAIT',x=1),dict(op='G_END')],
 'two':[dict(op='G_CALL',a=1,b=0,c=0),dict(op='G_CALL',a=0,b=1,c=0),dict(op='G_WAIT',x=3),dict(op='G_END')],
 'movi':[dict(op='G_MOVI',a=7,x=0x12345678),dict(op='G_CALL',a=0,b=0,c=0),dict(op='G_WAIT',x=1),dict(op='G_END')],
 'target1':[dict(op='G_CALL',a=1,b=0,c=0),dict(op='G_WAIT',x=1),dict(op='G_END')]}
 for n,program in programs.items():images[n]=image.assemble_image('mother',program,{},700+len(images),instruction_version=2)
 images['receiver']=image.pack_image('mother',parsed['program'],parsed['records'],parsed['header'],instruction_version=2)
 cases=[dict(name='single',image='single',CALLS=1),dict(name='repeat_jobs',image='single',CALLS=2,RUNS=2,STALL=3),dict(name='two_parallel',image='two',CALLS=2),dict(name='movi',image='movi',CALLS=1),dict(name='receiver_ready_ack',image='receiver',CALLS=2,READY1=1,DEPENDENCY=1,TRAFFIC=1,STALL=2),dict(name='held_call',image='two',CALLS=2,HOLD_TARGET=0,HOLD_CYCLES=180,DELAY1=10),dict(name='cancel_peer_error',image='two',CALLS=2,ERROR_TARGET=0,DELAY0=10,DELAY1=200,CANCELS=1,EXPECTED=9),dict(name='ready_error',image='receiver',CALLS=1,READY1=1,DEPENDENCY=1,ERROR_TARGET=1,EXPECTED=9),dict(name='missing_peer',image='single',CALLS=1,NO_TERMINAL=0,POISON=1),dict(name='stale_return',image='single',CALLS=1,BAD_RETURN=1,POISON=1),dict(name='revoke',image='single',CALLS=0,MODE=5,HOLD_TARGET=0,HOLD_CYCLES=2000,POISON=1),dict(name='disabled_target',image='target1',CALLS=0,ENABLED=1,EXPECTED=4),dict(name='partial_load',image='single',CALLS=0,MODE=1),dict(name='bad_header',image='single',CALLS=0,MODE=2),dict(name='start_generation',image='single',CALLS=0,MODE=3),dict(name='start_arguments',image='single',CALLS=0,MODE=4),dict(name='prefix_overflow',image='two',CALLS=2,PREFIX_MAX=1)]
 rtl=ROOT/'project/rtl/mother_control_v1';bank=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v');assert sha(bank)=='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
 if a.netlist:assert a.cells;sources=[a.netlist,a.cells]
 else:sources=[rtl/'mc_min_controller.sv',rtl/'control_pm.sv',ROOT/'project/rtl/s_sram/block_feed_s16k_sram.sv',rtl/'mother_control_64.sv']
 verilator='/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator';cmd=[verilator,'--binary','--timing','-Wno-fatal','--x-initial','unique','--x-assign','unique','--top-module','tb_mother','-I'+str(rtl),'-I'+str(HERE),'--Mdir',str(out/'obj'),'-j',str(os.environ.get('SLURM_CPUS_PER_TASK','4')),str(HERE/'tb_mother.sv'),*map(str,sources),str(bank)]
 def run(cmd,log):
  with (out/log).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:raise RuntimeError(f'{log}: exit {r.returncode}')
 run(cmd,'compile.log');results=[]
 for c in cases:
  data=images[c['image']]
  if c.get('MODE')==2:data=bytes([data[0]^1])+data[1:]
  path=out/(c['name']+'.mem');path.write_text('\n'.join(f'{int.from_bytes(data[i:i+16],"little"):032x}' for i in range(0,len(data),16))+'\n')
  for mode,seed in [(1,143),(2,143),(2,144)]:
   args=[str(out/'obj/Vtb_mother'),'+IMAGE='+str(path),'+WORDS='+str(len(data)//16),'+verilator+rand+reset+'+str(mode),'+verilator+seed+'+str(seed)]+['+'+k+'='+str(v) for k,v in c.items() if k not in ('name','image')]
   log=f"{c['name']}-{mode}-{seed}.log";run(args,log);assert 'PASS mother' in (out/log).read_text();results.append(dict(case=c['name'],reset_mode=mode,seed=seed,image_sha256=hashlib.sha256(data).hexdigest(),log_sha256=sha(out/log)));print('PASS',log,flush=True)
 report=dict(schema='mother-pm-regression/1',passed=True,results=results,source_sha256={str(f):sha(f) for f in sources},bank_sha256=sha(bank),compile_command=cmd,actual_sram=True,actual_block_rtl=False,finite_peers=2,full_isa=False,physical_netlist=bool(a.netlist),instruction_version=2,instruction_bits=64)
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
