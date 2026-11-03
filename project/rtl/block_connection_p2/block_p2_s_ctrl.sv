// Issue151 P2: one outstanding ordinary S read/write, including write ACKs.
// Native mapping: s_we -> S.wr, s_rsp_ready -> S.take. Native S has no error pin.
// resetn is active-low synchronous. Top must reset/invalidate the native S and
// all consumers coherently; reset is not a rollback of an accepted S write.
`default_nettype none
module block_p2_s_ctrl (
    input  wire         clk,
    input  wire         resetn,

    input  wire         req_valid,
    output wire         req_ready,
    input  wire         req_write,
    input  wire [9:0]   req_addr,
    input  wire [127:0] req_data,

    output wire         rsp_valid,
    input  wire         rsp_ready,
    output wire [127:0] rsp_data,
    output wire         rsp_error,

    output wire         s_req,
    output wire         s_we,
    output wire [9:0]   s_addr,
    output wire [127:0] s_din,
    output wire         s_rsp_ready,
    input  wire         s_ready,
    input  wire         s_rsp_valid,
    input  wire [127:0] s_dout
);
    localparam [1:0] ST_IDLE = 2'd0;
    localparam [1:0] ST_ISSUE = 2'd1;
    localparam [1:0] ST_WAIT_ACK = 2'd2;
    localparam [1:0] ST_RESP = 2'd3;

    reg [1:0] state;
    reg write_hold;
    reg [9:0] addr_hold;
    reg [127:0] data_hold;
    reg [127:0] response_hold;

    assign req_ready = resetn && state == ST_IDLE;
    assign rsp_valid = resetn && state == ST_RESP;
    assign rsp_data = response_hold;
    assign rsp_error = 1'b0;

    // Keep the captured native request asserted until S accepts it once.
    assign s_req = resetn && state == ST_ISSUE;
    assign s_we = write_hold;
    assign s_addr = addr_hold;
    assign s_din = data_hold;

    // S returns a response for writes too. Capture exactly one native response
    // before offering the generic response, then stop taking native responses.
    assign s_rsp_ready = resetn && state == ST_WAIT_ACK;

    always @(posedge clk) begin
        if (!resetn) begin
            state <= ST_IDLE;
            write_hold <= 1'b0;
            addr_hold <= 10'd0;
            data_hold <= 128'd0;
            response_hold <= 128'd0;
        end else begin
            case (state)
                ST_IDLE: begin
                    if (req_valid && req_ready) begin
                        write_hold <= req_write;
                        addr_hold <= req_addr;
                        data_hold <= req_data;
                        state <= ST_ISSUE;
                    end
                end
                ST_ISSUE: begin
                    if (s_req && s_ready)
                        state <= ST_WAIT_ACK;
                end
                ST_WAIT_ACK: begin
                    if (s_rsp_valid && s_rsp_ready) begin
                        response_hold <= s_dout;
                        state <= ST_RESP;
                    end
                end
                ST_RESP: begin
                    if (rsp_valid && rsp_ready)
                        state <= ST_IDLE;
                end
                default: state <= ST_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
