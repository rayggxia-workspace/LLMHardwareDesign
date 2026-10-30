// A finite half-duplex128-bit packet bridge, one transaction outstanding.
// Two header beats/request+response; data beat on request(write) or response(read).
module memory_link(input wire clk,reset,input wire req,wr,input wire [31:0] addr,
 input wire [127:0] din,output wire ready,output wire valid,input wire take,output reg [127:0] dout,
 output wire t_req,t_wr,output wire [31:0] t_addr,output wire [127:0] t_data,
 input wire t_ready,t_valid,output wire t_take,input wire [127:0] t_result,
 output wire wire_valid,output wire [127:0] wire_data,output reg [31:0] beats,transactions);
 reg [3:0] state;reg sr_wr,ep_wr;reg [31:0] sr_addr,ep_addr;reg [127:0] sr_data,ep_data,result;
 assign ready=state==0;assign valid=state==9;
 assign t_req=state==4;assign t_wr=ep_wr;assign t_addr=ep_addr;assign t_data=ep_data;assign t_take=state==5;
 assign wire_valid=(state==1||state==2||state==3||state==6||state==7||state==8);
 assign wire_data=state==1?{64'h4938305f52455130,31'b0,sr_wr,sr_addr}:
                  state==2?128'h4938305f524551310000000000000000:
                  state==3?sr_data:state==6?128'h4938305f525350300000000000000000:
                  state==7?128'h4938305f525350310000000000000000:state==8?result:128'b0;
 always @(posedge clk)begin
  if(reset)begin state<=0;sr_wr<=0;sr_addr<=0;sr_data<=0;ep_wr<=0;ep_addr<=0;ep_data<=0;result<=0;dout<=0;beats<=0;transactions<=0;end
  else begin
   if(wire_valid)beats<=beats+1;
   case(state)
   0:if(req)begin sr_wr<=wr;sr_addr<=addr;sr_data<=din;transactions<=transactions+1;state<=1;end
   1:begin ep_wr<=wire_data[32];ep_addr<=wire_data[31:0];state<=2;end
   2:state<=sr_wr?3:4;
   3:begin ep_data<=wire_data;state<=4;end
   4:if(t_ready)state<=5;
   5:if(t_valid)begin result<=t_result;state<=6;end
   6:state<=7;
   7:begin if(ep_wr)begin dout<=0;state<=9;end else state<=8;end
   8:begin dout<=wire_data;state<=9;end
   9:if(take)state<=0;
   default:state<=0;
   endcase
  end
 end
endmodule
