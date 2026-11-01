// One consumer lease, exactly 384 x 128 bits of provisional payload storage.
// RAM is never reset. Old bytes are inaccessible until the complete new write.
// A coordinated hard reset is required if the consumer/fabric also resets.
module transaction6k (
 input wire clk, reset,
 input wire begin_valid, output wire begin_ready,
 input wire [1:0] begin_owner, input wire [31:0] begin_generation,
 input wire [9:0] begin_words,
 input wire write_valid, output wire write_ready,
 input wire [9:0] write_index, input wire [127:0] write_data,
 input wire commit_valid, output wire commit_ready,
 input wire revoke_valid, output wire revoke_ready,
 output wire read_valid, input wire read_take,
 output wire [9:0] read_index, output wire [127:0] read_data,
 output wire read_last,
 output reg [1:0] owner, output reg [31:0] generation,
 output reg [9:0] word_count,
 input wire release_valid, output wire release_ready,
 output wire busy, sealed, committed,
 output reg protocol_error, output wire [2:0] debug_state
);
 localparam EMPTY=0, FILL=1, SEALED=2, READ_REQ=3, READ_HOLD=4, RELEASE=5;
 reg [2:0] state;
 reg [9:0] received, cursor;
 reg [127:0] payload [0:383];
 reg [127:0] held;
 wire legal_size = begin_words > 0 && begin_words <= 384;
 assign busy = state != EMPTY;
 assign sealed = !reset && state == SEALED;
 assign committed = !reset && (state == READ_REQ || state == READ_HOLD || state == RELEASE);
 assign begin_ready = !reset && state == EMPTY && legal_size;
 assign revoke_ready = !reset && (state == FILL || state == SEALED);
 assign write_ready = !reset && state == FILL && !revoke_valid && write_index == received;
 assign commit_ready = !reset && state == SEALED && !revoke_valid;
 assign read_valid = !reset && state == READ_HOLD;
 assign read_index = cursor;
 assign read_data = held;
 assign read_last = read_valid && cursor + 1 == word_count;
 assign release_ready = !reset && state == RELEASE;
 assign debug_state = state;
 always @(posedge clk) begin
  if (reset) begin
   state <= EMPTY; received <= 0; cursor <= 0; held <= 0;
   owner <= 0; generation <= 0; word_count <= 0; protocol_error <= 0;
  end else begin
   if (begin_valid && state == EMPTY && !legal_size) protocol_error <= 1;
   if (write_valid && state == FILL && !revoke_valid && write_index != received) protocol_error <= 1;
   if (revoke_valid && revoke_ready) begin
    state <= EMPTY; received <= 0; cursor <= 0;
   end else case (state)
    EMPTY: if (begin_valid && begin_ready) begin
     state <= FILL; received <= 0; cursor <= 0;
     owner <= begin_owner; generation <= begin_generation; word_count <= begin_words;
    end
    FILL: if (write_valid && write_ready) begin
     payload[received] <= write_data;
     received <= received + 1;
     if (received + 1 == word_count) state <= SEALED;
    end
    SEALED: if (commit_valid && commit_ready) state <= READ_REQ;
    READ_REQ: begin held <= payload[cursor]; state <= READ_HOLD; end
    READ_HOLD: if (read_take) begin
     if (cursor + 1 == word_count) state <= RELEASE;
     // Refill the finite holding register on the consumption edge. Immutable
     // committed payload uses the same 1RW storage as provisional writes.
     else begin cursor <= cursor + 1; held <= payload[cursor+1]; end
    end
    RELEASE: if (release_valid) state <= EMPTY;
    default: begin state <= EMPTY; protocol_error <= 1; end
   endcase
  end
 end
endmodule
