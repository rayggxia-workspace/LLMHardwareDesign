// The controller schedules ordinary transactions and complete feeder jobs
// in distinct phases. Keep a stalled response or done event owned until taken.
module local_s_p (
    input wire clk, reset,
    input wire req_valid, req_write,
    input wire [9:0] req_addr,
    input wire [127:0] req_data,
    output wire req_ready, rsp_valid,
    input wire rsp_ready,
    output wire [127:0] rsp_data,
    input wire load_valid, load_bank, load_a_wide, load_b_wide, load_reuse_b,
    input wire [3:0] load_rows,
    input wire [2:0] load_tiles,
    input wire [9:0] load_a_base, load_b_base,
    output wire load_ready, done_valid, done_error,
    input wire done_take, a_ready, b_ready,
    output wire a_valid, a_bank, a_wide, b_valid, b_bank, b_wide, b_half,
    output wire [2:0] a_row,
    output wire [1:0] a_tile, b_tile,
    output wire [127:0] a_data,
    output wire [511:0] b_data
`ifdef USE_POWER_PINS
    , inout wire vdd, gnd
`endif
);
    wire memory_ready, loader_ready, loader_busy, loader_done, loader_error;
    wire wide_req, wide_ready, wide_valid, wide_take;
    wire [7:0] wide_addr;
    wire [511:0] wide_data;
    reg [1:0] outstanding;

    // A simultaneously presented new load gets priority at an idle boundary.
    // Once either phase has started, only its own handshakes can release it.
    wire ordinary_enabled = !loader_busy && !loader_done &&
                            !(load_valid && outstanding == 0);
    wire load_enabled = outstanding == 0;
    assign req_ready = ordinary_enabled && memory_ready;
    assign load_ready = load_enabled && loader_ready;
    assign done_valid = !reset && loader_done;
    assign done_error = !reset && loader_error;

    always @(posedge clk) begin
        if (reset)
            outstanding <= 0;
        else begin
            case ({req_valid && req_ready, rsp_valid && rsp_ready})
                2'b10: outstanding <= outstanding + 1'b1;
                2'b01: outstanding <= outstanding - 1'b1;
                default: begin end
            endcase
        end
    end

    block_feed_s16k_sram #(.ECHO_WRITE_DATA(1'b0)) storage (
        .clk(clk), .reset(reset), .req(req_valid && ordinary_enabled),
        .wr(req_write), .addr(req_addr), .din(req_data), .ready(memory_ready),
        .valid(rsp_valid), .take(rsp_ready), .dout(rsp_data),
        .wide_req(wide_req), .wide_addr(wide_addr), .wide_ready(wide_ready),
        .wide_valid(wide_valid), .wide_take(wide_take), .wide_dout(wide_data)
`ifdef USE_POWER_PINS
        , .vdd(vdd), .gnd(gnd)
`endif
    );

    block_feed_loader feeder (
        .clk(clk), .reset(reset), .load_valid(load_valid && load_enabled),
        .load_ready(loader_ready), .load_bank(load_bank), .load_rows(load_rows),
        .load_tiles(load_tiles), .load_a_wide(load_a_wide), .load_b_wide(load_b_wide),
        .load_reuse_b(load_reuse_b), .load_a_base(load_a_base), .load_b_base(load_b_base),
        .done_valid(loader_done), .done_take(done_take), .done_error(loader_error),
        .busy(loader_busy), .mem_req(wide_req), .mem_addr(wide_addr),
        .mem_ready(wide_ready), .mem_valid(wide_valid), .mem_take(wide_take),
        .mem_data(wide_data), .a_valid(a_valid), .a_ready(a_ready), .a_bank(a_bank),
        .a_row(a_row), .a_tile(a_tile), .a_wide(a_wide), .a_data(a_data),
        .b_valid(b_valid), .b_ready(b_ready), .b_bank(b_bank), .b_tile(b_tile),
        .b_wide(b_wide), .b_half(b_half), .b_data(b_data)
    );
endmodule
