module block_cfj_cf #(
    parameter integer KIND = 1, // 1 F, 2 C
    parameter integer CLIENTS = KIND == 2 ? 5 : 4,
    parameter bit LATE_G_E = 0
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
    output wire [127:0] tx_data,
    output reg late_g_valid,
    output reg [31:0] late_g_data,
    input wire late_g_take,
    input wire late_e_valid,
    input wire [31:0] late_e_data,
    output wire late_e_take
);
    wire [CLIENTS-1:0] s_req, s_wr, s_ready, s_valid, s_take;
    wire [10*CLIENTS-1:0] s_addr;
    wire [128*CLIENTS-1:0] s_in, s_out;
    localparam [1:0] TX_IDLE=0, TX_READ=1, TX_HELD=2;
    reg [1:0] tx_state;
    reg [127:0] tx_hold;

    assign s_req[2] = rx_valid;
    assign s_wr[2] = 1'b1;
    assign s_addr[20+:10] = rx_addr;
    assign s_in[256+:128] = rx_data;
    assign s_take[2] = rx_stored_ready;
    assign rx_ready = s_ready[2];
    assign rx_stored = s_valid[2];
    assign s_req[3] = tx_req && tx_state==TX_IDLE;
    assign s_wr[3] = 1'b0;
    assign s_addr[30+:10] = tx_addr;
    assign s_in[384+:128] = 128'b0;
    // Retire the SRAM read into a separate slot before waiting on the peer.
    // tx_take still releases that slot only after the remote write ACK.
    assign s_take[3] = !reset && tx_state==TX_READ;
    assign tx_ready = s_ready[3];
    assign tx_valid = !reset && tx_state==TX_HELD;
    assign tx_data = tx_hold;

    always @(posedge clk) begin
        if (reset) tx_state <= TX_IDLE;
        else case (tx_state)
            TX_IDLE: if (s_req[3] && s_ready[3]) tx_state <= TX_READ;
            TX_READ: if (s_valid[3]) begin
                tx_hold <= s_out[384+:128];
                tx_state <= TX_HELD;
            end
            TX_HELD: if (tx_take) tx_state <= TX_IDLE;
            default: tx_state <= TX_IDLE;
        endcase
    end

    cfj_s_port #(.CLIENTS(CLIENTS)) store (
        .clk(clk), .reset(reset), .req_valid(s_req), .req_write(s_wr),
        .req_addr(s_addr), .req_data(s_in), .req_ready(s_ready),
        .rsp_valid(s_valid), .rsp_ready(s_take), .rsp_data(s_out)
    );

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
            wire direct = LATE_G_E && meta[63];
            cfj_e_port arithmetic (
                .clk(clk), .reset(reset), .in_valid(request), .in_ready(ready),
                .in_op(meta[3:0]), .in_shift(meta[8:4]),
                .in_a(a), .in_b(b), .in_c(c),
                .use_late_a(direct), .late_valid(late_e_valid),
                .late_a({96'b0, late_e_data}), .late_take(late_e_take),
                .out_valid(response), .out_ready(take), .out_data(data),
                .out_error(error), .out_saturated(saturated)
            );
        end else if (i == 1) begin: activate
            wire native_valid, native_error;
            wire direct = LATE_G_E && meta[63];
            wire publish_ready = !direct || !late_g_valid || late_g_take;
            assign response = native_valid && publish_ready;
            assign error = native_error;
            assign data[127:32] = 0;
            always @(posedge clk) begin
                if (reset) late_g_valid <= 0;
                else begin
                    if (late_g_valid && late_g_take) late_g_valid <= 0;
                    if (direct && response && take && !native_error) begin
                        late_g_valid <= 1;
                        late_g_data <= data[31:0];
                    end
                end
            end
            block_v2_g leaf (
                .clk(clk), .reset(reset), .in_valid(request), .in_ready(ready),
                .in_fn(meta[2:0]), .in_gated(meta[3]), .in_x(a[31:0]), .in_gate(b[31:0]),
                .out_valid(native_valid), .out_ready(take && publish_ready), .out_data(data[31:0]),
                .out_error(native_error), .out_saturated(saturated)
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
