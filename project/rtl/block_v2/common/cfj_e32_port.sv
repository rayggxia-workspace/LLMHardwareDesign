// Bridge the local S128 client to the qualified two-beat E32 aperture.
// The client holds metadata and captured operands until the result is taken.
module cfj_e32_port (
    input wire clk, reset,
    input wire request, output wire ready,
    input wire [18:0] meta,
    input wire [127:0] a, b, c,
    output wire response, input wire take,
    output wire [127:0] data,
    output wire error, saturated
);
    localparam [1:0] IDLE=0, SEND=1, RECEIVE_LOW=2, RECEIVE_HIGH=3;
    reg [1:0] phase, operand;
    reg high_half;
    reg [63:0] low_data;
    wire [3:0] op = meta[3:0];
    wire [1:0] last_operand = op==3 || op==4 || op==10 || op==11 ? 2'd0 :
                              op==1 || op==9 ? 2'd2 : 2'd1;
    wire [127:0] word_data = operand==0 ? a : operand==1 ? b : c;
    wire in_ready, out_valid;
    wire [63:0] out_data;
    wire [3:0] clipped;
    assign ready = !reset && phase==IDLE;
    assign response = !reset && phase==RECEIVE_HIGH && out_valid;
    assign data = {out_data, low_data};
    assign saturated = |clipped;

    e_s32_ap64 leaf (
        .clk(clk), .reset(reset), .in_valid(!reset && phase==SEND), .in_ready(in_ready),
        .in_data(high_half ? word_data[127:64] : word_data[63:0]),
        .in_op(op), .in_mask(meta[7:4]), .in_shift(meta[15:8]), .in_minus(meta[18:16]),
        .out_valid(out_valid),
        .out_ready(!reset && (phase==RECEIVE_LOW || (phase==RECEIVE_HIGH && take))),
        .out_data(out_data), .out_clipped(clipped), .out_error(error)
    );

    always @(posedge clk) begin
        if (reset) begin
            phase <= IDLE;
            operand <= 0;
            high_half <= 0;
        end else case (phase)
            IDLE: if (request) begin
                operand <= 0;
                high_half <= 0;
                phase <= SEND;
            end
            SEND: if (in_ready) begin
                high_half <= !high_half;
                if (high_half) begin
                    operand <= operand + 1'b1;
                    if (operand==last_operand) phase <= RECEIVE_LOW;
                end
            end
            RECEIVE_LOW: if (out_valid) begin
                low_data <= out_data;
                phase <= RECEIVE_HIGH;
            end
            RECEIVE_HIGH: if (out_valid && take) phase <= IDLE;
        endcase
    end
endmodule
