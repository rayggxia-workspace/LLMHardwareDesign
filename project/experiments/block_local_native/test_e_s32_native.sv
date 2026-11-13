`timescale 1ns/1ps
module test_e_s32_native;
 reg clk;initial clk=0;always #5 clk=~clk;
 reg reset=1,in_valid=0,out_ready=0;
 reg [3:0] in_op=0,in_mask=0;
 reg [7:0] in_shift=0;
 reg [2:0] in_minus=0;
 reg [127:0] in_data=0;
 wire in_ready,out_valid,out_error;
 wire [127:0] out_data;
 wire [3:0] out_clipped;
 e_s32_native dut(.*);
 reg [535:0] vectors[768];
 string vector_path;
 integer seed,cycles,request_words=0,returned=0,held=0,bad=0;
 initial cycles=0;
 always @(posedge clk)begin
  cycles<=cycles+1;
  if(cycles>40000)$fatal(1,"finite E32 watchdog");
 end
 task automatic send(input reg[127:0] data);
  in_valid=1;in_data=data;
  do @(posedge clk);while(!in_ready);
  @(negedge clk);in_valid=0;request_words=request_words+1;
 endtask
 initial begin
  if(!$value$plusargs("vectors=%s",vector_path))$fatal(1,"vectors required");
  if(!$value$plusargs("seed=%d",seed))seed=1;
  $readmemh(vector_path,vectors);
  repeat(3)@(negedge clk);reset=0;
  // Reset must flush a partly admitted command, not invent a result.
  in_op=0;in_mask=15;send(128'h7fffffff);
  reset=1;repeat(2)@(negedge clk);reset=0;#1;
  if(out_valid||!in_ready)$fatal(1,"partly collected command survived reset");
  for(integer t=0;t<768;t=t+1)begin
   in_op=vectors[t][512+:4];in_shift=vectors[t][516+:8];
   in_mask=vectors[t][524+:4];in_minus=vectors[t][528+:3];
   send(vectors[t][0+:128]);
   if(!vectors[t][535])begin
    if(vectors[t][512+:4]!=3&&vectors[t][512+:4]!=4&&vectors[t][512+:4]!=10&&vectors[t][512+:4]!=11)begin
     // First-beat control is held by the device. Later operand metadata is
     // deliberately unrelated and must not re-decode an opcode.
     in_op=15;in_shift=8'h80;in_mask=0;in_minus=7;
     send(vectors[t][128+:128]);
    end
    if(vectors[t][512+:4]==1||vectors[t][512+:4]==9)send(vectors[t][256+:128]);
   end else bad=bad+1;
   while(!out_valid)@(negedge clk);
   repeat((t+seed)%7+1)begin
    if(!out_valid||in_ready||out_error!==vectors[t][535]||out_clipped!==vectors[t][531+:4]||
       out_data!==vectors[t][384+:128])$fatal(1,"E32 result/hold case=%0d actual=%h expected=%h sat=%h",t,out_data,vectors[t][384+:128],out_clipped);
    held=held+1;@(negedge clk);
   end
   out_ready=1;@(negedge clk);out_ready=0;returned=returned+1;
   if(out_valid)$fatal(1,"duplicated result");
  end
  $display("PASS e_s32_native commands=768 returned=%0d words=%0d malformed=%0d held=%0d cycles=%0d reset_partial=1",returned,request_words,bad,held,cycles);
  $finish;
 end
endmodule
