// Select the first maximum from a complete stream in vocabulary order.
// All logits in one command share the caller's signed S32 exponent.
module s32_token_argmax (
    input wire clk, reset,
    input wire cmd_valid,
    output wire cmd_ready,
    input wire [31:0] cmd_length, cmd_tag,
    input wire in_valid,
    output wire in_ready,
    input wire [31:0] in_index,
    input wire [3:0] in_mask,
    input wire [127:0] in_data,
    output wire done_valid,
    input wire done_ready,
    output reg [31:0] done_token, done_tag,
    output reg signed [31:0] done_logit,
    output reg done_error
);
    localparam [1:0] IDLE = 0, STREAM = 1, REPORT = 2;
    reg [1:0] state;
    reg [31:0] remaining, next_index;
    reg have_best, next_have_best;
    reg [31:0] best_token;
    reg signed [31:0] best_logit;
    reg [3:0] required_mask;

    assign cmd_ready = !reset && state == IDLE;
    assign in_ready = !reset && state == STREAM;
    assign done_valid = !reset && state == REPORT;

    always @* begin
        required_mask = 0;
        next_have_best = have_best;
        best_token = done_token;
        best_logit = done_logit;
        for (integer lane = 0; lane < 4; lane = lane + 1) begin
            if (remaining > 32'(lane)) begin
                required_mask[lane] = 1;
                if (!next_have_best || $signed(in_data[32*lane +: 32]) > best_logit) begin
                    next_have_best = 1;
                    best_logit = $signed(in_data[32*lane +: 32]);
                    best_token = next_index + 32'(lane);
                end
            end
        end
    end

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            remaining <= 0;
            next_index <= 0;
            have_best <= 0;
            done_token <= 0;
            done_logit <= 0;
            done_tag <= 0;
            done_error <= 0;
        end else begin
            case (state)
                IDLE: if (cmd_valid && cmd_ready) begin
                    remaining <= cmd_length;
                    next_index <= 0;
                    have_best <= 0;
                    done_token <= 0;
                    done_logit <= 0;
                    done_tag <= cmd_tag;
                    done_error <= cmd_length == 0;
                    state <= cmd_length == 0 ? REPORT : STREAM;
                end
                STREAM: if (in_valid && in_ready) begin
                    if (in_index != next_index || in_mask != required_mask) begin
                        done_error <= 1;
                        state <= REPORT;
                    end else begin
                        have_best <= next_have_best;
                        done_token <= best_token;
                        done_logit <= best_logit;
                        if (remaining <= 32'd4) begin
                            state <= REPORT;
                        end else begin
                            remaining <= remaining - 32'd4;
                            next_index <= next_index + 32'd4;
                        end
                    end
                end
                REPORT: if (done_valid && done_ready)
                    state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
