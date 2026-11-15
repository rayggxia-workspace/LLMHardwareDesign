// Apply the resident N factor and gamma with two separately rounded E products.
// The caller retains the disjoint activation and gamma leases through completion.
// An error leaves the in-place destination unpublished, possibly partly written.
module s32_rms_apply_s128 #(parameter bit RESULT_IN_GAMMA=1'b0) (
    input  logic clk, reset,
    input  logic cmd_valid,
    output logic cmd_ready,
    input  logic [9:0] cmd_x, cmd_gamma, cmd_words,
    input  logic [31:0] cmd_factor,
    input  logic signed [7:0] cmd_factor_shift, cmd_gamma_shift,
    output logic done_valid, done_error,
    input  logic done_ready,
    output logic s_req_valid, s_req_write,
    input  logic s_req_ready,
    output logic [9:0] s_req_address,
    output logic [127:0] s_req_data,
    input  logic s_rsp_valid, s_rsp_error,
    output logic s_rsp_ready,
    input  logic [127:0] s_rsp_data,
    output logic e_in_valid,
    input  logic e_in_ready,
    output logic [63:0] e_in_data,
    output logic [3:0] e_in_op, e_in_mask,
    output logic [7:0] e_in_shift,
    output logic [2:0] e_in_minus,
    input  logic e_out_valid, e_out_error,
    output logic e_out_ready,
    input  logic [63:0] e_out_data,
    input  logic [3:0] e_out_clipped
);
    typedef enum logic [3:0] {IDLE, READ_X, WAIT_X, READ_GAMMA, WAIT_GAMMA,
                              SEND_E, WAIT_E, WRITE_RESULT, WAIT_WRITE, REPORT} state_t;
    state_t state;
    logic [9:0] x_address, gamma_address, remaining;
    logic [31:0] factor;
    logic [7:0] factor_shift, gamma_shift;
    logic [127:0] lhs, rhs, result;
    logic [1:0] input_beat;
    logic applying_gamma, high_result;
    logic [127:0] operand;
    logic [10:0] x_end, gamma_end;
    logic command_legal;

    assign x_end = {1'b0, cmd_x} + {1'b0, cmd_words};
    assign gamma_end = {1'b0, cmd_gamma} + {1'b0, cmd_words};
    assign command_legal = cmd_words != 0 && !cmd_factor[31] && x_end <= 1024 && gamma_end <= 1024 &&
        (x_end <= {1'b0, cmd_gamma} || gamma_end <= {1'b0, cmd_x}) &&
        cmd_factor_shift >= -8'sd63 && cmd_factor_shift <= 8'sd63 &&
        cmd_gamma_shift >= -8'sd63 && cmd_gamma_shift <= 8'sd63;
    assign cmd_ready = !reset && state == IDLE;
    assign done_valid = !reset && state == REPORT;
    assign s_req_valid = !reset && (state == READ_X || state == READ_GAMMA || state == WRITE_RESULT);
    assign s_req_write = state == WRITE_RESULT;
    assign s_req_address = state == READ_GAMMA || (RESULT_IN_GAMMA && state == WRITE_RESULT) ? gamma_address : x_address;
    assign s_req_data = result;
    assign s_rsp_ready = !reset && (state == WAIT_X || state == WAIT_GAMMA || state == WAIT_WRITE);

    assign e_in_valid = !reset && state == SEND_E;
    assign e_out_ready = !reset && state == WAIT_E;
    assign operand = input_beat[1] ? (applying_gamma ? rhs : {4{factor}}) : lhs;
    assign e_in_data = input_beat[0] ? operand[127:64] : operand[63:0];
    assign e_in_op = 4'd2;
    assign e_in_mask = 4'hf;
    assign e_in_shift = applying_gamma ? gamma_shift : factor_shift;
    assign e_in_minus = 0;

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            x_address <= 0;
            gamma_address <= 0;
            remaining <= 0;
            factor <= 0;
            factor_shift <= 0;
            gamma_shift <= 0;
            lhs <= 0;
            rhs <= 0;
            result <= 0;
            input_beat <= 0;
            applying_gamma <= 0;
            high_result <= 0;
            done_error <= 0;
        end else begin
            case (state)
                IDLE: if (cmd_valid && cmd_ready) begin
                    x_address <= cmd_x;
                    gamma_address <= cmd_gamma;
                    remaining <= cmd_words;
                    factor <= cmd_factor;
                    factor_shift <= cmd_factor_shift;
                    gamma_shift <= cmd_gamma_shift;
                    done_error <= !command_legal;
                    state <= command_legal ? READ_X : REPORT;
                end
                READ_X: if (s_req_ready) state <= WAIT_X;
                WAIT_X: if (s_rsp_valid) begin
                    lhs <= s_rsp_data;
                    applying_gamma <= 0;
                    input_beat <= 0;
                    high_result <= 0;
                    done_error <= s_rsp_error;
                    state <= s_rsp_error ? REPORT : SEND_E;
                end
                READ_GAMMA: if (s_req_ready) state <= WAIT_GAMMA;
                WAIT_GAMMA: if (s_rsp_valid) begin
                    lhs <= result;
                    rhs <= s_rsp_data;
                    applying_gamma <= 1;
                    input_beat <= 0;
                    high_result <= 0;
                    done_error <= s_rsp_error;
                    state <= s_rsp_error ? REPORT : SEND_E;
                end
                SEND_E: if (e_in_ready) begin
                    if (input_beat == 3) state <= WAIT_E;
                    else input_beat <= input_beat + 1'b1;
                end
                WAIT_E: if (e_out_valid) begin
                    done_error <= done_error || e_out_error || e_out_clipped != 0;
                    if (high_result) begin
                        result[127:64] <= e_out_data;
                        if (done_error || e_out_error || e_out_clipped != 0) state <= REPORT;
                        else state <= applying_gamma ? WRITE_RESULT : READ_GAMMA;
                    end else begin
                        result[63:0] <= e_out_data;
                        high_result <= 1;
                    end
                end
                WRITE_RESULT: if (s_req_ready) state <= WAIT_WRITE;
                WAIT_WRITE: if (s_rsp_valid) begin
                    done_error <= s_rsp_error;
                    if (s_rsp_error || remaining == 1) state <= REPORT;
                    else begin
                        x_address <= x_address + 1'b1;
                        gamma_address <= gamma_address + 1'b1;
                        remaining <= remaining - 1'b1;
                        state <= READ_X;
                    end
                end
                REPORT: if (done_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
