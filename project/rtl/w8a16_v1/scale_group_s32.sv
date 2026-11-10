// Candidate group scale service. Positive finite nonzero FP16 weight scales.
// A is formed from Q16 input by RNE shift in [0,17]. Each group is rounded
// to Q16 before adding the previous S32 projection state; final bias is Q16.
// No persistent S64/S128. A 44-bit product and range-before-left-shift avoid
// an unbounded wide accumulator. Any active lane fault rejects the vector.
module scale_group_s32 (
 input wire clk, reset,
 input wire in_valid, output wire in_ready,
 input wire [31:0] in_tag,
 input wire [3:0] in_n,
 input wire in_first, in_final,
 input wire [5:0] in_a_shift,
 input wire [255:0] in_partial,
 input wire [127:0] in_scale_fp16,
 input wire [255:0] in_previous, in_bias,
 output reg out_valid, input wire out_ready,
 output reg [31:0] out_tag,
 output reg [255:0] out_data,
 output reg out_error
);
 assign in_ready = !reset && (!out_valid || out_ready);
 function automatic [32:0] scale_lane(
  input signed [31:0] partial,
  input [15:0] fp,
  input [5:0] a_shift
 );
  reg [10:0] mantissa;
  reg signed [43:0] product, rounded;
  reg [43:0] remainder_bits, half_value, mask;
  reg signed [43:0] lower_bound, upper_bound;
  reg bad;
  integer shift, right_shift;
  begin
   bad = fp[15] || fp[14:10]==31 || fp[14:0]==0 || a_shift>17;
   mantissa = fp[14:10]==0 ? {1'b0,fp[9:0]} : {1'b1,fp[9:0]};
   shift = int'(a_shift) + (fp[14:10]==0 ? -24 : int'(fp[14:10])-25);
   product = partial * $signed({1'b0,mantissa});
   rounded = 0;
   if (!bad) begin
    if (shift>=0) begin
     // Bounds are exact for shifts [0,22]; the lower bound is a power of two.
     lower_bound = -44'sd2147483648 >>> shift;
     upper_bound = 44'sd2147483647 >>> shift;
     if (product<lower_bound || product>upper_bound) bad=1;
     else rounded=product <<< shift;
    end else begin
     right_shift=-shift;
     mask=(44'd1 << right_shift)-1'b1;
     remainder_bits=$unsigned(product) & mask;
     half_value=44'd1 << (right_shift-1);
     rounded=product >>> right_shift;
     if (remainder_bits>half_value ||
         (remainder_bits==half_value && rounded[0])) rounded=rounded+1'b1;
     if (rounded < -44'sd2147483648 || rounded > 44'sd2147483647) bad=1;
    end
   end
   scale_lane={bad,bad ? 32'd0 : rounded[31:0]};
  end
 endfunction
 wire [32:0] scaled [0:7];
 wire signed [32:0] summed [0:7];
 wire signed [33:0] biased [0:7];
 wire [7:0] bad_lane;
 wire bad_vector = in_n==0 || in_n>8 || (|bad_lane);
 for (genvar n=0; n<8; n=n+1) begin: lanes
  assign scaled[n]=scale_lane($signed(in_partial[n*32+:32]),
                              in_scale_fp16[n*16+:16], in_a_shift);
  assign summed[n]=$signed({scaled[n][31],scaled[n][31:0]}) +
   (in_first ? 33'sd0 : $signed({in_previous[n*32+31],in_previous[n*32+:32]}));
  assign biased[n]=$signed({summed[n][32],summed[n]}) +
   (in_final ? $signed({{2{in_bias[n*32+31]}},in_bias[n*32+:32]}) : 34'sd0);
  assign bad_lane[n]=n<in_n && (scaled[n][32] || summed[n][32]!=summed[n][31] ||
                                               biased[n][33:31]!={3{biased[n][31]}});
 end
 always @(posedge clk) begin
  if (reset) begin out_valid<=0; out_tag<=0; out_data<=0; out_error<=0; end
  else if (in_ready) begin
   out_valid<=in_valid;
   if (in_valid) begin
    out_tag<=in_tag; out_error<=bad_vector;
    for (integer n=0; n<8; n=n+1)
     out_data[n*32+:32]<=!bad_vector && n<in_n ? biased[n][31:0] : 32'd0;
   end
  end
 end
endmodule
