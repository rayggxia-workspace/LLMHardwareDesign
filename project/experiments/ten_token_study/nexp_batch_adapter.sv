// Candidate local U adapter; native N source is instantiated unchanged.
// f(x)=exp(x-max(x,0)) = exp(min(x,0)-0), for every signed S16 x.
// A transaction owns N until all four responses arrive. The caller must
// arbitrate this adapter with other N services before bottom-base freeze.
module nexp_batch_adapter(
 input wire clk,reset,
 input wire in_valid,output wire in_ready,input wire [3:0] in_count,
 input wire [127:0] in_data,
 output reg out_valid,input wire out_ready,output reg [127:0] out_data,
 output reg out_error
);
 reg active,waiting;reg [1:0] step;reg [3:0] count;
 reg [127:0] clamped;
 wire n_ready,n_valid,n_error,n_sat,n_busy;
 wire [127:0] n_data;
 reg [3:0] op,ncount;reg [127:0] operand;
 assign in_ready=!reset&&!active&&!out_valid;
 always @* begin
  op=0;ncount=0;operand=0;
  case(step)
   0:op=0;
   1:begin op=1;ncount=count;end // n explicit zero operands establish max=0/count=n
   2:op=2;
   3:begin op=3;ncount=count;operand=clamped;end
  endcase
 end
 block_v2_n native_n(.clk(clk),.reset(reset),.cmd_valid(active&&!waiting),
  .cmd_ready(n_ready),.cmd_op(op),.cmd_count(ncount),.cmd_param(32'd0),
  .cmd_data(operand),.cmd_aux(128'd0),.rsp_valid(n_valid),
  .rsp_ready(active&&waiting),.rsp_data(n_data),.rsp_error(n_error),
  .rsp_saturated(n_sat),.busy(n_busy));
 always @(posedge clk)begin
  if(reset)begin active<=0;waiting<=0;step<=0;count<=0;clamped<=0;out_valid<=0;out_data<=0;out_error<=0;end
  else begin
   if(out_valid&&out_ready)out_valid<=0;
   if(in_valid&&in_ready)begin
    out_error<=0;out_data<=0;
    if(in_count==0||in_count>8)begin out_error<=1;out_valid<=1;end
    else begin
     active<=1;waiting<=0;step<=0;count<=in_count;
     for(integer i=0;i<8;i=i+1)
      clamped[16*i+:16]<=i<in_count&&in_data[16*i+15]?in_data[16*i+:16]:16'd0;
    end
   end
   if(active&&!waiting&&n_ready)waiting<=1;
   if(active&&waiting&&n_valid)begin
    waiting<=0;
    if(n_error||step==3)begin
     active<=0;out_valid<=1;out_error<=n_error;
     for(integer i=0;i<8;i=i+1)out_data[16*i+:16]<=i<count?n_data[16*i+:16]:16'd0;
    end else step<=step+1'b1;
   end
  end
 end
endmodule
