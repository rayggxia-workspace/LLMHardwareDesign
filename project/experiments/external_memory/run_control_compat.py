"""Read-only snapshot of #162 D, exercised with both actual S RTL variants.

No mutation of the control worktree. SRAM uses its explicit simulation model.
This is local RTL simulation, not the remote Slurm/physical flow.
"""
import argparse, hashlib, json, os, shutil, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--control-root',type=Path,required=True)
    p.add_argument('--verilator',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--control-commit',required=True,help='Observed host Git HEAD; file SHA remains authoritative')
    a=p.parse_args();control=a.control_root.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    names=['project/rtl/control_v1/'+n+'.sv' for n in ['control_d','control_dma_planner','control_dma_read','control_dma_write']]
    fixtures=['project/experiments/control_v1/control_d_s_pair.sv','project/experiments/control_v1/test_d.cpp']
    storage=['project/rtl/block_feed_v1/'+n+'.sv' for n in ['block_feed_s_macro','block_feed_s16k','block_feed_loader']]
    storage+=['project/rtl/s_sram/'+n for n in ['block_feed_s_macro_sram.sv','block_feed_s16k_sram.sv','s_sram_256x128_freepdk45.sim.sv']]
    receipt=dict(passed=False,scope='D + actual S RTL interface compatibility; SRAM sim model, no PPA/system qualification',control_head=a.control_commit,inputs={},runs={},commands=[])
    try:
      with tempfile.TemporaryDirectory(prefix='i156-control-') as t:
        t=Path(t);stage=t/'src';stage.mkdir()
        for base,paths in [(control,names+fixtures),(ROOT,storage)]:
          for n in paths:
            src=base/n;dst=stage/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
            receipt['inputs'][str(src)]=sha(src)
            saved=out/'sources'/n;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,saved)
        tool=t/'tool';shutil.copytree(a.verilator.resolve().parent.parent,tool)
        compiler=tool/'bin/verilator';env=dict(os.environ,VERILATOR_ROOT=str(tool/'share/verilator'))
        receipt['tool']=subprocess.check_output([compiler,'--version'],text=True,env=env).strip()
        for variant in ['cell','sram']:
          work=out/variant;work.mkdir();pair=stage/fixtures[0]
          text=pair.read_text()
          if variant=='sram':text=text.replace('block_feed_s_macro storage(', 'block_feed_s_macro_sram storage(')
          top=t/(variant+'.sv');top.write_text(text);shutil.copyfile(top,work/'fixture.sv')
          cpp=t/(variant+'.cpp')
          original=(stage/fixtures[1]).read_text()
          marker=' std::cout<<'
          assert original.count(marker)==1
          supplement='''
 { // Coordinated reset with accepted AXI work; flush platform and D together.
  Sim x;x.send(descriptor(false,201,0,0,1024,1,0,0));
  for(unsigned i=0;i<12;++i)x.tick();
  need(x.ar_count>0,"reset exercises accepted AXI work");
  x.v.reset=1;for(unsigned i=0;i<4;++i){x.v.clk=0;x.v.eval();x.v.clk=1;x.v.eval();}
  x.reads={};x.writes.clear();x.b_pending={false,false};x.reads_live=0;x.writes_live=0;
  x.s_pending=false;x.stalled_complete=false;x.completions.clear();
  x.v.reset=0;x.v.clk=0;x.v.eval();
  x.send(descriptor(false,202,8192,0,256,1,0,0));
  need(x.finish()==(uint64_t(256)<<32|202),"post-reset fresh descriptor completion");
  x.send(descriptor(true,203,49152,0,256,1,0,0));
  need(x.finish()==(uint64_t(256)<<32|203),"post-reset data store");
  for(unsigned i=0;i<256;++i)need(x.ext[49152+i]==x.ext[8192+i],"post-reset actual S readback");
  x.drained();
 }
'''
          cpp.write_text(original.replace(marker,supplement+marker))
          shutil.copyfile(cpp,work/'test.cpp');sources=[stage/n for n in names+storage]
          argv=[compiler,'--cc','--exe','--build','-j','4','-Wno-fatal','--top-module','control_d_s_pair','--Mdir',t/(variant+'-obj'),'--x-initial','unique','--x-assign','unique','-DS_SRAM_SIM','-CFLAGS','-std=c++17 -O1 -DREAL_S',*sources,top,cpp]
          receipt['commands'].append(list(map(str,argv)))
          with (work/'build.log').open('w') as f:subprocess.run(list(map(str,argv)),env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
          receipt['runs'][variant]=[]
          for init,seed in [(1,162),(2,162),(2,163)]:
            argv=[t/(variant+'-obj/Vcontrol_d_s_pair'),f'+verilator+rand+reset+{init}',f'+verilator+seed+{seed}']
            with (work/f'{init}-{seed}.json').open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True)
            row=json.loads((work/f'{init}-{seed}.json').read_text());assert row['passed'];receipt['runs'][variant].append(dict(init=init,seed=seed,**row))
        for name,h in receipt['inputs'].items():assert sha(Path(name))==h,'concurrent source mutation: '+name
        receipt['passed']=True
    finally:
      receipt['outputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
      (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt['runs']))
if __name__=='__main__':main()
