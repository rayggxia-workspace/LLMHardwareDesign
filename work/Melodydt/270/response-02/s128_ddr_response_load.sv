`timescale 1ns/1ps
// Ordered DMA response stream. A request reserves its data slot until
// the final SRAM acknowledgement, and its DDR credit until the return.
module s128_ddr_response_load (
    input logic clk, reset,
    input logic launch_valid,
    output logic launch_ready,
    input logic [63:0] launch_base,
    input logic [9:0] launch_s_base,
    input logic [7:0] launch_bursts,
    input logic launch_pair, launch_pair_high,
    output logic done_valid, done_error,
    input logic done_ready,
    output logic rd_valid,
    input logic rd_ready,
    output logic [63:0] rd_address,
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
    localparam logic [7:0] DDR_CREDITS = 8, RESPONSE_SLOTS = 16;
    typedef enum logic [1:0] {IDLE, ACTIVE, REPORT} state_t;
    state_t state;
    logic [63:0] base;
    logic [9:0] s_base;
    logic [7:0] issued, returned, committed, bursts;
    logic pair, pair_high;
    logic [511:0] payload [16];
    logic poisoned [16];
    logic [2:0] sent, acknowledged;

    wire [11:0] words = launch_pair ? {3'd0, launch_bursts, 1'b0} : {2'd0, launch_bursts, 2'b0};
    wire [7:0] last = launch_bursts - 8'd1;
    wire [64:0] span = (launch_pair ? {48'd0, last, 9'd0} : {51'd0, last, 6'd0}) + 65'd64;
    wire legal = launch_base[5:0] == 0 && launch_bursts != 0 &&
        {1'b0, launch_base} + span <= (65'd1 << 64) && {2'd0, launch_s_base} + words <= 12'd1024;
    wire have_data = returned != committed;
    wire drop = have_data && poisoned[committed[3:0]];
    wire [2:0] writes = pair ? 3'd2 : 3'd4;
    wire take_ddr = rd_rsp_valid && rd_rsp_ready;
    wire take_s = s_rsp_valid && s_rsp_ready;
    wire commit_burst = drop || (take_s && acknowledged + 3'd1 == writes);
    wire [9:0] word_base = s_base + (pair ? {1'b0, committed, 1'b0} : {committed, 2'b0});
    wire [1:0] lane = pair ? {pair_high, sent[0]} : sent[1:0];
    wire [31:0] ack_tag = {22'h12a000, word_base + {7'd0, acknowledged}};

    assign launch_ready = !reset && state == IDLE;
    assign done_valid = !reset && state == REPORT;
    assign rd_valid = !reset && state == ACTIVE && issued < bursts &&
        (issued - returned < DDR_CREDITS || take_ddr) &&
        (issued - committed < RESPONSE_SLOTS || commit_burst);
    assign rd_address = base + (pair ? {47'd0, issued, 9'd0} : {50'd0, issued, 6'd0});
    assign rd_rsp_ready = !reset && state == ACTIVE && returned != issued;
    assign s_rsp_ready = !reset && state == ACTIVE && acknowledged < sent;
    assign s_valid = !reset && state == ACTIVE && have_data && !drop &&
        sent < writes && (sent - acknowledged < 3'd2 || take_s);
    assign s_address = word_base + {7'd0, sent};
    assign s_data = payload[committed[3:0]][{lane, 7'd0}+:128];
    assign s_tag = {22'h12a000, s_address};

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            base <= 0;
            s_base <= 0;
            issued <= 0;
            returned <= 0;
            committed <= 0;
            bursts <= 0;
            pair <= 0;
            pair_high <= 0;
            sent <= 0;
            acknowledged <= 0;
            done_error <= 0;
        end else begin
            case (state)
                IDLE: if (launch_valid) begin
                    base <= launch_base;
                    s_base <= launch_s_base;
                    bursts <= launch_bursts;
                    pair <= launch_pair;
                    pair_high <= launch_pair_high;
                    issued <= 0;
                    returned <= 0;
                    committed <= 0;
                    sent <= 0;
                    acknowledged <= 0;
                    done_error <= !legal;
                    state <= legal ? ACTIVE : REPORT;
                end
                ACTIVE: begin
                    if (rd_valid && rd_ready) issued <= issued + 1'b1;
                    if (take_ddr) begin
                        payload[returned[3:0]] <= rd_rsp_data;
                        poisoned[returned[3:0]] <= rd_rsp_tag != {56'd0, returned};
                        returned <= returned + 1'b1;
                        if (rd_rsp_tag != {56'd0, returned}) done_error <= 1;
                    end
                    if (take_s && s_rsp_tag != ack_tag) done_error <= 1;
                    if (commit_burst) begin
                        committed <= committed + 1'b1;
                        sent <= 0;
                        acknowledged <= 0;
                        // A failed beat stays poisoned. Accepted work drains in order
                        // before the scope can reset the datapath or admit another span.
                        if (committed + 1'b1 == bursts) state <= REPORT;
                    end else begin
                        if (s_valid && s_ready) sent <= sent + 1'b1;
                        if (take_s) acknowledged <= acknowledged + 1'b1;
                    end
                end
                REPORT: if (done_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule

