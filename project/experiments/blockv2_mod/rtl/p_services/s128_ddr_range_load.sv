`timescale 1ns/1ps
// Refill one resident S128 span from 64-byte DDR bursts. A two-burst record
// can select one aligned S128 word pair for the V layout without rewriting data.
module s128_ddr_range_load #(
    parameter bit PIPELINE_WRITES = 1'b0
) (
    input logic clk, reset,
    input logic launch_valid,
    output logic launch_ready,
    input logic [63:0] launch_base,
    input logic [9:0] launch_s_base,
    input logic [7:0] launch_bursts,
    input logic launch_pair, launch_pair_beat, launch_pair_high,
    output logic done_valid, done_error,
    input logic done_ready,
    output logic rd_valid,
    input logic rd_ready,
    output logic [63:0] rd_address, rd_tag,
    input logic rd_rsp_valid,
    output logic rd_rsp_ready,
    input logic [63:0] rd_rsp_tag,
    input logic [511:0] rd_rsp_data,
    output logic s_valid,
    input logic s_ready,
    output logic [9:0] s_address,
    output logic [127:0] s_data,
    output logic [31:0] s_tag,
    input logic s_rsp_valid,
    output logic s_rsp_ready,
    input logic [31:0] s_rsp_tag
);
    typedef enum logic [2:0] {IDLE, READ, READ_WAIT, STORE, STORE_WAIT, REPORT} state_t;
    state_t state;
    logic [63:0] base;
    logic [9:0] s_base;
    logic [7:0] burst, bursts;
    logic [1:0] word;
    logic pair, pair_beat, pair_high;
    logic [511:0] data;
    logic [2:0] sent, acknowledged;
    wire [2:0] write_count = pair ? 3'd2 : 3'd4;
    wire pipe_ack = s_rsp_valid && s_rsp_ready;
    wire pipe_send = s_valid && s_ready;
    wire [9:0] ack_address = s_base + (pair ? {9'd0, acknowledged[0]} : {burst, acknowledged[1:0]});
    wire bad_ack = pipe_ack && s_rsp_tag != {22'h12a000, ack_address};

    wire [11:0] launch_words = launch_pair ? 12'd2 : {2'b0, launch_bursts, 2'b0};
    wire [64:0] launch_end = {1'b0, launch_base} + {51'd0, launch_bursts, 6'd0};
    wire legal = launch_base[5:0] == 0 && launch_bursts != 0 &&
        (!launch_pair || launch_bursts == 2 || (launch_bursts == 1 && !launch_pair_beat)) &&
        launch_end <= (65'd1 << 64) &&
        {2'b0, launch_s_base} + launch_words <= 12'd1024;
    wire store_this_burst = !pair || burst[0] == pair_beat;
    wire last_word = pair ? word[0] : &word;
    wire [1:0] data_lane = pair ? {pair_high, word[0]} : word;
    wire last_burst = burst == bursts - 1'b1;

    assign launch_ready = !reset && state == IDLE;
    assign done_valid = !reset && state == REPORT;
    assign rd_valid = !reset && state == READ;
    assign rd_address = base + {50'd0, burst, 6'd0};
    assign rd_tag = {56'd0, burst};
    assign rd_rsp_ready = !reset && state == READ_WAIT;
    assign s_valid = !reset && state == STORE && (!PIPELINE_WRITES ||
        (sent < write_count && (sent - acknowledged < 3'd2 || pipe_ack)));
    wire [1:0] write_word = PIPELINE_WRITES ? sent[1:0] : word;
    assign s_address = s_base + (pair ? {9'd0, write_word[0]} : {burst, write_word});
    wire [1:0] write_lane = PIPELINE_WRITES ? (pair ? {pair_high, sent[0]} : sent[1:0]) : data_lane;
    assign s_data = data[{write_lane, 7'd0}+:128];
    assign s_tag = {22'h12a000, s_address};
    assign s_rsp_ready = !reset && (PIPELINE_WRITES
        ? state == STORE && acknowledged < sent : state == STORE_WAIT);

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            base <= 0;
            s_base <= 0;
            burst <= 0;
            bursts <= 0;
            word <= 0;
            pair <= 0;
            pair_beat <= 0;
            pair_high <= 0;
            data <= 0;
            sent <= 0;
            acknowledged <= 0;
            done_error <= 0;
        end else begin
            case (state)
                IDLE: if (launch_valid && launch_ready) begin
                    base <= launch_base;
                    s_base <= launch_s_base;
                    burst <= 0;
                    bursts <= launch_bursts;
                    word <= 0;
                    pair <= launch_pair;
                    pair_beat <= launch_pair_beat;
                    pair_high <= launch_pair_high;
                    done_error <= !legal;
                    state <= legal ? READ : REPORT;
                end
                READ: if (rd_valid && rd_ready) state <= READ_WAIT;
                READ_WAIT: if (rd_rsp_valid && rd_rsp_ready) begin
                    if (rd_rsp_tag != rd_tag) begin
                        done_error <= 1;
                        state <= REPORT;
                    end else if (store_this_burst) begin
                        data <= rd_rsp_data;
                        sent <= 0;
                        acknowledged <= 0;
                        state <= STORE;
                    end else if (last_burst) begin
                        state <= REPORT;
                    end else begin
                        burst <= burst + 1'b1;
                        state <= READ;
                    end
                end
                STORE: if (PIPELINE_WRITES) begin
                    if (pipe_send) sent <= sent + 1'b1;
                    if (pipe_ack) begin
                        acknowledged <= acknowledged + 1'b1;
                        if (bad_ack) done_error <= 1;
                        if (acknowledged + 1'b1 == write_count) begin
                            if (last_burst || done_error || bad_ack) state <= REPORT;
                            else begin
                                burst <= burst + 1'b1;
                                state <= READ;
                            end
                        end
                    end
                end else if (s_valid && s_ready) state <= STORE_WAIT;
                STORE_WAIT: if (s_rsp_valid && s_rsp_ready) begin
                    if (s_rsp_tag != s_tag) begin
                        done_error <= 1;
                        state <= REPORT;
                    end else if (!last_word) begin
                        word <= word + 1'b1;
                        state <= STORE;
                    end else if (last_burst) begin
                        state <= REPORT;
                    end else begin
                        word <= 0;
                        burst <= burst + 1'b1;
                        state <= READ;
                    end
                end
                REPORT: if (done_ready) state <= IDLE;
                default: begin
                    done_error <= 1;
                    state <= REPORT;
                end
            endcase
        end
    end
endmodule
