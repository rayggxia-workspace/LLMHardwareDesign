`timescale 1ns/1ps
// Commit the striped output of the three-P FFN through a typed local call.
module ffn_down_store_scope #(
    parameter logic [31:0] TOPOLOGY = 25001
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
    output logic [2:0] s_req_valid,
    input logic [2:0] s_req_ready,
    output logic [9:0] s_req_address,
    input logic [2:0] s_rsp_valid,
    output logic [2:0] s_rsp_ready,
    input logic [2:0][127:0] s_rsp_data,
    input logic [2:0] s_rsp_error,
    output logic wr_valid,
    input logic wr_ready,
    output logic [63:0] wr_address, wr_tag,
    output logic [511:0] wr_data,
    input logic wr_done_valid,
    output logic wr_done_ready,
    input logic [63:0] wr_done_tag,
    input logic wr_done_error
);
    typedef enum logic [1:0] {IDLE, WAIT_DDR, REPORT} state_t;
    state_t state;
    logic writer_ready, writer_done, writer_error, cancelled;
    logic [7:0] committed;
    logic [9:0] sram_words;
    wire [63:0] base = service_descriptor[255:192];
    wire legal = TOPOLOGY!=0 && service_descriptor[127:0]=={TOPOLOGY,32'h02500002,16'd1,16'd128,32'h38534446}
              && service_descriptor[191:128]==0 && service_descriptor[991:320]==0
              && base[5:0]==0 && base<=64'hffff_ffff_ffff_e000
              && service_descriptor[319:256]==(base>>6);
    wire _unused_crc = ^service_descriptor[1023:992]; // LC validates the descriptor CRC.
    wire accept = service_valid && service_ready;
    wire abort_now = service_cancel_valid && service_cancel_ready;
    wire sram_read = |(s_rsp_valid & s_rsp_ready & ~s_rsp_error);
    wire commit = wr_done_valid && wr_done_ready && !wr_done_error &&
                  wr_done_tag==((wr_address>>6));

    assign service_ready = !reset && state==IDLE && writer_ready;
    assign service_cancel_ready = !reset && state==WAIT_DDR;
    assign service_done_valid = !reset && state==REPORT;

    ffn_down_store #(.TAG_BY_ADDRESS(1'b1)) writer(
        .clk,.reset,.launch_valid(accept&&legal),.launch_ready(writer_ready),.launch_base(base),
        .done_valid(writer_done),.done_error(writer_error),.done_ready(state==WAIT_DDR),
        .s_req_valid,.s_req_ready,.s_req_address,.s_rsp_valid,.s_rsp_ready,.s_rsp_data,.s_rsp_error,
        .wr_valid,.wr_ready,.wr_address,.wr_tag,.wr_data,
        .wr_done_valid,.wr_done_ready,.wr_done_tag,.wr_done_error);

    always_ff @(posedge clk) begin
        if(reset) begin
            state<=IDLE;
            cancelled<=0;
            committed<=0;
            sram_words<=0;
            service_done_owner<=0;
            service_done_ticket<=0;
            service_done_status<=0;
            service_done_read_bytes<=0;
            service_done_write_bytes<=0;
        end else begin
            if(abort_now) cancelled<=1;
            if(commit) committed<=committed+1'b1;
            if(sram_read) sram_words<=sram_words+1'b1;
            case(state)
                IDLE: if(accept) begin
                    service_done_owner<=service_owner;
                    service_done_ticket<=service_ticket;
                    service_done_status<=legal ? 0 : 16'h0200;
                    service_done_read_bytes<=0;
                    service_done_write_bytes<=0;
                    committed<=0;
                    sram_words<=0;
                    cancelled<=0;
                    state<=legal ? WAIT_DDR : REPORT;
                end
                WAIT_DDR: if(writer_done) begin
                    service_done_status<=writer_error || committed!=8'd128 || sram_words!=10'd512 ? 16'h0202 :
                                         cancelled || abort_now ? 16'h0201 : 16'd0;
                    service_done_read_bytes<=32'(sram_words)*16;
                    service_done_write_bytes<=32'(committed)*64;
                    state<=REPORT;
                end
                REPORT: if(service_done_ready) state<=IDLE;
                default: state<=IDLE;
            endcase
        end
    end
endmodule

