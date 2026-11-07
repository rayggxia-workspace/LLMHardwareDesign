`timescale 1ns/1ps
// One outstanding 16-byte transaction. Reset invalidates protocol state, not RAM.
module control_pm #(
    parameter integer BYTES=16384,
    parameter bit USE_SRAM=1'b1
)(
    input wire clk_i,rst_ni,
    input wire req_valid_i,req_write_i,
    input wire [13:0] req_address_i,
    input wire [127:0] req_data_i,
    output wire req_ready_o,
    output wire rsp_valid_o,
    input wire rsp_ready_i,
    output wire [127:0] rsp_data_o,
    output wire rsp_error_o
);
    localparam [1:0] IDLE=0,ISSUE=1,WAIT=2,RESPOND=3;
    reg [1:0] state;
    reg write_hold,error_hold;
    reg [9:0] address_hold;
    reg [127:0] data_hold,response_hold;
    wire memory_ready,memory_valid;
    wire [127:0] memory_data;
    wire memory_request=rst_ni && state==ISSUE;
    wire memory_take=rst_ni && state==WAIT;
    assign req_ready_o=rst_ni && state==IDLE;
    assign rsp_valid_o=rst_ni && state==RESPOND;
    assign rsp_data_o=response_hold;
    assign rsp_error_o=error_hold;
    generate if(USE_SRAM) begin: sram
        block_feed_s16k_sram #(.ECHO_WRITE_DATA(1'b0)) storage(
            .clk(clk_i),.reset(!rst_ni),.req(memory_request),.wr(write_hold),
            .addr(address_hold),.din(data_hold),.ready(memory_ready),
            .valid(memory_valid),.take(memory_take),.dout(memory_data),
            .wide_req(1'b0),.wide_addr(8'b0),.wide_ready(),.wide_valid(),
            .wide_take(1'b0),.wide_dout());
    end else begin: inferred
        // No initial values or reset loop: infer storage, not a resettable FF bank.
        reg [127:0] memory[0:BYTES/16-1];
        reg valid;
        reg [127:0] response;
        assign memory_ready=rst_ni && !valid;
        assign memory_valid=rst_ni && valid;
        assign memory_data=response;
        always @(posedge clk_i) begin
            if(!rst_ni) begin valid<=0;response<=0;end
            else begin
                if(memory_request && memory_ready) begin
                    valid<=1;
                    if(write_hold) begin memory[address_hold]<=data_hold;response<=0;end
                    else response<=memory[address_hold];
                end
                if(valid && memory_take)valid<=0;
            end
        end
    end endgenerate
    always @(posedge clk_i) begin
        if(!rst_ni) begin state<=IDLE;write_hold<=0;address_hold<=0;data_hold<=0;response_hold<=0;error_hold<=0;end
        else case(state)
            IDLE:if(req_valid_i && req_ready_o)begin
                write_hold<=req_write_i;address_hold<=req_address_i[13:4];data_hold<=req_data_i;
                response_hold<=0;
                error_hold<=req_address_i[3:0]!=0 || {18'b0,req_address_i}+32'd16>BYTES;
                state<=req_address_i[3:0]!=0 || {18'b0,req_address_i}+32'd16>BYTES ? RESPOND : ISSUE;
            end
            ISSUE:if(memory_ready)state<=WAIT;
            WAIT:if(memory_valid)begin response_hold<=memory_data;state<=RESPOND;end
            RESPOND:if(rsp_ready_i)state<=IDLE;
        endcase
    end
endmodule
