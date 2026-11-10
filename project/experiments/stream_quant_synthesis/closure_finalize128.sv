// Final conversion once after all K groups. Reject range errors; never hide
// them with clipping. Bias is S32/Q16 and is added after the common shift.
module closure_finalize128(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [3:0] in_count,input wire [1023:0] in_data,
 input wire [6:0] in_shift,input wire [255:0] in_bias,
 output reg out_valid,input wire out_ready,output reg [255:0] out_data,output reg out_error
);
 assign in_ready=!reset&&(!out_valid||out_ready);
 wire signed [128:0] value[0:7];wire [127:0] residue[0:7];
 wire [127:0] mask=(128'd1<<in_shift)-1;
 wire [127:0] half=128'd1<<(in_shift==0?7'd0:in_shift-1'b1);
 wire signed [128:0] rounded[0:7],total[0:7];wire [7:0] bad;
 for(genvar i=0;i<8;i=i+1)begin: lane
  assign value[i]=$signed({in_data[i*128+127],in_data[i*128+:128]})>>>in_shift;
  assign residue[i]=in_data[i*128+:128]&mask;
  assign rounded[i]=value[i]+129'(in_shift!=0&&(residue[i]>half||(residue[i]==half&&value[i][0])));
  assign total[i]=rounded[i]+$signed({{97{in_bias[i*32+31]}},in_bias[i*32+:32]});
  assign bad[i]=i<in_count&&(total[i]<-129'sd2147483648||total[i]>129'sd2147483647);
 end
 always @(posedge clk)begin
  if(reset)begin out_valid<=0;out_data<=0;out_error<=0;end
  else if(in_ready)begin
   out_valid<=in_valid;
   if(in_valid)begin
    out_error<=in_count==0||in_count>8||(|bad);
    for(integer i=0;i<8;i=i+1)out_data[i*32+:32]<=i<in_count?32'(total[i]):32'd0;
   end
  end
 end
endmodule
