"""Derive full-U regressions without changing their existing assertions."""
from pathlib import Path
import hashlib,json
from vectors import generate as vectors

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise ValueError('source anchor '+a)
    return s.replace(a,b)

BRIDGE_TASK=r'''
 task automatic bridge_case(input integer count,input bit alias_input,input bit nostore);
  integer prior_reads,prior_writes;reg [127:0] lo,hi,raw16,unused,got0,got1;
  reg [15:0] exp_value;
  begin
   lo=0;hi=0;raw16=128'hdeadbeefdeadbeefdeadbeefdeadbeef;
   for(integer i=0;i<count;i++)begin
    raw16[16*i+:16]=16'(i*977-count*333);
    scalar(raw16[16*i+:16],exp_value);
    if(i<4)lo[32*i+:32]={16'd0,exp_value};else hi[32*(i-4)+:32]={16'd0,exp_value};
   end
   dst=alias_input?16:32;
   access(1,dst,128'hcafe,unused);access(1,dst+1'b1,128'hfeed,unused);access(1,16,raw16,unused);
   prior_reads=reads;prior_writes=writes;
   command(15,4'(count),32'h4e583136,1,!nostore,0,20'd16,0,4,0,0,got0);
   if(got0!==lo||reads-prior_reads!=1||writes-prior_writes!=(nostore?0:count>4?2:1))$fatal(1,"bridge count/low/traffic n=%0d",count);
   if(!nostore)begin
    access(0,dst,0,got0);access(0,dst+1'b1,0,got1);
    if(got0!==lo||got1!==(count>4?hi:128'hfeed))$fatal(1,"bridge S32 stored result n=%0d",count);
   end
   bridge_checks++;dst=32;
  end
 endtask
 integer bridge_checks=0;
 reg [522:0] evectors[0:4095];string vector_path;
 reg ev=0,estore=0,edirect=0,etake=0;reg [1:0] esources=0;reg [3:0] eop=0;
 reg [4:0] eshift=0;reg [29:0] esrc=0;reg [9:0] edst=80;
 wire eready,edone,eerror,esat;wire [127:0] edata;
 task automatic e_case(input integer index,input bit extra_sources);
  integer start,guard,pr,pw;reg [127:0] unused,readback,held_e;
  begin
   access(1,64,evectors[index][513:386],unused);access(1,65,evectors[index][385:258],unused);
   access(1,66,evectors[index][257:130],unused);
   @(negedge clk);ev=1;estore=1;edirect=0;etake=0;
   eop=evectors[index][517:514];eshift=evectors[index][522:518];esrc={10'd66,10'd65,10'd64};
   esources=extra_sources?3:((eop==3||eop==6)?3:((eop==7||eop==8||eop>=10)?1:2));
   guard=0;do begin @(posedge clk);guard++;if(guard>512)$fatal(1,"E U accept timeout");end while(!eready);
   start=ticks;@(negedge clk);ev=0;guard=0;
   do begin @(posedge clk);guard++;if(guard>2048)$fatal(1,"E U completion timeout");end while(!edone);
   if({eerror,esat,edata}!==evectors[index][129:0])$fatal(1,"full U E numerical idx=%0d",index);
   $display("E_U_MEASURE pipe=%0d index=%0d op=%0d extra=%0d sources=%0d cycles=%0d",PIPE,index,eop,extra_sources,esources,ticks-start);
   held_e=edata;repeat(3)begin @(negedge clk);if(!edone||edata!==held_e||eready)$fatal(1,"E U backpressure");end
   etake=1;@(posedge clk);@(negedge clk);etake=0;
   if(!eerror)begin access(0,80,0,readback);if(readback!==held_e)$fatal(1,"E U store ACK");end
  end
 endtask
'''

BRIDGE_TESTS=r'''
  if(BRIDGE!=0)begin
   for(integer n=1;n<=8;n++)begin bridge_case(n,0,0);bridge_case(n,1,0);if(n<=4)bridge_case(n,0,1);end
   // Descriptor rejection precedes every S access, including wrap and loss.
   for(integer bad=0;bad<5;bad++)begin
    dst=bad==0?1023:32;start_reads=reads;start_writes=writes;
    command(15,bad==2?0:bad==3?9:8,32'h4e583136,bad==4?2:1,bad!=1,0,20'd16,1,3,0,0,got);
    if(reads!=start_reads||writes!=start_writes)$fatal(1,"bridge invalid descriptor side effect");
   end
   dst=32;
   // An external held response must delay the second output ACK as well.
   access(1,16,0,ignored);
   fork
    begin
     command(15,8,32'h4e583136,1,1,0,20'd16,0,0,0,0,got);
     if(got!=={4{32'd32768}})$fatal(1,"bridge contention value");
    end
    begin
     do @(posedge clk);while(!(dut.request[0]&&dut.accept[0]&&dut.write[0]));
     @(negedge clk);io_v=1;io_w=0;io_addr=16;io_take=0;
     do @(posedge clk);while(!io_ready[0]);@(negedge clk);io_v=0;
     do @(negedge clk);while(!io_rsp[0]);
     wait(dut.n_service.second_write&&dut.request[0]&&dut.write[0]);
     repeat(6)begin @(negedge clk);if(done)$fatal(1,"bridge done before second ACK");end
     io_take=1;@(posedge clk);@(negedge clk);io_take=0;
    end
   join
   access(0,33,0,got);if(got!=={4{32'd32768}})$fatal(1,"bridge upper ACK readback");
   // Reset after a first write can leave a partial destination. No completion
   // may survive; the owner must reload/reissue the entire command.
   access(1,16,0,ignored);
   @(negedge clk);cv=1;cm={32'h4e583136,4'd8,4'd15};sources=1;src=16;cs=1;ct=0;
   do @(posedge clk);while(!cr);@(negedge clk);cv=0;
   wait(dut.n_service.second_write);@(negedge clk);reset=1;
   repeat(3)@(negedge clk);reset=0;repeat(35)@(negedge clk);if(done)$fatal(1,"bridge ghost completion");
   bridge_case(8,0,0);
   $display("BRIDGE_PASS checks=%0d invalid=5 contention=1 reset=1",bridge_checks);
  end
  for(integer n=1;n<=8;n++)begin
   access(1,16,0,ignored);
   if(BRIDGE!=0)command(15,4'(n),32'h4e583136,1,1,0,20'd16,0,0,1,0,got);
  end
  if(!$value$plusargs("VECTORS=%s",vector_path))$fatal(1,"E U missing vectors");
  $readmemh(vector_path,evectors);
  for(integer operation=0;operation<16;operation++)for(integer sample=0;sample<4;sample++)begin
   e_case(operation*256+sample*65,0);e_case(operation*256+sample*65,1);
  end
  $display("E_U_PASS checks=128");
'''

