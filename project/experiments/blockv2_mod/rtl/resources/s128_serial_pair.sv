// Parent request selector, one accepted request held through response consumption.
module s128_serial_pair(
 input wire clk,reset,
 input wire [1:0] c_valid,c_write,
 output wire [1:0] c_ready,c_response_valid,
 input wire [1:0] c_response_ready,
 input wire [19:0] c_address,
 input wire [255:0] c_data,
 output wire req_valid,req_write,
 input wire req_ready,
 output wire [9:0] req_address,
 output wire [127:0] req_data,
 input wire rsp_valid,
 output wire rsp_ready
);
 reg owned,sent,owner;
 assign req_valid=!reset&&owned&&!sent&&c_valid[owner];
 assign req_write=c_write[owner];
 assign req_address=c_address[owner*10+:10];
 assign req_data=c_data[owner*128+:128];
 assign c_ready=(!reset&&owned&&!sent&&req_ready)?(2'b01<<owner):2'b00;
 assign c_response_valid=(!reset&&owned&&sent&&rsp_valid)?(2'b01<<owner):2'b00;
 assign rsp_ready=!reset&&owned&&sent&&c_response_ready[owner];
 always @(posedge clk)begin
  if(reset)begin owned<=0;sent<=0;owner<=0;end
  else begin
   if(!owned&&|c_valid)begin owned<=1;owner<=!c_valid[0];sent<=0;end
   if(req_valid&&req_ready)sent<=1;
   if(rsp_valid&&rsp_ready)begin owned<=0;sent<=0;end
  end
 end
endmodule
