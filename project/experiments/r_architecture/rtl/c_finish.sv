// Added finite hardware for wide global accumulation, RNE and S32 checking.
// One lane per cycle. Errors reject a transaction; data wraps exactly as R.
module c_finish(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [511:0] in_a,in_b,input wire [5:0] in_shift,input wire [1:0] in_op,
 output reg out_valid,input wire out_ready,output reg [511:0] out_data,output reg out_error
);
 reg running;reg [2:0] lane;reg [511:0] aa,bb;reg [5:0] shift;reg [1:0] op;
 reg signed [63:0] value,rounded;reg [63:0] mask,remn,half;
 reg signed [64:0] sum;reg bad;
 assign in_ready=!reset&&!running&&(!out_valid||out_ready);
 always @*begin
  value=$signed(aa[64*lane+:64]);rounded=value;mask=0;remn=0;half=0;
  if(shift!=0&&op!=2)begin
   mask=(64'd1<<shift)-1;remn=$unsigned(value)&mask;half=64'd1<<(shift-1);
   rounded=(value>>>shift)+$signed({63'd0,(remn>half)||((remn==half)&&value[shift])});
  end
  sum=$signed({rounded[63],rounded});
  if(op!=0)sum=sum+$signed({bb[64*lane+63],bb[64*lane+:64]});
  bad=op==3||(op==2?(sum[64]!=sum[63]):(sum[64:31]!={34{sum[31]}}));
 end
 integer j;
 always @(posedge clk)begin
  if(reset)begin running<=0;out_valid<=0;out_error<=0;out_data<=0;lane<=0;aa<=0;bb<=0;shift<=0;op<=0;end
  else begin
   if(out_valid&&out_ready)out_valid<=0;
   if(in_valid&&in_ready)begin aa<=in_a;bb<=in_b;shift<=in_shift;op<=in_op;running<=1;lane<=0;out_error<=0;end
   else if(running)begin
    out_error<=out_error||bad;
    out_data[64*lane+:64]<=op==2?sum[63:0]:{{32{sum[31]}},sum[31:0]};
    if(lane==7)begin running<=0;out_valid<=1;end else lane<=lane+1'b1;
   end
  end
 end
endmodule
