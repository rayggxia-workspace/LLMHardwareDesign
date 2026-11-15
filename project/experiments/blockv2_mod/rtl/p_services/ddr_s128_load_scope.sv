`timescale 1ns/1ps
// Typed LC provider for one DDR-backed 512-byte or 8 KiB SRAM window.
module ddr_s128_load_scope #(
    parameter logic [31:0] TOPOLOGY = 0,
    parameter int PAYLOAD_BYTES = 8192,
    parameter bit LOCAL_DMA_SEQUENCE = 0
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

    output logic rd_valid,
    input logic rd_ready,
    output logic [63:0] rd_address, rd_tag,
    input logic rd_rsp_valid,
    output logic rd_rsp_ready,
    input logic [63:0] rd_rsp_tag,
    input logic [511:0] rd_rsp_data,
    input logic rd_rsp_error,

    output logic s_valid,
    input logic s_ready,
    output logic [9:0] s_address,
    output logic [127:0] s_data,
    output logic [31:0] s_tag,
    input logic s_rsp_valid,
    output logic s_rsp_ready,
    input logic [31:0] s_rsp_tag,
    input logic s_rsp_error
);
    localparam bit ROW512 = PAYLOAD_BYTES == 512;
    localparam logic [31:0] SCHEMA = ROW512 ? 32'h314c5244 : 32'h384c5244;
    localparam logic [31:0] ABI = 32'h02500002;
    localparam logic [15:0] BAD_DESCRIPTOR = 16'h0220, ABORTED = 16'h0221,
                            TRANSFER_FAULT = 16'h0222, SEQUENCE_EXHAUSTED = 16'h0223;
    typedef enum logic [1:0] {IDLE, ACTIVE, REPORT} state_t;
    state_t state;
    logic cancelled;
    logic [9:0] destination;
    logic launch_ready, done_valid, done_error;
    logic [63:0] loader_read_tag;
    logic [8:0] loader_address;
    // A physical client may serve multiple LCs with independent ticket
    // namespaces. Each command owns 128 serials on the 31-bit DMA interface.
    logic [23:0] dma_sequence;
    wire exhausted = LOCAL_DMA_SEQUENCE && (&dma_sequence);

    wire [15:0] destination_word = service_descriptor[143:128];
    wire [63:0] source_base = service_descriptor[255:192];
    wire valid_descriptor = (ROW512 || PAYLOAD_BYTES==8192) && TOPOLOGY!=0 && service_descriptor[31:0]==SCHEMA &&
        service_descriptor[47:32]==16'd128 && service_descriptor[63:48]==16'd1 &&
        service_descriptor[95:64]==ABI && service_descriptor[127:96]==TOPOLOGY &&
        service_descriptor[191:144]=='0 && service_descriptor[991:256]=='0 &&
        destination_word<=(ROW512 ? 16'd992 : 16'd512) && source_base[5:0]==0 &&
        source_base<=(ROW512 ? 64'hffff_ffff_ffff_fe00 : 64'hffff_ffff_ffff_e000);
    // The LC validates the CRC while fetching the record.
    wire _unused_crc = ^service_descriptor[1023:992];
    wire accept = service_valid && service_ready;
    wire launch = accept && valid_descriptor && !exhausted;
    wire abort_now = service_cancel_valid && service_cancel_ready;
    wire read_matched = !rd_rsp_error && rd_rsp_tag==rd_tag;
    wire write_matched = !s_rsp_error && s_rsp_tag==s_tag;

    assign service_ready = !reset && state==IDLE && launch_ready;
    assign service_done_valid = !reset && state==REPORT;
    // Drain the admitted transfer, including a held SRAM write, before abort.
    // Accept a late cancel while holding the already settled terminal.
    assign service_cancel_ready = !reset && state!=IDLE;
    assign rd_tag = {25'd0,(LOCAL_DMA_SEQUENCE ? {8'd0,dma_sequence} : service_done_ticket),7'd0} | loader_read_tag;
    generate if (ROW512) begin: row
        wire _unused=^{destination,loader_address};
        assign loader_address='0;
        s128_ddr_range_load loader(
            .clk,.reset,.launch_valid(launch),.launch_ready(launch_ready),
            .launch_base(source_base),.launch_s_base(destination_word[9:0]),.launch_bursts(8'd8),
            .launch_pair(1'b0),.launch_pair_beat(1'b0),.launch_pair_high(1'b0),
            .done_valid,.done_error,.done_ready(state==ACTIVE),
            .rd_valid,.rd_ready,.rd_address,.rd_tag(loader_read_tag),.rd_rsp_valid,.rd_rsp_ready,
            .rd_rsp_tag(read_matched ? loader_read_tag : loader_read_tag ^ 64'd1),.rd_rsp_data,
            .s_valid,.s_ready,.s_address,.s_data,.s_tag,.s_rsp_valid,.s_rsp_ready,
            .s_rsp_tag(s_rsp_error ? s_tag ^ 32'd1 : s_rsp_tag));
    end else begin: tile
        assign s_address = destination + {1'b0,loader_address};
        ffn_x_ddr_load #(.RELEASE_ON_ERROR(1'b1)) loader(
            .clk,.reset,.launch_valid(launch),.launch_ready,.launch_base(source_base),
            .done_valid,.done_error,.done_ready(state==ACTIVE),
            .rd_valid,.rd_ready,.rd_address,.rd_tag(loader_read_tag),.rd_rsp_valid,.rd_rsp_ready,
            .rd_rsp_tag(read_matched ? loader_read_tag : loader_read_tag ^ 64'd1),.rd_rsp_data,
            .s_valid,.s_ready,.s_address(loader_address),.s_data,.s_tag,.s_rsp_valid,.s_rsp_ready,
            .s_rsp_tag(s_rsp_error ? s_tag ^ 32'd1 : s_rsp_tag));
    end endgenerate

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            dma_sequence <= 0;
            cancelled <= 0;
            destination <= 0;
            service_done_owner <= 0;
            service_done_ticket <= 0;
            service_done_status <= 0;
            service_done_read_bytes <= 0;
            service_done_write_bytes <= 0;
        end else begin
            case (state)
                IDLE: if (accept) begin
                    cancelled <= 0;
                    destination <= destination_word[9:0];
                    service_done_owner <= service_owner;
                    service_done_ticket <= service_ticket;
                    service_done_status <= !valid_descriptor ? BAD_DESCRIPTOR :
                                           exhausted ? SEQUENCE_EXHAUSTED : 16'd0;
                    service_done_read_bytes <= 0;
                    service_done_write_bytes <= 0;
                    if (launch && LOCAL_DMA_SEQUENCE) dma_sequence <= dma_sequence + 1'b1;
                    state <= launch ? ACTIVE : REPORT;
                end
                ACTIVE: begin
                    if (abort_now) cancelled <= 1;
                    if (rd_rsp_valid && rd_rsp_ready && read_matched)
                        service_done_read_bytes <= service_done_read_bytes + 32'd64;
                    if (s_rsp_valid && s_rsp_ready && write_matched)
                        service_done_write_bytes <= service_done_write_bytes + 32'd16;
                    if (done_valid) begin
                        if (done_error) service_done_status <= TRANSFER_FAULT;
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
