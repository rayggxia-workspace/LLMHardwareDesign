// Physical C0 receiver sidecar. Sources 0..3 are P2, U0, U1 and F0.
// P2 is wired to its native SRAM port; the other three use native S TX.
module qwen_c0_receive (
    input  logic clk, reset,
    input  logic command_valid,
    output logic command_ready,
    input  logic [1:0] command_source,
    input  logic [9:0] command_source_addr, command_sink_addr,
    output logic response_valid, response_error,
    input  logic response_ready,
    output logic p2_req_valid, p2_req_write,
    output logic [9:0] p2_req_addr,
    input  logic p2_req_ready, p2_rsp_valid,
    input  logic [127:0] p2_rsp_data,
    output logic p2_rsp_ready,
    output logic [2:0] tx_req, tx_take,
    output logic [29:0] tx_addr,
    input  logic [2:0] tx_ready, tx_valid,
    input  logic [383:0] tx_data,
    output logic c0_rx_valid, c0_rx_stored_ready,
    output logic [9:0] c0_rx_addr,
    output logic [127:0] c0_rx_data,
    input  logic c0_rx_reserved, c0_rx_ready, c0_rx_stored
);
    logic p2_tx_req, p2_tx_take, p2_tx_ready, p2_tx_valid;
    logic [9:0] p2_tx_addr;
    logic [127:0] p2_tx_data;

    qwen_sram_port_adapter p2 (
        .clk, .reset,
        .tx_req(p2_tx_req), .tx_take(p2_tx_take), .tx_addr(p2_tx_addr),
        .tx_ready(p2_tx_ready), .tx_valid(p2_tx_valid), .tx_data(p2_tx_data),
        .rx_valid(1'b0), .rx_stored_ready(1'b0), .rx_addr(10'b0), .rx_data(128'b0),
        .rx_ready(), .rx_stored(),
        .io_req_valid(p2_req_valid), .io_req_write(p2_req_write),
        .io_req_addr(p2_req_addr), .io_req_data(),
        .io_req_ready(p2_req_ready), .io_rsp_valid(p2_rsp_valid),
        .io_rsp_data(p2_rsp_data), .io_rsp_ready(p2_rsp_ready)
    );

    qwen_word_switch word_switch (
        .clk, .reset, .command_valid, .command_ready, .command_source,
        .command_sink(1'b0), .command_source_addr, .command_sink_addr,
        .response_valid, .response_error, .response_ready,
        .tx_req({tx_req, p2_tx_req}), .tx_take({tx_take, p2_tx_take}),
        .tx_addr({tx_addr, p2_tx_addr}), .tx_ready({tx_ready, p2_tx_ready}),
        .tx_valid({tx_valid, p2_tx_valid}), .tx_data({tx_data, p2_tx_data}),
        .rx_valid(c0_rx_valid), .rx_stored_ready(c0_rx_stored_ready),
        .rx_addr(c0_rx_addr), .rx_data(c0_rx_data),
        .rx_reserved(c0_rx_reserved), .rx_ready(c0_rx_ready), .rx_stored(c0_rx_stored)
    );
endmodule
