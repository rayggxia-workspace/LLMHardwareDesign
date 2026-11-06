// Qwen candidate transport using one active word transfer per cycle sequence.
// Endpoint IDs: P0 P1 P2 U0 U1 C0 F0 J0 J1. The controller owns reservations.
// P/J ports are their first native SRAM request/response ports.
module qwen_nine_transport (
    input  logic clk, reset,
    input  logic command_valid,
    output logic command_ready,
    input  logic [3:0] command_source, command_sink,
    input  logic [9:0] command_source_addr, command_sink_addr,
    output logic response_valid, response_error,
    input  logic response_ready,
    input  logic [8:0] sink_reserved,
    output logic [4:0] pj_req_valid, pj_req_write, pj_rsp_ready,
    output logic [49:0] pj_req_addr,
    output logic [639:0] pj_req_data,
    input  logic [4:0] pj_req_ready, pj_rsp_valid,
    input  logic [639:0] pj_rsp_data,
    output logic [3:0] ucf_tx_req, ucf_tx_take,
    output logic [39:0] ucf_tx_addr,
    input  logic [3:0] ucf_tx_ready, ucf_tx_valid,
    input  logic [511:0] ucf_tx_data,
    output logic [3:0] ucf_rx_valid, ucf_rx_stored_ready,
    output logic [39:0] ucf_rx_addr,
    output logic [511:0] ucf_rx_data,
    input  logic [3:0] ucf_rx_ready, ucf_rx_stored
);
    // Row-major mask of the 23 directed Qwen relations in PR #176.
    localparam logic [80:0] QWEN_ALLOWED = 81'h8084090382213fa08214;
    logic [8:0] tx_req, tx_take, tx_ready, tx_valid;
    logic [89:0] tx_addr;
    logic [1151:0] tx_data;
    logic [8:0] rx_valid, rx_ready, rx_stored, rx_stored_ready;
    logic [89:0] rx_addr;
    logic [1151:0] rx_data;

    for (genvar i = 0; i < 5; i++) begin : native_pj
        localparam integer ID = i < 3 ? i : i+4;
        qwen_sram_port_adapter port_adapter (
            .clk, .reset, .tx_req(tx_req[ID]), .tx_take(tx_take[ID]),
            .tx_addr(tx_addr[10*ID+:10]), .tx_ready(tx_ready[ID]), .tx_valid(tx_valid[ID]),
            .tx_data(tx_data[128*ID+:128]),
            .rx_valid(rx_valid[ID]), .rx_stored_ready(rx_stored_ready[ID]),
            .rx_addr(rx_addr[10*ID+:10]), .rx_data(rx_data[128*ID+:128]),
            .rx_ready(rx_ready[ID]), .rx_stored(rx_stored[ID]),
            .io_req_valid(pj_req_valid[i]), .io_req_write(pj_req_write[i]),
            .io_req_addr(pj_req_addr[10*i+:10]), .io_req_data(pj_req_data[128*i+:128]),
            .io_req_ready(pj_req_ready[i]), .io_rsp_valid(pj_rsp_valid[i]),
            .io_rsp_data(pj_rsp_data[128*i+:128]), .io_rsp_ready(pj_rsp_ready[i])
        );
    end
    assign ucf_tx_req = tx_req[6:3];
    assign ucf_tx_take = tx_take[6:3];
    assign ucf_tx_addr = tx_addr[30+:40];
    assign tx_ready[6:3] = ucf_tx_ready;
    assign tx_valid[6:3] = ucf_tx_valid;
    assign tx_data[384+:512] = ucf_tx_data;
    assign ucf_rx_valid = rx_valid[6:3];
    assign ucf_rx_stored_ready = rx_stored_ready[6:3];
    assign ucf_rx_addr = rx_addr[30+:40];
    assign ucf_rx_data = rx_data[384+:512];
    assign rx_ready[6:3] = ucf_rx_ready;
    assign rx_stored[6:3] = ucf_rx_stored;

    qwen_word_switch #(.SOURCES(9), .SINKS(9), .ALLOWED(QWEN_ALLOWED)) word_switch (
        .clk, .reset, .command_valid, .command_ready, .command_source, .command_sink,
        .command_source_addr, .command_sink_addr, .response_valid, .response_error,
        .response_ready, .tx_req, .tx_take, .tx_addr, .tx_ready, .tx_valid, .tx_data,
        .rx_valid, .rx_stored_ready, .rx_addr, .rx_data, .rx_reserved(sink_reserved),
        .rx_ready, .rx_stored
    );
endmodule
