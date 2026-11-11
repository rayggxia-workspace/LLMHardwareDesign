// Translate one local execution descriptor into compact E operand beats.
// The memory and E interfaces remain separate physical binding points.
module pu_compact_e_service #(parameter integer SHIFT_WIDTH=5) (
    input wire clk, reset,
    input wire cmd_valid, cmd_store, cmd_direct_a,
    output wire cmd_ready,
    input wire [1:0] cmd_sources, // Total A/B/C count, including direct A when selected.
    input wire [3:0] cmd_op,
    input wire [SHIFT_WIDTH-1:0] cmd_shift,
    input wire [29:0] cmd_src,
    input wire [9:0] cmd_dst,
    output wire done_valid,
    input wire done_ready,
    output reg done_error, done_saturated,
    output reg [127:0] done_data,
    output wire s_req_valid, s_req_write,
    input wire s_req_ready,
    output wire [9:0] s_req_addr,
    output wire [127:0] s_req_data,
    input wire s_rsp_valid,
    output wire s_rsp_ready,
    input wire [127:0] s_rsp_data,
    input wire direct_a_valid, direct_a_abort,
    output wire direct_a_ready,
    input wire [127:0] direct_a_data,
    output wire e_in_valid,
    input wire e_in_ready,
    output reg [3:0] e_in_op,
    output reg [SHIFT_WIDTH-1:0] e_in_shift,
    output reg [127:0] e_in_data,
    input wire e_out_valid,
    output wire e_out_ready,
    input wire [127:0] e_out_data,
    input wire e_out_error, e_out_saturated
);
    localparam [3:0] IDLE=0, READ_REQ=1, READ_RSP=2, SEND=3,
                     EXEC_RSP=4, WRITE_REQ=5, WRITE_RSP=6, DONE=7, DIRECT_A=8;
    reg [3:0] state;
    reg store_result;
    reg [1:0] beat, last_beat, source_count;
    reg [29:0] source_words;
    reg [9:0] destination_word;

    assign cmd_ready = !reset && state == IDLE;
    assign done_valid = !reset && state == DONE;
    assign s_req_valid = !reset && (state == READ_REQ || state == WRITE_REQ);
    assign s_req_write = state == WRITE_REQ;
    assign s_req_addr = s_req_write ? destination_word : source_words[9:0];
    assign s_req_data = done_data;
    assign s_rsp_ready = !reset && (state == READ_RSP || state == WRITE_RSP);
    assign direct_a_ready = !reset && state == DIRECT_A;
    assign e_in_valid = !reset && state == SEND;
    assign e_out_ready = !reset && state == EXEC_RSP;

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
        end else begin
            case (state)
                IDLE: if (cmd_valid) begin
                    source_words <= cmd_src;
                    destination_word <= cmd_dst;
                    store_result <= cmd_store;
                    e_in_op <= cmd_op;
                    e_in_shift <= cmd_shift;
                    beat <= 0;
                    source_count <= cmd_sources;
                    e_in_data <= 0;
                    if (cmd_op == 3 || cmd_op == 6)
                        last_beat <= 2;
                    else if (cmd_op == 7 || cmd_op == 8 || cmd_op >= 10)
                        last_beat <= 0;
                    else
                        last_beat <= 1;
                    state <= cmd_sources == 0 ? SEND :
                             cmd_direct_a ? DIRECT_A : READ_REQ;
                end
                DIRECT_A: if (direct_a_abort) begin
                    done_error <= 1'b1;
                    done_saturated <= 1'b0;
                    done_data <= 0;
                    state <= DONE;
                end else if (direct_a_valid) begin
                    e_in_data <= direct_a_data;
                    state <= SEND;
                end
                READ_REQ: if (s_req_ready) state <= READ_RSP;
                READ_RSP: if (s_rsp_valid) begin
                    // Descriptor operands beyond the opcode arity are still read,
                    // matching legacy S traffic, but are never sent as a new E command.
                    if (beat > last_beat) begin
                        beat <= beat + 1'b1;
                        source_words <= {10'b0, source_words[29:10]};
                        state <= {1'b0, beat} + 3'd1 < {1'b0, source_count} ? READ_REQ : EXEC_RSP;
                    end else begin
                        e_in_data <= s_rsp_data;
                        state <= SEND;
                    end
                end
                SEND: if (e_in_ready) begin
                    if (beat == last_beat && {1'b0, beat} + 3'd1 >= {1'b0, source_count})
                        state <= EXEC_RSP;
                    else begin
                        beat <= beat + 1'b1;
                        source_words <= {10'b0, source_words[29:10]};
                        // Compact E needs its opcode-defined beats even when the
                        // descriptor omits an operand. Supply zero without reading S.
                        e_in_data <= 0;
                        state <= {1'b0, beat} + 3'd1 < {1'b0, source_count} ? READ_REQ : SEND;
                    end
                end
                EXEC_RSP: if (e_out_valid) begin
                    done_data <= e_out_data;
                    done_error <= e_out_error;
                    done_saturated <= e_out_saturated;
                    state <= store_result && !e_out_error ? WRITE_REQ : DONE;
                end
                WRITE_REQ: if (s_req_ready) state <= WRITE_RSP;
                WRITE_RSP: if (s_rsp_valid) state <= DONE;
                DONE: if (done_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
