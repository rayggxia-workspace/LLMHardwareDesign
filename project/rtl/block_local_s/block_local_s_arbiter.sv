// One physical Block owns this arbiter and its S. No remote S address/owner bus.
// Request acceptance reserves one command register, not a completed RAM write.
module block_local_s_arbiter #(
 parameter integer CLIENTS = 4,
 parameter integer OWNER_BITS = CLIENTS > 1 ? $clog2(CLIENTS) : 1
)(
 input wire clk, reset,
 input wire [CLIENTS-1:0] req_valid, req_write,
 input wire [CLIENTS*10-1:0] req_addr,
 input wire [CLIENTS*128-1:0] req_data,
 output reg [CLIENTS-1:0] req_ready,
 output reg [CLIENTS-1:0] rsp_valid,
 input wire [CLIENTS-1:0] rsp_ready,
 output reg [CLIENTS*128-1:0] rsp_data,
 output wire mem_req, mem_write,
 output wire [9:0] mem_addr,
 output wire [127:0] mem_data,
 input wire mem_ready, mem_valid,
 input wire [127:0] mem_result,
 output wire mem_take,
 output wire busy
);
 localparam [1:0] IDLE=0, SEND=1, RETURN=2;
 reg [1:0] state;
 reg [OWNER_BITS-1:0] owner, next_owner;
 reg saved_write;
 reg [9:0] saved_addr;
 reg [127:0] saved_data;
 reg found;
 reg [OWNER_BITS-1:0] selected;
 integer candidate;
 always @* begin
  found=0; selected=0; candidate=0;
  for(integer offset=0; offset<CLIENTS; offset=offset+1) begin
   candidate=int'(next_owner)+offset;
   if(candidate>=CLIENTS) candidate=candidate-CLIENTS;
   if(!found && req_valid[candidate]) begin
    found=1; selected=OWNER_BITS'(candidate);
   end
  end
  req_ready=0; rsp_valid=0; rsp_data=0;
  if(!reset) begin
   if(state==IDLE && found) req_ready[selected]=1;
   if(state==RETURN) begin
    rsp_valid[owner]=mem_valid;
    rsp_data[128*int'(owner)+:128]=mem_result;
   end
  end
 end
 assign mem_req=!reset && state==SEND;
 assign mem_write=saved_write;
 assign mem_addr=saved_addr;
 assign mem_data=saved_data;
 assign mem_take=!reset && state==RETURN && rsp_ready[owner];
 assign busy=state!=IDLE;
 always @(posedge clk) begin
  if(reset) begin
   state<=IDLE; owner<=0; next_owner<=0;
   saved_write<=0; saved_addr<=0; saved_data<=0;
  end else case(state)
   IDLE: if(found) begin
    owner<=selected;
    next_owner<=selected==OWNER_BITS'(CLIENTS-1) ? OWNER_BITS'(0) : selected+1'b1;
    saved_write<=req_write[selected];
    saved_addr<=req_addr[10*int'(selected)+:10];
    saved_data<=req_data[128*int'(selected)+:128];
    state<=SEND;
   end
   SEND: if(mem_ready) state<=RETURN;
   RETURN: if(mem_valid && rsp_ready[owner]) state<=IDLE;
   default: state<=IDLE;
  endcase
 end
endmodule
