// Candidate raw group dot, not a qualified replacement for the main M macro.
// Eight columns x sixteen A16/W8 products per accepted beat. One group is
// contiguous, with K=16 (head) or K=128. Projection contexts belong to the
// subsequent scale/state service; this core holds only one eight-lane group.
// Malformed beats report an error without changing the current group.
module m_group_s32 (
 input wire clk, reset,
 input wire in_valid, output wire in_ready,
 input wire in_first, in_last,
 input wire [31:0] in_tag,
 input wire [7:0] in_group_k, in_offset,
 input wire [4:0] in_k,
 input wire [3:0] in_n,
 input wire [255:0] in_a,
 input wire [1023:0] in_w,
 output reg out_valid, input wire out_ready,
 output reg [31:0] out_tag,
 output reg [3:0] out_n,
 output reg [255:0] out_data,
 output reg out_error
);
 wire advance = !out_valid || out_ready;
 assign in_ready = !reset && advance;
 reg v0, v1, first0, first1, last0, last1, bad0, bad1;
 reg [31:0] tag0, tag1, active_tag;
 reg [7:0] group0, group1, offset0, offset1, active_group, next_offset;
 reg [4:0] k0, k1;
 reg [3:0] n0, n1, active_n;
 reg active;
 reg signed [23:0] product [0:7][0:15];
 wire signed [27:0] tree1 [0:7][0:7];
 wire signed [27:0] tree2 [0:7][0:3];
 wire signed [27:0] tree3 [0:7][0:1];
 wire signed [27:0] tree4 [0:7];
 reg signed [27:0] beat_sum [0:7];
 reg signed [31:0] accumulator [0:7];
 wire signed [31:0] total [0:7];
 wire [8:0] end_offset = {1'b0,offset1} + {4'b0,k1};
 wire fault = bad1 ||
   (first1 ? (active || offset1 != 0) :
    (!active || tag1 != active_tag || group1 != active_group ||
     offset1 != next_offset || n1 != active_n)) ||
   end_offset > {1'b0,group1} ||
   (last1 != (end_offset == {1'b0,group1}));
 for (genvar n=0; n<8; n=n+1) begin: columns
  for (genvar k=0; k<8; k=k+1) begin: pairs
   assign tree1[n][k] = {{4{product[n][2*k][23]}},product[n][2*k]} +
                        {{4{product[n][2*k+1][23]}},product[n][2*k+1]};
  end
  for (genvar k=0; k<4; k=k+1) begin: fours
   assign tree2[n][k] = tree1[n][2*k] + tree1[n][2*k+1];
  end
  for (genvar k=0; k<2; k=k+1) begin: eights
   assign tree3[n][k] = tree2[n][2*k] + tree2[n][2*k+1];
  end
  assign tree4[n] = tree3[n][0] + tree3[n][1];
  assign total[n] = (first1 ? 32'sd0 : accumulator[n]) +
                    {{4{beat_sum[n][27]}},beat_sum[n]};
 end
 always @(posedge clk) begin
  if (reset) begin
   v0<=0; v1<=0; active<=0; out_valid<=0; out_error<=0;
   out_tag<=0; out_n<=0; out_data<=0;
   active_tag<=0; active_group<=0; active_n<=0; next_offset<=0;
  end else if (advance) begin
   out_valid<=0;
   if (v1) begin
    out_valid<=last1 || fault;
    if (last1 || fault) begin
     out_tag<=tag1; out_n<=n1; out_error<=fault;
     for (integer n=0; n<8; n=n+1)
      out_data[n*32+:32]<=(!fault && n<n1) ? total[n] : 32'd0;
    end
    if (!fault) begin
     active<=!last1; active_tag<=tag1; active_group<=group1;
     active_n<=n1; next_offset<=end_offset[7:0];
     for (integer n=0; n<8; n=n+1)
      accumulator[n]<=n<n1 ? total[n] : 32'sd0;
    end
   end
   v1<=v0; first1<=first0; last1<=last0; bad1<=bad0;
   tag1<=tag0; group1<=group0; offset1<=offset0; k1<=k0; n1<=n0;
   if (v0) for (integer n=0; n<8; n=n+1) beat_sum[n]<=tree4[n];
   v0<=in_valid;
   if (in_valid) begin
    first0<=in_first; last0<=in_last; tag0<=in_tag;
    group0<=in_group_k; offset0<=in_offset; k0<=in_k; n0<=in_n;
    bad0<=in_k==0 || in_k>16 || in_n==0 || in_n>8 ||
          (in_group_k!=16 && in_group_k!=128);
    for (integer n=0; n<8; n=n+1)
     for (integer k=0; k<16; k=k+1)
      product[n][k]<=(n<in_n && k<in_k) ?
       $signed(in_a[k*16+:16]) * $signed(in_w[(n*16+k)*8+:8]) : 24'sd0;
   end
  end
 end
endmodule
