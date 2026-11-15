// Finite parent SRAM selector. Build-time clients; no product-created active mux.
module s128_service_selector #(parameter integer CLIENTS=3,
 parameter integer OWNER_BITS=CLIENTS>1?$clog2(CLIENTS):1)(
 input wire clk,reset,
 input wire [CLIENTS-1:0] c_valid,c_write,
 output wire [CLIENTS-1:0] c_ready,c_response_valid,
 input wire [CLIENTS-1:0] c_response_ready,
 input wire [CLIENTS*10-1:0] c_address,
 input wire [CLIENTS*128-1:0] c_data,
 output wire req_valid,req_write,input wire req_ready,
 output wire [9:0] req_address,output wire [127:0] req_data,
 input wire rsp_valid,output wire rsp_ready
);
 reg owned,sent;reg [OWNER_BITS-1:0] owner;integer chosen;
 always @* begin
  chosen=-1;
  for(integer i=CLIENTS-1;i>=0;i=i-1)if(c_valid[i])chosen=i;
 end
 assign req_valid=!reset&&owned&&!sent&&c_valid[owner];
 assign req_write=c_write[owner];
 assign req_address=c_address[owner*10+:10];
 assign req_data=c_data[owner*128+:128];
 assign c_ready=(!reset&&owned&&!sent&&req_ready)?(CLIENTS'(1)<<owner):'0;
 assign c_response_valid=(!reset&&owned&&sent&&rsp_valid)?(CLIENTS'(1)<<owner):'0;
 assign rsp_ready=!reset&&owned&&sent&&c_response_ready[owner];
 always @(posedge clk)begin
  if(reset)begin owned<=0;sent<=0;owner<=0;end
  else begin
   if(!owned&&chosen>=0)begin owned<=1;owner<=OWNER_BITS'(chosen);sent<=0;end
   if(req_valid&&req_ready)sent<=1;
   if(rsp_valid&&rsp_ready)begin owned<=0;sent<=0;end
  end
 end
 initial if(CLIENTS<1)$error("SRAM selector requires registered clients");
endmodule
