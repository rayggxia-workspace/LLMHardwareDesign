"""Pure generation from byte-exact run18 tests; actual EDA is server-only."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BENCH_SHA={
 'r2_r1_tb_legacy.sv':'de8acde82398a7faedd75aab363393875611f5614af96398dc3ee675e44379da',
 'r2_r1_tb_enabled_legacy.sv':'0bb13a59d2593b457f83628ca2d58d2a01eb5a6194e9e793fcc9d9ef198ccfb4',
 'r2_tb_nexp_compute.sv':'0bb18a1d14f6c95c90a431ba665d9ac16b23a2e0714c6f97bef567ead69d1b11',
 'r2_tb_nexp_group_gate.sv':'311a022741a8e87e1fed445c66f18d3b85eae32c822b3fa282b4abebff1788f2',
 'r2_tb_nexp_stateless.sv':'6c43d49e990fae8053d86df67eb52cf796a692feba3cdb7f44e9973a54861a81',
 'r2_tb_nexp_u.sv':'4d036bdf1e35e3e8e38bdad77e35fb9e5a18c8730995139597c59becee00eb0d'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(text,old,new):
 if text.count(old)!=1:raise ValueError('R4 bench anchor drift '+repr(old))
 return text.replace(old,new,1)

def rtl_generator():
 path=HERE/'generate_rtl.py'
 if not path.exists():path=HERE.parents[1]/'feed/round4/generate.py'
 spec=importlib.util.spec_from_file_location('round4_rtl_generator',path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def watcher(h,cv,ready,op,count,valid,take,error,direct):
 # Observe actual old-state CALC edges, not predicted wall time. The one
 # production N never accepts a successor before its held response retires.
 return f'''
 integer lane_pending=0,lane_count=0,lane_one_steps=0;
 integer lane_completed=0,lane_checked=0,lane_steps=0,lane_cycles=0;
 integer lane_hist[1:8];integer lane_hist_steps[1:8];
 initial for(integer i=1;i<=8;i++)begin lane_hist[i]=0;lane_hist_steps[i]=0;end
 always @(posedge clk)begin
  lane_cycles<=lane_cycles+1;
  if(reset)begin lane_pending=0;lane_one_steps=0;end
  else begin
   if({valid}&&{take}&&lane_pending!=0)begin
    if({error})begin
     if(lane_one_steps!=0)$fatal(1,"invalid native op12 executed CALC");
    end else begin
     if(lane_count<1||lane_count>8||lane_one_steps!=(lane_count+LANES-1)/LANES)
      $fatal(1,"actual op12 CALC steps mismatch count=%0d lanes=%0d steps=%0d",lane_count,LANES,lane_one_steps);
     lane_completed++;lane_checked++;lane_steps+=lane_one_steps;
     lane_hist[lane_count]++;lane_hist_steps[lane_count]+=lane_one_steps;
    end
    lane_pending=0;
   end
   if({cv}&&{ready}&&{op}==12)begin
    if(lane_pending!=0)$fatal(1,"overlapping native op12 ownership");
    lane_pending=1;lane_count=int'({count});lane_one_steps=0;
   end
   if({h}.phase=={h}.CALC&&{h}.operation==12)begin
    if(lane_pending==0)$fatal(1,"CALC without accepted op12");
    lane_one_steps++;
   end
  end
 end
 task automatic lane_report;
  begin
   $display("NEXP_LANE_PATH direct_mode=%0d direct_lanes=%0d op12_completed=%0d calc_steps=%0d checked_commands=%0d",{direct},LANES,lane_completed,lane_steps,lane_checked);
   for(integer i=1;i<=8;i++)$display("NEXP_LANE_COUNT count=%0d commands=%0d calc_steps=%0d",i,lane_hist[i],lane_hist_steps[i]);
  end
 endtask
 // Passive trace is injected into BOTH exact-R2 and candidate tests. It adds
 // no stimulus/delay and compares all accepted native commands/responses.
 always @(posedge clk)if(!reset)begin
  if({h}.cmd_valid&&{h}.cmd_ready)
   $display("R4_TRACE CMD c=%0d op=%0d count=%0d param=%h data=%h aux=%h",lane_cycles,{h}.cmd_op,{h}.cmd_count,{h}.cmd_param,{h}.cmd_data,{h}.cmd_aux);
  if({h}.rsp_valid&&{h}.rsp_ready)
   $display("R4_TRACE RSP c=%0d data=%h error=%0d sat=%0d",lane_cycles,{h}.rsp_data,{h}.rsp_error,{h}.rsp_saturated);
 end
'''

def instrument(text,kind,candidate):
 if kind=='compute':
  old='module tb_nexp_compute #(parameter integer DIRECT=1);'
  text=once(text,old,old[:-2]+', LANES=2);' if candidate else old+'\n localparam integer LANES=2;')
  if candidate:text=once(text,'block_v2_n #(.NEXP_DIRECT(DIRECT)) only_native_N(',
   'block_v2_n #(.NEXP_DIRECT(DIRECT),.NEXP_DIRECT_LANES(LANES)) only_native_N(')
  code=watcher('only_native_N','nv','nready','nm[3:0]','nm[7:4]','nr','nrr','ne','DIRECT')
  text=once(text,'  $display("NEXP_NATIVE_PATH','  lane_report();\n  $display("NEXP_NATIVE_PATH')
 elif kind=='full_U':
  old='module tb_nexp_u #(parameter integer DIRECT=1);'
  text=once(text,old,old[:-2]+', LANES=2);' if candidate else old+'\n localparam integer LANES=2;')
  if candidate:text=once(text,'pu_u_group #(.NEXP_BATCH(1),.NEXP_DIRECT(DIRECT)) dut(',
   'pu_u_group #(.NEXP_BATCH(1),.NEXP_DIRECT(DIRECT),.NEXP_DIRECT_LANES(LANES)) dut(')
  code=watcher('dut.normalize','dut.core_valid','dut.core_ready','dut.core_meta[3:0]',
   'dut.core_meta[7:4]','dut.core_result_valid','dut.core_result_ready','dut.core_error','DIRECT')
  text=once(text,'  $display("NEXP_NATIVE_PATH','  lane_report();\n  $display("NEXP_NATIVE_PATH')
 else:
  text=once(text,'module tb_nexp_stateless;',
   'module tb_nexp_stateless #(parameter integer LANES=2);' if candidate else 'module tb_nexp_stateless;\n localparam integer LANES=2;')
  if candidate:text=once(text,'block_v2_n #(.NEXP_DIRECT(1)) dut(',
   'block_v2_n #(.NEXP_DIRECT(1),.NEXP_DIRECT_LANES(LANES)) dut(')
  code=watcher('dut','cv','ready','op','count','valid','take','error',"1'b1")
  text=once(text,'  $display("STATELESS_PASS','  lane_report();\n  $display("STATELESS_PASS')
 return once(text,'endmodule',code+'endmodule')

def prepare(repo,out,integrated=True):
 for name,digest in BENCH_SHA.items():
  if sha(HERE/name)!=digest:raise ValueError('run18 bench template drift '+name)
 repo,out=Path(repo).resolve(),Path(out).resolve();result=rtl_generator().generate(repo,out,integrated)
 for name in BENCH_SHA:(out/name).write_bytes((HERE/name).read_bytes())
 for kind,name in (('compute','tb_nexp_compute.sv'),('full_U','tb_nexp_u.sv'),('stateless','tb_nexp_stateless.sv')):
  source=(HERE/('r2_'+name)).read_text(encoding='utf8')
  for prefix,candidate in (('baseline_',False),('',True)):
   (out/(prefix+name)).write_bytes(instrument(source,kind,candidate).encode())
 gate=(HERE/'r2_tb_nexp_group_gate.sv').read_text(encoding='utf8')
 gate=once(gate,'module tb_nexp_group_gate;','module tb_nexp_group_gate #(parameter integer LANES=2);')
 gate=once(gate,'.NEXP_DIRECT(i/2)) dut(','.NEXP_DIRECT(i/2),.NEXP_DIRECT_LANES(LANES)) dut(')
 (out/'tb_nexp_group_gate.sv').write_bytes(gate.encode())
 enabled=(HERE/'r2_r1_tb_enabled_legacy.sv').read_text(encoding='utf8')
 direct=once(enabled,'pu_u_group #(.NEXP_BATCH(1)) dut (',
  'pu_u_group #(.NEXP_BATCH(1),.NEXP_DIRECT(1),.NEXP_DIRECT_LANES(4)) dut (')
 (out/'tb_direct_legacy.sv').write_bytes(direct.encode())
 disabled=once(enabled,'pu_u_group #(.NEXP_BATCH(1)) dut (',
  'pu_u_group #(.NEXP_BATCH(1),.NEXP_DIRECT(0),.NEXP_DIRECT_LANES(4)) dut (')
 (out/'tb_disabled_legacy.sv').write_bytes(disabled.encode())
 plain=(HERE/'r2_r1_tb_legacy.sv').read_text(encoding='utf8')
 plain=once(plain,'pu_u_group dut (','pu_u_group #(.NEXP_DIRECT_LANES(4)) dut (')
 (out/'tb_lanes4_legacy.sv').write_bytes(plain.encode())
 result['bench_sha256']={p.name:sha(p) for p in out.glob('*.sv')}
 result['template_run18_sha256']=BENCH_SHA
 (out/'preparation.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--prepare',action='store_true');a=p.parse_args();print(json.dumps(prepare(a.repo,a.out,not a.prepare)))
