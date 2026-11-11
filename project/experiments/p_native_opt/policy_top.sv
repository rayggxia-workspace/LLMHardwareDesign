// C++ drives a finite single-response byte memory model. The unmodified
// production arbiter is observed in parallel for the default cycle comparison.
module policy_top #(
    parameter bit POLICY_ENABLE=1'b0,
    parameter integer MAX_CONSUMER_BURST=2
) (
    input wire clk, reset,
    input wire [3:0] req_valid, req_write, rsp_ready,
    input wire [39:0] req_addr,
    input wire [511:0] req_data,
    output wire [3:0] req_ready, rsp_valid,
    output wire [511:0] rsp_data,
    output wire mem_req, mem_write, mem_take, busy,
    output wire [9:0] mem_addr,
    output wire [127:0] mem_data,
    input wire mem_ready, mem_valid,
    input wire [127:0] mem_result,
    output wire [3:0] ref_req_ready, ref_rsp_valid,
    output wire [511:0] ref_rsp_data,
    output wire ref_mem_req, ref_mem_write, ref_mem_take, ref_busy,
    output wire [9:0] ref_mem_addr,
    output wire [127:0] ref_mem_data
);
    popt_s_policy_arbiter #(.POLICY_ENABLE(POLICY_ENABLE),
        .MAX_CONSUMER_BURST(MAX_CONSUMER_BURST)) dut(.*);
    block_local_s_arbiter original(
        .clk, .reset, .req_valid, .req_write, .req_addr, .req_data,
        .req_ready(ref_req_ready), .rsp_valid(ref_rsp_valid),
        .rsp_ready, .rsp_data(ref_rsp_data),
        .mem_req(ref_mem_req), .mem_write(ref_mem_write), .mem_addr(ref_mem_addr),
        .mem_data(ref_mem_data), .mem_ready, .mem_valid, .mem_result,
        .mem_take(ref_mem_take), .busy(ref_busy)
    );
endmodule
