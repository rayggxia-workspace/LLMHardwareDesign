// Eight independent signed8 products; no accumulator or hidden state.
module block_v1_m8(input wire [63:0] a,b,output wire [127:0] product);
 genvar i;generate for(i=0;i<8;i=i+1)begin:LANE
 assign product[16*i+:16]=$signed(a[8*i+:8])*$signed(b[8*i+:8]);
 end endgenerate
endmodule
