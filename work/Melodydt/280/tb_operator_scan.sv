`timescale 1ps/1ps
module tb_operator_scan;
 reg clk=0,reset=1,cmd_valid=0;
 always #1667 clk=~clk;
 reg [12:0] cmd_length=0;
 reg signed [5:0] cmd_baseline_shift=0;
 wire cmd_ready,done_valid,done_error,s_req_valid,s_rsp_ready;
 wire signed [5:0] done_shift;
 wire [5:0] done_extra_shift;
 wire [31:0] done_tag;
 wire [9:0] s_req_address;
 reg s_rsp_valid=0;
 reg [127:0] s_rsp_data=0;
 wire s_req_ready=!s_rsp_valid;
 s32_rms_range_scan dut(.clk,.reset,.cmd_valid,.cmd_ready,.cmd_base(10'd0),.cmd_length,.cmd_baseline_shift,.cmd_tag(32'd1),
   .done_valid,.done_ready(1'b1),.done_shift,.done_extra_shift,.done_tag,.done_error,
   .s_req_valid,.s_req_ready,.s_req_address,.s_rsp_valid,.s_rsp_ready,.s_rsp_data,.s_rsp_error(1'b0));
 reg [127:0] memory[0:1023];
 integer reads=0,words=0,cycles=0;
 always @(posedge clk)begin
   cycles<=cycles+1;
   if(reset)s_rsp_valid<=0;
   else begin
     if(s_rsp_valid&&s_rsp_ready)s_rsp_valid<=0;
     if(s_req_valid&&s_req_ready)begin
       if(s_req_address!==10'(reads)||reads>=words)$fatal(1,"scan read order");
       s_rsp_data<=memory[s_req_address];s_rsp_valid<=1;reads<=reads+1;
     end
   end
 end
 integer fd,n,elements,baseline,extra,start_cycle;
 string vectors,wave;
 time active_start,active_end,idle_end;
 initial begin
   if(!$value$plusargs("vectors=%s",vectors)||!$value$plusargs("wave=%s",wave))$fatal(1,"args");
   $dumpfile(wave);$dumpvars(0,tb_operator_scan);
   fd=$fopen(vectors,"r");if(!fd)$fatal(1,"vectors");
   n=$fscanf(fd,"%d %d %d\n",elements,baseline,extra);
   if(n!=3||elements<1||elements>4096||baseline<-32||baseline+extra>31)$fatal(1,"scan header");
   words=(elements+3)/4;
   for(integer i=0;i<words;i=i+1)begin n=$fscanf(fd,"%h\n",memory[i]);if(n!=1)$fatal(1,"word");end
   repeat(4)@(negedge clk);reset=0;repeat(4)@(negedge clk);
   active_start=$time;start_cycle=cycles;cmd_length=13'(elements);cmd_baseline_shift=6'(baseline);cmd_valid=1;
   do @(posedge clk);while(!cmd_ready);
   @(negedge clk);cmd_valid=0;
   do @(posedge clk);while(!done_valid);
   if(done_error||done_tag!=1||done_shift!==6'(baseline+extra)||done_extra_shift!==6'(extra)||reads!=words)$fatal(1,"scan mismatch");
   @(negedge clk);active_end=$time;
   $display("OPERATOR_PASS units=%0d cycles=%0d reads=%0d extra=%0d",elements,cycles-start_cycle,reads,done_extra_shift);
   repeat((active_end-active_start)/3334)@(negedge clk);idle_end=$time;
   $display("ACTIVITY_PASS active_start=%0d active_end=%0d idle_end=%0d",active_start,active_end,idle_end);
   #1;$finish;
 end
 initial begin #100000000000;$fatal(1,"watchdog");end
endmodule
