(* blackbox *) module m_native_leaf_s32 (
 input wire clk,reset,
 input wire lc_valid,output wire lc_ready,input wire lc_sop,lc_eop,input wire [127:0] lc_data,
 output wire lr_valid,input wire lr_ready,output wire lr_sop,lr_eop,output wire [127:0] lr_data,
 input wire a_valid,output wire a_ready,input wire [255:0] a_data,
 input wire [31:0] a_session,input wire [2:0] a_beat,
 output wire mc_req_valid,input wire mc_req_ready,output wire [63:0] mc_req_address,
 output wire [31:0] mc_req_tag,output wire mc_req_channel,output wire [4:0] mc_req_record_beats,
 output wire mc_close_valid,input wire mc_close_ready,output wire [31:0] mc_close_tag_base,
 input wire mc_rsp_valid,output wire mc_rsp_ready,input wire [31:0] mc_rsp_tag,input wire [511:0] mc_rsp_data,
 output wire mc_fence_req_valid,input wire mc_fence_req_ready,
 output wire [31:0] mc_fence_req_cookie,output wire [8:0] mc_fence_req_epoch,
 input wire mc_fence_done_valid,output wire mc_fence_done_ready,
 input wire [31:0] mc_fence_done_cookie,input wire [8:0] mc_fence_done_epoch,
 output wire fault_interrupt
);
endmodule

(* blackbox *) module local_s_base (
    input wire clk, reset,
    input wire req_valid, req_write,
    input wire [9:0] req_addr,
    input wire [127:0] req_data,
    output wire req_ready, rsp_valid,
    input wire rsp_ready,
    output wire [127:0] rsp_data
`ifdef USE_POWER_PINS
    , inout wire vdd, gnd
`endif
);
endmodule
