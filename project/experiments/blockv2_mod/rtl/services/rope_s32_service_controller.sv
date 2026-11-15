// Control-only service. No physical Block boundary or selected macro instance.
`timescale 1ns/1ps
// A rotary result owns its SRAM destination until the real write response.
module rope_s32_service_controller (
    input  wire clk,reset,
    input  wire cmd_valid,
    output wire cmd_ready,
    input  wire [9:0] cmd_dst,
    input  wire [31:0] cmd_tag,
    input  wire cmd_negate,
    input  wire [7:0] cmd_cos_shift,cmd_neg_shift,cmd_neg_align,
    input  wire [7:0] cmd_sin_shift,cmd_sin_align,cmd_out_shift,
    input  wire [127:0] cmd_value,cmd_paired,cmd_cos,cmd_sin,
    output wire busy,done_valid,
    input  wire done_ready,
    output reg  [31:0] done_tag,
    output reg  done_error,
    output wire s_req_valid,
    input  wire s_req_ready,
    output reg  [9:0] s_req_address,
    output wire [127:0] s_req_data,
    input  wire s_rsp_valid,
    output wire s_rsp_ready,
    input  wire s_rsp_error,
    output wire resource_e_in_valid,
    input wire resource_e_in_ready,
    output wire [63:0] resource_e_in_data,
    output wire [3:0] resource_e_in_op,
    output wire [3:0] resource_e_in_mask,
    output wire [7:0] resource_e_in_shift,
    output wire [2:0] resource_e_in_minus,
    input wire resource_e_out_valid,
    output wire resource_e_out_ready,
    input wire [63:0] resource_e_out_data,
    input wire [3:0] resource_e_out_clipped,
    input wire resource_e_out_error
);
    localparam [1:0] IDLE=0, CALC=1, WRITE_ACK=2, REPORT=3;
    reg [1:0] state;
    wire rope_cmd_ready, rope_done_valid, rope_done_error;
    wire [3:0] rope_clipped;
    wire rope_done_take = state==CALC && (rope_done_error || s_req_ready);
    wire e_in_valid,e_in_ready,e_out_valid,e_out_ready,e_out_error;
    wire [63:0] e_in_data,e_out_data;
    wire [3:0] e_in_op,e_in_mask,e_out_clipped;
    wire [7:0] e_in_shift;
    wire [2:0] e_in_minus;

    assign cmd_ready = !reset && state==IDLE && rope_cmd_ready;
    assign busy = !reset && state!=IDLE;
    assign done_valid = !reset && state==REPORT;
    assign s_req_valid = !reset && state==CALC && rope_done_valid && !rope_done_error;
    assign s_rsp_ready = !reset && state==WRITE_ACK;

    rope_e32_ap64 rope(
        .clk,.reset,.cmd_valid(cmd_valid&&state==IDLE),.cmd_ready(rope_cmd_ready),.cmd_negate,
        .cmd_cos_shift,.cmd_neg_shift,.cmd_neg_align,.cmd_sin_shift,.cmd_sin_align,.cmd_out_shift,
        .cmd_value,.cmd_paired,.cmd_cos,.cmd_sin,
        .done_valid(rope_done_valid),.done_ready(rope_done_take),.done_data(s_req_data),
        .done_clipped(rope_clipped),.done_error(rope_done_error),
        .e_in_valid,.e_in_ready,.e_in_data,.e_in_op,.e_in_mask,.e_in_shift,.e_in_minus,
        .e_out_valid,.e_out_ready,.e_out_data,.e_out_clipped,.e_out_error
    );
    // Resource e is supplied by the selected parent binding.

    wire _unused = ^rope_clipped;

    always @(posedge clk) begin
        if(reset) begin state<=IDLE; done_tag<=0; done_error<=0; s_req_address<=0; end
        else begin
            case(state)
                IDLE: if(cmd_valid&&cmd_ready) begin
                    state<=CALC; done_tag<=cmd_tag; done_error<=0; s_req_address<=cmd_dst;
                end
                CALC: if(rope_done_valid&&rope_done_take) begin
                    state<=rope_done_error ? REPORT : WRITE_ACK;
                    done_error<=rope_done_error;
                end
                WRITE_ACK: if(s_rsp_valid&&s_rsp_ready) begin state<=REPORT; done_error<=s_rsp_error; end
                REPORT: if(done_valid&&done_ready) state<=IDLE;
                default: begin state<=REPORT; done_error<=1; end
            endcase
        end
    end

    assign resource_e_in_valid = e_in_valid;
    assign e_in_ready = resource_e_in_ready;
    assign resource_e_in_data = e_in_data;
    assign resource_e_in_op = e_in_op;
    assign resource_e_in_mask = e_in_mask;
    assign resource_e_in_shift = e_in_shift;
    assign resource_e_in_minus = e_in_minus;
    assign e_out_valid = resource_e_out_valid;
    assign resource_e_out_ready = e_out_ready;
    assign e_out_data = resource_e_out_data;
    assign e_out_clipped = resource_e_out_clipped;
    assign e_out_error = resource_e_out_error;
endmodule
