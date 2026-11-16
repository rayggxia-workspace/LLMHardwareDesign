`timescale 1ns/1ps
module tb_raw;
 reg clk;initial begin clk=0;forever #5 clk=~clk;end
 reg reset=1,in_valid=0,out_ready=0;
 wire in_ready,out_valid,out_error;
 reg [31:0] in_tag;reg [3:0] in_n;
 reg [2:0] beat;
 reg [2047:0] a_frame;reg [8191:0] w_frame;
 wire [255:0] in_a=a_frame[beat*256+:256];
 wire [1023:0] in_w=w_frame[beat*1024+:1024];
 wire raw_valid,raw_ready,raw_error;wire [31:0] raw_tag;wire [3:0] raw_n;wire [255:0] raw_data;
 wire [31:0] out_tag;wire [255:0] out_data;
 m_group_s32 raw(.clk,.reset,.in_valid,.in_ready,.in_first(beat==0),.in_last(beat==7),
  .in_tag,.in_group_k(8'd128),.in_offset({1'b0,beat,4'd0}),.in_k(5'd16),.in_n,.in_a,.in_w,
  .out_valid(raw_valid),.out_ready(raw_ready),.out_tag(raw_tag),.out_n(raw_n),.out_data(raw_data),.out_error(raw_error));
 scale_group_s32 scale(.clk,.reset,.in_valid(raw_valid),.in_ready(raw_ready),.in_tag(raw_tag),
  .in_n(raw_n),.in_first(1'b1),.in_final(1'b1),.in_a_shift(6'd0),.in_partial(raw_data),
  .in_previous(256'd0),.in_bias(256'd0),.in_scale_fp16({8{16'h3c00}}),
  .out_valid,.out_ready,.out_tag,.out_data,.out_error);
 string path;integer fd,got,count=0;reg [255:0] expected,held;reg [31:0] held_tag;
 initial begin
  if(!$value$plusargs("vectors=%s",path))$fatal(1,"vectors missing");
  fd=$fopen(path,"r");if(fd==0)$fatal(1,"vectors unreadable");
  repeat(4)@(negedge clk);reset=0;
  while(!$feof(fd))begin
   got=$fscanf(fd,"%h %h %h %h %h\n",in_tag,in_n,a_frame,w_frame,expected);
   if(got!=5)$fatal(1,"bad raw vector");
   for(integer j=0;j<8;j=j+1)begin
    beat=3'(j);in_valid=1;
    do @(posedge clk);while(!in_ready);
    @(negedge clk);in_valid=0;
    repeat($urandom_range(0,2))@(negedge clk);
   end
   while(!out_valid)@(negedge clk);
   if(out_error || out_tag!==in_tag || out_data!==expected || raw_error)
    $fatal(1,"raw/scale-one exactness failed group%0d",count);
   held=out_data;held_tag=out_tag;
   repeat($urandom_range(0,6))begin
    @(negedge clk);if(!out_valid || out_data!==held || out_tag!==held_tag)$fatal(1,"raw held changed");
   end
   out_ready=1;@(posedge clk);@(negedge clk);out_ready=0;count=count+1;
  end
  $display("PASS raw scale-one groups=%0d",count);$finish;
 end
 initial begin #1000000000;$fatal(1,"watchdog");end
endmodule
