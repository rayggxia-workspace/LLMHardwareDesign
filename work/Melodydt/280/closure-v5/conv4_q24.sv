// Explicit candidate: eight independent depthwise four-tap dots.
// Value S32/Q16, coefficient S32/Q24, one final RNE to S32/Q16.
// This is not an IEEE FP32 replacement or a whole-model precision claim.
module conv4_q24(
 input wire clk,reset,cmd_valid,output wire cmd_ready,
 input wire [1:0] cmd_op,input wire [2:0] cmd_index,input wire [127:0] cmd_data,
 output reg rsp_valid,input wire rsp_ready,output reg [127:0] rsp_data,output reg rsp_error
);
 reg signed [31:0] values[0:31],weights[0:31],result[0:7];
 reg [7:0] values_valid,weights_valid;
 reg [2:0] state;reg [1:0] tap;
 reg signed [31:0] a[0:7],b[0:7];
 reg signed [63:0] product[0:7];reg signed [66:0] sum[0:7];
 reg output_valid;
 integer i;
 assign cmd_ready=!reset && state==0 && (!rsp_valid||rsp_ready);
 function automatic signed [66:0] rounded(input signed [66:0] v);
   reg signed [66:0] q;reg [23:0] remainder;
   begin q=v>>>24;remainder=v[23:0];
     rounded=q+((remainder>24'h800000)||(remainder==24'h800000 && q[0]));end
 endfunction
 always @(posedge clk) begin
  if(reset)begin
   values_valid<=0;weights_valid<=0;state<=0;tap<=0;rsp_valid<=0;rsp_data<=0;rsp_error<=0;output_valid<=0;
   for(i=0;i<8;i=i+1)begin a[i]<=0;b[i]<=0;product[i]<=0;sum[i]<=0;result[i]<=0;end
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if(cmd_valid&&cmd_ready)begin
    rsp_valid<=1;rsp_error<=0;rsp_data<=0;
    case(cmd_op)
     0,1:begin
      for(i=0;i<4;i=i+1)if(cmd_op==0)values[4*cmd_index+i]<=cmd_data[32*i+:32];else weights[4*cmd_index+i]<=cmd_data[32*i+:32];
      if(cmd_op==0)values_valid[cmd_index]<=1;else weights_valid[cmd_index]<=1;output_valid<=0;
     end
     2:if(values_valid!=8'hff||weights_valid!=8'hff)rsp_error<=1;
       else begin state<=1;tap<=0;rsp_valid<=0;for(i=0;i<8;i=i+1)sum[i]<=0;end
     3:if(cmd_index>1||!output_valid)rsp_error<=1;
       else for(i=0;i<4;i=i+1)rsp_data[32*i+:32]<=result[4*cmd_index+i];
    endcase
   end
   case(state)
    1:begin for(i=0;i<8;i=i+1)begin a[i]<=values[4*i+tap];b[i]<=weights[4*i+tap];end state<=2;end
    2:begin for(i=0;i<8;i=i+1)product[i]<=a[i]*b[i];state<=3;end
    3:begin for(i=0;i<8;i=i+1)sum[i]<=sum[i]+product[i];
       if(tap==3)state<=4;else begin tap<=tap+1;state<=1;end end
    4:begin
       for(i=0;i<8;i=i+1)begin
        result[i]<=32'(rounded(sum[i]));
        if(rounded(sum[i])>67'sd2147483647||rounded(sum[i])< -67'sd2147483648)rsp_error<=1;
       end
       output_valid<=1;rsp_valid<=1;state<=0;
      end
   endcase
  end
 end
endmodule
