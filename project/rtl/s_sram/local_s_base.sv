// One controller-selected 128-bit request port. Responses retire in order.
module local_s_base (
    input wire clk, reset,
    input wire req_valid, req_write,
    input wire [9:0] req_addr,
    input wire [127:0] req_data,
    output wire req_ready, rsp_valid,
    input wire rsp_ready,
    output wire [127:0] rsp_data
`ifdef USE_POWER_PINS
    , inout wire vdd, gnd
`endif
);
    block_feed_s16k_sram #(.ECHO_WRITE_DATA(1'b0)) storage (
        .clk(clk), .reset(reset), .req(req_valid), .wr(req_write),
        .addr(req_addr), .din(req_data), .ready(req_ready), .valid(rsp_valid),
        .take(rsp_ready), .dout(rsp_data),
        .wide_req(1'b0), .wide_addr(8'b0), .wide_ready(),
        .wide_valid(), .wide_take(1'b0), .wide_dout()
`ifdef USE_POWER_PINS
        , .vdd(vdd), .gnd(gnd)
`endif
    );
endmodule
