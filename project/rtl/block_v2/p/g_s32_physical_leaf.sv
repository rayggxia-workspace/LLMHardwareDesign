(* blackbox *) module g_s32 (
    input  wire        clk,
    input  wire        reset,
    input  wire        in_valid,
    output wire        in_ready,
    input  wire [63:0] in_gate,
    input  wire [63:0] in_up,
    input  wire        in_gated,
    input  wire [1:0]  in_mask,
    output wire        out_valid,
    input  wire        out_ready,
    output wire [63:0] out_data,
    output wire [1:0]  out_mask,
    output wire        out_error
);
endmodule
