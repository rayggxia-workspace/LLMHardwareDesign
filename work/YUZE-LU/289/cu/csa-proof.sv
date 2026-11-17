module csa_proof(input [63:0] a,b,c,output ok);
wire [63:0] gold=a+b+c;
wire [63:0] gate=(a^b^c)+(((a&b)|(a&c)|(b&c))<<1);
assign ok=gold==gate;
endmodule
