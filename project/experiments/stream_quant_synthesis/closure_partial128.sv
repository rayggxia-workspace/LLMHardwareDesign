// Eight exact W8 group partials with FP16 mantissa/exponent descriptors.
// Prior S128 partial is supplied by SRAM; result ownership lasts until ACK.
// This arithmetic service does not invent SRAM ports or an M context loader.
module closure_partial128(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [3:0] in_count,input wire [319:0] in_partial,
 input wire [87:0] in_mantissa,input wire [55:0] in_shift,
 input wire [1023:0] in_previous,
 output reg out_valid,input wire out_ready,output reg [1023:0] out_data,output reg out_error
);
 assign in_ready=!reset&&(!out_valid||out_ready);
 wire signed [51:0] product[0:7];
 wire signed [255:0] term[0:7];
 wire signed [128:0] sum[0:7];
 wire [7:0] bad;
 for(genvar i=0;i<8;i=i+1)begin: lane
  assign product[i]=$signed(in_partial[i*40+:40])*$signed({1'b0,in_mantissa[i*11+:11]});
  assign term[i]={{204{product[i][51]}},product[i]}<<<in_shift[i*7+:7];
  assign sum[i]=$signed({in_previous[i*128+127],in_previous[i*128+:128]})+$signed({term[i][127],term[i][127:0]});
  assign bad[i]=i<in_count&&(in_mantissa[i*11+:11]==0||term[i]>(256'sd1<<127)-1||term[i]<-(256'sd1<<127)||sum[i][128]!=sum[i][127]);
 end
 always @(posedge clk)begin
  if(reset)begin out_valid<=0;out_data<=0;out_error<=0;end
  else if(in_ready)begin
   out_valid<=in_valid;
   if(in_valid)begin
    for(integer i=0;i<8;i=i+1)begin
     out_data[i*128+:128]<=i<in_count?sum[i][127:0]:128'd0;
    end
    out_error<=in_count==0||in_count>8||(|bad);
   end
  end
 end
endmodule
