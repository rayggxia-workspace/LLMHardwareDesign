// Isolated Issue247 candidate. Two registered payload slots; no sink-ready
// combinational path to source-ready. Capacity remains finite under a stall.
// A full FIFO first consumes one beat before reopening source admission.
module pj_feed_elastic #(
 parameter integer WIDTH=1
)(
 input wire clk, reset,
 input wire src_valid, output wire src_ready, input wire [WIDTH-1:0] src_data,
 output wire dst_valid, input wire dst_ready, output reg [WIDTH-1:0] dst_data,
 output wire empty
);
 reg [WIDTH-1:0] tail_data;
 reg [1:0] count;
 assign src_ready=!reset && count<2'd2;
 assign dst_valid=!reset && count!=2'd0;
 // Explicit empty is a separate completion contract. Ready means not-full.
 assign empty=reset || count==2'd0;
 wire push=src_valid && src_ready;
 wire pop=dst_valid && dst_ready;
 always @(posedge clk) begin
  if(reset) begin
   count<=2'd0;
  end else begin
   case({push,pop})
    2'b10: begin
     if(count==2'd0) dst_data<=src_data;
     else tail_data<=src_data;
     count<=count+1'b1;
    end
    2'b01: begin
     if(count==2'd2) dst_data<=tail_data;
     count<=count-1'b1;
    end
    2'b11: begin
     // Simultaneous push/pop is possible with count==1 only: replace front.
     dst_data<=src_data;
    end
    default: begin end
   endcase
  end
 end
endmodule
