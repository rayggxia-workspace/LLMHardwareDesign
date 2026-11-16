`timescale 1ns/1ps
module tb_column_tile_probe;
 // Generated from the frozen row probe's P/S interfaces and handshake tasks.
 `include "p_probe_common.svh"
 // Same E service -> compact E and S/arbiter connections as U. Host copies
 // complete 128-bit words between the two private stores; it never unpacks.
 logic e_cmd=0,e_take=0;
 wire e_ready,e_done,e_error,e_sat;
 wire [127:0] e_result;
 wire [3:0] u_req,u_wr,u_ready,u_rsp,u_take;
 wire [39:0] u_addr;
 wire [511:0] u_data,u_result;
 logic uh_req=0,uh_wr=0,uh_take=0;
 logic [9:0] uh_addr=0;
 logic [127:0] uh_data=0;
 assign u_req[0]=0;assign u_wr[0]=0;assign u_take[0]=0;
 assign u_addr[9:0]=0;assign u_data[127:0]=0;
 assign u_req[2]=uh_req;assign u_wr[2]=uh_wr;assign u_take[2]=uh_take;
 assign u_addr[29:20]=uh_addr;assign u_data[383:256]=uh_data;
 assign u_req[3]=0;assign u_wr[3]=0;assign u_take[3]=0;
 assign u_addr[39:30]=0;assign u_data[511:384]=0;
 wire um_req,um_wr,um_ready,um_valid,um_take;
 wire [9:0] um_addr;
 wire [127:0] um_data,um_result;
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
 wire [3:0] eo;wire [4:0] es;
 wire [127:0] ed,od;
 pu_compact_e_service e_service(
  .clk(clk),.reset(reset),.cmd_valid(e_cmd),.cmd_store(1'b1),.cmd_direct_a(1'b0),
  .cmd_sources(2'd1),.cmd_ready(e_ready),.cmd_op(4'd8),.cmd_shift(5'd15),
  .cmd_src(30'd0),.cmd_dst(10'd1),.done_valid(e_done),.done_ready(e_take),
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
 integer e_acks=0,e_commands=0;
 integer e_start=-1,e_count=0,e_min=2147483647,e_max=0,e_elapsed;
 always @(posedge clk)begin
  if(reset)e_start=-1;
  else begin
   if(e_cmd && e_ready)begin
    if(e_start>=0)$fatal(1,"overlapping E service profile");
    e_start=cycle;
   end
   if(e_start>=0 && e_done)begin
    e_elapsed=cycle-e_start;e_count=e_count+1;
    if(e_elapsed<e_min)e_min=e_elapsed;
    if(e_elapsed>e_max)e_max=e_elapsed;
    e_start=-1;
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
 task automatic u_access(input bit wr,input logic[127:0] value,output logic[127:0] result);
  logic[127:0] held;
  @(negedge clk);uh_req=1;uh_wr=wr;uh_addr=wr?10'd0:10'd1;uh_data=value;
  do @(posedge clk);while(!u_ready[2]);
  @(negedge clk);uh_req=0;
  do @(posedge clk);while(!u_rsp[2]);
  held=u_result[383:256];
  repeat(2)begin @(negedge clk);if(!u_rsp[2] || u_result[383:256]!==held)$fatal(1,"U host response lost");end
  result=held;uh_take=1;@(posedge clk);@(negedge clk);uh_take=0;
 endtask
 task automatic flags;
  integer initial_acks;
  logic[127:0] held;
  initial_acks=e_acks;
  @(negedge clk);e_cmd=1;
  do @(posedge clk);while(!e_ready);
  @(negedge clk);e_cmd=0;
  do @(posedge clk);while(!e_done);
  if(e_error || e_sat || e_acks!=initial_acks+1)$fatal(1,"E flags missing actual write ACK");
  held=e_result;
  repeat(3)begin @(negedge clk);if(!e_done || e_ready || e_result!==held)$fatal(1,"E completion lost");end
  e_take=1;@(posedge clk);@(negedge clk);e_take=0;e_commands=e_commands+1;
 endtask
 logic[63:0] inputs_mem[0:VECTOR_WORDS-1];
 // Explicit external full-word objects for the optional three-phase order.
 // The host transports words; E/M still perform every sign/scatter operation.
 logic[127:0] external_packed[0:127],external_flags[0:127];
 for(genvar bank=0;bank<4;bank=bank+1)begin: controlled_sram_initial_state
  initial begin
   integer pattern;logic[127:0] seed;
   if($value$plusargs("sinit=%d",pattern))begin
    if(pattern<0 || pattern>2)$fatal(1,"invalid SRAM initial state");
    for(integer word_index=0;word_index<256;word_index=word_index+1)begin
     seed=pattern==0?128'd0:pattern==1?{128{1'b1}}:
       {32'h9e3779b9 ^ 32'(word_index),32'h85ebca6b ^ 32'(bank),
        32'hc2b2ae35 ^ 32'(word_index*17+bank),32'h27d4eb2f ^ 32'(word_index*97+bank)};
     dut.store.storage.banks[bank].memory.mem[word_index]=seed;
     u_store.storage.banks[bank].memory.mem[word_index]=~seed;
    end
   end
  end
 end
 task automatic run_matrix(input integer id,input integer nrows,input integer ncols,input integer kval,
   input integer abase,input integer bbase,input integer goldbase,input integer finalbase);
  integer begin_cycle,begin_a,begin_b,begin_wide,begin_ack,begin_eack,begin_ecmd;
  integer kk,rr,cc,part,half,lane,addr,shift,slot;
  logic[127:0] got,result,payload,expected,packed_value,flag_value;
  logic[31:0] avalue;logic[15:0] component;
  begin
   @(negedge clk);reset=1;repeat(4)@(negedge clk);reset=0;rows=4'(nrows);
   repeat(4)@(negedge clk);
   // Only the finite unused A/B feeder padding is initialized. Every result
   // is written before reading; no SRAM or M data reset value is assumed.
   for(rr=0;rr<8;rr=rr+1)begin access(1,rr,0,got);access(1,16+rr,0,got);end
   begin_cycle=cycle;begin_a=a_fires;begin_b=b_fires;begin_wide=wide_reads;begin_ack=store_acks;
   begin_eack=e_acks;begin_ecmd=e_commands;
   for(kk=0;kk<kval;kk=kk+1)begin
    // Native B is column-major: B[n*8+k], not B[k*8+n].
    // Ksegment1 therefore uses one full scalar record per output column.
    for(cc=0;cc<ncols;cc=cc+1)begin
     payload=0;payload[15:0]=inputs_mem[bbase+kk*ncols+cc][15:0];
     access(1,16+cc,payload,got);
    end
    for(part=0;part<3;part=part+1)begin
     for(rr=0;rr<nrows;rr=rr+1)begin
      avalue=inputs_mem[abase+rr*kval+kk][31:0];
      case(part)0:component=avalue[15:0];1:component=avalue[31:16];default:component={15'b0,avalue[15]};endcase
      payload=0;payload[15:0]=component;access(1,rr,payload,got);
     end
     feed(part!=0);
     command(4,0,64'd1 | (part==0?64'd0:64'd16<<16),0,0,result);
     command(10,0,(64'(nrows)<<15) | (64'(ncols)<<8) | 64'h1013 |
       ((kk==0 && part==0)?64'd4:64'd0),0,0,result);
    end
   end
   // Save/check every original accumulator and all rounded output vectors
   // before reusing M for scatter. The original full-K context ends here.
   for(rr=0;rr<nrows;rr=rr+1)begin
    for(half=0;half<(ncols+1)/2;half=half+1)begin
     command(3,(rr<<3)|half,0,1,32+4*rr+half,result);expected=0;
     for(lane=0;lane<2;lane=lane+1)if(2*half+lane<ncols)
      expected[lane*64+:64]=inputs_mem[goldbase+rr*ncols+2*half+lane];
     if(result!==expected)$fatal(1,"column raw S64 mismatch id=%0d row=%0d pair=%0d",id,rr,half);
     access(0,32+4*rr+half,0,got);if(got!==expected)$fatal(1,"column raw SRAM mismatch");
    end
    for(part=0;part<4;part=part+1)for(half=0;half<(ncols+3)/4;half=half+1)begin
     slot=96+part*16+rr*2+half;
     command(5,(rr<<3)|half,64'h200 | 64'(part*8),1,slot,result);expected=0;
     for(lane=0;lane<4;lane=lane+1)if(4*half+lane<ncols)
      expected[lane*32+:32]=inputs_mem[finalbase+(rr*ncols+4*half+lane)*4+part][31:0];
     if(result!==expected)$fatal(1,"column final packed mismatch id=%0d row=%0d half=%0d shift=%0d got=%h expected=%h",id,rr,half,part*8,result,expected);
     access(0,slot,0,got);if(got!==expected)$fatal(1,"column final packed SRAM mismatch");
     if($test$plusargs("materialized"))external_packed[slot-96]=got;
    end
   end
   rows=1;
   if($test$plusargs("materialized"))begin
    // All packed writes/reads have completed before the E lease starts.
    // Destroy the old local copies to catch accidental dependence on them.
    for(part=0;part<4;part=part+1)for(rr=0;rr<nrows;rr=rr+1)
     for(half=0;half<(ncols+3)/4;half=half+1)begin
      slot=part*16+rr*2+half;access(1,96+slot,128'hdeadbeef,got);
      u_access(1,external_packed[slot],got);flags();u_access(0,0,flag_value);
      external_flags[slot]=flag_value;
     end
    // Actual extra sixteen LOAD/ACKs, not an assumed reset/zero SRAM value.
    for(rr=0;rr<8;rr=rr+1)begin access(1,rr,0,got);access(1,16+rr,0,got);end
    $display("MATERIALIZED_PHASE id=%0d packed=%0d flags=%0d refill=16",id,
       4*nrows*((ncols+3)/4),4*nrows*((ncols+3)/4));
   end
   for(part=0;part<4;part=part+1)for(rr=0;rr<nrows;rr=rr+1)begin
    for(half=0;half<(ncols+3)/4;half=half+1)begin
     slot=part*16+rr*2+half;
     if($test$plusargs("materialized"))begin
      packed_value=external_packed[slot];flag_value=external_flags[slot];
     end else begin
      access(0,96+slot,0,packed_value);
      u_access(1,packed_value,got);flags();u_access(0,0,flag_value);
     end
     // Complete word transport only: testbench does not split or shift data.
     access(1,192+slot,flag_value,got);
     for(cc=4*half;cc<ncols && cc<4*half+4;cc=cc+1)begin
      // Reconstruct x from signed S16 limbs:
      // x = low + high*65536 - (low arithmetic>>15)*65536.
      for(shift=0;shift<3;shift=shift+1)begin
       access(1,0,shift==2?flag_value:packed_value,got);
       addr=2*(cc%4)+(shift==1?1:0);
       payload=0;payload[addr*16+:16]=16'd1;
       access(1,16,payload,got); // One offline N1/K8 basis-vector record.
       feed(0);
       command(4,0,(shift==2?64'hffff:64'd1) | (shift==0?64'd0:64'd16<<16),0,0,result);
       command(10,0,(64'd1<<15) | 64'h1183 | (shift==0?64'd4:64'd0),0,0,result);
      end
      slot=512+part*64+rr*8+cc;
      command(5,0,64'h200,1,slot,result);
      expected={96'b0,inputs_mem[finalbase+(rr*ncols+cc)*4+part][31:0]};
      if(result!==expected)$fatal(1,"scatter scalar mismatch id=%0d row=%0d col=%0d shift=%0d got=%h expected=%h",id,rr,cc,part*8,result,expected);
      access(0,slot,0,got);if(got!==expected)$fatal(1,"scatter canonical S32 SRAM mismatch");
     end
    end
   end
   $display("COLUMN_TILE {\"id\":%0d,\"rows\":%0d,\"columns\":%0d,\"k\":%0d,\"cycles\":%0d,\"a_fires\":%0d,\"b_fires\":%0d,\"wide_reads\":%0d,\"store_acks\":%0d,\"e_store_acks\":%0d,\"e_commands\":%0d,\"dot_a_stage_words\":%0d,\"dot_b_stage_words\":%0d}",
    id,nrows,ncols,kval,cycle-begin_cycle,a_fires-begin_a,b_fires-begin_b,wide_reads-begin_wide,store_acks-begin_ack,
    e_acks-begin_eack,e_commands-begin_ecmd,3*nrows*kval,ncols*kval);
  end
 endtask
 initial begin
  for(integer r=1;r<=8;r=r+1)begin
   for(integer key=0;key<32;key=key+1)begin p_count[r][key]=0;p_min[r][key]=2147483647;p_max[r][key]=0;end
   for(integer key=0;key<16;key=key+1)begin m_count[r][key]=0;m_min[r][key]=2147483647;m_max[r][key]=0;end
   for(integer key=0;key<2;key=key+1)begin f_count[r][key]=0;f_min[r][key]=2147483647;f_max[r][key]=0;end
  end
  $readmemh("vectors.hex",inputs_mem);
  `include "cases.svh"
  if(p_start>=0 || m_start>=0 || f_start>=0 || e_start>=0)$fatal(1,"unfinished passive profile");
  for(integer r=1;r<=8;r=r+1)begin
   for(integer key=0;key<32;key=key+1)if(p_count[r][key]>0)
    $display("COLUMN_PROFILE {\"boundary\":\"p-command\",\"rows\":%0d,\"op\":%0d,\"store\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",r,key%16,key/16,p_count[r][key],p_min[r][key],p_max[r][key]);
   for(integer key=0;key<16;key=key+1)if(m_count[r][key]>0)
    $display("COLUMN_PROFILE {\"boundary\":\"native-m\",\"rows\":%0d,\"op\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",r,key,m_count[r][key],m_min[r][key],m_max[r][key]);
   for(integer key=0;key<2;key=key+1)if(f_count[r][key]>0)
    $display("COLUMN_PROFILE {\"boundary\":\"feeder\",\"rows\":%0d,\"reuse_b\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",r,key,f_count[r][key],f_min[r][key],f_max[r][key]);
  end
  $display("COLUMN_PROFILE {\"boundary\":\"e-service\",\"op\":8,\"shift\":15,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",e_count,e_min,e_max);
  $display("PASS native column tile and scalar scatter probe");$finish;
 end
endmodule
