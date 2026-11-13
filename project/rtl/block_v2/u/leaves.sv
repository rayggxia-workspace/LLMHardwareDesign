(* blackbox *) module n_s32_softmax_s128 (
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,input wire [31:0] cmd_tag,
 input wire [9:0] cmd_base,input wire [12:0] cmd_count,input wire cmd_committed,
 input wire abort_valid,output wire abort_ready,input wire [31:0] abort_tag,
 output reg rsp_valid,input wire rsp_ready,output reg [31:0] rsp_tag,
 output reg rsp_error,rsp_aborted,output reg [11:0] rsp_writes,
 output wire s_req_valid,input wire s_req_ready,output wire s_req_write,
 output wire [9:0] s_req_address,output wire [127:0] s_req_data,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data,input wire s_rsp_error
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
(* blackbox *) module block_v2_e_compact (
 input wire clk, reset, in_valid,
 output wire in_ready,
 input wire [3:0] in_op,
 input wire [4:0] in_shift,
 input wire [127:0] in_data,
 output wire out_valid,
 input wire out_ready,
 output wire [127:0] out_data,
 output wire out_error, out_saturated
);
endmodule
