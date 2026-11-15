`timescale 1ns/1ps
// A rotary result owns its SRAM destination until the real write response.
module rope_e32_s128_commit (
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
    input  wire s_rsp_error
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
    e_s32_ap64 provider(
        .clk,.reset,.in_valid(e_in_valid),.in_ready(e_in_ready),.in_data(e_in_data),
        .in_op(e_in_op),.in_mask(e_in_mask),.in_shift(e_in_shift),.in_minus(e_in_minus),
        .out_valid(e_out_valid),.out_ready(e_out_ready),.out_data(e_out_data),
        .out_clipped(e_out_clipped),.out_error(e_out_error)
    );
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
endmodule
