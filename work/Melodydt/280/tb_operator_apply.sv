`timescale 1ps/1ps
module tb_operator_apply;
 reg clk=0,reset=1,cmd_valid=0;
 always #1667 clk=~clk;
 reg [9:0] cmd_words=0;
 reg [31:0] cmd_factor=0;
 reg signed [7:0] cmd_factor_shift=0,cmd_gamma_shift=0;
 wire cmd_ready,done_valid,done_error,s_req_valid,s_req_write,s_rsp_ready;
 wire [9:0] s_req_address;
 wire [127:0] s_req_data;
 reg s_rsp_valid=0;
 reg [127:0] s_rsp_data=0;
 wire s_req_ready=!s_rsp_valid;
 wire e_in_valid,e_in_ready,e_out_valid,e_out_ready,e_out_error;
 wire [63:0] e_in_data,e_out_data;
 wire [3:0] e_in_op,e_in_mask,e_out_clipped;
 wire [7:0] e_in_shift;
 wire [2:0] e_in_minus;
 s32_rms_apply_s128 dut(.clk,.reset,.cmd_valid,.cmd_ready,.cmd_x(10'd0),.cmd_gamma(10'd512),
   .cmd_words,.cmd_factor,.cmd_factor_shift,.cmd_gamma_shift,.done_valid,.done_error,.done_ready(1'b1),
   .s_req_valid,.s_req_write,.s_req_ready,.s_req_address,.s_req_data,.s_rsp_valid,.s_rsp_error(1'b0),.s_rsp_ready,.s_rsp_data,
   .e_in_valid,.e_in_ready,.e_in_data,.e_in_op,.e_in_mask,.e_in_shift,.e_in_minus,
   .e_out_valid,.e_out_error,.e_out_ready,.e_out_data,.e_out_clipped);
 e_s32_ap64 provider(.clk,.reset,.in_valid(e_in_valid),.in_ready(e_in_ready),.in_data(e_in_data),
   .in_op(e_in_op),.in_mask(e_in_mask),.in_shift(e_in_shift),.in_minus(e_in_minus),
   .out_valid(e_out_valid),.out_ready(e_out_ready),.out_data(e_out_data),.out_clipped(e_out_clipped),.out_error(e_out_error));
 reg [127:0] memory[0:1023],expected_word[0:511];
 integer words=0,reads=0,writes=0,cycles=0;
 always @(posedge clk)begin
   cycles<=cycles+1;
   if(reset)s_rsp_valid<=0;
   else begin
     if(s_rsp_valid&&s_rsp_ready)s_rsp_valid<=0;
     if(s_req_valid&&s_req_ready)begin
       s_rsp_valid<=1;
       if(s_req_write)begin
         if(writes>=words||s_req_address!==10'(writes)||s_req_data!==expected_word[writes])$fatal(1,"apply write mismatch");
         memory[s_req_address]<=s_req_data;s_rsp_data<=0;writes<=writes+1;
       end else begin
         if(s_req_address!==10'((reads%2==0?0:512)+reads/2)||reads>=2*words)$fatal(1,"apply read order");
         s_rsp_data<=memory[s_req_address];reads<=reads+1;
       end
     end
   end
 end
 integer fd,n,factor,fs,gs,start_cycle;
 string vectors,wave;
 time active_start,active_end,idle_end;
 initial begin
   if(!$value$plusargs("vectors=%s",vectors)||!$value$plusargs("wave=%s",wave))$fatal(1,"args");
   $dumpfile(wave);$dumpvars(0,tb_operator_apply);
   fd=$fopen(vectors,"r");if(!fd)$fatal(1,"vectors");
   n=$fscanf(fd,"%d %d %d %d\n",words,factor,fs,gs);
   if(n!=4||words<1||words>512||factor<0||fs<-63||fs>63||gs<-63||gs>63)$fatal(1,"apply header");
   for(integer i=0;i<words;i=i+1)begin
     n=$fscanf(fd,"%h %h %h\n",memory[i],memory[512+i],expected_word[i]);if(n!=3)$fatal(1,"word");
   end
   repeat(4)@(negedge clk);reset=0;repeat(4)@(negedge clk);
   active_start=$time;start_cycle=cycles;cmd_words=10'(words);cmd_factor=32'(factor);cmd_factor_shift=8'(fs);cmd_gamma_shift=8'(gs);cmd_valid=1;
   do @(posedge clk);while(!cmd_ready);
   @(negedge clk);cmd_valid=0;
   do @(posedge clk);while(!done_valid);
   if(done_error||reads!=2*words||writes!=words)$fatal(1,"apply terminal mismatch");
   for(integer i=0;i<words;i=i+1)if(memory[i]!==expected_word[i])$fatal(1,"apply readback");
   @(negedge clk);active_end=$time;
   $display("OPERATOR_PASS units=%0d cycles=%0d reads=%0d writes=%0d",words*4,cycles-start_cycle,reads,writes);
   repeat((active_end-active_start)/3334)@(negedge clk);idle_end=$time;
   $display("ACTIVITY_PASS active_start=%0d active_end=%0d idle_end=%0d",active_start,active_end,idle_end);
   #1;$finish;
 end
 initial begin #100000000000;$fatal(1,"watchdog");end
endmodule
