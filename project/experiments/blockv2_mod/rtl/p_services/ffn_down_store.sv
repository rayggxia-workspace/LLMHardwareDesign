`timescale 1ns/1ps
// Gather real distributed Down words in logical channel order and retire only
// after the strict DDR write completions. No extra SRAM or unbounded buffer.
module ffn_down_store #(
    parameter bit TAG_BY_ADDRESS = 1'b0
) (
    input  logic clk, reset,
    input  logic launch_valid,
    output logic launch_ready,
    input  logic [63:0] launch_base,
    output logic done_valid, done_error,
    input  logic done_ready,
    output logic [2:0] s_req_valid,
    input  logic [2:0] s_req_ready,
    output logic [9:0] s_req_address,
    input  logic [2:0] s_rsp_valid,
    output logic [2:0] s_rsp_ready,
    input  logic [2:0][127:0] s_rsp_data,
    input  logic [2:0] s_rsp_error,
    output logic wr_valid,
    input  logic wr_ready,
    output logic [63:0] wr_address, wr_tag,
    output logic [511:0] wr_data,
    input  logic wr_done_valid,
    output logic wr_done_ready,
    input  logic [63:0] wr_done_tag,
    input  logic wr_done_error
);
    typedef enum logic [1:0] {IDLE, SEND, WAIT, DONE} state_t;
    state_t state;
    logic [6:0] burst;
    logic [63:0] base;
    logic engine_ready, engine_done, engine_error;
    logic [63:0] engine_tag;
    logic read_valid, read_ready, read_take;
    logic [9:0] linear_word;
    logic [1:0] response_p;
    wire [8:0] group = linear_word[9:1];
    wire [1:0] request_p = 2'(group % 9'd3);
    wire [8:0] local_group = group / 9'd3;

    assign launch_ready = !reset && state == IDLE;
    assign done_valid = !reset && state == DONE;
    assign s_req_address = {local_group, linear_word[0]};
    assign s_req_valid = read_valid ? 3'b001 << request_p : 3'b000;
    assign read_ready = s_req_ready[request_p];
    assign s_rsp_ready = read_take ? 3'b001 << response_p : 3'b000;

    wire [63:0] expected_tag = (TAG_BY_ADDRESS ? base>>6 : 64'd0) + 64'(burst);
    s128_ddr64_store writer(
        .clk, .reset, .cmd_valid(state == SEND), .cmd_ready(engine_ready),
        .cmd_source_word({1'b0, burst, 2'b00}), .cmd_ddr_address(base + {51'd0, burst, 6'd0}),
        .cmd_tag(expected_tag), .done_valid(engine_done), .done_ready(state == WAIT),
        .done_tag(engine_tag), .done_error(engine_error),
        .s_req_valid(read_valid), .s_req_ready(read_ready), .s_req_address(linear_word),
        .s_rsp_valid(s_rsp_valid[response_p]), .s_rsp_ready(read_take),
        .s_rsp_data(s_rsp_data[response_p]), .s_rsp_error(s_rsp_error[response_p]),
        .wr_valid, .wr_ready, .wr_address, .wr_tag, .wr_data,
        .wr_done_valid, .wr_done_ready, .wr_done_tag, .wr_done_error
    );

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            response_p <= 0;
            burst <= 0;
            base <= 0;
            done_error <= 0;
        end else begin
            if (read_valid && read_ready) response_p <= request_p;
            case (state)
                IDLE: if (launch_valid && launch_ready) begin
                    burst <= 0;
                    base <= launch_base;
                    done_error <= launch_base[5:0] != 0 || launch_base > 64'hffff_ffff_ffff_e000;
                    state <= launch_base[5:0] != 0 || launch_base > 64'hffff_ffff_ffff_e000 ? DONE : SEND;
                end
                SEND: if (engine_ready) state <= WAIT;
                WAIT: if (engine_done) begin
                    done_error <= engine_error || engine_tag != expected_tag;
                    if (engine_error || engine_tag != expected_tag || (&burst)) state <= DONE;
                    else begin
                        burst <= burst + 1'b1;
                        state <= SEND;
                    end
                end
                DONE: if (done_ready) state <= IDLE;
                default: begin
                    done_error <= 1;
                    state <= DONE;
                end
            endcase
        end
    end
endmodule
