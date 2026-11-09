// New independent leaf candidate, NOT the qualified block_v2_m ABI.
// 16 K positions x 8 outputs: S32 x signed/unsigned byte products.
// Wider B formats use explicit byte-plane commands with b_shift=0/8/16/24.
// 8 row contexts, exact 96-bit full-K sums; one final RNE/S32 saturation.
// Four registered stages. A stalled output freezes all stages/contexts.
module m_s32_stream_candidate #(
 parameter integer K=16, N=8, ROWS=8
)(
 input wire clk,reset,
 input wire in_valid,output wire in_ready,
 input wire [2:0] in_row,input wire in_first,in_last,
 input wire [5:0] in_k,input wire [3:0] in_n,
 input wire [5:0] in_round_shift,input wire [4:0] in_b_shift,input wire in_b_unsigned,
 input wire [K*32-1:0] in_a,input wire [N*K*8-1:0] in_b,
 output reg out_valid,input wire out_ready,output reg [2:0] out_row,
 output reg [N*32-1:0] out_data,output reg [N-1:0] out_saturated,output reg out_error
);
 wire advance=!out_valid||out_ready;
 assign in_ready=!reset&&advance;
 reg v0,v1,v2;
 reg [2:0] row0,row1,row2;
 reg first0,last0,first1,last1,bad0,bad1,error2;
 reg [3:0] n0,n1,n2;reg [5:0] round0,round1,round2;
 reg [4:0] bshift0,bshift1;
 reg signed [40:0] products[0:N-1][0:K-1];
 reg signed [47:0] sums[0:N-1];
 reg signed [95:0] accum[0:ROWS-1][0:N-1],total2[0:N-1];
 reg [ROWS-1:0] context_valid;reg [3:0] context_n[0:ROWS-1];
 reg signed [47:0] reduction;
 reg signed [95:0] term,total;
 reg fault;reg [32:0] converted;
 function automatic signed [40:0] byte_product;
  input signed [31:0] a;input [7:0] b;input is_unsigned;
  reg signed [8:0] digit;
  begin digit=is_unsigned?$signed({1'b0,b}):$signed({b[7],b});byte_product=a*digit;end
 endfunction
 function automatic [32:0] quantize;
  input signed [95:0] value;input [5:0] shift;
  reg signed [95:0] q,remn,half;
  begin
   q=value>>>shift;remn=value-(q<<<shift);half=96'sd1<<(shift==0?0:shift-1);
   if(shift!=0&&(remn>half||(remn==half&&q[0])))q=q+1;
   if(q>96'sd2147483647)quantize={1'b1,32'h7fffffff};
   else if(q< -96'sd2147483648)quantize={1'b1,32'h80000000};
   else quantize={1'b0,q[31:0]};
  end
 endfunction
 always @(posedge clk)begin
  if(reset)begin
   v0<=0;v1<=0;v2<=0;out_valid<=0;out_error<=0;out_data<=0;out_saturated<=0;out_row<=0;
   context_valid<=0;
  end else if(advance)begin
   out_valid<=v2;
   if(v2)begin
    out_row<=row2;out_error<=error2;
    for(integer n=0;n<N;n=n+1)begin
     converted=quantize(total2[n],round2);
     out_data[32*n+:32]<=!error2&&n<n2?converted[31:0]:32'd0;
     out_saturated[n]<=!error2&&n<n2&&converted[32];
    end
   end
   v2<=0;
   if(v1)begin
    fault=bad1||(!first1&&!context_valid[row1])||(!first1&&context_valid[row1]&&context_n[row1]!=n1);
    v2<=last1||fault;row2<=row1;round2<=round1;n2<=n1;error2<=fault;
    if(!fault)begin
     context_valid[row1]<=!last1;context_n[row1]<=n1;
     for(integer n=0;n<N;n=n+1)begin
      term={{48{sums[n][47]}},sums[n]};term=term<<<bshift1;
      total=(first1?96'sd0:accum[row1][n])+term;
      accum[row1][n]<=n<n1?total:96'sd0;total2[n]<=n<n1?total:96'sd0;
     end
    end else begin context_valid[row1]<=0;for(integer n=0;n<N;n=n+1)total2[n]<=0;end
   end
   v1<=v0;row1<=row0;first1<=first0;last1<=last0;bad1<=bad0;n1<=n0;round1<=round0;bshift1<=bshift0;
   if(v0)for(integer n=0;n<N;n=n+1)begin
    reduction=0;for(integer k=0;k<K;k=k+1)reduction=reduction+{{7{products[n][k][40]}},products[n][k]};
    sums[n]<=reduction;
   end
   v0<=in_valid;
   if(in_valid)begin
    row0<=in_row;first0<=in_first;last0<=in_last;n0<=in_n;round0<=in_round_shift;bshift0<=in_b_shift;
    bad0<=in_k==0||in_k>K||in_n==0||in_n>N||in_row>=ROWS||
     !(in_b_shift==0||in_b_shift==8||in_b_shift==16||in_b_shift==24);
    for(integer n=0;n<N;n=n+1)for(integer k=0;k<K;k=k+1)
     products[n][k]<=k<in_k&&n<in_n?byte_product($signed(in_a[32*k+:32]),in_b[(n*K+k)*8+:8],in_b_unsigned):41'sd0;
   end
  end
 end
endmodule
