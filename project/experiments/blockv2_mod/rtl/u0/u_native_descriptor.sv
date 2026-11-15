`timescale 1ns/1ps
// Pure format conversion after the native LC's descriptor CRC/topology check.
// The selected service still validates its operational bounds before traffic.
module u_native_descriptor(
 input wire [1023:0] raw,
 input wire [31:0] topology,
 output reg valid,
 output reg [1023:0] compact
);
 wire [31:0] schema=raw[31:0],abi=raw[64+:32];
 wire [15:0] operation=raw[48+:16];
 wire [15:0] a=raw[128+:16],b=raw[144+:16],c=raw[160+:16],n=raw[176+:16];
 wire header=raw[32+:16]==128 && raw[96+:32]==topology && topology!=0;
 wire [63:0] address=raw[192+:64];
 always @* begin
  valid=0;compact=0;
  compact[31:0]=1;
  if(header)begin
   if(schema==32'h31434c44 && abi==32'h02500002 && operation==1)begin
    valid=b>=1&&b<=64&&raw[191:160]==0&&address[6:0]==0&&
       address<=64'h0001000000000000-({48'd0,b}<<7)&&
       ({1'b0,a}+({1'b0,b}<<3))<=1024&&raw[991:256]==0;
    compact[32+:16]=16'h010a;
    compact[512+:48]=address[47:0];compact[576+:32]={16'd0,b};
    compact[608+:32]={16'd0,a};
   end else if(schema==32'h31435344 && abi==32'h02500002 && operation==1)begin
    valid=b>=1&&b<=128&&raw[191:160]==0&&address[5:0]==0&&
       ({1'b0,a}+({1'b0,b}<<2))<=1024&&
       address<=64'd0-({48'd0,b}<<6)&&raw[256+:64]<=64'd0-{48'd0,b}&&raw[991:320]==0;
    compact[32+:16]=16'h010b;
    compact[512+:32]=raw[128+:32];compact[544+:128]=raw[192+:128];
   end else if(schema==32'h384c5244 && abi==32'h02500002 && operation==1)begin
    valid=(a==0||a==512)&&raw[191:144]==0&&address[6:0]==0&&
       address<=64'h0000ffffffffe000&&raw[991:256]==0;
    compact[32+:16]=16'h0105;
    compact[512+:32]=address[31:0];compact[544+:32]={16'd0,address[47:32]};
    compact[608+:32]={16'd0,a};
   end else if(schema==3 && abi==7 && operation==2)begin
    valid=n>0&&n<=1024&&({1'b0,a}+{1'b0,n})<=1024&&
       ({1'b0,b}+{1'b0,n})<=1024&&({1'b0,c}+{1'b0,n})<=1024&&
       (a==c||({1'b0,a}+{1'b0,n})<=c||({1'b0,c}+{1'b0,n})<=a)&&
       (b==c||({1'b0,b}+{1'b0,n})<=c||({1'b0,c}+{1'b0,n})<=b)&&raw[991:192]==0;
    compact[32+:16]=16'h0107;compact[512+:64]=raw[128+:64];
   end else if(schema==3 && abi==7 && operation==3)begin
    valid=((a==0&&b==512)||(a==512&&b==0))&&(c==0||c==512)&&n==0&&
       raw[192+:32]!=0&&raw[991:256]==0&&
       $signed(raw[224+:8])>=-32&&$signed(raw[224+:8])<=31&&
       $signed(raw[240+:8])>=-63&&$signed(raw[240+:8])<=63&&
       $signed(raw[248+:8])>=-63&&$signed(raw[248+:8])<=63;
    compact[32+:16]=16'h0106;
    compact[512+:32]={29'd0,c[9],b[9],a[9]};
    compact[544+:32]=raw[192+:32];compact[576+:32]=raw[224+:32];
   end else if(schema==32'h38535744 && abi==32'h02500002 && operation==1)begin
    valid=raw[128+:32]<=512&&raw[160+:32]==0&&address[5:0]==0&&
       address<=64'hffffffffffffe000&&raw[256+:64]<=64'hffffffffffffff80&&raw[991:320]==0;
    compact[32+:16]=16'h0108;
    compact[512+:32]=raw[128+:32];compact[544+:128]=raw[192+:128];
   end else if(schema==32'h44454650 && abi==32'h02500002 && operation==2)begin
    valid=raw[991:368]==0&&raw[358:352]==0;
    compact[32+:16]=16'h010c;compact[512+:256]=raw[128+:256];
   end else if(schema==32'h44454650 && abi==32'h02500002 && operation==1)begin
    valid=raw[991:352]==0;
    compact[32+:16]=16'h0109;compact[512+:224]=raw[128+:224];
   end else if(schema==32'h31485447 && abi==32'h02500002 && operation==1)begin
    // GTH1: table64, rows32, index-byte16, destination-word16,
    // optional prompt-address64, flags32 (bit0 selects DDR index).
    valid=raw[191:176]==0&&raw[134:128]==0&&raw[192+:32]!=0&&
       raw[224+:16]<16384&&raw[225:224]==0&&
       (raw[240+:16]==0||raw[240+:16]==512)&&
       raw[319:304]==0&&raw[257:256]==0&&
       raw[320+:32]<=1&&raw[991:352]==0;
    compact[32+:16]=16'h0104;
    compact[512+:32]=raw[128+:32];
    compact[544+:32]={raw[224+:16],raw[160+:16]};
    compact[576+:32]=raw[192+:32];compact[608+:32]={16'd0,raw[240+:16]};
    compact[640+:32]=raw[256+:32];
    compact[672+:32]={15'd0,raw[320],raw[288+:16]};
   end
  end
 end
endmodule
