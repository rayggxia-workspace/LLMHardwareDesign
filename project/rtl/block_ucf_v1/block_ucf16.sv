// Physical composition for U16 (N+E), F16 (G+E) and C16 (G+E+R).
// Fixed lanes are E, N/G, RX, TX, and (C only) R. External RX and TX
// address reservations and object identities are supplied by the controller.
module block_ucf16 #(
    parameter integer KIND = 0, // 0 U, 1 F, 2 C
    parameter integer CLIENTS = KIND == 2 ? 5 : 4
)(
    input wire clk, reset,
    input wire [CLIENTS-3:0] cmd_valid,
    output wire [CLIENTS-3:0] cmd_ready,
    input wire [(CLIENTS-2)*64-1:0] cmd_meta,
    input wire [(CLIENTS-2)*2-1:0] cmd_sources,
    input wire [(CLIENTS-2)*30-1:0] cmd_addresses,
    input wire [CLIENTS-3:0] cmd_store,
    input wire [(CLIENTS-2)*10-1:0] cmd_dst,
    output wire [CLIENTS-3:0] done_valid,
    input wire [CLIENTS-3:0] done_ready,
    output wire [(CLIENTS-2)*128-1:0] done_data,
    output wire [CLIENTS-3:0] done_error, done_saturated,
    input wire rx_valid,
    output wire rx_ready,
    input wire [9:0] rx_addr,
    input wire [127:0] rx_data,
    output wire rx_stored,
    input wire rx_stored_ready,
    input wire tx_req,
    output wire tx_ready,
    input wire [9:0] tx_addr,
    output wire tx_valid,
    input wire tx_take,
    output wire [127:0] tx_data
);
    wire [CLIENTS-1:0] s_req, s_wr, s_ready, s_valid, s_take;
    wire [10*CLIENTS-1:0] s_addr;
    wire [128*CLIENTS-1:0] s_in, s_out;

    assign s_req[2] = rx_valid;
    assign s_wr[2] = 1'b1;
    assign s_addr[20+:10] = rx_addr;
    assign s_in[256+:128] = rx_data;
    assign s_take[2] = rx_stored_ready;
    assign rx_ready = s_ready[2];
    assign rx_stored = s_valid[2];
    assign s_req[3] = tx_req;
    assign s_wr[3] = 1'b0;
    assign s_addr[30+:10] = tx_addr;
    assign s_in[384+:128] = 128'b0;
    assign s_take[3] = tx_take;
    assign tx_ready = s_ready[3];
    assign tx_valid = s_valid[3];
    assign tx_data = s_out[384+:128];

    /* verilator lint_off PINCONNECTEMPTY */
    block_local_s_macro #(.CLIENTS(CLIENTS), .WITH_FEEDER(0), .USE_SRAM(1)) store (
        .clk(clk), .reset(reset), .req_valid(s_req), .req_write(s_wr),
        .req_addr(s_addr), .req_data(s_in), .req_ready(s_ready),
        .rsp_valid(s_valid), .rsp_ready(s_take), .rsp_data(s_out),
        .load_valid(1'b0), .load_ready(), .load_bank(1'b0), .load_rows(4'b0),
        .load_tiles(3'b0), .load_a_wide(1'b0), .load_b_wide(1'b0),
        .load_reuse_b(1'b0), .load_a_base(10'b0), .load_b_base(10'b0),
        .done_valid(), .done_take(1'b0), .done_error(), .busy(),
        .a_valid(), .a_ready(1'b0), .a_bank(), .a_row(), .a_tile(), .a_wide(), .a_data(),
        .b_valid(), .b_ready(1'b0), .b_bank(), .b_tile(), .b_wide(), .b_half(), .b_data()
    );
    /* verilator lint_on PINCONNECTEMPTY */

    for (genvar i = 0; i < CLIENTS-2; i = i+1) begin: engine
        localparam integer S = i == 2 ? 4 : i;
        wire request, ready, response, take, error, saturated;
        wire [63:0] meta;
        wire [127:0] a, b, c, data;

        ucf_s_compute_client client (
            .clk(clk), .reset(reset), .cmd_valid(cmd_valid[i]), .cmd_ready(cmd_ready[i]),
            .cmd_meta(cmd_meta[64*i+:64]), .cmd_sources(cmd_sources[2*i+:2]),
            .cmd_addresses(cmd_addresses[30*i+:30]), .cmd_store(cmd_store[i]), .cmd_dst(cmd_dst[10*i+:10]),
            .done_valid(done_valid[i]), .done_ready(done_ready[i]), .done_data(done_data[128*i+:128]),
            .done_error(done_error[i]), .done_saturated(done_saturated[i]),
            .s_req_valid(s_req[S]), .s_req_ready(s_ready[S]), .s_req_write(s_wr[S]),
            .s_req_addr(s_addr[10*S+:10]), .s_req_data(s_in[128*S+:128]),
            .s_rsp_valid(s_valid[S]), .s_rsp_ready(s_take[S]), .s_rsp_data(s_out[128*S+:128]),
            .exec_valid(request), .exec_ready(ready), .exec_meta(meta), .exec_a(a), .exec_b(b), .exec_c(c),
            .result_valid(response), .result_ready(take), .result_data(data),
            .result_error(error), .result_saturated(saturated)
        );
        if (i == 0) begin: element
            block_v2_e leaf (
                .clk(clk), .reset(reset), .in_valid(request), .in_ready(ready),
                .in_op(meta[3:0]), .in_shift(meta[8:4]), .in_a(a), .in_b(b), .in_c(c),
                .out_valid(response), .out_ready(take), .out_data(data),
                .out_error(error), .out_saturated(saturated)
            );
        end else if (i == 1 && KIND == 0) begin: normalize
            wire busy;
            block_v2_n leaf (
                .clk(clk), .reset(reset), .cmd_valid(request), .cmd_ready(ready),
                .cmd_op(meta[3:0]), .cmd_count(meta[7:4]), .cmd_param(meta[39:8]),
                .cmd_data(a), .cmd_aux(b), .rsp_valid(response), .rsp_ready(take),
                .rsp_data(data), .rsp_error(error), .rsp_saturated(saturated), .busy(busy)
            );
        end else if (i == 1) begin: activate
            assign data[127:32] = 0;
            block_v2_g leaf (
                .clk(clk), .reset(reset), .in_valid(request), .in_ready(ready),
                .in_fn(meta[2:0]), .in_gated(meta[3]), .in_x(a[31:0]), .in_gate(b[31:0]),
                .out_valid(response), .out_ready(take), .out_data(data[31:0]),
                .out_error(error), .out_saturated(saturated)
            );
        end else begin: recurrent
            assign saturated = 0;
            ucf_r256_service leaf (
                .clk(clk), .reset(reset), .request(request), .ready(ready),
                .meta(meta), .operand(a), .response(response), .take(take),
                .data(data), .error(error)
            );
        end
    end
endmodule
