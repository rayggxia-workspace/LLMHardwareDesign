// Six requesters, one actual S port. Ownership is held through read/write ACK.
// Registered request selection breaks long paths through the central mux.
module control_s_arbiter #(parameter integer CLIENTS=6)(
 input wire clk,reset,input wire [CLIENTS-1:0] req,wr,input wire [CLIENTS*10-1:0] addr,input wire [CLIENTS*128-1:0] din,
 output reg [CLIENTS-1:0] ready,valid,input wire [CLIENTS-1:0] take,output wire [127:0] dout,
 output wire s_req,s_wr,output wire [9:0] s_addr,output wire [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take,input wire [127:0] s_dout
);
 reg [2:0] state;reg [2:0] owner,next_owner;
 reg held_wr;reg [9:0] held_addr;reg [127:0] held_data;
 reg [CLIENTS-1:0] captured_wr;
 reg [127:0] held_response;
 reg found;reg [2:0] selected;
 always @* begin
  found=0;selected=0;
  for(integer k=0;k<CLIENTS;k=k+1) begin
   if(!found && req[(32'(next_owner)+k)%CLIENTS]) begin found=1;selected=3'((32'(next_owner)+k)%CLIENTS);end
  end
  ready=0;valid=0;
  if(state==3) ready[owner]=1'b1;
  if(state==5) valid[owner]=1'b1;
 end
 assign s_req=state==2;assign s_wr=held_wr;assign s_addr=held_addr;assign s_din=held_data;
 assign dout=held_response;assign s_take=state==4;
 always @(posedge clk) begin
  if(reset) begin state<=0;owner<=0;next_owner<=0;held_wr<=0;captured_wr<=0;held_addr<=0;held_data<=0;held_response<=0;end
  else begin
   // Snapshot every non-reset edge. The command's state-0 edge is the sample
   // consumed in state 1; later samples cannot alter held_wr. Keeping the
   // snapshot free of arbitration enables avoids a constant client's write
   // mode masking the otherwise live state-control cone in composition.
   captured_wr<=wr;
   case(state)
   0:if(found) begin owner<=selected;held_addr<=addr[selected*10+:10];held_data<=din[selected*128+:128];state<=1;end
   // Own a full command-setup stage, including all six write controls. This
   // keeps constant client write modes outside the combinational arbitration
   // cone without specializing or changing any client's read/write contract.
   1:begin held_wr<=captured_wr[owner];state<=2;end
   2:if(s_ready) state<=3;
   // ACK the original requester after S has accepted the held request. A
   // response remains in S until the following bounded capture stage.
   3:state<=4;
   4:if(s_valid) begin held_response<=s_dout;state<=5;end
   5:if(take[owner]) begin state<=0;next_owner<=32'(owner)==CLIENTS-1?3'd0:owner+1;end
   default:state<=0;
   endcase
  end
 end
endmodule
