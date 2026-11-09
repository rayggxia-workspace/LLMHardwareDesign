"""Prepare R2 tests from exact run16 benches; no compilation or simulation."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BENCH_SHA={
 'r1_tb_nexp_compute.sv':'fb78901119e4617d40283177c848ca1de10350a48c6a09b7ddab5181cca5f65d',
 'r1_tb_nexp_u.sv':'0c938eec4f49fcc4f7a1aea48a504266fb1424fc9321acd85b60a90406222004',
 'r1_tb_legacy.sv':'de8acde82398a7faedd75aab363393875611f5614af96398dc3ee675e44379da',
 'r1_tb_enabled_legacy.sv':'0bb13a59d2593b457f83628ca2d58d2a01eb5a6194e9e793fcc9d9ef198ccfb4'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(text,old,new):
 if text.count(old)!=1:raise ValueError('R2 test anchor drift '+repr(old))
 return text.replace(old,new,1)

def rtl_generator():
 path=HERE/'generate_rtl.py'
 if not path.exists():path=HERE.parents[1]/'feed/round2/generate.py'
 spec=importlib.util.spec_from_file_location('round2_rtl_generator',path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

def prepare(repo,out,integrated=True):
 repo,out=Path(repo).resolve(),Path(out).resolve()
 for name,digest in BENCH_SHA.items():
  if sha(HERE/name)!=digest:raise ValueError('run16 benchmark drift '+name)
 module=rtl_generator();result=module.generate(repo,out,integrated)
 for name in BENCH_SHA:(out/name).write_bytes((HERE/name).read_bytes())
 compute=(HERE/'r1_tb_nexp_compute.sv').read_text(encoding='utf8')
 compute=once(compute,'module tb_nexp_compute;','module tb_nexp_compute #(parameter integer DIRECT=1);')
 compute=once(compute,'pu_nexp_shared dut(','pu_nexp_shared #(.NEXP_DIRECT(DIRECT)) dut(')
 compute=once(compute,'block_v2_n only_native_N(','block_v2_n #(.NEXP_DIRECT(DIRECT)) only_native_N(')
 compute=once(compute,' integer ticks=0,checks=0,values=0,frames=0,n_commands=0;',
  ''' integer ticks=0,checks=0,values=0,frames=0,n_commands=0;
 integer direct_commands=0,other_commands=0;
 always @(posedge clk)if(!reset&&nv&&nready)begin
  if(nm[3:0]==12)direct_commands++;else other_commands++;
 end''')
 compute=once(compute,'  $display("NEXP_COMPUTE_PASS',
  '''  $display("NEXP_NATIVE_PATH direct_mode=%0d op12_commands=%0d other_commands=%0d",DIRECT,direct_commands,other_commands);
  $display("NEXP_COMPUTE_PASS''')
 (out/'tb_nexp_compute.sv').write_bytes(compute.encode())
 full=(HERE/'r1_tb_nexp_u.sv').read_text(encoding='utf8')
 full=once(full,'module tb_nexp_u;','module tb_nexp_u #(parameter integer DIRECT=1);')
 full=once(full,'pu_u_group #(.NEXP_BATCH(1)) dut(','pu_u_group #(.NEXP_BATCH(1),.NEXP_DIRECT(DIRECT)) dut(')
 full=once(full,' integer ticks=0,reads=0,writes=0,core_accept=-1,core_response=-1,checks=0;',
  ''' integer ticks=0,reads=0,writes=0,core_accept=-1,core_response=-1,checks=0;
 integer direct_commands=0,other_commands=0;
 always @(posedge clk)if(!reset&&dut.core_valid&&dut.core_ready)begin
  if(dut.core_meta[3:0]==12)direct_commands++;else other_commands++;
 end''')
 full=once(full,'  $display("NEXP_U_PASS',
  '''  $display("NEXP_NATIVE_PATH direct_mode=%0d op12_commands=%0d other_commands=%0d",DIRECT,direct_commands,other_commands);
  $display("NEXP_U_PASS''')
 begin=full.index('  // This destructive ABI intentionally invalidates an earlier scalar context.')
 end=full.index('  // Real shared-S arbitration',begin)
 old=full[begin:end]
 new='''  // DIRECT0 reproduces the original destructive ABI exactly. DIRECT1
  // computes expected values before the snapshot, then issues no golden
  // scalar command between the snapshot and the operation under test.
  if(DIRECT==0)begin
'''+old+'''  end else begin
   scalar(16'd12345,x);command(7,0,0,0,0,0,0,0,0,0,0,before_stats);
   access(1,16,0,ignored);
   command(15,4,32'h4e583332,1,1,0,20'd16,0,3,0,1,got);
   if(got!=={4{32'd32768}})$fatal(1,"direct preserve result");
   command(7,0,0,0,0,0,0,0,0,0,0,after_stats);
   if(before_stats!==after_stats)$fatal(1,"direct batch changed normal context");
  end
'''
 full=once(full,old,new)
 (out/'tb_nexp_u.sv').write_bytes(full.encode())
 for name in ('tb_nexp_stateless.sv','tb_nexp_group_gate.sv'):(out/name).write_bytes((HERE/name).read_bytes())
 result['bench_sha256']={p.name:sha(p) for p in out.glob('*.sv')}
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 return result

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--prepare',action='store_true');a=p.parse_args();print(json.dumps(prepare(a.repo,a.out,not a.prepare)))
