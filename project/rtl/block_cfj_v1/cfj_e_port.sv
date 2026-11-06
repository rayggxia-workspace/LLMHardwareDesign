// The service producer holds its operands until acceptance of the final beat.
module cfj_e_port (
    input wire clk, reset, in_valid,
    output wire in_ready,
    input wire [3:0] in_op,
    input wire [4:0] in_shift,
    input wire [127:0] in_a, in_b, in_c,
    input wire use_late_a, late_valid,
    input wire [127:0] late_a,
    output wire late_take,
    output wire out_valid,
    input wire out_ready,
    output wire [127:0] out_data,
    output wire out_error, out_saturated
);
    reg [1:0] beat;
    wire leaf_ready;
    wire last = beat==0 ? (in_op==7 || in_op==8 || in_op>=10) :
                beat==2 || (in_op!=3 && in_op!=6);
    wire late_first = use_late_a && beat==0;
    wire send = !reset && in_valid && (!late_first || late_valid);
    assign in_ready = send && leaf_ready && last;
    assign late_take = late_first && send && leaf_ready;

    always @(posedge clk) begin
        if (reset) beat <= 0;
        else if (send && leaf_ready) beat <= last ? 2'd0 : beat+1'b1;
    end

    block_v2_e_compact leaf (
        .clk(clk), .reset(reset), .in_valid(send), .in_ready(leaf_ready),
        .in_op(in_op), .in_shift(in_shift),
        .in_data(late_first ? late_a : beat==0 ? in_a : beat==1 ? in_b : in_c),
        .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data),
        .out_error(out_error), .out_saturated(out_saturated)
    );
endmodule
