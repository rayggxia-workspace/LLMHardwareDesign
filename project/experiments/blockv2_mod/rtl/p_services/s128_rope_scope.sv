`timescale 1ns/1ps
// Typed resident RoPE dispatch. Completion follows the last acknowledged S128 write.
module s128_rope_scope #(
    parameter logic [31:0] TOPOLOGY = 0
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
    output logic s_req_valid,
    input logic s_req_ready,
    output logic s_req_write,
    output logic [9:0] s_req_address,
    output logic [127:0] s_req_data,
    input logic s_rsp_valid,
    output logic s_rsp_ready,
    input logic [127:0] s_rsp_data,
    input logic s_rsp_error
);
    localparam logic [31:0] SCHEMA=32'h31455052, ABI=32'h02500002;
    localparam logic [15:0] OPERATION=1, BAD_DESCRIPTOR=16'h0230, ABORTED=16'h0231, SERVICE_FAULT=16'h0232;
    typedef enum logic [1:0] {IDLE, ACTIVE, REPORT} state_t;
    state_t state;
    logic cancelled, pending_write;
    wire [15:0] source=service_descriptor[143:128], cosine=service_descriptor[159:144];
    wire [15:0] sine=service_descriptor[175:160], destination=service_descriptor[191:176];
    wire [47:0] shifts=service_descriptor[239:192];

    function automatic logic overlap(input logic [15:0] a, b);
        return {1'b0,a} < {1'b0,b}+17'd32 && {1'b0,b} < {1'b0,a}+17'd32;
    endfunction

    function automatic logic valid_precision(input logic [79:0] data);
        int signed fields[10];
        logic valid;
        for (int i=0; i<10; i++) fields[i]=int'($signed(data[8*i+:8]));
        valid=1'b1;
        for (int i=0; i<6; i++) valid=valid && fields[i]>=-63 && fields[i]<=63;
        return valid && fields[9]==-14 &&
               fields[6]+fields[9]+fields[0]==fields[8] &&
               fields[1]+fields[2]==0 &&
               fields[6]+fields[9]+fields[3]+fields[4]==fields[8] &&
               fields[8]+fields[5]==fields[7];
    endfunction

    wire valid_descriptor=TOPOLOGY!=0 && service_descriptor[31:0]==SCHEMA &&
        service_descriptor[47:32]==16'd128 && service_descriptor[63:48]==OPERATION &&
        service_descriptor[95:64]==ABI && service_descriptor[127:96]==TOPOLOGY &&
        service_descriptor[991:272]=='0 && valid_precision(service_descriptor[271:192]) &&
        source<=992 && cosine<=992 && sine<=992 && destination<=992 &&
        !overlap(source,cosine) && !overlap(source,sine) && !overlap(source,destination) &&
        !overlap(cosine,sine) && !overlap(cosine,destination) && !overlap(sine,destination);
    // The native LC already checked the descriptor CRC on the fetched bytes.
    wire _unused_crc=^service_descriptor[1023:992];
    wire row_ready,row_done,row_error;
    wire [31:0] row_tag;
    wire cancel=service_cancel_valid && service_cancel_ready;
    wire accept=service_valid && service_ready;
    wire ack=s_rsp_valid && s_rsp_ready && !s_rsp_error;
    wire [31:0] reads=service_done_read_bytes+(ack && !pending_write ? 32'd16 : 32'd0);
    wire [31:0] writes=service_done_write_bytes+(ack && pending_write ? 32'd16 : 32'd0);

    assign service_ready=!reset && state==IDLE && row_ready;
    assign service_cancel_ready=!reset && state==ACTIVE && !cancelled;
    assign service_done_valid=!reset && state==REPORT;

    s128_rope_leased_row row(
        .clk,.reset,.cmd_valid(accept && valid_descriptor),.cmd_ready(row_ready),.busy(),
        .cmd_source(source[9:0]),.cmd_cos(cosine[9:0]),.cmd_sin(sine[9:0]),
        .cmd_dest(destination[9:0]),.cmd_shifts(shifts),.cmd_tag(service_ticket),
        .done_valid(row_done),.done_ready(state==ACTIVE),.done_tag(row_tag),.done_error(row_error),
        .s_req_valid,.s_req_ready,.s_req_write,.s_req_address,.s_req_data,
        .s_rsp_valid,.s_rsp_ready,.s_rsp_data,.s_rsp_error);

    always_ff @(posedge clk) begin
        if (reset) begin
            state<=IDLE;
            cancelled<=0;
            pending_write<=0;
            service_done_owner<=0;
            service_done_ticket<=0;
            service_done_status<=0;
            service_done_read_bytes<=0;
            service_done_write_bytes<=0;
        end else begin
            case (state)
                IDLE: if (accept) begin
                    cancelled<=0;
                    pending_write<=0;
                    service_done_owner<=service_owner;
                    service_done_ticket<=service_ticket;
                    service_done_status<=valid_descriptor ? 16'd0 : BAD_DESCRIPTOR;
                    service_done_read_bytes<=0;
                    service_done_write_bytes<=0;
                    state<=valid_descriptor ? ACTIVE : REPORT;
                end
                ACTIVE: begin
                    if (cancel) cancelled<=1;
                    if (s_req_valid && s_req_ready) pending_write<=s_req_write;
                    service_done_read_bytes<=reads;
                    service_done_write_bytes<=writes;
                    if (row_done) begin
                        if (row_error || row_tag!=service_done_ticket || reads!=2048 || writes!=512)
                            service_done_status<=SERVICE_FAULT;
                        else if (cancelled || cancel)
                            service_done_status<=ABORTED;
                        state<=REPORT;
                    end
                end
                REPORT: if (service_done_ready) state<=IDLE;
                default: state<=IDLE;
            endcase
        end
    end
endmodule
