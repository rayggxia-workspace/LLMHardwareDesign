// One accepted host programming command at a time. The registered payload
// drives the ten local command endpoints, whose native ABIs stay unchanged.
module native_host_program_switch #(
    parameter integer TARGETS = 10,
    parameter integer TARGET_BITS = TARGETS > 1 ? $clog2(TARGETS) : 1,
    parameter integer REQUEST_BITS = 322,
    parameter integer RESPONSE_BITS = 176
) (
    input wire clk, reset,
    input wire allow_request,
    input wire host_req_valid,
    output wire host_req_ready,
    input wire [TARGET_BITS-1:0] host_req_target,
    input wire [REQUEST_BITS-1:0] host_req_payload,
    output wire host_rsp_valid,
    input wire host_rsp_ready,
    output wire [TARGET_BITS-1:0] host_rsp_target,
    output wire [RESPONSE_BITS-1:0] host_rsp_payload,
    output wire host_rsp_bad_target,
    output wire idle,
    output reg [TARGETS-1:0] target_req_valid,
    input wire [TARGETS-1:0] target_req_ready,
    output reg [REQUEST_BITS-1:0] target_req_payload,
    input wire [TARGETS-1:0] target_rsp_valid,
    output reg [TARGETS-1:0] target_rsp_ready,
    input wire [TARGETS*RESPONSE_BITS-1:0] target_rsp_payload
);
    reg pending, sending, bad_target;
    reg [TARGET_BITS-1:0] owner;
    wire target_exists = {1'b0, host_req_target} < (TARGET_BITS+1)'(TARGETS);

    assign idle = !pending;
    assign host_req_ready = !reset && allow_request && idle;
    assign host_rsp_valid = !reset && pending && !sending &&
        (bad_target || target_rsp_valid[owner]);
    assign host_rsp_target = owner;
    assign host_rsp_bad_target = host_rsp_valid && bad_target;
    assign host_rsp_payload = (pending && !sending && !bad_target) ?
        target_rsp_payload[owner*RESPONSE_BITS+:RESPONSE_BITS] : '0;

    always @* begin
        target_req_valid = '0;
        target_rsp_ready = '0;
        if (!reset && pending && sending)
            target_req_valid[owner] = 1'b1;
        if (!reset && pending && !sending && !bad_target)
            target_rsp_ready[owner] = host_rsp_ready;
    end

    always @(posedge clk) begin
        if (host_req_valid && host_req_ready && target_exists)
            target_req_payload <= host_req_payload;
        if (reset) begin
            pending <= 1'b0;
            sending <= 1'b0;
            bad_target <= 1'b0;
            owner <= '0;
        end else if (host_req_valid && host_req_ready) begin
            pending <= 1'b1;
            sending <= target_exists;
            bad_target <= !target_exists;
            owner <= host_req_target;
        end else if (pending && sending && target_req_ready[owner]) begin
            sending <= 1'b0;
        end else if (host_rsp_valid && host_rsp_ready) begin
            pending <= 1'b0;
        end
    end
endmodule
