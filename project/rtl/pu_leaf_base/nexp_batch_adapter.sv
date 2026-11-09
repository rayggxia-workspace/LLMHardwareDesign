// Issue247 R2. Default keeps R1's four-command destructive sequence.
// Optional direct mode issues one stateless native op12 with identical values.
// Both modes own the same single N until the final response is retired.
module nexp_batch_adapter #(parameter integer NEXP_DIRECT=0) (
 input wire clk,reset,
 input wire in_valid,output wire in_ready,input wire [3:0] in_count,
 input wire [127:0] in_data,
 output reg out_valid,input wire out_ready,output reg [127:0] out_data,
 output reg out_error,
 output wire n_cmd_valid,input wire n_ready,
 output wire [3:0] n_cmd_op,n_cmd_count,output wire [127:0] n_cmd_data,
 input wire n_valid,output wire n_rsp_ready,input wire [127:0] n_data,input wire n_error
);
 reg active,waiting;reg [1:0] step;reg [3:0] count;
 reg [127:0] clamped;
 reg [3:0] op,ncount;reg [127:0] operand;
 assign in_ready=!reset&&!active&&!out_valid;
 always @* begin
  op=0;ncount=0;operand=0;
  if(NEXP_DIRECT!=0)begin op=12;ncount=count;operand=clamped;end
  else begin
   case(step)
    0:op=0;
    1:begin op=1;ncount=count;end // n explicit zeros establish max=0/count=n
    2:op=2;
    3:begin op=3;ncount=count;operand=clamped;end
   endcase
  end
 end
 assign n_cmd_valid=active&&!waiting;
 assign n_cmd_op=op;assign n_cmd_count=ncount;assign n_cmd_data=operand;
 assign n_rsp_ready=active&&waiting;
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
    if(n_error||NEXP_DIRECT!=0||step==3)begin
     active<=0;out_valid<=1;out_error<=n_error;
     for(integer i=0;i<8;i=i+1)out_data[16*i+:16]<=i<count?n_data[16*i+:16]:16'd0;
    end else step<=step+1'b1;
   end
  end
 end
endmodule
