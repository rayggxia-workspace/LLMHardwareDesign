`timescale 1ns/1ps
// Parent control routing: no hard boundary and no macro data connections.
// Route tables are generated from the registered services of this LC.
module macro_service_dispatch #(
 parameter integer SLOTS=1,ROUTES=1,
 parameter logic [31:0] TOPOLOGY=0,
 parameter logic [ROUTES*32-1:0] SCHEMAS=0,ABIS=0,
 parameter logic [ROUTES*16-1:0] OPCODES=0,
 parameter logic [ROUTES*8-1:0] SLOT_MAP=0
)(
 input wire clk,reset,
 input wire service_valid,output wire service_ready,
 input wire [127:0] service_owner,input wire [31:0] service_ticket,
 input wire [1023:0] service_descriptor,
 input wire service_cancel_valid,output wire service_cancel_ready,
 output wire service_done_valid,input wire service_done_ready,
 output wire [127:0] service_done_owner,output wire [31:0] service_done_ticket,
 output wire [15:0] service_done_status,
 output wire [31:0] service_done_read_bytes,service_done_write_bytes,
 output reg [SLOTS-1:0] provider_valid,input wire [SLOTS-1:0] provider_ready,
 output wire [127:0] provider_owner,output wire [31:0] provider_ticket,
 output wire [1023:0] provider_descriptor,
 output reg [SLOTS-1:0] provider_cancel_valid,input wire [SLOTS-1:0] provider_cancel_ready,
 input wire [SLOTS-1:0] provider_done_valid,output reg [SLOTS-1:0] provider_done_ready,
 input wire [SLOTS*128-1:0] provider_done_owner,
 input wire [SLOTS*32-1:0] provider_done_ticket,
 input wire [SLOTS*16-1:0] provider_done_status,
 input wire [SLOTS*32-1:0] provider_done_read_bytes,provider_done_write_bytes
);
 reg busy,rejected;
 reg [7:0] selected;
 reg [127:0] owner;
 reg [31:0] ticket;
 integer route_matches,route_slot;
 always_comb begin
  route_matches=0;route_slot=0;
  for(integer i=0;i<ROUTES;i++)begin
   if(service_descriptor[31:0]==SCHEMAS[i*32+:32]&&
      service_descriptor[95:64]==ABIS[i*32+:32]&&
      service_descriptor[63:48]==OPCODES[i*16+:16])begin
    route_matches=route_matches+1;route_slot=int'(SLOT_MAP[i*8+:8]);
   end
  end
 end
 wire legal=TOPOLOGY!=0&&SLOTS>0&&SLOTS<=256&&route_matches==1&&route_slot<SLOTS&&
            service_descriptor[47:32]==128&&service_descriptor[127:96]==TOPOLOGY;
 assign service_ready=!reset&&!busy&&(legal?provider_ready[route_slot]:1'b1);
 assign provider_owner=service_owner;
 assign provider_ticket=service_ticket;
 assign provider_descriptor=service_descriptor;
 assign service_cancel_ready=!reset&&busy&&(rejected||provider_cancel_ready[selected]);
 wire identity_bad=provider_done_owner[selected*128+:128]!=owner||
                   provider_done_ticket[selected*32+:32]!=ticket;
 assign service_done_valid=!reset&&busy&&(rejected||provider_done_valid[selected]);
 assign service_done_owner=owner;
 assign service_done_ticket=ticket;
 assign service_done_status=rejected?16'h03f0:identity_bad?16'h03f2:provider_done_status[selected*16+:16];
 assign service_done_read_bytes=rejected?0:provider_done_read_bytes[selected*32+:32];
 assign service_done_write_bytes=rejected?0:provider_done_write_bytes[selected*32+:32];
 always_comb begin
  provider_valid=0;provider_cancel_valid=0;provider_done_ready=0;
  // VALID is independent of READY, including descriptor rejection by a provider.
  if(!reset&&!busy&&legal)provider_valid[route_slot]=service_valid;
  if(!reset&&busy&&!rejected)begin
   provider_cancel_valid[selected]=service_cancel_valid;
   provider_done_ready[selected]=service_done_ready;
  end
 end
 always @(posedge clk)begin
  if(reset)begin busy<=0;rejected<=0;selected<=0;owner<=0;ticket<=0;end
  else begin
   if(service_valid&&service_ready)begin
    busy<=1;rejected<=!legal;selected<=legal?8'(route_slot):8'd0;
    owner<=service_owner;ticket<=service_ticket;
   end
   if(service_done_valid&&service_done_ready)begin busy<=0;rejected<=0;end
  end
 end
endmodule
