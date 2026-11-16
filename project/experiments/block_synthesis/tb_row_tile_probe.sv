`timescale 1ns/1ps
module tb_row_tile_probe;
 `include "vectors_size.svh"
 logic clk=0,reset=1;
 always #5 clk=~clk;
 integer cycle=0,a_fires=0,b_fires=0,wide_reads=0,store_acks=0;
 // Passive acceptance-to-first-completion profiles. Deliberate completion
 // backpressure in the tasks below is excluded. Never drive DUT signals here.
 integer p_count[1:8][0:31],p_min[1:8][0:31],p_max[1:8][0:31];
 integer m_count[1:8][0:15],m_min[1:8][0:15],m_max[1:8][0:15];
 integer f_count[1:8][0:1],f_min[1:8][0:1],f_max[1:8][0:1];
 integer p_start=-1,p_rows,p_key,m_start=-1,m_rows,m_key;
 integer f_start=-1,f_rows,f_key,elapsed;
 always @(posedge clk) begin
  cycle=cycle+1;
  if(reset)begin p_start=-1;m_start=-1;f_start=-1;end
  else begin
   if(cmd_valid && cmd_ready)begin
    if(p_start>=0)$fatal(1,"overlapping P command profile");
    p_start=cycle;p_rows=int'(rows);p_key=int'(cmd_op)+16*int'(cmd_store);
   end
   if(p_start>=0 && cmd_done)begin
    elapsed=cycle-p_start;
    p_count[p_rows][p_key]=p_count[p_rows][p_key]+1;
    if(elapsed<p_min[p_rows][p_key])p_min[p_rows][p_key]=elapsed;
    if(elapsed>p_max[p_rows][p_key])p_max[p_rows][p_key]=elapsed;
    p_start=-1;
   end
   if(dut.m_dispatch && dut.m_ready)begin
    if(m_start>=0)$fatal(1,"overlapping native M profile");
    m_start=cycle;m_rows=int'(rows);m_key=int'(dut.m_op);
   end
   if(m_start>=0 && dut.m_valid && dut.m_pending && !dut.m_dispatch && !dut.m_commit)begin
    elapsed=cycle-m_start;
    m_count[m_rows][m_key]=m_count[m_rows][m_key]+1;
    if(elapsed<m_min[m_rows][m_key])m_min[m_rows][m_key]=elapsed;
    if(elapsed>m_max[m_rows][m_key])m_max[m_rows][m_key]=elapsed;
    m_start=-1;
   end
   if(load_valid && load_ready)begin
    if(f_start>=0)$fatal(1,"overlapping feeder profile");
    f_start=cycle;f_rows=int'(rows);f_key=int'(reuse_b);
   end
   if(f_start>=0 && load_done)begin
    elapsed=cycle-f_start;
    f_count[f_rows][f_key]=f_count[f_rows][f_key]+1;
    if(elapsed<f_min[f_rows][f_key])f_min[f_rows][f_key]=elapsed;
    if(elapsed>f_max[f_rows][f_key])f_max[f_rows][f_key]=elapsed;
    f_start=-1;
   end
   if(dut.a_valid && dut.a_ready)a_fires=a_fires+1;
   if(dut.b_valid && dut.b_ready)b_fires=b_fires+1;
   if(dut.store.wide_req && dut.store.wide_ready)wide_reads=wide_reads+1;
   if(dut.local_rsp[1] && dut.local_take[1])store_acks=store_acks+1;
  end
 end
 initial begin
  repeat(100000000)@(posedge clk);
  $fatal(1,"row tile handshake watchdog");
 end
 logic [1:0] io_req_valid=0,io_req_write=0,io_rsp_ready=0;
 logic [19:0] io_req_addr=0;
 logic [255:0] io_req_data=0;
 wire [1:0] io_req_ready,io_rsp_valid;
 wire [255:0] io_rsp_data;
 logic load_valid=0,load_take=0,reuse_b=0;
 logic [3:0] rows=1;
 wire load_ready,load_done,load_error;
 logic cmd_valid=0,cmd_store=0,cmd_take=0;
 logic [3:0] cmd_op=0;
 logic [5:0] cmd_index=0;
 logic [63:0] cmd_data=0;
 logic [9:0] cmd_dst=0;
 wire cmd_ready,cmd_done,cmd_error,cmd_saturated;
 wire [127:0] cmd_result;
 pu_p_group dut(
  .clk(clk),.reset(reset),.io_req_valid(io_req_valid),.io_req_write(io_req_write),
  .io_req_addr(io_req_addr),.io_req_data(io_req_data),.io_req_ready(io_req_ready),
  .io_rsp_valid(io_rsp_valid),.io_rsp_ready(io_rsp_ready),.io_rsp_data(io_rsp_data),
  .load_valid(load_valid),.load_ready(load_ready),.load_bank(1'b0),.load_rows(rows),.load_tiles(3'd1),
  .load_a_wide(1'b1),.load_b_wide(1'b1),.load_reuse_b(reuse_b),.load_a_base(10'd0),.load_b_base(10'd16),
  .load_done(load_done),.load_take(load_take),.load_error(load_error),
  .cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_op(cmd_op),.cmd_index(cmd_index),.cmd_data(cmd_data),
  .cmd_store(cmd_store),.cmd_route(1'b0),.cmd_pack16(1'b0),.cmd_dst(cmd_dst),
  .cmd_done(cmd_done),.cmd_take(cmd_take),.cmd_error(cmd_error),.cmd_saturated(cmd_saturated),.cmd_result(cmd_result),
  .gate_valid(1'b0),.gate_route(1'b0),.gate_ready(),.gate_a(10'b0),.gate_b(10'b0),.gate_dst(10'b0),
  .gate_done(),.gate_take(1'b1),.gate_error(),.gate_saturated(),
  .m_to_g_valid(),.m_to_g_data(),.m_to_g_take(1'b0),
  .g_from_m_valid(1'b0),.g_from_m_data(32'b0),.g_from_m_take());
 defparam dut.store.storage.banks[0].memory.VERBOSE=0;
 defparam dut.store.storage.banks[1].memory.VERBOSE=0;
 defparam dut.store.storage.banks[2].memory.VERBOSE=0;
 defparam dut.store.storage.banks[3].memory.VERBOSE=0;

 task automatic access(input bit wr,input integer addr,input logic[127:0] value,output logic[127:0] result);
  logic[127:0] held;
  @(negedge clk);io_req_valid=1;io_req_write={1'b0,wr};io_req_addr={10'b0,10'(addr)};io_req_data={128'b0,value};
  do @(posedge clk);while(!io_req_ready[0]);
  @(negedge clk);io_req_valid=0;
  do @(posedge clk);while(!io_rsp_valid[0]);
  held=io_rsp_data[127:0];
  repeat(2)begin
   @(negedge clk);
   if(!io_rsp_valid[0] || io_rsp_data[127:0]!==held)$fatal(1,"host response did not hold");
  end
  result=held;io_rsp_ready=1;
  @(posedge clk);@(negedge clk);io_rsp_ready=0;
 endtask
 task automatic feed(input bit reuse_weight);
  @(negedge clk);load_valid=1;reuse_b=reuse_weight;
  do @(posedge clk);while(!load_ready);
  @(negedge clk);load_valid=0;
  do @(posedge clk);while(!load_done);
  repeat(2)begin
   @(negedge clk);
   if(!load_done || load_error || load_ready)$fatal(1,"feeder completion did not hold");
  end
  load_take=1;@(posedge clk);@(negedge clk);load_take=0;
 endtask
 task automatic command(input integer op,input integer index,input logic[63:0] data,
                        input bit store,input integer destination,output logic[127:0] result);
  integer initial_acks;
  logic[127:0] held;
  logic held_sat;
  initial_acks=store_acks;
  @(negedge clk);cmd_valid=1;cmd_op=4'(op);cmd_index=6'(index);cmd_data=data;cmd_store=store;cmd_dst=10'(destination);
  do @(posedge clk);while(!cmd_ready);
  @(negedge clk);cmd_valid=0;
  do @(posedge clk);while(!cmd_done);
  if(cmd_error)$fatal(1,"native M command error op=%0d index=%0d data=%h",op,index,data);
  if(store_acks!=initial_acks+int'(store))$fatal(1,"command completed without matching S write ACK");
  held=cmd_result;held_sat=cmd_saturated;
  repeat(3)begin
   @(negedge clk);
   if(!cmd_done || cmd_ready || cmd_error || cmd_result!==held || cmd_saturated!==held_sat)
    $fatal(1,"M completion did not hold under backpressure");
  end
  result=held;cmd_take=1;@(posedge clk);@(negedge clk);cmd_take=0;
 endtask
 logic[63:0] inputs_mem[0:VECTOR_WORDS-1];
 task automatic run_case(input integer id,input integer nrows,input integer kval,
                         input integer abase,input integer bbase,input integer goldbase,input integer finalbase);
  integer begin_cycle,begin_a,begin_b,begin_wide,begin_ack;
  integer kk,rr,part,shift;
  logic[127:0] got,result,payload,expected;
  logic[31:0] avalue;
  logic[15:0] component;
  begin
   @(negedge clk);reset=1;
   repeat(4)@(negedge clk);
   reset=0;rows=4'(nrows);
   repeat(4)@(negedge clk);
   // Initialize only the finite staging/output windows, including feeder padding.
   for(rr=0;rr<80;rr=rr+1)access(1,rr,128'b0,got);
   begin_cycle=cycle;begin_a=a_fires;begin_b=b_fires;begin_wide=wide_reads;begin_ack=store_acks;
   for(kk=0;kk<kval;kk=kk+1)begin
    payload=0;payload[15:0]=inputs_mem[bbase+kk][15:0];
    access(1,16,payload,got); // One B record, shared by all rows and three A components.
    for(part=0;part<3;part=part+1)begin
     for(rr=0;rr<nrows;rr=rr+1)begin
      avalue=inputs_mem[abase+rr*kval+kk][31:0];
      case(part)0:component=avalue[15:0];1:component=avalue[31:16];default:component={15'b0,avalue[15]};endcase
      payload=0;payload[15:0]=component;access(1,rr,payload,got);
     end
     feed(part!=0);
     command(4,0,64'd1 | (part==0 ? 64'd0 : 64'd16<<16),0,0,result);
     command(10,0,(64'(nrows)<<15) | 64'h1113 | ((kk==0 && part==0)?64'd4:64'd0),0,0,result);
    end
   end
   for(rr=0;rr<nrows;rr=rr+1)begin
    command(3,rr<<3,0,1,32+rr,result);
    expected={64'b0,inputs_mem[goldbase+rr]};
    if(result!==expected)$fatal(1,"raw S64 mismatch id=%0d row=%0d got=%h expected=%h",id,rr,result,expected);
    access(0,32+rr,0,got);
    if(got!==expected)$fatal(1,"raw S64 SRAM store mismatch");
    for(part=0;part<4;part=part+1)begin
     shift=part*8;
     command(5,rr<<3,64'h200 | 64'(shift),1,64+rr,result);
     expected={96'b0,inputs_mem[finalbase+rr*4+part][31:0]};
     if(result!==expected)$fatal(1,"final RNE mismatch id=%0d row=%0d shift=%0d got=%h expected=%h",id,rr,shift,result,expected);
     access(0,64+rr,0,got);
     if(got!==expected)$fatal(1,"final SRAM store mismatch");
    end
   end
   $display("ROW_TILE {\"id\":%0d,\"rows\":%0d,\"k\":%0d,\"cycles\":%0d,\"a_fires\":%0d,\"b_fires\":%0d,\"wide_reads\":%0d,\"store_acks\":%0d,\"a_stage_words\":%0d,\"b_stage_words\":%0d}",
    id,nrows,kval,cycle-begin_cycle,a_fires-begin_a,b_fires-begin_b,wide_reads-begin_wide,store_acks-begin_ack,3*nrows*kval,kval);
  end
 endtask
 initial begin
  for(integer r=1;r<=8;r=r+1)begin
   for(integer key=0;key<32;key=key+1)begin
    p_count[r][key]=0;p_min[r][key]=2147483647;p_max[r][key]=0;
   end
   for(integer key=0;key<16;key=key+1)begin
    m_count[r][key]=0;m_min[r][key]=2147483647;m_max[r][key]=0;
   end
   for(integer key=0;key<2;key=key+1)begin
    f_count[r][key]=0;f_min[r][key]=2147483647;f_max[r][key]=0;
   end
  end
  $readmemh("vectors.hex",inputs_mem);
  `include "cases.svh"
  if(p_start>=0 || m_start>=0 || f_start>=0)$fatal(1,"unfinished passive profile");
  for(integer r=1;r<=8;r=r+1)begin
   for(integer key=0;key<32;key=key+1)if(p_count[r][key]>0)
    $display("ROW_PROFILE {\"boundary\":\"p-command\",\"rows\":%0d,\"op\":%0d,\"store\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",r,key%16,key/16,p_count[r][key],p_min[r][key],p_max[r][key]);
   for(integer key=0;key<16;key=key+1)if(m_count[r][key]>0)
    $display("ROW_PROFILE {\"boundary\":\"native-m\",\"rows\":%0d,\"op\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",r,key,m_count[r][key],m_min[r][key],m_max[r][key]);
   for(integer key=0;key<2;key=key+1)if(f_count[r][key]>0)
    $display("ROW_PROFILE {\"boundary\":\"feeder\",\"rows\":%0d,\"reuse_b\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",r,key,f_count[r][key],f_min[r][key],f_max[r][key]);
  end
  $display("PASS native row tile probe");
  $finish;
 end
endmodule
