`timescale 1ps/1ps
module tb_operator_rope;
 reg clk=0,reset=1,cmd_valid=0,done_ready=0,cmd_negate=0;
 always #1667 clk=~clk;
 reg [7:0] cmd_cos_shift=0,cmd_neg_shift=0,cmd_neg_align=0,cmd_sin_shift=0,cmd_sin_align=0,cmd_out_shift=0;
 reg [127:0] cmd_value=0,cmd_paired=0,cmd_cos=0,cmd_sin=0;
 wire cmd_ready,done_valid,done_error;
 wire [127:0] done_data;
 wire [3:0] done_clipped;
 wire e_in_valid,e_in_ready,e_out_valid,e_out_ready,e_out_error;
 wire [63:0] e_in_data,e_out_data;
 wire [3:0] e_in_op,e_in_mask,e_out_clipped;
 wire [7:0] e_in_shift;
 wire [2:0] e_in_minus;
 rope_e32_ap64 dut(.*);
 e_s32_ap64 provider(.clk,.reset,.in_valid(e_in_valid),.in_ready(e_in_ready),.in_data(e_in_data),
   .in_op(e_in_op),.in_mask(e_in_mask),.in_shift(e_in_shift),.in_minus(e_in_minus),
   .out_valid(e_out_valid),.out_ready(e_out_ready),.out_data(e_out_data),.out_clipped(e_out_clipped),.out_error(e_out_error));
 integer cycles=0,inputs=0,outputs=0,commands=0;
 always @(posedge clk) begin
   cycles<=cycles+1;
   if(!reset)begin
     if(e_in_valid&&e_in_ready) inputs<=inputs+1;
     if(e_out_valid&&e_out_ready) outputs<=outputs+1;
   end
 end
 integer fd,n,count,negative,cs,ns,na,ss,sa,os,start_cycle,begin_packet,min_cycles=100000,max_cycles=0;
 reg [127:0] expected_value;
 string vectors,wave;
 time active_start,active_end,idle_end;
 initial begin
   if(!$value$plusargs("vectors=%s",vectors)||!$value$plusargs("wave=%s",wave)) $fatal(1,"missing args");
   $dumpfile(wave);$dumpvars(0,tb_operator_rope);
   fd=$fopen(vectors,"r");if(!fd) $fatal(1,"missing vectors");
   n=$fscanf(fd,"%d\n",count);if(n!=1||count<1) $fatal(1,"bad count");
   repeat(4) @(negedge clk);reset=0;
   repeat(4) @(negedge clk); active_start=$time;start_cycle=cycles;
   for(integer i=0;i<count;i=i+1)begin
     n=$fscanf(fd,"%d %d %d %d %d %d %d %h %h %h %h %h\n",negative,cs,ns,na,ss,sa,os,cmd_value,cmd_paired,cmd_cos,cmd_sin,expected_value);
     if(n!=12) $fatal(1,"bad packet");
     cmd_negate=1'(negative);cmd_cos_shift=8'(cs);cmd_neg_shift=8'(ns);cmd_neg_align=8'(na);
     cmd_sin_shift=8'(ss);cmd_sin_align=8'(sa);cmd_out_shift=8'(os);
     begin_packet=cycles;cmd_valid=1;
     do @(posedge clk);while(!cmd_ready);
     @(negedge clk);cmd_valid=0;done_ready=1;
     do @(posedge clk);while(!done_valid);
     if(done_error||done_clipped||done_data!==expected_value) $fatal(1,"RoPE data/flag mismatch packet=%0d",i);
     @(negedge clk);done_ready=0;commands=commands+1;
     if(cycles-begin_packet<min_cycles) min_cycles=cycles-begin_packet;
     if(cycles-begin_packet>max_cycles) max_cycles=cycles-begin_packet;
   end
   active_end=$time;
   $display("OPERATOR_PASS units=%0d cycles=%0d inputs=%0d outputs=%0d min_packet=%0d max_packet=%0d",commands,cycles-start_cycle,inputs,outputs,min_cycles,max_cycles);
   repeat((active_end-active_start)/3334) @(negedge clk);idle_end=$time;
   $display("ACTIVITY_PASS active_start=%0d active_end=%0d idle_end=%0d",active_start,active_end,idle_end);
   #1;$finish;
 end
 initial begin #100000000000;$fatal(1,"watchdog");end
endmodule
