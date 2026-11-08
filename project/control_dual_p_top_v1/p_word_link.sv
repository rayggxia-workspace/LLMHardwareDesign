`timescale 1ns/1ps
// Fixed P0->P1 word and identity, held until a real destination commit is recorded.
module p_word_link(
    input wire clk,reset,
    input wire source_valid,output wire source_ready,
    input wire [9:0] source_address,input wire [127:0] source_data,source_identity,
    input wire destination_reserved,input wire [9:0] destination_reserved_address,
    output wire destination_valid,input wire destination_ready,
    output wire [9:0] destination_address,output wire [127:0] destination_data,
    input wire destination_ack,output wire destination_ack_ready,
    output wire ack_valid,input wire ack_ready,output wire [127:0] ack_identity,
    output wire store_commit,output reg busy
);
    reg sent,committed;
    reg [9:0] address;
    reg [127:0] data,identity;
    assign source_ready=!reset && !busy;
    assign destination_valid=!reset && busy && !sent && destination_reserved &&
        destination_reserved_address==address;
    assign destination_address=address;
    assign destination_data=data;
    assign destination_ack_ready=!reset && busy && sent && !committed;
    assign store_commit=destination_ack && destination_ack_ready;
    assign ack_valid=!reset && busy && committed;
    assign ack_identity=identity;
    always @(posedge clk) begin
        if(reset) begin busy<=0;sent<=0;committed<=0;address<=0;data<=0;identity<=0;end
        else begin
            if(source_valid && source_ready) begin
                busy<=1;sent<=0;committed<=0;
                address<=source_address;data<=source_data;identity<=source_identity;
            end
            if(destination_valid && destination_ready) sent<=1;
            if(store_commit) committed<=1;
            if(ack_valid && ack_ready) begin busy<=0;sent<=0;committed<=0;end
        end
    end
endmodule
