`timescale 1ns/1ps
// A typed LC provider for one K/V or activation row. The selected S128 window stays
// leased until the last accepted write commits or the transport drains on error.
module s128_kv_store_scope #(
    parameter logic [31:0] TOPOLOGY = 0,
    parameter bit ACTIVATION_ROW = 1'b0,
    parameter bit ACTIVATION_SPAN = 1'b0,
    parameter bit SHARED_STORE = 1'b0,
    parameter bit COUNTED_STORE = 1'b0
) (
    input logic clk, reset,
    input logic service_valid,
    output logic service_ready,
    input logic [127:0] service_owner,
    input logic [31:0] service_ticket,
    input logic [1023:0] service_descriptor,
    input logic service_cancel_valid,
    output logic service_cancel_ready,
    output logic service_done_valid,
    input logic service_done_ready,
    output logic [127:0] service_done_owner,
    output logic [31:0] service_done_ticket,
    output logic [15:0] service_done_status,
    output logic [31:0] service_done_read_bytes, service_done_write_bytes,

    output wire s_req_valid,
    input wire s_req_ready,
    output wire [9:0] s_req_address,
    input wire s_rsp_valid,
    output wire s_rsp_ready,
    input wire [127:0] s_rsp_data,
    input wire s_rsp_error,
    output wire wr_valid,
    input wire wr_ready,
    output wire [63:0] wr_address, wr_tag,
    output wire [511:0] wr_data,
    input wire wr_done_valid,
    output wire wr_done_ready,
    input wire [63:0] wr_done_tag,
    input wire wr_done_error
);
    localparam logic [31:0] KV_SCHEMA = 32'h3152564b;
    localparam logic [31:0] ROW_SCHEMA = 32'h38535744;
    localparam logic [31:0] SPAN_SCHEMA = 32'h31535744;
    localparam logic [31:0] ABI = 32'h02500002;
    localparam int MAX_BURSTS = ACTIVATION_ROW || SHARED_STORE || COUNTED_STORE ? 128 : 8;
    localparam logic [15:0] STORE_K = 1, STORE_V = 2;
    localparam logic [15:0] BAD_DESCRIPTOR = 16'h0200, ABORTED = 16'h0201, TRANSFER_FAULT = 16'h0202;
    typedef enum logic [1:0] {IDLE, WAIT_ROW, REPORT} state_t;
    state_t state;
    logic cancelled;
    logic [63:0] expected_tag;

    wire [31:0] schema = service_descriptor[31:0];
    wire is_kv = schema == KV_SCHEMA;
    wire is_row = schema == ROW_SCHEMA;
    wire is_span = schema == SPAN_SCHEMA;
    wire is_counted = schema == 32'h31435344; // DSC1
    wire supported_schema = (is_counted && COUNTED_STORE) || (is_kv && (SHARED_STORE || !(ACTIVATION_ROW || ACTIVATION_SPAN))) ||
                            (is_row && (SHARED_STORE || ACTIVATION_ROW)) ||
                            (is_span && (SHARED_STORE || ACTIVATION_SPAN));
    wire [15:0] counted_bursts = service_descriptor[159:144];
    wire [8:0] bursts = is_counted ? counted_bursts[8:0] : is_row ? 9'd128 : 9'd8;
    wire [15:0] operation = service_descriptor[63:48];
    wire [15:0] source_word = service_descriptor[143:128];
    wire [63:0] ddr_address = service_descriptor[255:192];
    wire [63:0] first_tag = service_descriptor[319:256];
    wire valid_descriptor = TOPOLOGY != 0 && !(ACTIVATION_ROW && ACTIVATION_SPAN) &&
        supported_schema && service_descriptor[47:32] == 16'd128 &&
        (operation == STORE_K || (is_kv && operation == STORE_V)) &&
        service_descriptor[95:64] == ABI && service_descriptor[127:96] == TOPOLOGY &&
        (is_counted ? (counted_bursts>=1 && counted_bursts<=128 && service_descriptor[191:160]=='0) : service_descriptor[191:144]=='0) && service_descriptor[991:320] == '0 &&
        {1'b0,source_word}+{6'd0,bursts,2'b00} <= 17'd1024 && ddr_address[5:0] == 0 &&
        ddr_address <= 64'd0-(64'(bursts)<<6) && first_tag <= 64'd0-64'(bursts);
    // The LC fetch checks the descriptor CRC.
    wire _unused_crc = ^service_descriptor[1023:992];

    wire row_ready, row_busy, row_done_valid, row_done_error;
    wire [63:0] row_done_tag;
    wire burst_valid, burst_ready, burst_done_valid, burst_done_ready, burst_done_error;
    wire [9:0] burst_word;
    wire [63:0] burst_address, burst_tag, burst_done_tag;
    wire accept = service_valid && service_ready;
    wire abort_now = service_cancel_valid && service_cancel_ready;

    assign service_ready = !reset && state == IDLE && row_ready;
    assign service_done_valid = !reset && state == REPORT;
    // Once issued, an entire row drains through physical completions. A
    // cancellation during REPORT is accepted with the settled terminal held.
    assign service_cancel_ready = !reset && state != IDLE;

    s128_kv_row_transfer #(.BURSTS(MAX_BURSTS), .VARIABLE_BURSTS(SHARED_STORE || COUNTED_STORE)) row(
        .clk, .reset, .cmd_valid(accept && valid_descriptor), .cmd_ready(row_ready), .busy(row_busy),
        .cmd_bursts(bursts), .cmd_sram_word(source_word[9:0]), .cmd_ddr_address(ddr_address), .cmd_tag(first_tag),
        .done_valid(row_done_valid), .done_ready(state == WAIT_ROW), .done_tag(row_done_tag),
        .done_error(row_done_error), .burst_valid, .burst_ready,
        .burst_sram_word(burst_word), .burst_ddr_address(burst_address), .burst_tag,
        .burst_done_valid, .burst_done_ready, .burst_done_tag, .burst_done_error);
    wire _unused_busy = row_busy;

    s128_ddr64_store burst(
        .clk, .reset, .cmd_valid(burst_valid), .cmd_ready(burst_ready),
        .cmd_source_word(burst_word), .cmd_ddr_address(burst_address), .cmd_tag(burst_tag),
        .done_valid(burst_done_valid), .done_ready(burst_done_ready), .done_tag(burst_done_tag),
        .done_error(burst_done_error),
        .s_req_valid, .s_req_ready, .s_req_address, .s_rsp_valid, .s_rsp_ready, .s_rsp_data, .s_rsp_error,
        .wr_valid, .wr_ready, .wr_address, .wr_tag, .wr_data,
        .wr_done_valid, .wr_done_ready, .wr_done_tag, .wr_done_error);

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            cancelled <= 0;
            expected_tag <= 0;
            service_done_owner <= 0;
            service_done_ticket <= 0;
            service_done_status <= 0;
            service_done_read_bytes <= 0;
            service_done_write_bytes <= 0;
        end else begin
            case (state)
                IDLE: if (accept) begin
                    service_done_owner <= service_owner;
                    service_done_ticket <= service_ticket;
                    service_done_status <= valid_descriptor ? 16'd0 : BAD_DESCRIPTOR;
                    service_done_read_bytes <= 0;
                    service_done_write_bytes <= 0;
                    expected_tag <= first_tag;
                    cancelled <= 0;
                    state <= valid_descriptor ? WAIT_ROW : REPORT;
                end
                WAIT_ROW: begin
                    if (abort_now) cancelled <= 1;
                    if (s_rsp_valid && s_rsp_ready && !s_rsp_error)
                        service_done_read_bytes <= service_done_read_bytes + 32'd16;
                    if (burst_done_valid && burst_done_ready && !burst_done_error && burst_done_tag == burst_tag)
                        service_done_write_bytes <= service_done_write_bytes + 32'd64;
                    if (row_done_valid) begin
                        if (row_done_error || row_done_tag != expected_tag) service_done_status <= TRANSFER_FAULT;
                        else if (cancelled || abort_now) service_done_status <= ABORTED;
                        state <= REPORT;
                    end
                end
                REPORT: if (service_done_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
