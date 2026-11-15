`timescale 1ns/1ps
// Four-lane Qwen2.5 rotary slice using one existing compact E32 aperture.
// The caller reads paired half-vector words and supplies sign-extended Q14
// cosine/sine. All multiply, conversion, rounding, and addition use E32.
module rope_e32_ap64 (
    input  wire clk, reset,
    input  wire cmd_valid,
    output wire cmd_ready,
    input  wire [7:0] cmd_cos_shift, cmd_neg_shift, cmd_neg_align,
    input  wire [7:0] cmd_sin_shift, cmd_sin_align, cmd_out_shift,
    input  wire cmd_negate,
    input  wire [127:0] cmd_value, cmd_paired, cmd_cos, cmd_sin,
    output wire done_valid,
    input  wire done_ready,
    output reg  [127:0] done_data,
    output reg  [3:0] done_clipped,
    output reg  done_error,

    output wire e_in_valid,
    input  wire e_in_ready,
    output wire [63:0] e_in_data,
    output wire [3:0] e_in_op, e_in_mask,
    output wire [7:0] e_in_shift,
    output wire [2:0] e_in_minus,
    input  wire e_out_valid,
    output wire e_out_ready,
    input  wire [63:0] e_out_data,
    input  wire [3:0] e_out_clipped,
    input  wire e_out_error
);
    localparam [3:0] IDLE=0, COSINE=1, NEGATE=2, NEG_ALIGN=3, SINE=4,
                     SIN_ALIGN=5, SUM=6, K_PACK=7, REPORT=8;
    localparam [3:0] ADD2=0, PRODUCT=2, CONVERT32=3;

    reg [3:0] phase;
    reg [7:0] cos_shift, neg_shift, neg_align, sin_shift, sin_align, out_shift;
    reg negate, receiving, high_result;
    reg [1:0] input_beat;
    reg [63:0] result_low;
    reg [127:0] value, paired, cosine, sine, cosine_product, intermediate;
    reg [127:0] operand_a, operand_b;
    reg [3:0] operation;
    reg [7:0] shift;

    function automatic invalid_shift(input [7:0] amount);
        return $signed(amount)<-8'sd63 || $signed(amount)>8'sd63;
    endfunction
    wire bad_command = invalid_shift(cmd_cos_shift) || invalid_shift(cmd_neg_shift) ||
                       invalid_shift(cmd_neg_align) || invalid_shift(cmd_sin_shift) ||
                       invalid_shift(cmd_sin_align) || invalid_shift(cmd_out_shift);

    wire [127:0] returned = {e_out_data,result_low};
    wire unary = operation==CONVERT32;
    wire last_input = unary ? input_beat==1 : input_beat==3;
    wire [127:0] selected_operand = input_beat[1] ? operand_b : operand_a;

    assign cmd_ready = !reset && phase==IDLE;
    assign done_valid = !reset && phase==REPORT;
    assign e_in_valid = !reset && phase!=IDLE && phase!=REPORT && !receiving;
    assign e_out_ready = !reset && receiving;
    assign e_in_data = input_beat[0] ? selected_operand[127:64] : selected_operand[63:0];
    assign e_in_op = operation;
    assign e_in_mask = 4'hf;
    assign e_in_shift = shift;
    assign e_in_minus = 0;

    always @* begin
        operation = CONVERT32;
        shift = 0;
        operand_a = intermediate;
        operand_b = 0;
        case(phase)
            COSINE: begin
                operation = PRODUCT; shift = cos_shift;
                operand_a = value; operand_b = cosine;
            end
            NEGATE: begin
                operation = PRODUCT; shift = neg_shift;
                operand_a = paired; operand_b = {128{1'b1}};
            end
            NEG_ALIGN: shift = neg_align;
            SINE: begin
                operation = PRODUCT; shift = sin_shift;
                operand_a = negate ? intermediate : paired; operand_b = sine;
            end
            SIN_ALIGN: shift = sin_align;
            SUM: begin
                operation = ADD2; operand_a = cosine_product; operand_b = intermediate;
            end
            K_PACK: shift = out_shift;
            default: begin end
        endcase
    end

    always @(posedge clk) begin
        if(reset) begin
            phase<=IDLE; cos_shift<=0;neg_shift<=0;neg_align<=0;sin_shift<=0;sin_align<=0;out_shift<=0;
            negate<=0; receiving<=0; high_result<=0;
            input_beat<=0; result_low<=0; value<=0; paired<=0; cosine<=0; sine<=0;
            cosine_product<=0; intermediate<=0;
            done_data<=0; done_clipped<=0; done_error<=0;
        end else if(cmd_valid&&cmd_ready) begin
            phase<=bad_command ? REPORT : COSINE;
            cos_shift<=cmd_cos_shift;neg_shift<=cmd_neg_shift;neg_align<=cmd_neg_align;
            sin_shift<=cmd_sin_shift;sin_align<=cmd_sin_align;out_shift<=cmd_out_shift;
            negate<=cmd_negate;
            value<=cmd_value; paired<=cmd_paired; cosine<=cmd_cos; sine<=cmd_sin;
            done_data<=0; done_clipped<=0; done_error<=bad_command;
        end else if(done_valid&&done_ready) begin
            phase<=IDLE;
        end else if(e_in_valid&&e_in_ready) begin
            if(last_input) begin
                receiving<=1; input_beat<=0;
            end else input_beat<=input_beat+1'b1;
        end else if(e_out_valid&&e_out_ready) begin
            if(!high_result) begin
                result_low<=e_out_data; high_result<=1;
            end else begin
                receiving<=0; high_result<=0;
                done_clipped<=done_clipped | e_out_clipped;
                if(e_out_error) begin
                    phase<=REPORT; done_error<=1;
                end else begin
                    case(phase)
                        COSINE: begin
                            cosine_product<=returned; phase<=negate ? NEGATE : SINE;
                        end
                        NEGATE: begin
                            intermediate<=returned; phase<=neg_align!=0 ? NEG_ALIGN : SINE;
                        end
                        NEG_ALIGN: begin intermediate<=returned; phase<=SINE; end
                        SINE: begin
                            intermediate<=returned; phase<=sin_align!=0 ? SIN_ALIGN : SUM;
                        end
                        SIN_ALIGN: begin intermediate<=returned; phase<=SUM; end
                        SUM: if(out_shift!=0) begin intermediate<=returned; phase<=K_PACK; end
                             else begin done_data<=returned; phase<=REPORT; end
                        K_PACK: begin done_data<=returned; phase<=REPORT; end
                        default: begin phase<=REPORT; done_error<=1; end
                    endcase
                end
            end
        end
    end
endmodule
