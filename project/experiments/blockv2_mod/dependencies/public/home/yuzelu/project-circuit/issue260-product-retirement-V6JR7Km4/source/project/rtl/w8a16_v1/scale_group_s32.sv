// Exact Q16 group scaling, split at multiplier / RNE / prefix-add boundaries.
// Three elastic stages. The owner RF commits only the final vector response;
// an active-lane error rejects the entire vector. Latency is ready/valid driven.
module scale_group_s32 #(
 // Projection RF adds its live prefix after these two arithmetic stages.
 // Standalone users retain the original three-stage previous/bias behavior.
 parameter bit ROUND_ONLY = 1'b0
) (
 input wire clk, reset,
 input wire in_valid, output wire in_ready,
 input wire [31:0] in_tag,
 input wire [3:0] in_n,
 input wire in_first, in_final,
 input wire [5:0] in_a_shift,
 input wire [255:0] in_partial,
 input wire [127:0] in_scale_fp16,
 input wire [255:0] in_previous, in_bias,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_tag,
 output wire [255:0] out_data,
 output wire out_error
);
 reg product_valid, rounded_valid;
 reg final_valid, final_error;
 reg [31:0] final_tag;
 reg [255:0] final_data;
 wire output_ready = ROUND_ONLY ? out_ready : (!final_valid || out_ready);
 wire rounded_ready = !rounded_valid || output_ready;
 wire product_ready = !product_valid || rounded_ready;
 assign in_ready = !reset && product_ready;
 reg [31:0] product_tag, rounded_tag;
 reg [3:0] product_n, rounded_n;
 reg product_final, rounded_final;
 reg [255:0] product_previous, product_bias, rounded_previous, rounded_bias;
 reg signed [43:0] products [0:7];
 reg signed [6:0] shifts [0:7];
 reg [7:0] product_bad, rounded_bad;
 reg [255:0] rounded_data;
 wire [7:0] rounded_active_bad;
 for(genvar active=0;active<8;active=active+1) begin: round_status
  assign rounded_active_bad[active]=active<rounded_n && rounded_bad[active];
 end
 wire rounded_error = rounded_n==0 || rounded_n>8 || (|rounded_active_bad);
 assign out_valid = ROUND_ONLY ? rounded_valid : final_valid;
 assign out_tag = ROUND_ONLY ? rounded_tag : final_tag;
 assign out_data = ROUND_ONLY ? (rounded_error ? 256'd0 : rounded_data) : final_data;
 assign out_error = ROUND_ONLY ? rounded_error : final_error;

 function automatic [32:0] round_lane(
  input signed [43:0] product,
  input signed [6:0] exponent_shift,
  input invalid
 );
  reg signed [43:0] rounded, lower_bound, upper_bound;
  reg [43:0] remainder_bits, half_value, mask;
  reg bad;
  integer shift, right_shift;
  begin
   bad=invalid; rounded=0; shift=int'(exponent_shift);
   if(!bad) begin
    if(shift>=0) begin
     lower_bound=-44'sd2147483648 >>> shift;
     upper_bound=44'sd2147483647 >>> shift;
     if(product<lower_bound || product>upper_bound) bad=1;
     else rounded=product <<< shift;
    end else begin
     right_shift=-shift;
     mask=(44'd1 << right_shift)-1'b1;
     remainder_bits=$unsigned(product) & mask;
     half_value=44'd1 << (right_shift-1);
     rounded=product >>> right_shift;
     if(remainder_bits>half_value ||
        (remainder_bits==half_value && rounded[0])) rounded=rounded+1'b1;
     if(rounded < -44'sd2147483648 || rounded > 44'sd2147483647) bad=1;
    end
   end
   round_lane={bad,bad ? 32'd0 : rounded[31:0]};
  end
 endfunction

 wire [32:0] rounded_lane [0:7];
 wire signed [32:0] summed [0:7];
 wire signed [33:0] biased [0:7];
 wire [7:0] bad_lane;
 wire bad_vector = rounded_n==0 || rounded_n>8 || (|bad_lane);
 for(genvar n=0;n<8;n=n+1) begin: lanes
  wire [15:0] fp = in_scale_fp16[n*16+:16];
  wire [10:0] mantissa = fp[14:10]==0 ? {1'b0,fp[9:0]} : {1'b1,fp[9:0]};
  wire signed [6:0] exponent_shift = $signed({1'b0,in_a_shift}) +
      (fp[14:10]==0 ? -7'sd24 : $signed({2'b0,fp[14:10]})-7'sd25);
  assign rounded_lane[n]=round_lane(products[n],shifts[n],product_bad[n]);
  assign summed[n]=$signed({rounded_data[n*32+31],rounded_data[n*32+:32]}) +
    $signed({rounded_previous[n*32+31],rounded_previous[n*32+:32]});
  assign biased[n]=$signed({summed[n][32],summed[n]}) +
    (rounded_final ? $signed({{2{rounded_bias[n*32+31]}},rounded_bias[n*32+:32]}) : 34'sd0);
  assign bad_lane[n]=n<rounded_n && (rounded_bad[n] ||
    summed[n][32]!=summed[n][31] || biased[n][33:31]!={3{biased[n][31]}});

  always @(posedge clk) begin
   if(!reset && product_ready && in_valid) begin
    products[n]<=$signed(in_partial[n*32+:32]) * $signed({1'b0,mantissa});
    shifts[n]<=exponent_shift;
    product_bad[n]<=fp[15] || fp[14:10]==31 || fp[14:0]==0 || in_a_shift>17;
   end
   if(!reset && rounded_ready && product_valid) begin
    rounded_data[n*32+:32]<=rounded_lane[n][31:0];
    rounded_bad[n]<=rounded_lane[n][32];
   end
  end
 end
 always @(posedge clk) begin
  if(reset) begin
   product_valid<=0; rounded_valid<=0; final_valid<=0;
   product_tag<=0; rounded_tag<=0; final_tag<=0; final_data<=0; final_error<=0;
   product_n<=0; rounded_n<=0; product_final<=0; rounded_final<=0;
   product_previous<=0; product_bias<=0; rounded_previous<=0; rounded_bias<=0;
  end else begin
   if(product_ready) begin
    product_valid<=in_valid;
    if(in_valid) begin
     product_tag<=in_tag; product_n<=in_n; product_final<=in_final;
     product_previous<=in_first ? 256'd0 : in_previous;
     product_bias<=in_bias;
    end
   end
   if(rounded_ready) begin
    rounded_valid<=product_valid;
    if(product_valid) begin
     rounded_tag<=product_tag; rounded_n<=product_n; rounded_final<=product_final;
     rounded_previous<=product_previous; rounded_bias<=product_bias;
    end
   end
   if(!ROUND_ONLY && output_ready) begin
    final_valid<=rounded_valid;
    if(rounded_valid) begin
     final_tag<=rounded_tag; final_error<=bad_vector;
     for(integer n=0;n<8;n=n+1)
      final_data[n*32+:32]<=!bad_vector && n<rounded_n ? biased[n][31:0] : 32'd0;
    end
   end
  end
 end
endmodule
