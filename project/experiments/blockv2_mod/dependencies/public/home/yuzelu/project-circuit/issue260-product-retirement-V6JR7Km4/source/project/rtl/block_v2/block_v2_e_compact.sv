// A command starts with operand A. Subsequent beats supply B and C as needed.
// Opcode and shift are sampled only on the first beat.
module block_v2_e_compact (
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
 localparam FIRST=2'd0, SECOND=2'd1, THIRD=2'd2;
 reg [1:0] beat;
 reg [3:0] op;
 reg [4:0] shift;
 reg [127:0] a, b;
 wire first_is_last = in_op == 7 || in_op == 8 || in_op >= 10;
 wire needs_c = op == 3 || op == 6;
 wire last = beat == FIRST ? first_is_last : beat == THIRD || !needs_c;
 wire exec_ready;

 assign in_ready = !reset && (!last || exec_ready);

 always @(posedge clk) begin
  if (reset) beat <= FIRST;
  else if (in_valid && in_ready) begin
   if (last) beat <= FIRST;
   else if (beat == FIRST) begin
    a <= in_data;
    op <= in_op;
    shift <= in_shift;
    beat <= SECOND;
   end else begin
    b <= in_data;
    beat <= THIRD;
   end
  end
 end

 block_v2_e core (
  .clk(clk), .reset(reset), .in_valid(in_valid && last), .in_ready(exec_ready),
  .in_op(beat == FIRST ? in_op : op), .in_shift(beat == FIRST ? in_shift : shift),
  .in_a(beat == FIRST ? in_data : a),
  .in_b(beat == SECOND ? in_data : beat == THIRD ? b : 128'b0),
  .in_c(beat == THIRD ? in_data : 128'b0),
  .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data),
  .out_error(out_error), .out_saturated(out_saturated)
 );
endmodule
