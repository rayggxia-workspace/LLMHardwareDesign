// Bounded research control-plane cost model. Not a production controller.
// 512-byte microstore, 384-byte parallel register file, counters and one
// 128-bit command channel. Full endpoint responses can retire 512 bits/cycle.
module control_support(
 input wire clk,reset,config_valid,config_code,input wire [5:0] config_index,input wire [127:0] config_data,
 input wire start,output wire ready,output reg busy,failed,
 output wire command_valid,input wire command_ready,output wire [2:0] command_channel,output wire [127:0] command_data,
 output wire [31:0] command_address,output wire [47:0] command_meta,
 input wire feedback_valid,output wire feedback_ready,input wire [511:0] feedback_data,input wire feedback_wide,feedback_error,
 output wire [3071:0] register_words
);
 reg [63:0] code[0:63];reg [127:0] rf[0:23];reg [5:0] pc;reg [31:0] count,address;
 wire [63:0] ir=code[pc];wire [3:0] op=ir[63:60];wire [4:0] index=ir[59:55];
 assign ready=!busy&&!reset;
 assign command_valid=busy&&!reset&&op==1;
 assign command_channel=ir[54:52];assign command_data=index<24?rf[index]:128'b0;
 assign command_address=address;assign command_meta=ir[47:0];
 assign feedback_ready=busy&&!reset&&op==2;
 for(genvar i=0;i<24;i=i+1)assign register_words[128*i+:128]=rf[i];
 always @(posedge clk)begin
  if(reset)begin busy<=0;failed<=0;pc<=0;count<=0;address<=0;end
  else if(!busy)begin
   if(config_valid)begin if(config_code)code[config_index]<=config_data[63:0];else if(config_index<24)rf[config_index]<=config_data;end
   if(start)begin busy<=1;failed<=0;pc<=0;count<=0;address<=0;end
  end else case(op)
   0:busy<=0;
   1:if(command_ready)pc<=pc+1;
   2:if(feedback_valid)begin
    if(index<24)rf[index]<=feedback_data[127:0];
    if(feedback_wide&&index<21)for(integer j=1;j<4;j=j+1)rf[index+j]<=feedback_data[128*j+:128];
    failed<=failed||feedback_error;pc<=pc+1;
   end
   3:begin count<=ir[31:0];pc<=pc+1;end
   4:if(count>1)begin count<=count-1;pc<=ir[5:0];end else begin count<=0;pc<=pc+1;end
   5:begin address<=address+ir[31:0];pc<=pc+1;end
   6:pc<=failed?ir[5:0]:pc+1;
   default:begin failed<=1;busy<=0;end
  endcase
 end
endmodule
