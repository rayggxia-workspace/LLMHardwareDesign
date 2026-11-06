// P/J SRAM request/response port to the same word protocol as U/C/F.
// A write response means the destination SRAM has committed the word.
module qwen_sram_port_adapter (
    input  logic clk, reset,
    input  logic tx_req, tx_take,
    input  logic [9:0] tx_addr,
    output logic tx_ready, tx_valid,
    output logic [127:0] tx_data,
    input  logic rx_valid, rx_stored_ready,
    input  logic [9:0] rx_addr,
    input  logic [127:0] rx_data,
    output logic rx_ready, rx_stored,
    output logic io_req_valid, io_req_write,
    output logic [9:0] io_req_addr,
    output logic [127:0] io_req_data,
    input  logic io_req_ready, io_rsp_valid,
    input  logic [127:0] io_rsp_data,
    output logic io_rsp_ready
);
    logic outstanding, was_write;

    always_comb begin
        io_req_valid = !reset && !outstanding && (rx_valid || tx_req);
        io_req_write = rx_valid;
        io_req_addr = rx_valid ? rx_addr : tx_addr;
        io_req_data = rx_data;
        tx_ready = !reset && !outstanding && !rx_valid && io_req_ready;
        rx_ready = !reset && !outstanding && io_req_ready;
        tx_valid = !reset && outstanding && !was_write && io_rsp_valid;
        rx_stored = !reset && outstanding && was_write && io_rsp_valid;
        tx_data = io_rsp_data;
        io_rsp_ready = !reset && outstanding && (was_write ? rx_stored_ready : tx_take);
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            outstanding <= 1'b0;
            was_write <= 1'b0;
        end else if (io_req_valid && io_req_ready) begin
            outstanding <= 1'b1;
            was_write <= io_req_write;
        end else if (io_rsp_valid && io_rsp_ready) begin
            outstanding <= 1'b0;
        end
    end
endmodule
