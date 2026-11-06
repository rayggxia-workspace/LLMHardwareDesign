// One destination reservation and one outstanding P16 SRAM-word transfer.
// P1 holds its read response until the actual P0 write response is accepted.
module ffn_copy (
    input wire clk, reset, start,
    input wire [9:0] source_word, dest_word,
    output wire ready, done,
    output wire source_req, input wire source_ready,
    output reg [9:0] source_addr,
    input wire source_rsp, output wire source_take,
    input wire [127:0] source_data,
    output wire dest_req, input wire dest_ready,
    output reg [9:0] dest_addr,
    output wire [127:0] dest_data,
    input wire dest_rsp, output wire dest_take,
    input wire allow_ack
);
    localparam IDLE=0, READ=1, WRITE=2, ACK=3, RELEASE=4;
    reg [2:0] state;
    assign ready=state==IDLE && !reset;
    assign source_req=state==READ && !reset;
    assign dest_req=state==WRITE && source_rsp && !reset;
    assign dest_data=source_data;
    assign dest_take=state==ACK && allow_ack && !reset;
    assign source_take=state==RELEASE && !reset;
    assign done=source_take && source_rsp;
    always @(posedge clk) begin
        if(reset) state<=IDLE;
        else case(state)
            IDLE: if(start) begin
                source_addr<=source_word;
                dest_addr<=dest_word;
                state<=READ;
            end
            READ: if(source_ready) state<=WRITE;
            WRITE: if(dest_req && dest_ready) state<=ACK;
            ACK: if(dest_rsp && dest_take) state<=RELEASE;
            RELEASE: if(source_rsp) state<=IDLE;
            default: state<=IDLE;
        endcase
    end
endmodule
