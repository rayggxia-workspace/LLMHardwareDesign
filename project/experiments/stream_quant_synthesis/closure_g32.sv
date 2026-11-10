// Experimental two-lane G: S32/Q16 inputs, full S64/Q32 gated result.
// Fixed +/-16 SiLU approximation, 2049 Q16 samples, RNE interpolation.
// New active leaf candidate; no inherited area/300MHz/physical qualification.
module closure_g32(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [63:0] in_a,in_b,
 output reg out_valid,input wire out_ready,output reg [127:0] out_data
);
 reg signed [31:0] lut[0:2048];
 initial $readmemh("g32-lut.hex",lut);
 wire advance=!out_valid||out_ready;
 assign in_ready=!reset&&advance;
 reg v0,v1;
 reg signed [31:0] a0[0:1],b0[0:1];
 reg signed [63:0] p1[0:1];
 function automatic signed [31:0] activate(input signed [31:0] x);
  reg [20:0] offset;reg [11:0] index;reg [9:0] fraction;
  reg signed [63:0] delta,interpolation,q;
  begin
   if(x<=-32'sd1048576)activate=0;
   else if(x>=32'sd1048576)activate=x;
   else begin
    offset=21'($unsigned(x+32'sd1048576));index=12'(offset>>10);fraction=offset[9:0];
    delta={{32{lut[index+1'b1][31]}},lut[index+1'b1]}-{{32{lut[index][31]}},lut[index]};
    interpolation=delta*$signed({1'b0,fraction});q=interpolation>>>10;
    if(interpolation[9:0]>10'd512||(interpolation[9:0]==10'd512&&q[0]))q=q+1;
    activate=32'($signed({{32{lut[index][31]}},lut[index]})+q);
   end
  end
 endfunction
 always @(posedge clk)begin
  if(reset)begin v0<=0;v1<=0;out_valid<=0;out_data<=0;end
  else if(advance)begin
   out_valid<=v1;
   if(v1)for(integer i=0;i<2;i=i+1)out_data[i*64+:64]<=p1[i];
   v1<=v0;
   if(v0)for(integer i=0;i<2;i=i+1)p1[i]<=a0[i]*b0[i];
   v0<=in_valid;
   if(in_valid)for(integer i=0;i<2;i=i+1)begin
    a0[i]<=activate($signed(in_a[i*32+:32]));b0[i]<=$signed(in_b[i*32+:32]);
   end
  end
 end
endmodule
