// Co-issue the N producer and compact E consumer for one configured late link.
module pu_u_direct_pair (
    input wire clk, reset, enable,
    input wire svc_valid, output wire svc_ready,
    input wire [1023:0] descriptor,
    output wire rsp_valid, input wire rsp_ready,
    output reg [15:0] status,
    output reg saturated,
    output wire [31:0] read_bytes, write_bytes,
    output wire [1:0] cmd_valid, cmd_store, done_ready,
    output wire [127:0] cmd_meta,
    output wire [3:0] cmd_sources,
    output wire [59:0] cmd_addresses,
    output wire [19:0] cmd_dst,
    input wire [1:0] cmd_ready, done_valid, done_error, done_saturated,
    output wire abort_direct_a
);
    localparam IDLE=0, EXEC=1, RESPONSE=2;
    reg [1:0] state, issued, retired;
    reg [39:0] n_meta;
    reg [19:0] n_src, e_bc;
    reg [1:0] n_sources;
    reg [8:0] e_meta;
    reg [9:0] e_dst;
    wire [31:0] n_fields=descriptor[512+:32];
    wire [31:0] e_fields=descriptor[640+:32];
    wire [1:0] accepted=cmd_valid & cmd_ready;
    wire [1:0] completed=done_ready & done_valid;
    // N errors are control information. E may still be waiting for its first beat.
    assign abort_direct_a=state==EXEC && issued[0] &&
        ((completed[1] && done_error[1]) || (retired[1] && status!=0));
    assign svc_ready=!reset && state==IDLE;
    assign rsp_valid=!reset && state==RESPONSE;
    assign cmd_valid=state==EXEC ? ~issued : 2'b00;
    assign cmd_store=2'b01;
    assign done_ready=state==EXEC ? issued & ~retired : 2'b00;
    assign cmd_meta={24'b0,n_meta,55'b0,e_meta};
    assign cmd_sources={n_sources,2'b00};
    assign cmd_addresses={10'b0,n_src,e_bc,10'b0};
    assign cmd_dst={10'b0,e_dst};
    assign read_bytes=status==0 ? (({30'b0,n_sources} +
        ((e_meta[3:0]==3 || e_meta[3:0]==6) ? 2 :
         (e_meta[3:0]==7 || e_meta[3:0]==8 || e_meta[3:0]==10) ? 0 : 1)) << 4) : 0;
    assign write_bytes=status==0 ? 32'd16 : 32'd0;

    always @(posedge clk) begin
        if (reset) begin
            state<=IDLE;
            issued<=0;
            retired<=0;
            status<=0;
            saturated<=0;
        end else case (state)
            IDLE: if (svc_valid) begin
                issued<=0;
                retired<=0;
                saturated<=0;
                if (!enable || n_fields>2 || descriptor[575:564]!=0 ||
                    descriptor[639:616]!=0 || e_fields[31:19]!=0 ||
                    e_fields[3:0]>10 || descriptor[1023:692]!=0) begin
                    status<=16'd5;
                    state<=RESPONSE;
                end else begin
                    status<=0;
                    n_sources<=n_fields[1:0];
                    n_src<=descriptor[544+:20];
                    n_meta<=descriptor[576+:40];
                    e_meta<=e_fields[8:0];
                    e_dst<=e_fields[18:9];
                    e_bc<=descriptor[672+:20];
                    state<=EXEC;
                end
            end
            EXEC: begin
                issued<=issued | accepted;
                retired<=retired | completed;
                if (|(completed & done_error)) status<=16'd9;
                if (|(completed & done_saturated)) saturated<=1;
                if (&(retired | completed)) state<=RESPONSE;
            end
            RESPONSE: if (rsp_ready) state<=IDLE;
            default: state<=IDLE;
        endcase
    end
endmodule
