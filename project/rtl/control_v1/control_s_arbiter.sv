// Six requesters, one actual S port. Ownership is held through read/write ACK.
// Registered request selection breaks long paths through the central mux.
module control_s_arbiter(
 input wire clk,reset,input wire [5:0] req,wr,input wire [59:0] addr,input wire [767:0] din,
 output reg [5:0] ready,valid,input wire [5:0] take,output wire [127:0] dout,
 output wire s_req,s_wr,output wire [9:0] s_addr,output wire [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take,input wire [127:0] s_dout
);
 reg [1:0] state;reg [2:0] owner,next_owner;
 reg held_wr;reg [9:0] held_addr;reg [127:0] held_data;
 reg found;reg [2:0] selected;
 always @* begin
  found=0;selected=0;
  for(integer k=0;k<6;k=k+1) begin
   if(!found && req[(32'(next_owner)+k)%6]) begin found=1;selected=3'((32'(next_owner)+k)%6);end
  end
  ready=0;valid=0;
  if(state==1) ready[owner]=s_ready;
  if(state==2) valid[owner]=s_valid;
 end
 assign s_req=state==1;assign s_wr=held_wr;assign s_addr=held_addr;assign s_din=held_data;
 assign dout=s_dout;assign s_take=state==2 && take[owner];
 always @(posedge clk) begin
  if(reset) begin state<=0;owner<=0;next_owner<=0;held_wr<=0;held_addr<=0;held_data<=0;end
  else case(state)
   0:if(found) begin owner<=selected;held_wr<=wr[selected];held_addr<=addr[selected*10+:10];held_data<=din[selected*128+:128];state<=1;end
   1:if(s_ready) state<=2;
   2:if(s_valid && s_take) begin state<=0;next_owner<=owner==5?3'd0:owner+1;end
   default:state<=0;
  endcase
 end
endmodule
