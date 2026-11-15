`timescale 1ns/1ps
// Drive the existing E32 ADD2 word service from a fetched LC descriptor.
// Partial destination overlap is rejected. Exact in-place ADD2 is permitted.
module s32_add_scope #(
    parameter logic [31:0] SCHEMA=0, PROVIDER_ABI=0, TOPOLOGY=0,
    parameter logic [15:0] OPERATION=0
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

    output logic word_valid,
    input logic word_ready,
    output logic [9:0] word_left, word_right, word_destination,
    output logic [31:0] word_tag,
    input logic word_done_valid,
    output logic word_done_ready,
    input logic [31:0] word_done_tag,
    input logic word_error,
    input logic [3:0] word_clipped
);
    localparam logic [15:0] BAD_DESCRIPTOR=16'h0200, ABORTED=16'h0201,
                            WORD_FAULT=16'h0202, CLIPPED=16'h0203;
    typedef enum logic [1:0] {IDLE, OFFER, WAIT_WORD, REPORT} state_t;
    state_t state;
    logic [9:0] left_base, right_base, destination_base, index;
    logic [10:0] words_left;
    logic cancelled;

    wire [15:0] left = service_descriptor[143:128];
    wire [15:0] right = service_descriptor[159:144];
    wire [15:0] destination = service_descriptor[175:160];
    wire [15:0] count = service_descriptor[191:176];
    wire [16:0] left_end = {1'b0,left} + {1'b0,count};
    wire [16:0] right_end = {1'b0,right} + {1'b0,count};
    wire [16:0] destination_end = {1'b0,destination} + {1'b0,count};
    wire left_alias = left != destination &&
                      {1'b0,left} < destination_end && {1'b0,destination} < left_end;
    wire right_alias = right != destination &&
                       {1'b0,right} < destination_end && {1'b0,destination} < right_end;
    wire valid_descriptor = SCHEMA!=0 && PROVIDER_ABI!=0 && TOPOLOGY!=0 && OPERATION!=0 &&
        service_descriptor[31:0]==SCHEMA && service_descriptor[47:32]==16'd128 &&
        service_descriptor[63:48]==OPERATION && service_descriptor[95:64]==PROVIDER_ABI &&
        service_descriptor[127:96]==TOPOLOGY && service_descriptor[991:192]=='0 &&
        count!=0 && left_end<=17'd1024 && right_end<=17'd1024 && destination_end<=17'd1024 &&
        !left_alias && !right_alias;
    wire abort_now = service_cancel_valid && service_cancel_ready;
    // The LC validates this field while fetching the entire record.
    wire _unused_crc = ^service_descriptor[1023:992];

    assign service_ready = !reset && state==IDLE;
    assign service_cancel_ready = !reset && (state==OFFER || state==WAIT_WORD) && !cancelled;
    assign service_done_valid = !reset && state==REPORT;
    assign word_valid = !reset && state==OFFER;
    assign word_done_ready = !reset && state==WAIT_WORD;
    assign word_left = left_base + index;
    assign word_right = right_base + index;
    assign word_destination = destination_base + index;
    assign word_tag = {22'd0,index};

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            left_base <= 0;
            right_base <= 0;
            destination_base <= 0;
            index <= 0;
            words_left <= 0;
            cancelled <= 0;
            service_done_owner <= 0;
            service_done_ticket <= 0;
            service_done_status <= 0;
            service_done_read_bytes <= 0;
            service_done_write_bytes <= 0;
        end else begin
            if (abort_now) cancelled <= 1;
            case (state)
                IDLE: if (service_valid && service_ready) begin
                    service_done_owner <= service_owner;
                    service_done_ticket <= service_ticket;
                    service_done_status <= valid_descriptor ? 16'd0 : BAD_DESCRIPTOR;
                    service_done_read_bytes <= 0;
                    service_done_write_bytes <= 0;
                    left_base <= left[9:0];
                    right_base <= right[9:0];
                    destination_base <= destination[9:0];
                    words_left <= count[10:0];
                    index <= 0;
                    cancelled <= 0;
                    state <= valid_descriptor ? OFFER : REPORT;
                end
                OFFER: if (word_valid && word_ready) state <= WAIT_WORD;
                WAIT_WORD: if (word_done_valid && word_done_ready) begin
                    if (word_done_tag!=word_tag || word_error) begin
                        service_done_status <= WORD_FAULT;
                        state <= REPORT;
                    end else begin
                        service_done_read_bytes <= service_done_read_bytes + 32;
                        service_done_write_bytes <= service_done_write_bytes + 16;
                        if (cancelled || abort_now || word_clipped!=0 || words_left==1) begin
                            if (cancelled || abort_now) service_done_status <= ABORTED;
                            else if (word_clipped!=0) service_done_status <= CLIPPED;
                            state <= REPORT;
                        end else begin
                            index <= index + 1'b1;
                            words_left <= words_left - 1'b1;
                            state <= OFFER;
                        end
                    end
                end
                REPORT: if (service_done_valid && service_done_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
