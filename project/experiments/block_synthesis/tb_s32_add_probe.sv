`timescale 1ns/1ps
module tb_s32_add_probe;
 `include "p_add_common.svh"
 logic[63:0] inputs_mem[0:VECTOR_WORDS-1];
 for(genvar bank=0;bank<4;bank=bank+1)begin: controlled_sram_initial_state
  initial begin
   integer pattern;logic[127:0] seed;
   if($value$plusargs("sinit=%d",pattern))begin
    if(pattern<0 || pattern>2)$fatal(1,"invalid SRAM initial state");
    for(integer wi=0;wi<256;wi=wi+1)begin
     seed=pattern==0?128'd0:pattern==1?{128{1'b1}}:
       {32'h9e3779b9^32'(wi),32'h85ebca6b^32'(bank),32'hc2b2ae35^32'(wi*17+bank),32'h27d4eb2f^32'(wi*97+bank)};
     dut.store.storage.banks[bank].memory.mem[wi]=seed;
    end
   end
  end
 end
 task automatic run_add(input integer id,input integer nrows,input integer ninputs,
                        input integer prepared,input integer gold,input integer finalbase,input integer signbase);
  integer rr,operand,part,at,begin_cycle,begin_a,begin_b,begin_wide,begin_ack;
  logic[127:0] got,result,payload,expected;
  begin
   @(negedge clk);reset=1;repeat(4)@(negedge clk);reset=0;rows=4'(nrows);
   repeat(4)@(negedge clk);
   // Explicit bounded feeder padding, not power-on SRAM contents.
   for(rr=0;rr<8;rr=rr+1)begin access(1,rr,0,got);access(1,16+rr,0,got);end
   // The immutable weight vector is [1,0,...], one column and Ksegment1.
   access(1,16,128'd1,got);
   begin_cycle=cycle;begin_a=a_fires;begin_b=b_fires;begin_wide=wide_reads;begin_ack=store_acks;
   at=prepared;
   for(operand=0;operand<ninputs;operand=operand+1)begin
    for(part=0;part<3;part=part+1)begin
     for(rr=0;rr<nrows;rr=rr+1)begin
      payload=0;payload[15:0]=inputs_mem[at][15:0];at=at+1;access(1,rr,payload,got);
     end
     feed(!(operand==0 && part==0));
     command(4,0,{48'b0,inputs_mem[signbase+operand][15:0]} | (part==0?64'd0:64'd16<<16),0,0,result);
     // Exactly one live r-by-1 S64 context; clear only on the first term.
     command(10,0,(64'(nrows)<<15) | 64'h1113 |
       ((operand==0 && part==0)?64'd4:64'd0),0,0,result);
    end
   end
   for(rr=0;rr<nrows;rr=rr+1)begin
    command(3,rr<<3,0,0,0,result);expected=0;expected[63:0]=inputs_mem[gold+rr];
    if(result!==expected)$fatal(1,"Add raw S64 mismatch id=%0d row=%0d got=%h expected=%h",id,rr,result,expected);
    command(5,rr<<3,64'h200,1,512+rr*8,result);
    expected=0;expected[31:0]=inputs_mem[finalbase+rr][31:0];
    if(result!==expected)$fatal(1,"Add final S32 mismatch id=%0d row=%0d",id,rr);
    access(0,512+rr*8,0,got);
    if(got!==expected)$fatal(1,"Add SRAM writeback mismatch id=%0d row=%0d",id,rr);
   end
   if(a_fires-begin_a!=3*ninputs*nrows || b_fires-begin_b!=2 ||
      wide_reads-begin_wide!=2+3*ninputs*((nrows+3)/4) || store_acks-begin_ack!=nrows)
    $fatal(1,"Add native resource counts differ id=%0d",id);
   $display("ADD_CASE {\"id\":%0d,\"a_fires\":%0d,\"b_fires\":%0d,\"wide_reads\":%0d,\"write_acks\":%0d,\"cycles\":%0d}",
      id,a_fires-begin_a,b_fires-begin_b,wide_reads-begin_wide,store_acks-begin_ack,cycle-begin_cycle);
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
  for(integer r=1;r<=8;r=r+1)begin
   for(integer key=0;key<32;key=key+1)if(p_count[r][key]>0)
    $display("ADD_PROFILE {\"boundary\":\"p-command\",\"rows\":%0d,\"op\":%0d,\"store\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",
      r,key%16,key/16,p_count[r][key],p_min[r][key],p_max[r][key]);
   for(integer key=0;key<2;key=key+1)if(f_count[r][key]>0)
    $display("ADD_PROFILE {\"boundary\":\"feeder\",\"rows\":%0d,\"reuse_b\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",
      r,key,f_count[r][key],f_min[r][key],f_max[r][key]);
  end
  $display("PASS native S32 Add row aggregate");$finish;
 end
endmodule
