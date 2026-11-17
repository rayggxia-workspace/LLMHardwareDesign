`timescale 1ps/1ps
module tb_operator_softmax;
 reg clk=0,reset=1,cmd_valid=0;
 always #1667 clk=~clk;
 reg [12:0] cmd_count=0;
 wire cmd_ready,abort_ready,rsp_valid,rsp_error,rsp_aborted;
 wire [31:0] rsp_tag;
 wire [11:0] rsp_writes;
 wire s_req_valid,s_req_write,s_rsp_ready;
 wire [9:0] s_req_address;
 wire [127:0] s_req_data;
 reg s_rsp_valid=0;
 reg [127:0] s_rsp_data=0;
 wire s_req_ready=!s_rsp_valid;
 n_s32_softmax_s128 dut(.clk,.reset,.cmd_valid,.cmd_ready,.cmd_tag(32'd1),
   .cmd_base(10'd0),.cmd_count,.cmd_committed(1'b1),.abort_valid(1'b0),.abort_ready,.abort_tag(32'd0),
   .rsp_valid,.rsp_ready(1'b1),.rsp_tag,.rsp_error,.rsp_aborted,.rsp_writes,
   .s_req_valid,.s_req_ready,.s_req_write,.s_req_address,.s_req_data,
   .s_rsp_valid,.s_rsp_ready,.s_rsp_data,.s_rsp_error(1'b0));
 // Explicit one-outstanding S128 fixture. It is outside the powered DUT.
 reg [127:0] memory[0:1023],exponents[0:1023],probabilities[0:1023];
 integer words=0,reads=0,writes=0,cycles=0;
 always @(posedge clk) begin
   cycles<=cycles+1;
   if(reset) s_rsp_valid<=0;
   else begin
     if(s_rsp_valid&&s_rsp_ready) s_rsp_valid<=0;
     if(s_req_valid&&s_req_ready) begin
       if(s_req_address>=words) $fatal(1,"S aperture out of range");
       s_rsp_valid<=1;
       if(s_req_write) begin
         if(writes>=2*words || s_req_address!==10'(writes%words) ||
            s_req_data !== (writes<words ? exponents[writes%words] : probabilities[writes%words]))
           $fatal(1,"softmax intermediate/final write mismatch index=%0d data=%h",writes,s_req_data);
         memory[s_req_address]<=s_req_data; s_rsp_data<=0; writes<=writes+1;
       end else begin s_rsp_data<=memory[s_req_address]; reads<=reads+1; end
     end
   end
 end
 integer fd,n,elements,start_cycle;
 string vectors,wave;
 time active_start,active_end,idle_end;
 initial begin
   if(!$value$plusargs("vectors=%s",vectors)||!$value$plusargs("wave=%s",wave)) $fatal(1,"missing args");
   $dumpfile(wave); $dumpvars(0,tb_operator_softmax);
   fd=$fopen(vectors,"r"); if(!fd) $fatal(1,"missing vectors");
   n=$fscanf(fd,"%d\n",elements); if(n!=1||elements<1||elements>4096) $fatal(1,"bad length");
   words=(elements+3)/4;
   for(integer i=0;i<words;i=i+1) begin
     n=$fscanf(fd,"%h %h %h\n",memory[i],exponents[i],probabilities[i]);
     if(n!=3) $fatal(1,"bad word");
   end
   repeat(4) @(negedge clk);reset=0;
   repeat(4) @(negedge clk);
   active_start=$time; start_cycle=cycles;cmd_count=13'(elements);cmd_valid=1;
   do @(posedge clk);while(!cmd_ready);
   @(negedge clk);cmd_valid=0;
   do @(posedge clk);while(!rsp_valid);
   if(rsp_error||rsp_aborted||rsp_tag!=1||rsp_writes!=2*words||reads!=3*words||writes!=2*words)
     $fatal(1,"softmax terminal/count mismatch");
   for(integer i=0;i<words;i=i+1) if(memory[i]!==probabilities[i]) $fatal(1,"softmax readback mismatch");
   @(negedge clk);active_end=$time;
   $display("OPERATOR_PASS units=%0d cycles=%0d reads=%0d writes=%0d",elements,cycles-start_cycle,reads,writes);
   repeat((active_end-active_start)/3334) @(negedge clk);idle_end=$time;
   $display("ACTIVITY_PASS active_start=%0d active_end=%0d idle_end=%0d",active_start,active_end,idle_end);
   #1;$finish;
 end
 initial begin #100000000000;$fatal(1,"watchdog");end
endmodule
