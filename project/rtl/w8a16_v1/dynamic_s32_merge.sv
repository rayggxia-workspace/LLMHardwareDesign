// Independent exact dynamic full-K S32 dot merge. Refs #250.
// One owned 8x80-bit transient accumulator; all persistent results are S32.
// Input partials are K128/A(radix15)xW(radix7) in kk,ai,bi order. No
// intermediate rounding. The final partial performs one full-K RNE/saturate.
module dynamic_s32_merge (
 input wire clk, reset,
 input wire in_valid, output wire in_ready,
 input wire [1:0] in_kind, // 0 BEGIN, 1 PARTIAL, 2 CANCEL; 3 rejected.
 input wire [127:0] in_key,
 input wire [31:0] in_tag,
 input wire [15:0] in_full_k, in_kk,
 input wire [7:0] in_length,
 input wire [3:0] in_n,
 input wire [1:0] in_ai,
 input wire [2:0] in_bi,
 input wire [5:0] in_shift,
 input wire [255:0] in_raw,
 output reg out_valid, input wire out_ready,
 output reg [1:0] out_kind,
 output reg [127:0] out_key,
 output reg [31:0] out_tag,
 output reg out_error, out_done,
 output reg [255:0] out_data
);
 localparam [1:0] IDLE=0, APPLY=1, ROUND=2;
 reg [1:0] state;
 reg active;
 reg [127:0] owner;
 reg [15:0] full_k, next_kk;
 reg [3:0] lanes;
 reg [1:0] next_ai;
 reg [2:0] next_bi;
 reg [5:0] final_shift;
 reg signed [79:0] accum [0:7];
 reg [255:0] raw_hold;
 reg [5:0] digit_shift;
 reg packet_last;
 wire response_space=!out_valid || out_ready;
 assign in_ready=!reset && state==IDLE && response_space;
 wire [16:0] remaining={1'b0,full_k}-{1'b0,next_kk};
 wire [7:0] expected_length=remaining>17'd128 ? 8'd128 : remaining[7:0];
 wire last_pair=next_ai==2 && next_bi==4;
 wire last_k={1'b0,next_kk}+{9'd0,expected_length}=={1'b0,full_k};
 wire [5:0] offered_digit_shift={4'd0,in_ai}*6'd15+{3'd0,in_bi}*6'd7;
 wire [21:0] bound_per_k=in_ai==2 ? (in_bi==4 ? 22'd16 : 22'd254) :
  (in_bi==4 ? 22'd262136 : 22'd4161409);
 wire [29:0] bound_product={22'd0,in_length}*{8'd0,bound_per_k};
 wire [63:0] raw_bound={34'd0,bound_product};
 reg raw_bad;
 always @* begin
  raw_bad=0;
  for(integer j=0;j<8;j=j+1) begin
   if(j<int'(in_n)) begin
    if($signed({{32{in_raw[j*32+31]}},in_raw[j*32+:32]})>$signed(raw_bound) ||
       $signed({{32{in_raw[j*32+31]}},in_raw[j*32+:32]})<-$signed(raw_bound)) raw_bad=1;
   end else if(in_raw[j*32+:32]!=0) raw_bad=1;
  end
 end
 wire partial_bad=!active || in_key!=owner || in_full_k!=full_k ||
  in_kk!=next_kk || in_ai!=next_ai || in_bi!=next_bi || in_n!=lanes ||
  in_length!=expected_length || raw_bad;
 function automatic [31:0] rne_saturate(input signed [79:0] value,input [5:0] shift);
  reg signed [79:0] q;
  reg [79:0] mask, rem_bits, half_value;
  begin
   q=value;
   if(shift!=0) begin
    mask=(80'd1<<shift)-1'b1;rem_bits=$unsigned(value)&mask;
    half_value=80'd1<<(shift-1'b1);q=value>>>shift;
    if(rem_bits>half_value || (rem_bits==half_value && q[0]))q=q+1'b1;
   end
   if(q>80'sd2147483647)rne_saturate=32'h7fffffff;
   else if(q < -80'sd2147483648)rne_saturate=32'h80000000;
   else rne_saturate=q[31:0];
  end
 endfunction
 always @(posedge clk) begin
  if(reset) begin
   state<=IDLE;active<=0;owner<=0;full_k<=0;next_kk<=0;lanes<=0;
   next_ai<=0;next_bi<=0;final_shift<=0;raw_hold<=0;digit_shift<=0;packet_last<=0;
   out_valid<=0;out_kind<=0;out_key<=0;out_tag<=0;out_error<=0;out_done<=0;out_data<=0;
   for(integer j=0;j<8;j=j+1)accum[j]<=0;
  end else begin
   if(out_valid && out_ready)out_valid<=0;
   case(state)
    IDLE: if(in_valid && in_ready) begin
     out_kind<=in_kind;out_key<=in_key;out_tag<=in_tag;
     out_error<=0;out_done<=0;out_data<=0;
     if(in_kind==0) begin
      out_valid<=1;
      if(active || in_full_k==0 || in_n==0 || in_n>8)out_error<=1;
      else begin
       active<=1;owner<=in_key;full_k<=in_full_k;lanes<=in_n;final_shift<=in_shift;
       next_kk<=0;next_ai<=0;next_bi<=0;
       for(integer j=0;j<8;j=j+1)accum[j]<=0;
      end
     end else if(in_kind==1) begin
      if(partial_bad)begin out_valid<=1;out_error<=1;end
      else begin
       raw_hold<=in_raw;digit_shift<=offered_digit_shift;
       packet_last<=last_pair && last_k;state<=APPLY;
       if(last_pair)begin next_ai<=0;next_bi<=0;next_kk<=next_kk+{8'd0,expected_length};end
       else if(next_bi==4)begin next_bi<=0;next_ai<=next_ai+1'b1;end
       else next_bi<=next_bi+1'b1;
      end
     end else if(in_kind==2) begin
      out_valid<=1;
      if(!active || in_key!=owner)out_error<=1;
      else begin active<=0;out_done<=1;end
     end else begin out_valid<=1;out_error<=1;end
    end
    APPLY: begin
     for(integer j=0;j<8;j=j+1)
      accum[j]<=accum[j]+($signed({{48{raw_hold[j*32+31]}},raw_hold[j*32+:32]})<<<digit_shift);
     state<=ROUND;
    end
    ROUND: begin
     out_valid<=1;out_done<=packet_last;
     if(packet_last) begin
      active<=0;
      for(integer j=0;j<8;j=j+1)
       out_data[j*32+:32]<=j<int'(lanes) ? rne_saturate(accum[j],final_shift) : 32'd0;
     end
     state<=IDLE;
    end
    default: state<=IDLE;
   endcase
  end
 end
endmodule
