// One credit for each external port. Both request and response cross
// registered boundaries. A write completes only after the SRAM responds.
module pj_mem_port #(
 parameter REQ_WIDTH=128, RSP_WIDTH=128
) (
 input wire clk, reset,
 input wire req_valid, req_write, input wire [9:0] req_addr,
 input wire [REQ_WIDTH-1:0] req_data, output wire req_ready,
 output wire rsp_valid, output reg [RSP_WIDTH-1:0] rsp_data, input wire rsp_ready,
 output wire s_req_valid, output reg s_req_write, output reg [9:0] s_req_addr,
 output reg [REQ_WIDTH-1:0] s_req_data, input wire s_req_ready,
 input wire s_rsp_valid, input wire [RSP_WIDTH-1:0] s_rsp_data, output wire s_rsp_ready
);
 localparam EMPTY=0, SEND=1, WAIT_S=2, RECEIVE=3;
 reg [1:0] state;
 assign req_ready=!reset && state==EMPTY;
 assign s_req_valid=state==SEND;
 assign s_rsp_ready=state==WAIT_S;
 assign rsp_valid=state==RECEIVE;
 always @(posedge clk) begin
  if(reset) state<=EMPTY;
  else case(state)
   EMPTY: if(req_valid) begin
    s_req_addr<=req_addr; s_req_data<=req_data; s_req_write<=req_write; state<=SEND;
   end
   SEND: if(s_req_ready) state<=WAIT_S;
   WAIT_S: if(s_rsp_valid) begin rsp_data<=s_rsp_data; state<=RECEIVE; end
   RECEIVE: if(rsp_ready) state<=EMPTY;
   default: state<=EMPTY;
  endcase
 end
endmodule
