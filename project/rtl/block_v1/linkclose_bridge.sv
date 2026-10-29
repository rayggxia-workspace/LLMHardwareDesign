// Finite prefabricated interface candidate, separate from accepted M/S/T.
// Two entries break the ready combinational path. Full+pop deliberately has
// one admission bubble; output payload is registered and stable while stalled.
module linkclose_elastic #(parameter WIDTH=131)(
 input wire clk,reset,input wire s_valid,output wire s_ready,
 input wire [WIDTH-1:0] s_data,output wire m_valid,input wire m_ready,
 output wire [WIDTH-1:0] m_data,output wire [1:0] occupancy
);
 reg [WIDTH-1:0] bank[0:1];
 reg rd,wr; reg [1:0] used;
 wire push=s_valid&&s_ready,pop=m_valid&&m_ready;
 assign s_ready=!reset&&used<2;
 assign m_valid=!reset&&used!=0;
 assign m_data=bank[rd];
 assign occupancy=used;
 always @(posedge clk) begin
  if(reset)begin rd<=0;wr<=0;used<=0;end
  else begin
   if(push)begin bank[wr]<=s_data;wr<=~wr;end
   if(pop)rd<=~rd;
   case({push,pop})
    2'b10:used<=used+1;
    2'b01:used<=used-1;
    default:used<=used;
   endcase
  end
 end
endmodule

// Route every M response through finite storage, retaining the per-command
// capture tag. Non-result command acknowledgements must not enter T payload.
module linkclose_bridge(
 input wire clk,reset,input wire command_valid,command_ready,command_capture,
 input wire response_valid,output wire response_ready,
 input wire [127:0] response_data,input wire response_error,response_saturated,
 input wire begin_valid,begin_ready,input wire write_enable,
 output wire write_valid,input wire write_ready,
 output wire [9:0] write_index,output wire [127:0] write_data,
 output wire [1:0] occupancy,output reg observed_error,observed_saturation
);
 reg capture;reg [9:0] index;
 wire valid,ready;wire [130:0] packet;
 linkclose_elastic queue(.clk(clk),.reset(reset),.s_valid(response_valid),
  .s_ready(response_ready),.s_data({capture,response_error,response_saturated,response_data}),
  .m_valid(valid),.m_ready(ready),.m_data(packet),.occupancy(occupancy));
 assign ready=packet[130]?(write_ready&&write_enable):1'b1;
 assign write_valid=valid&&packet[130]&&write_enable;
 assign write_data=packet[127:0];
 assign write_index=index;
 always @(posedge clk)begin
  if(reset)begin capture<=0;index<=0;observed_error<=0;observed_saturation<=0;end
  else begin
   if(command_valid&&command_ready)capture<=command_capture;
   if(begin_valid&&begin_ready)index<=0;
   else if(write_valid&&write_ready)index<=index+1;
   if(valid&&ready)begin
    observed_error<=observed_error|packet[129];
    observed_saturation<=observed_saturation|packet[128];
   end
  end
 end
endmodule
