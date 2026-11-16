`timescale 1ns/1ps
module tb_resident_probe;
 `include "p_resident_common.svh"
 logic e_cmd=0,e_take=0;
 logic[1:0] e_sources=0;
 logic[3:0] e_opcode=0;
 logic[4:0] e_shift=0;
 logic[29:0] e_src=0;
 logic[9:0] e_dst=0;
 wire e_ready,e_done,e_error,e_sat;
 wire[127:0] e_result;
 wire[3:0] u_req,u_wr,u_ready,u_rsp,u_take;
 wire[39:0] u_addr;
 wire[511:0] u_data,u_result;
 logic uh_req=0,uh_wr=0,uh_take=0;
 logic[9:0] uh_addr=0;
 logic[127:0] uh_data=0;
 assign u_req[0]=0;assign u_wr[0]=0;assign u_take[0]=0;
 assign u_addr[9:0]=0;assign u_data[127:0]=0;
 assign u_req[2]=uh_req;assign u_wr[2]=uh_wr;assign u_take[2]=uh_take;
 assign u_addr[29:20]=uh_addr;assign u_data[383:256]=uh_data;
 assign u_req[3]=0;assign u_wr[3]=0;assign u_take[3]=0;
 assign u_addr[39:30]=0;assign u_data[511:384]=0;
 wire um_req,um_wr,um_ready,um_valid,um_take;
 wire[9:0] um_addr;
 wire[127:0] um_data,um_result;
 block_local_s_arbiter #(.CLIENTS(4)) u_arbiter(
  .clk(clk),.reset(reset),.req_valid(u_req),.req_write(u_wr),.req_addr(u_addr),.req_data(u_data),
  .req_ready(u_ready),.rsp_valid(u_rsp),.rsp_ready(u_take),.rsp_data(u_result),
  .mem_req(um_req),.mem_write(um_wr),.mem_addr(um_addr),.mem_data(um_data),
  .mem_ready(um_ready),.mem_valid(um_valid),.mem_result(um_result),.mem_take(um_take),.busy());
 local_s_base u_store(.clk(clk),.reset(reset),.req_valid(um_req),.req_write(um_wr),
  .req_addr(um_addr),.req_data(um_data),.req_ready(um_ready),.rsp_valid(um_valid),
  .rsp_ready(um_take),.rsp_data(um_result));
 defparam u_store.storage.banks[0].memory.VERBOSE=0;
 defparam u_store.storage.banks[1].memory.VERBOSE=0;
 defparam u_store.storage.banks[2].memory.VERBOSE=0;
 defparam u_store.storage.banks[3].memory.VERBOSE=0;
 wire ev,er,ov,ot,oe,os;
 wire[3:0] eo;wire[4:0] es;
 wire[127:0] ed,od;
 pu_compact_e_service e_service(
  .clk(clk),.reset(reset),.cmd_valid(e_cmd),.cmd_store(1'b1),.cmd_direct_a(1'b0),
  .cmd_sources(e_sources),.cmd_ready(e_ready),.cmd_op(e_opcode),.cmd_shift(e_shift),
  .cmd_src(e_src),.cmd_dst(e_dst),.done_valid(e_done),.done_ready(e_take),
  .done_error(e_error),.done_saturated(e_sat),.done_data(e_result),
  .s_req_valid(u_req[1]),.s_req_write(u_wr[1]),.s_req_ready(u_ready[1]),
  .s_req_addr(u_addr[19:10]),.s_req_data(u_data[255:128]),.s_rsp_valid(u_rsp[1]),
  .s_rsp_ready(u_take[1]),.s_rsp_data(u_result[255:128]),
  .direct_a_valid(1'b0),.direct_a_abort(1'b0),.direct_a_ready(),.direct_a_data(128'b0),
  .e_in_valid(ev),.e_in_ready(er),.e_in_op(eo),.e_in_shift(es),.e_in_data(ed),
  .e_out_valid(ov),.e_out_ready(ot),.e_out_data(od),.e_out_error(oe),.e_out_saturated(os));
 block_v2_e_compact e_leaf(.clk(clk),.reset(reset),.in_valid(ev),.in_ready(er),
  .in_op(eo),.in_shift(es),.in_data(ed),.out_valid(ov),.out_ready(ot),
  .out_data(od),.out_error(oe),.out_saturated(os));
 integer e_acks=0,loads=0,stores=0,native_m=0,native_e=0,case_id,begin_cycle,case_count=0;
 // Passive acceptance-to-first-completion, excluding deliberate response
 // holding and observer reads. Never drive DUT signals from these monitors.
 integer rp_count[0:511],rp_min[0:511],rp_max[0:511],rp_start=-1,rp_key;
 integer re_count[0:2047],re_min[0:2047],re_max[0:2047],re_start=-1,re_key;
 integer rf_count[0:1],rf_min[0:1],rf_max[0:1],rf_start=-1,rf_key,r_elapsed,r_cycle=0;
 always @(posedge clk)begin
  // Keep this counter in the monitor's own process. Reading the original
  // bench's blocking counter here races its separate posedge process.
  r_cycle=r_cycle+1;
  if(reset)begin rp_start=-1;re_start=-1;rf_start=-1;end
  else begin
   if(cmd_valid && cmd_ready)begin
    if(rp_start>=0)$fatal(1,"overlapping resident P profile");
    rp_start=r_cycle;
    if(cmd_op==4)rp_key=0;
    else if(cmd_op==10)rp_key=1+int'(cmd_data[7:4]);
    else if(cmd_op==5)rp_key=16+64*int'(cmd_data[9:8])+int'(cmd_data[5:0]);
    else $fatal(1,"unexpected resident P profile command");
   end
   if(rp_start>=0 && cmd_done)begin
    r_elapsed=r_cycle-rp_start;rp_count[rp_key]=rp_count[rp_key]+1;
    if(r_elapsed<rp_min[rp_key])rp_min[rp_key]=r_elapsed;
    if(r_elapsed>rp_max[rp_key])rp_max[rp_key]=r_elapsed;rp_start=-1;
   end
   if(e_cmd && e_ready)begin
    if(re_start>=0)$fatal(1,"overlapping resident E profile");
    re_start=r_cycle;re_key=int'(e_opcode)+16*int'(e_sources)+64*int'(e_shift);
   end
   if(re_start>=0 && e_done)begin
    r_elapsed=r_cycle-re_start;re_count[re_key]=re_count[re_key]+1;
    if(r_elapsed<re_min[re_key])re_min[re_key]=r_elapsed;
    if(r_elapsed>re_max[re_key])re_max[re_key]=r_elapsed;re_start=-1;
   end
   if(load_valid && load_ready)begin
    if(rf_start>=0)$fatal(1,"overlapping resident feeder profile");
    rf_start=r_cycle;rf_key=int'(reuse_b);
   end
   if(rf_start>=0 && load_done)begin
    r_elapsed=r_cycle-rf_start;rf_count[rf_key]=rf_count[rf_key]+1;
    if(r_elapsed<rf_min[rf_key])rf_min[rf_key]=r_elapsed;
    if(r_elapsed>rf_max[rf_key])rf_max[rf_key]=r_elapsed;rf_start=-1;
   end
  end
 end
 reg e_write_pending=0;
 always @(posedge clk)begin
  if(reset)e_write_pending<=0;
  else begin
   if(u_req[1] && u_ready[1] && u_wr[1])e_write_pending<=1;
   if(u_rsp[1] && u_take[1] && e_write_pending)begin e_acks=e_acks+1;e_write_pending<=0;end
  end
 end
 logic[127:0] fixture[0:VECTOR_WORDS-1],external_memory[0:EXTERNAL_WORDS-1];
 for(genvar bank=0;bank<4;bank=bank+1)begin: controlled_sram_initial_state
  initial begin
   integer pattern;logic[127:0] seed;
   if($value$plusargs("sinit=%d",pattern))begin
    if(pattern<0 || pattern>2)$fatal(1,"invalid SRAM initial state");
    for(integer wi=0;wi<256;wi=wi+1)begin
     seed=pattern==0?128'd0:pattern==1?{128{1'b1}}:
      {32'h9e3779b9^32'(wi),32'h85ebca6b^32'(bank),32'hc2b2ae35^32'(wi*17+bank),32'h27d4eb2f^32'(wi*97+bank)};
     dut.store.storage.banks[bank].memory.mem[wi]=seed;
     u_store.storage.banks[bank].memory.mem[wi]=~seed;
    end
   end
  end
 end
 task automatic u_access(input bit wr,input integer address,input logic[127:0] value,output logic[127:0] result);
  logic[127:0] held;
  @(negedge clk);uh_req=1;uh_wr=wr;uh_addr=10'(address);uh_data=value;
  do @(posedge clk);while(!u_ready[2]);
  @(negedge clk);uh_req=0;
  do @(posedge clk);while(!u_rsp[2]);
  held=u_result[383:256];
  repeat(2)begin @(negedge clk);if(!u_rsp[2] || u_result[383:256]!==held)$fatal(1,"U response lost");end
  result=held;uh_take=1;@(posedge clk);@(negedge clk);uh_take=0;
 endtask
 task automatic begin_case(input integer id);
  @(negedge clk);reset=1;repeat(4)@(negedge clk);reset=0;repeat(4)@(negedge clk);
  for(integer i=0;i<EXTERNAL_WORDS;i=i+1)external_memory[i]='x;
  case_id=id;loads=0;stores=0;native_m=0;native_e=0;begin_cycle=cycle;
 endtask
 // Transport only: no sign extraction, packing or arithmetic in the host.
 task automatic load_word(input integer actor,input integer address,input integer ext);
  logic[127:0] got;
  if(actor==0)access(1,address,external_memory[ext],got);
  else u_access(1,address,external_memory[ext],got);
  loads=loads+1;
 endtask
 task automatic store_word(input integer actor,input integer address,input integer ext,input integer expected);
  logic[127:0] got;
  if(actor==0)access(0,address,0,got);else u_access(0,address,0,got);
  if(got!==fixture[expected])$fatal(1,"resident STORE mismatch case=%0d",case_id);
  external_memory[ext]=got;stores=stores+1;
 endtask
 task automatic m_term(input integer abase,input integer bbase,input bit reuse_weight,
                       input integer k,input integer coefficient,input integer shift,input bit clear);
  logic[127:0] got;
  load_a_address=10'(abase);load_b_address=10'(bbase);
  feed(reuse_weight);
  command(4,0,64'(coefficient&65535) | (64'(shift)<<16),0,0,got);
  command(10,0,64'h9103 | (64'(k)<<4) | (clear?64'd4:64'd0),0,0,got);
 endtask
 task automatic m_final(input integer dst,input integer width,input integer shift,input integer expected);
  logic[127:0] got,stored;
  command(5,0,(width==16?64'h100:64'h200) | 64'(shift),1,dst,got);
  if(got!==fixture[expected])$fatal(1,"resident M result mismatch case=%0d dst=%0d got=%h expected=%h",case_id,dst,got,fixture[expected]);
  access(0,dst,0,stored);
  if(stored!==fixture[expected])$fatal(1,"resident M SRAM mismatch case=%0d",case_id);
  native_m=native_m+1;
 endtask
 task automatic e_command(input integer count,input integer a,input integer b,input integer c,
                          input integer dst,input integer opcode,input integer shift,input integer expected);
  integer initial_acks;logic[127:0] held,stored;
  initial_acks=e_acks;
  @(negedge clk);e_cmd=1;e_sources=2'(count);e_src={10'(c),10'(b),10'(a)};
  e_dst=10'(dst);e_opcode=4'(opcode);e_shift=5'(shift);
  do @(posedge clk);while(!e_ready);
  @(negedge clk);e_cmd=0;
  do @(posedge clk);while(!e_done);
  if(e_error || e_sat || e_acks!=initial_acks+1)$fatal(1,"resident E missing write ACK case=%0d",case_id);
  held=e_result;
  repeat(3)begin @(negedge clk);if(!e_done || e_ready || e_result!==held)$fatal(1,"resident E completion lost");end
  e_take=1;@(posedge clk);@(negedge clk);e_take=0;
  if(held!==fixture[expected])$fatal(1,"resident E result mismatch case=%0d dst=%0d got=%h expected=%h",case_id,dst,held,fixture[expected]);
  u_access(0,dst,0,stored);
  if(stored!==fixture[expected])$fatal(1,"resident E SRAM mismatch case=%0d",case_id);
  native_e=native_e+1;
 endtask
 task automatic end_case(input integer expected_loads,input integer expected_stores,input integer ms,input integer es);
  if(loads!=expected_loads || stores!=expected_stores || native_m!=ms || native_e!=es)
   $fatal(1,"resident event counts differ case=%0d",case_id);
  $display("RESIDENT_CASE {\"id\":%0d,\"loads\":%0d,\"stores\":%0d,\"m\":%0d,\"e\":%0d,\"cycles\":%0d}",case_id,loads,stores,native_m,native_e,cycle-begin_cycle);
  case_count=case_count+1;
 endtask
 initial begin
  for(integer key=0;key<512;key=key+1)begin rp_count[key]=0;rp_min[key]=2147483647;rp_max[key]=0;end
  for(integer key=0;key<2048;key=key+1)begin re_count[key]=0;re_min[key]=2147483647;re_max[key]=0;end
  for(integer key=0;key<2;key=key+1)begin rf_count[key]=0;rf_min[key]=2147483647;rf_max[key]=0;end
  for(integer r=1;r<=8;r=r+1)begin
   for(integer key=0;key<32;key=key+1)begin p_count[r][key]=0;p_min[r][key]=2147483647;p_max[r][key]=0;end
   for(integer key=0;key<16;key=key+1)begin m_count[r][key]=0;m_min[r][key]=2147483647;m_max[r][key]=0;end
   for(integer key=0;key<2;key=key+1)begin f_count[r][key]=0;f_min[r][key]=2147483647;f_max[r][key]=0;end
  end
  $readmemh("vectors.hex",fixture);
  `include "cases.svh"
  if(case_count!=CASE_COUNT)$fatal(1,"resident case count differs");
  if(rp_start>=0 || re_start>=0 || rf_start>=0)$fatal(1,"unfinished resident profile");
  for(integer key=0;key<512;key=key+1)if(rp_count[key]>0)
   $display("RESIDENT_PROFILE {\"boundary\":\"P\",\"key\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",key,rp_count[key],rp_min[key],rp_max[key]);
  for(integer key=0;key<2048;key=key+1)if(re_count[key]>0)
   $display("RESIDENT_PROFILE {\"boundary\":\"E\",\"key\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",key,re_count[key],re_min[key],re_max[key]);
  for(integer key=0;key<2;key=key+1)if(rf_count[key]>0)
   $display("RESIDENT_PROFILE {\"boundary\":\"feeder\",\"key\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",key,rf_count[key],rf_min[key],rf_max[key]);
  $display("PASS native resident record programs");$finish;
 end
endmodule
