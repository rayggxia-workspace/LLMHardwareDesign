// One outstanding SRAM transaction. Completion denotes the response, including for writes.
module pj_sram_client (
 input wire clk, reset,
 input wire start, output wire idle, input wire write_word,
 input wire [9:0] address, input wire [127:0] data,
 output wire req_valid, req_write, output wire [9:0] req_addr,
 output wire [127:0] req_data, input wire req_ready,
 input wire rsp_valid, output wire rsp_ready,
 output wire done
);
 localparam IDLE=0, REQUEST=1, RESPONSE=2;
 reg [1:0] state;
 assign idle=!reset && state==IDLE;
 assign req_valid=!reset && state==REQUEST;
 assign req_write=write_word;
 assign req_addr=address;
 assign req_data=data;
 assign rsp_ready=!reset && state==RESPONSE;
 assign done=rsp_ready && rsp_valid;
 always @(posedge clk) begin
  if(reset) state<=IDLE;
  else case(state)
   IDLE: if(start) state<=REQUEST;
   REQUEST: if(req_ready) state<=RESPONSE;
   RESPONSE: if(rsp_valid) state<=IDLE;
   default: state<=IDLE;
  endcase
 end
endmodule
