// New independent W8 leaf candidate. K16/N8, eight full-K contexts.
// A8 uses S32 accumulation; A16 uses S40. Maximum full K is 16384.
// No scale is applied between K fragments. Requantization is a separate service.
module w8_stream_mac #(
 parameter integer ABITS=8, AW=(ABITS==8?32:40)
)(
 input wire clk,reset,
 input wire in_valid,output wire in_ready,
 input wire [2:0] in_ctx,input wire in_first,in_last,
 input wire [4:0] in_k,input wire [3:0] in_n,input wire [15:0] in_offset,
 input wire [16*ABITS-1:0] in_a,input wire [1023:0] in_b,
 output reg out_valid,input wire out_ready,output reg [2:0] out_ctx,
 output reg [8*AW-1:0] out_data,output reg out_error
);
 localparam integer PW=ABITS+8,TW=PW+4;
 wire advance=!out_valid||out_ready;
 assign in_ready=!reset&&advance;
 reg v0,v1;
 reg [2:0] c0,c1;
 reg f0,f1,l0,l1,bad0,bad1;
 reg [3:0] n0,n1;
 reg [4:0] k0,k1;
 reg [15:0] off0,off1;
 reg signed [PW-1:0] product[0:7][0:15];
 wire signed [TW-1:0] tree1[0:7][0:7],tree2[0:7][0:3],tree3[0:7][0:1],tree4[0:7];
 reg signed [TW-1:0] sum[0:7];
 reg signed [AW-1:0] accum[0:7][0:7];
 reg [7:0] active;
 reg [15:0] next_k[0:7];reg [3:0] saved_n[0:7];
 wire fault=bad1||(f1?(active[c1]||off1!=0):(!active[c1]||next_k[c1]!=off1||saved_n[c1]!=n1))
       ||({1'b0,off1}+{12'b0,k1}>17'd16384);
 wire signed [AW-1:0] total[0:7];
 initial begin
  if(ABITS!=8&&ABITS!=16)$fatal(1,"ABITS must be 8 or 16");
  if(AW!=(ABITS==8?32:40))$fatal(1,"invalid accumulator contract");
 end
 for(genvar n=0;n<8;n=n+1)begin: cols
  for(genvar k=0;k<8;k=k+1)begin: level1
   assign tree1[n][k]={{4{product[n][2*k][PW-1]}},product[n][2*k]}+{{4{product[n][2*k+1][PW-1]}},product[n][2*k+1]};
  end
  for(genvar k=0;k<4;k=k+1)begin: level2
   assign tree2[n][k]=tree1[n][2*k]+tree1[n][2*k+1];
  end
  for(genvar k=0;k<2;k=k+1)begin: level3
   assign tree3[n][k]=tree2[n][2*k]+tree2[n][2*k+1];
  end
  assign tree4[n]=tree3[n][0]+tree3[n][1];
  assign total[n]=(f1?{AW{1'b0}}:accum[c1][n])+{{(AW-TW){sum[n][TW-1]}},sum[n]};
 end
 always @(posedge clk)begin
  if(reset)begin
   v0<=0;v1<=0;active<=0;out_valid<=0;out_error<=0;out_ctx<=0;out_data<=0;
  end else if(advance)begin
   out_valid<=0;
   if(v1)begin
    out_valid<=l1||fault;out_ctx<=c1;out_error<=fault;
    if(!fault)begin
     active[c1]<=!l1;next_k[c1]<=off1+{11'b0,k1};saved_n[c1]<=n1;
     for(integer n=0;n<8;n=n+1)begin
      accum[c1][n]<=n<n1?total[n]:{AW{1'b0}};
      out_data[n*AW+:AW]<=n<n1?total[n]:{AW{1'b0}};
     end
    end else out_data<=0; // rejected command does not corrupt an active context
   end
   v1<=v0;c1<=c0;f1<=f0;l1<=l0;bad1<=bad0;n1<=n0;k1<=k0;off1<=off0;
   if(v0)for(integer n=0;n<8;n=n+1)sum[n]<=tree4[n];
   v0<=in_valid;
   if(in_valid)begin
    c0<=in_ctx;f0<=in_first;l0<=in_last;n0<=in_n;k0<=in_k;off0<=in_offset;
    bad0<=in_k==0||in_k>16||in_n==0||in_n>8;
    for(integer n=0;n<8;n=n+1)for(integer k=0;k<16;k=k+1)begin
     if(k<in_k&&n<in_n)product[n][k]<=$signed(in_a[k*ABITS+:ABITS])*$signed(in_b[(n*16+k)*8+:8]);
     else product[n][k]<={PW{1'b0}};
    end
   end
  end
 end
endmodule
