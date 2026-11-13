// Native adapter for U/C/F. The upstream LC owns the PC, service identity
// and error retirement. RX reservation and commit tracking are independent
// of this adapter's command state.
module ucf_native_service #(parameter integer LANES=2) (
    input wire clk, reset,
    input wire svc_valid,
    output wire svc_ready,
    input wire [1023:0] descriptor,
    output wire rsp_valid,
    input wire rsp_ready,
    output reg [15:0] status,
    output reg saturated,
    output reg [31:0] read_bytes, write_bytes,
    output reg [LANES-1:0] cmd_valid, cmd_store, done_ready,
    output reg [LANES*64-1:0] cmd_meta,
    output reg [LANES*2-1:0] cmd_sources,
    output reg [LANES*30-1:0] cmd_addresses,
    output reg [LANES*10-1:0] cmd_dst,
    input wire [LANES-1:0] cmd_ready, done_valid, done_error, done_saturated,
    output wire send_start,
    input wire send_ready, send_done,
    output wire [9:0] source_addr, destination_addr,
    input wire receive_commit,
    output wire receive_reserved,
    output wire [9:0] receive_address
);
    localparam IDLE=0, ISSUE=1, WAIT_CMD=2, ISSUE_SEND=3, WAIT_SEND=4,
               WAIT_RECEIVE=5, RESPONSE=6;
    localparam OP_COMMAND=16'h100, OP_SEND=16'h101, OP_RECEIVE=16'h102, OP_RESERVE=16'h103;
    reg [2:0] state;
    reg [1:0] lane, sources;
    reg store;
    reg [63:0] meta;
    reg [29:0] addresses;
    reg [9:0] dst, reserved_address;
    reg reserved, committed;
    wire [15:0] op = descriptor[32+:16];
    wire [31:0] native0 = descriptor[512+:32];
    wire [31:0] native1 = descriptor[544+:32];
    wire [31:0] native2 = descriptor[576+:32];
    wire [31:0] native3 = descriptor[608+:32];

    wire e32 = native0[15];
    wire [3:0] e32_op = native2[3:0];
    wire signed [7:0] e32_shift = native2[15:8];
    wire [2:0] e32_minus = native2[18:16];
    wire [1:0] e32_sources = e32_op==3 || e32_op==4 || e32_op==10 || e32_op==11 ? 2'd1 :
                             e32_op==1 || e32_op==9 ? 2'd3 : 2'd2;
    wire e32_bad = native0[1:0]!=0 || native0[3:2]!=e32_sources ||
                   native2[31:19]!=0 || native3!=0 || e32_op>11 ||
                   e32_shift< -8'sd63 || e32_shift>8'sd63 ||
                   ((e32_op<2 || e32_op>4) && e32_shift!=0) ||
                   (e32_op>1 && e32_minus!=0) || (e32_op==0 && e32_minus[2]);

    // R256's native state load uses a truncated physical row index. Reject
    // malformed offsets before issuing a command that could alias live state.
    wire [9:0] r_load_index = native2[14:5];
    reg r_load_index_ok;
    always @* begin
        case (native2[4:2])
            0,1: r_load_index_ok = r_load_index<64;
            2,3,7: r_load_index_ok = r_load_index<4;
            4,6: r_load_index_ok = r_load_index<6;
            5: r_load_index_ok = r_load_index==0;
            default: r_load_index_ok = 0;
        endcase
    end
    assign svc_ready = !reset && state==IDLE;
    assign rsp_valid = !reset && state==RESPONSE;
    assign send_start = !reset && state==ISSUE_SEND;
    assign source_addr = addresses[9:0];
    assign destination_addr = dst;
    assign receive_reserved = !reset && reserved && !committed;
    assign receive_address = reserved_address;

    always @* begin
        cmd_valid=0; cmd_store=0; done_ready=0;
        cmd_meta=0; cmd_sources=0; cmd_addresses=0; cmd_dst=0;
        if (!reset && (state==ISSUE || state==WAIT_CMD)) begin
            for (integer i=0; i<LANES; i=i+1) if (lane==2'(i)) begin
                cmd_valid[i]=state==ISSUE;
                done_ready[i]=state==WAIT_CMD;
                cmd_store[i]=store;
                cmd_meta[64*i+:64]=meta;
                cmd_sources[2*i+:2]=sources;
                cmd_addresses[30*i+:30]=addresses;
                cmd_dst[10*i+:10]=dst;
            end
        end
    end

    always @(posedge clk) begin
        if (reset) begin
            state<=IDLE; lane<=0; sources<=0; store<=0; meta<=0; addresses<=0; dst<=0;
            status<=0; saturated<=0; read_bytes<=0; write_bytes<=0;
            reserved<=0; committed<=0; reserved_address<=0;
        end else begin
            if (receive_commit && reserved) committed<=1;
            case (state)
                IDLE: if (svc_valid) begin
                    status<=0; saturated<=0; read_bytes<=0; write_bytes<=0;
                    state<=RESPONSE;
                    if (descriptor[1023:640]!=0) status<=5;
                    else case (op)
                        OP_COMMAND: begin
                            if (native0[31:16]!=0 || (e32 && e32_bad) || {30'd0,native0[1:0]}>=LANES || (!e32 && native0[3:2]>2) ||
                                native1[31:30]!=0 ||
                                (LANES==3 && native0[1:0]==2 &&
                                 native2[1:0]==0 && !r_load_index_ok))
                                status<=5;
                            else begin
                                lane<=native0[1:0]; sources<=native0[3:2]; store<=native0[4];
                                dst<=native0[14:5]; addresses<=native1[29:0]; meta<={native3,native2};
                                if (native0[1:0]==0) meta[62]<=e32;
                                state<=ISSUE;
                            end
                        end
                        OP_SEND: begin
                            if (native0[31:20]!=0 || {native3,native2,native1}!=0) status<=5;
                            else begin
                                addresses<={20'd0,native0[9:0]}; dst<=native0[19:10];
                                state<=ISSUE_SEND;
                            end
                        end
                        OP_RESERVE: begin
                            if (native0[31:10]!=0 || {native3,native2,native1}!=0 || reserved) status<=5;
                            else begin
                                reserved<=1; reserved_address<=native0[9:0];
                            end
                        end
                        OP_RECEIVE: begin
                            if ({native3,native2,native1,native0}!=0 || !reserved) status<=5;
                            else state<=WAIT_RECEIVE;
                        end
                        default: status<=5;
                    endcase
                end
                ISSUE: if (|(cmd_valid & cmd_ready)) state<=WAIT_CMD;
                WAIT_CMD: if (|(done_valid & done_ready)) begin
                    status <= (|(done_error & done_ready)) ? 16'd9 : 16'd0;
                    saturated <= |(done_saturated & done_ready);
                    read_bytes <= {26'd0,sources,4'd0};
                    if (store && !(|(done_error & done_ready))) write_bytes<=16;
                    state<=RESPONSE;
                end
                ISSUE_SEND: if (send_ready) state<=WAIT_SEND;
                WAIT_SEND: if (send_done) begin
                    read_bytes<=16;
                    state<=RESPONSE;
                end
                WAIT_RECEIVE: if (committed) begin
                    committed<=0; reserved<=0;
                    write_bytes<=16;
                    state<=RESPONSE;
                end
                RESPONSE: if (rsp_ready) state<=IDLE;
                default: state<=IDLE;
            endcase
        end
    end
endmodule
