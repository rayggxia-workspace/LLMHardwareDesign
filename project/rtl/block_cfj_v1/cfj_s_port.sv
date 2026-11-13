// One outstanding transaction retains its requester through the real S response.
module cfj_s_port #(parameter integer CLIENTS=4) (
    input wire clk, reset,
    input wire [CLIENTS-1:0] req_valid, req_write,
    input wire [CLIENTS*10-1:0] req_addr,
    input wire [CLIENTS*128-1:0] req_data,
    output reg [CLIENTS-1:0] req_ready, rsp_valid,
    input wire [CLIENTS-1:0] rsp_ready,
    output wire [CLIENTS*128-1:0] rsp_data
);
    localparam integer IW = $clog2(CLIENTS);
    localparam IDLE=0, ISSUE=1, WAIT_RESPONSE=2;
    reg [1:0] state;
    reg [IW-1:0] owner, next_priority, selected;
    reg selected_valid;
    reg pending_write;
    reg [9:0] pending_addr;
    reg [127:0] pending_data;
    wire s_ready, s_valid;
    wire [127:0] s_data;

    always @* begin
        selected = 0;
        selected_valid = 0;
        for (integer i=0; i<CLIENTS; i=i+1)
            if (!selected_valid && i>=int'(next_priority) && req_valid[i]) begin
                selected = IW'(i);
                selected_valid = 1;
            end
        for (integer i=0; i<CLIENTS; i=i+1)
            if (!selected_valid && req_valid[i]) begin
                selected = IW'(i);
                selected_valid = 1;
            end
        req_ready = 0;
        rsp_valid = 0;
        if (!reset && state==IDLE && selected_valid) req_ready[selected] = 1;
        if (!reset && state==WAIT_RESPONSE) rsp_valid[owner] = s_valid;
    end
    assign rsp_data = {CLIENTS{s_data}};
    local_s_base leaf (
        .clk(clk), .reset(reset), .req_valid(!reset && state==ISSUE),
        .req_write(pending_write), .req_addr(pending_addr), .req_data(pending_data),
        .req_ready(s_ready), .rsp_valid(s_valid),
        .rsp_ready(!reset && state==WAIT_RESPONSE && rsp_ready[owner]), .rsp_data(s_data)
    );

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            next_priority <= 0;
        end else case (state)
            IDLE: if (selected_valid) begin
                owner <= selected;
                pending_write <= req_write[selected];
                pending_addr <= req_addr[10*int'(selected)+:10];
                pending_data <= req_data[128*int'(selected)+:128];
                next_priority <= selected==IW'(CLIENTS-1) ? IW'(0) : selected+1'b1;
                state <= ISSUE;
            end
            ISSUE: if (s_ready) state <= WAIT_RESPONSE;
            WAIT_RESPONSE: if (s_valid && rsp_ready[owner]) state <= IDLE;
            default: state <= IDLE;
        endcase
    end
endmodule
