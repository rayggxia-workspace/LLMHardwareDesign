`timescale 1ns/1ps
module tb_cohort_reset;
 reg clk=0;always #5 clk=~clk;
 reg por_ni=0,reset_valid=0,ack_valid=0,providers_quiet=1,fault=0,reload_valid=0;
 reg [31:0] reset_sequence=2,reset_generation=2,reset_epoch=2,ack_sequence=1,ack_epoch=1,prepared_generation=1;
 reg [7:0] ack_mask=0;reg [2:0] prepared_mask=7;
 wire reset_ready,reset_o,admit_o,reload_o,poisoned_o;wire [2:0] phase_o;wire [31:0] sequence_o,generation_o,epoch_o;wire [7:0] acknowledged_o;
 integer mode=0,n;
 cohort_reset_controller dut(.*);
 task ack;input [7:0] mask;
  begin @(negedge clk);ack_valid=1;ack_mask=mask;@(negedge clk);ack_valid=0;end
 endtask
 task reload;
  begin while(!reload_o)@(negedge clk);reload_valid=1;@(negedge clk);reload_valid=0;end
 endtask
 initial begin
  n=$value$plusargs("MODE=%d",mode);repeat(3)@(negedge clk);por_ni=1;
  if(mode==1)begin ack(8'h7f);repeat(20)@(negedge clk);if(!reset_o||admit_o||reload_o||acknowledged_o!=127)$fatal(1,"missing ACK released");end
  else if(mode==2||mode==3||mode==4)begin
   if(mode==2)ack_sequence=0;
   if(mode==3)ack_epoch=0;
   ack(8'h1);if(mode==4)ack(8'h1);
   repeat(5)@(negedge clk);if(!poisoned_o||admit_o||!reset_o)$fatal(1,"stale/duplicate ACK admitted");
  end else begin
   if(mode==5)providers_quiet=0;
   ack(8'hff);
   if(mode==5)begin repeat(20)@(negedge clk);if(admit_o||reload_o)$fatal(1,"nonquiet released");providers_quiet=1;end
   while(!reload_o)@(negedge clk);
   if(mode==6)prepared_mask=3;
   if(mode==7)prepared_generation=0;
   if(mode==8)begin repeat(20)@(negedge clk);if(admit_o)$fatal(1,"missing reload admitted");end
   else begin
    reload;
    if(mode==6||mode==7)begin if(!poisoned_o||admit_o)$fatal(1,"partial/stale reload admitted");end
    else begin
     if(!admit_o||reset_o||generation_o!=1||epoch_o!=1)$fatal(1,"initial cohort admission");
     if(mode==9)begin reset_epoch=1;reset_valid=1;@(negedge clk);reset_valid=0;if(!poisoned_o||admit_o)$fatal(1,"old epoch accepted");end
     else if(mode==10)begin fault=1;@(negedge clk);fault=0;if(!poisoned_o||admit_o)$fatal(1,"fault admitted");end
     else begin
      reset_valid=1;#1;if(admit_o)$fatal(1,"reset request failed to close immediate admission");@(negedge clk);reset_valid=0;
      ack_sequence=2;ack_epoch=2;prepared_generation=2;ack(8'hff);reload;
      if(!admit_o||generation_o!=2||epoch_o!=2||sequence_o!=2)$fatal(1,"new cohort admission");
     end
    end
   end
  end
  $display("PASS cohort mode=%0d generation=%0d epoch=%0d phase=%0d",mode,generation_o,epoch_o,phase_o);$finish;
 end
 initial begin #10000;$fatal(1,"cohort watchdog");end
endmodule
