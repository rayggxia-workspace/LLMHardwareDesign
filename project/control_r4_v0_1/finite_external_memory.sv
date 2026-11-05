`timescale 1ns/1ps
// Test-only finite native external memory; not HBM, AXI, or a PHY.
module finite_external_memory(input wire clk,reset,input wire [31:0] stall,mode,
 input wire req_valid,output wire req_ready,input wire [184:0] req_data,
 output wire rsp_valid,input wire rsp_ready,output wire [145:0] rsp_data);
 reg [127:0] memory[0:63];reg pending;reg [145:0] response;integer count=0,delay_left=0,i;
 assign req_ready=!reset&&!pending&&(stall==0||count%7==0);
 assign rsp_valid=!reset&&pending&&delay_left==0;
 assign rsp_data=response;
 initial begin
  pending=0;response=0;
  for(i=0;i<64;i=i+1)memory[i]=128'h0f0e0d0c0b0a09080706050403020100^{4{32'(i/4)-32'd6}};
 end
 always @(posedge clk)begin
  count<=count+1;
  if(reset)begin pending<=0;delay_left<=0;response<=0;end
  else begin
   if(pending&&delay_left!=0)delay_left<=delay_left-1;
   if(rsp_valid&&rsp_ready)pending<=0;
   if(req_valid&&req_ready)begin
    if(req_data[167:128]>=1024||req_data[131:128]!=0)$fatal(1,"external memory address outside finite fixture");
    pending<=1;delay_left<=2+int'(stall)*3;
    if(req_data[184])memory[req_data[137:132]]<=req_data[127:0];
    response<={mode==5?2'd1:2'd0,req_data[183:168]^(mode==6?16'h80:16'h0),req_data[184]?req_data[127:0]:memory[req_data[137:132]]};
    $display("E %0d REQ %0h",count,req_data);
   end
   if(rsp_valid&&rsp_ready)$display("E %0d RSP %0h",count,response);
  end
 end
endmodule
