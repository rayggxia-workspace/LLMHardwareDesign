`timescale 1ns/1ps
module tb_requant;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,in_valid=0,out_ready=0;
 wire in_ready,out_valid;
 reg signed [31:0] in_acc=0;
 reg [30:0] in_m=0;
 reg [5:0] in_shift=0;
 reg in_i16=0;
 wire signed [15:0] out_data;
 requant_serial dut(clk,reset,in_valid,in_ready,in_acc,in_m,in_shift,in_i16,out_valid,out_ready,out_data);
 integer file,rc,count=0,cycle=0,start_cycle,latency,minimum=99999,maximum=0,last_start=-1,min_interval=99999;
 integer acc,m,shift,bits,expected,stall,j;
 reg signed [15:0] held;
 always @(posedge clk) cycle=cycle+1;
 initial begin
   repeat(3) @(negedge clk);reset=0;
   file=$fopen("vectors.txt","r");
   if(file==0) $fatal(1,"missing vectors");
   while(!$feof(file)) begin
     rc=$fscanf(file,"%d %d %d %d %d %d\n",acc,m,shift,bits,expected,stall);
     if(rc==6) begin
       while(!in_ready) @(negedge clk);
       in_acc=acc;in_m=m;in_shift=shift;in_i16=(bits==16);in_valid=1;out_ready=0;
       @(negedge clk);start_cycle=cycle;
       if(last_start>=0 && start_cycle-last_start<min_interval) min_interval=start_cycle-last_start;
       last_start=start_cycle;
       in_valid=0;
       while(!out_valid) @(negedge clk);
       latency=cycle-start_cycle;
       if(latency<minimum) minimum=latency;
       if(latency>maximum) maximum=latency;
       if($signed(out_data)!==expected) $fatal(1,"mismatch case=%0d a=%0d m=%0d shift=%0d bits=%0d got=%0d expected=%0d",count,acc,m,shift,bits,$signed(out_data),expected);
       held=out_data;
       for(j=0;j<stall;j=j+1) begin
         @(negedge clk);
         if(!out_valid || out_data!==held || in_ready) $fatal(1,"backpressure stability failure");
       end
       out_ready=1;@(negedge clk);out_ready=0;
       count=count+1;
     end
   end
   // Reset a live request: its partial work must not leak as a stale response.
   while(!in_ready) @(negedge clk);
   in_valid=1;in_acc=-2147483648;in_m=2147483647;
   @(negedge clk);in_valid=0;repeat(5) @(negedge clk);
   reset=1;@(negedge clk);reset=0;repeat(30) @(negedge clk);
   if(out_valid || !in_ready) $fatal(1,"reset did not clear pending transaction");
   $display("REQUANT_PASS cases=%0d latency_min=%0d latency_max=%0d min_start_interval=%0d",count,minimum,maximum,min_interval);
   $finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