def prepare(repo,out):
    repo,out=Path(repo),Path(out);out.mkdir(parents=True,exist_ok=False)
    lock=json.loads((HERE/'baseline/source.json').read_bytes())
    for entry in lock['files'].values():
        if sha(HERE/'baseline'/entry['snapshot'])!=entry['sha256']:raise ValueError('baseline SHA changed')
    r4=repo/'project/experiments/rtl_iterations/round4'
    s=(r4/'r2_tb_nexp_u.sv').read_text(encoding='utf8')
    s=once(s,'module tb_nexp_u #(parameter integer DIRECT=1);','module tb_nexp_u #(parameter integer DIRECT=1, BRIDGE=0, PIPE=0);')
    s=once(s,'.NEXP_DIRECT(DIRECT)) dut(','.NEXP_DIRECT(DIRECT),.NEXP_DIRECT_LANES(4),.NEXP_S16(BRIDGE),.E_PIPELINE(PIPE)) dut(')
    s=once(s,' reg [127:0] got,ignored,expected,raw,before_stats,after_stats;',BRIDGE_TASK+'\n reg [127:0] got,ignored,expected,raw,before_stats,after_stats;')
    s=once(s,'reads-old_reads!=1||writes-old_writes!=1','reads-old_reads!=1||writes-old_writes!=((param==32\'h4e583136&&count>4)?2:1)')
    s=once(s,'$display("NEXP_FULL_U mode32=','$display("NEXP_FULL_U tag=%0d mode32=')
    s=once(s,'     mode32,count,finished-accepted,','     param,mode32,count,finished-accepted,')
    for old,new in [('.e_cmd_valid(1\'b0)','.e_cmd_valid(ev)'),('.e_cmd_store(1\'b0)','.e_cmd_store(estore)'),
        ('.e_cmd_direct_a(1\'b0)','.e_cmd_direct_a(edirect)'),('.e_done_ready(1\'b1)','.e_done_ready(etake)'),
        ('.e_cmd_ready()','.e_cmd_ready(eready)'),('.e_done_valid()','.e_done_valid(edone)'),('.e_done_error()','.e_done_error(eerror)'),
        ('.e_done_saturated()','.e_done_saturated(esat)'),('.e_cmd_sources(2\'d0)','.e_cmd_sources(esources)'),
        ('.e_cmd_op(4\'d0)','.e_cmd_op(eop)'),('.e_cmd_shift(5\'d0)','.e_cmd_shift(eshift)'),('.e_cmd_src(30\'d0)','.e_cmd_src(esrc)'),
        ('.e_cmd_dst(10\'d0)','.e_cmd_dst(edst)'),('.e_done_data()','.e_done_data(edata)')]:s=once(s,old,new)
    s=once(s,'  $display("NEXP_NATIVE_PATH',BRIDGE_TESTS+'\n  $display("NEXP_NATIVE_PATH')
    (out/'tb_u.sv').write_bytes(s.encode())
    baseline=s.replace(',.NEXP_S16(BRIDGE),.E_PIPELINE(PIPE)','')
    # Unreachable BRIDGE=0 code may still resolve hierarchical identifiers.
    baseline=baseline.replace('dut.n_service.second_write',"1'b0")
    (out/'tb_u_baseline.sv').write_bytes(baseline.encode())
    s=(r4/'r2_tb_nexp_compute.sv').read_text(encoding='utf8')
    s=once(s,'block_v2_n #(.NEXP_DIRECT(DIRECT)) only_native_N(', 'block_v2_n #(.NEXP_DIRECT(DIRECT),.NEXP_DIRECT_LANES(4)) only_native_N(')
    (out/'tb_compute.sv').write_bytes(s.encode())
    return dict(baseline=lock,vectors=vectors(out),generated_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()})
