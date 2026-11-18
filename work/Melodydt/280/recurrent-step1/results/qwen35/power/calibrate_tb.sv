`timescale 1ns/1ps
module calibrate_tb;
reg clk=0,reset=1,cmd_valid=0;
always #2.5 clk=~clk;
reg [3:0] cmd_op;
reg [9:0] cmd_index;
reg [127:0] cmd_data;
wire cmd_ready,rsp_valid,rsp_error,busy;
wire [127:0] rsp_data;
block_v1_r dut(.rsp_ready(1'b1),.*);
integer fd, ends, rc, op, idx, count=0, commands, final_command;
integer cycles=0, first_cycle, quiet_cycles, window_id=0;
reg [127:0] din, expected;
longint a,b,c;
always @(posedge clk) cycles<=cycles+1;
initial begin
  $dumpfile("raw.vcd");
  $dumpvars(0,dut);
  if (!$value$plusargs("count=%d",commands)) $fatal(1,"missing count");
  fd=$fopen("commands.txt","r");
  ends=$fopen("ends.txt","r");
  rc=$fscanf(ends,"%d",final_command);
  repeat(2) @(negedge clk);
  reset=0;
  @(negedge clk);
  first_cycle=cycles;
  a=$rtoi($realtime*1000);
  while(count<commands) begin
    rc=$fscanf(fd,"%d %d %h %h",op,idx,din,expected);
    if(rc!=4 || cmd_ready!==1) $fatal(1,"input %0d",count);
    cmd_op=op;cmd_index=idx;cmd_data=din;cmd_valid=1;
    @(negedge clk);
    cmd_valid=0;
    while(rsp_valid!==1) @(negedge clk);
    if(rsp_error!==0 || rsp_data!==expected)
      $fatal(1,"cmd %0d err %b got %h wanted %h",count,rsp_error,rsp_data,expected);
    if(count==final_command) begin
      b=$rtoi($realtime*1000);
      quiet_cycles=cycles-first_cycle;
      repeat(quiet_cycles) @(negedge clk);
      c=$rtoi($realtime*1000);
      $display("WINDOW %0d %0d %0d %0d",window_id,a,b,c);
      window_id=window_id+1;
      a=c;first_cycle=cycles;
      rc=$fscanf(ends,"%d",final_command);
    end
    count=count+1;
  end
  $display("GATE_REPLAY_PASS");
  $finish;
end
initial begin
  #20000000;
  $fatal(1,"timeout");
end
endmodule
