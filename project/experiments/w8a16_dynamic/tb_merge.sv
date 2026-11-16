`timescale 1ns/1ps
module tb_merge;
 reg clk;initial begin clk=0;forever #5 clk=~clk;end
 reg reset=1,in_valid=0,out_ready=0;
 wire in_ready,out_valid,out_error,out_done;
 reg [1:0] in_kind;reg [127:0] in_key;reg [31:0] in_tag;
 reg [15:0] in_full_k,in_kk;reg [7:0] in_length;reg [3:0] in_n;
 reg [1:0] in_ai;reg [2:0] in_bi;reg [5:0] in_shift;reg [255:0] in_raw;
 wire [1:0] out_kind;wire [127:0] out_key;wire [31:0] out_tag;wire [255:0] out_data;
 reg exp_error,exp_done;reg [255:0] exp_data;
 dynamic_s32_merge dut(.*);
 string path;integer fd,got,count=0,delay_cycles;
 reg [419:0] held;
 initial begin
  if(!$value$plusargs("vectors=%s",path))$fatal(1,"vectors missing");
  fd=$fopen(path,"r");if(fd==0)$fatal(1,"vectors unreadable");
  repeat(4)@(negedge clk);reset=0;
  while(!$feof(fd))begin
   got=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h %h\n",
     in_kind,in_key,in_tag,in_full_k,in_kk,in_length,in_n,in_ai,in_bi,in_shift,in_raw,
     exp_error,exp_done,exp_data);
   if(got!=14)$fatal(1,"bad vector %0d fields %0d",count,got);
   in_valid=1;do @(posedge clk);while(!in_ready);
   @(negedge clk);in_valid=0;
   while(!out_valid)@(negedge clk);
   if(out_kind!==in_kind || out_key!==in_key || out_tag!==in_tag || out_error!==exp_error ||
      out_done!==exp_done || out_data!==exp_data)$fatal(1,"merge mismatch cmd%0d tag%0d",count,in_tag);
   held={out_kind,out_key,out_tag,out_error,out_done,out_data};
   delay_cycles=$urandom_range(0,6);
   repeat(delay_cycles)begin
    @(negedge clk);
    if(!out_valid || {out_kind,out_key,out_tag,out_error,out_done,out_data}!==held)
     $fatal(1,"held response changed");
   end
   out_ready=1;@(posedge clk);@(negedge clk);out_ready=0;count=count+1;
  end
  // Reset drops accepted in-flight partial; no pre-reset response may leak.
  in_kind=0;in_full_k=128;in_n=1;in_key=7;in_valid=1;
  @(posedge clk);@(negedge clk);in_valid=0;out_ready=1;
  @(posedge clk);@(negedge clk);out_ready=0;
  in_kind=1;in_kk=0;in_length=128;in_ai=0;in_bi=0;in_raw=1;in_valid=1;
  @(posedge clk);@(negedge clk);in_valid=0;reset=1;
  @(posedge clk);@(negedge clk);reset=0;
  repeat(5)begin @(negedge clk);if(out_valid)$fatal(1,"reset response leak");end
  $display("PASS merge commands=%0d",count);$finish;
 end
 initial begin #1000000000;$fatal(1,"watchdog");end
endmodule
