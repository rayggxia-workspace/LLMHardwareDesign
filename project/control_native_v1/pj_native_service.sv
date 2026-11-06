// Native P/J command adapter. A P command uses the fixed SRAM replay path;
// the optional late M-to-G bypass is a separate topology qualification.
module pj_native_service #(parameter bit JOIN_BLOCK=0)(
    input wire clk, reset,
    input wire svc_valid, output wire svc_ready,
    input wire [1023:0] descriptor,
    output wire rsp_valid, input wire rsp_ready,
    output reg [15:0] status, output reg saturated,
    output reg [31:0] read_bytes, write_bytes,
    output wire load_valid, input wire load_ready,
    output wire load_take, input wire load_done, load_error,
    output wire [31:0] load_fields,
    output wire cmd_valid, input wire cmd_ready,
    output wire cmd_take, input wire cmd_done, cmd_error, cmd_saturated,
    output wire [31:0] cmd_fields, output wire [63:0] cmd_data,
    output wire gate_valid, input wire gate_ready,
    output wire gate_take, input wire gate_done, gate_error, gate_saturated,
    output wire [29:0] gate_fields,
    output wire start, input wire start_ready,
    output wire done_take, input wire done_valid, done_error,
    output wire [31:0] join_tag,
    output wire [20:0] join_fields,
    output wire release_valid, input wire release_ready
);
    localparam IDLE=0, ISSUE=1, WAIT_RESULT=2, RESPONSE=3;
    localparam LOAD=16'h110, MAT=16'h111, GATE=16'h112, JOIN=16'h120, RELEASE=16'h121;
    reg [1:0] state;
    reg [15:0] op;
    reg [31:0] fields, arg1, arg2;
    wire [15:0] request_op = descriptor[32+:16];
    wire [31:0] request_fields = descriptor[512+:32];
    wire unused_args = descriptor[544+:64]==0;
    wire valid_p = (request_op==LOAD && unused_args && request_fields[31]==0 &&
                    request_fields[4:1]!=0 && request_fields[4:1]<=8 &&
                    request_fields[7:5]!=0 && request_fields[7:5]<=4) ||
                   (request_op==MAT && request_fields[31:22]==0 &&
                    (!request_fields[10] || request_fields[3:0]==5) &&
                    (!request_fields[11] || request_fields[10])) ||
                   (request_op==GATE && unused_args && request_fields[31:30]==0 &&
                    request_fields[9:0]!=request_fields[29:20] &&
                    request_fields[19:10]!=request_fields[29:20]);
    wire valid_j = (request_op==JOIN && descriptor[607:576]==0 &&
                    request_fields[31:21]==0 && request_fields[19:10]!=0 &&
                    request_fields[19:10]<=384 &&
                    {1'b0,request_fields[19:10]}+{1'b0,request_fields[9:0]}<=1024) ||
                   (request_op==RELEASE && unused_args && request_fields==0);

    assign svc_ready = !reset && state==IDLE;
    assign rsp_valid = !reset && state==RESPONSE;
    assign load_valid = !reset && state==ISSUE && op==LOAD;
    assign load_take = !reset && state==WAIT_RESULT && op==LOAD;
    assign load_fields = fields;
    assign cmd_valid = !reset && state==ISSUE && op==MAT;
    assign cmd_take = !reset && state==WAIT_RESULT && op==MAT;
    assign cmd_fields = fields;
    assign cmd_data = {arg2,arg1};
    assign gate_valid = !reset && state==ISSUE && op==GATE;
    assign gate_take = !reset && state==WAIT_RESULT && op==GATE;
    assign gate_fields = fields[29:0];
    assign start = !reset && state==ISSUE && op==JOIN;
    assign done_take = !reset && state==WAIT_RESULT && op==JOIN;
    assign join_tag = arg1;
    assign join_fields = fields[20:0];
    assign release_valid = !reset && state==ISSUE && op==RELEASE;

    always @(posedge clk) begin
        if (reset) begin
            state<=IDLE; op<=0; fields<=0; arg1<=0; arg2<=0;
            status<=0; saturated<=0; read_bytes<=0; write_bytes<=0;
        end else case (state)
            IDLE: if (svc_valid) begin
                status<=0; saturated<=0; read_bytes<=0; write_bytes<=0;
                op<=request_op; fields<=request_fields;
                arg1<=descriptor[544+:32]; arg2<=descriptor[576+:32];
                if (descriptor[1023:608]==0 && (JOIN_BLOCK ? valid_j : valid_p)) state<=ISSUE;
                else begin status<=5; state<=RESPONSE; end
            end
            ISSUE: begin
                if (release_valid && release_ready) state<=RESPONSE;
                else if (load_valid && load_ready || cmd_valid && cmd_ready ||
                         gate_valid && gate_ready || start && start_ready) state<=WAIT_RESULT;
            end
            WAIT_RESULT: begin
                if (load_take && load_done) begin
                    status<=load_error ? 16'd9 : 16'd0;
                    state<=RESPONSE;
                end else if (cmd_take && cmd_done) begin
                    status<=cmd_error ? 16'd9 : 16'd0;
                    saturated<=cmd_saturated;
                    if (!cmd_error && fields[10]) write_bytes<=16;
                    state<=RESPONSE;
                end else if (gate_take && gate_done) begin
                    status<=gate_error ? 16'd9 : 16'd0;
                    saturated<=gate_saturated;
                    read_bytes<=32;
                    if (!gate_error) write_bytes<=16;
                    state<=RESPONSE;
                end else if (done_take && done_valid) begin
                    status<=done_error ? 16'd9 : 16'd0;
                    if (!done_error) write_bytes<={18'd0,fields[19:10],4'd0};
                    state<=RESPONSE;
                end
            end
            RESPONSE: if (rsp_ready) state<=IDLE;
            default: state<=IDLE;
        endcase
    end
endmodule
