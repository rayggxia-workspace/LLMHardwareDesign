`timescale 1ns/1ps
module tb_m_timing;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,av=0,bv=0,cv=0,rtake=1;
 wire ar,br,cr,rv,re,rs,busy;wire [127:0] result;
 reg [2:0] arow=0;reg [1:0] atile=0,btile=0;reg bhalf=0;
 reg [3:0] cop=0;reg [5:0] ci=0;reg [63:0] cd=0;
 block_v2_m dut(.clk(clk),.reset(reset),.a_valid(av),.a_ready(ar),.a_bank(1'b0),.a_row(arow),.a_tile(atile),.a_wide(1'b1),.a_data({8{16'd2}}),
 .b_valid(bv),.b_ready(br),.b_bank(1'b0),.b_tile(btile),.b_wide(1'b1),.b_half(bhalf),.b_data({32{16'd3}}),
 .cmd_valid(cv),.cmd_ready(cr),.cmd_op(cop),.cmd_index(ci),.cmd_data(cd),.rsp_valid(rv),.rsp_ready(rtake),.rsp_data(result),.rsp_error(re),.rsp_saturated(rs),.busy(busy));
 integer cycle=0;always @(posedge clk)cycle<=cycle+1;
 task automatic command(input integer op,input integer ix,input reg[63:0] data,output integer elapsed);
  integer begin_cycle;
  @(negedge clk);cv=1;cop=4'(op);ci=6'(ix);cd=data;
  do @(posedge clk);while(!cr);begin_cycle=cycle;
  @(negedge clk);cv=0;
  do @(posedge clk);while(!rv);
  if(re)$fatal(1,"M command error");elapsed=cycle-begin_cycle+1;
  @(negedge clk);
 endtask
 integer rows,ri,k,ki,nt,t,r,h,elapsed,unused;
 initial begin
  repeat(4)@(negedge clk);reset=0;
  for(ri=0;ri<3;ri=ri+1)begin
   rows=ri==0?1:ri==1?2:8;
   for(ki=0;ki<3;ki=ki+1)begin
    k=ki==0?1:ki==1?8:32;
    command(6,0,0,unused);nt=(k+7)/8;
    for(t=0;t<nt;t=t+1)begin
     for(r=0;r<rows;r=r+1)begin
      @(negedge clk);av=1;arow=3'(r);atile=2'(t);
      do @(posedge clk);while(!ar);@(negedge clk);av=0;
     end
     for(h=0;h<2;h=h+1)begin
      @(negedge clk);bv=1;btile=2'(t);bhalf=1'(h);
      do @(posedge clk);while(!br);@(negedge clk);bv=0;
     end
    end
    command(4,0,1,unused);
    command(10,0,(64'(rows)<<15)|(64'(nt)<<12)|(64'd8<<8)|(64'(k==1?1:8)<<4)|64'd7,elapsed);
    $display("M_PROFILE rows=%0d k=%0d ticks=%0d",rows,k,elapsed);
    command(3,0,0,unused);
    if($signed(result[63:0])!=6*k||$signed(result[127:64])!=6*k)$fatal(1,"native tile numerical check failed");
   end
  end
  $display("M_PROFILE_PASS");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
