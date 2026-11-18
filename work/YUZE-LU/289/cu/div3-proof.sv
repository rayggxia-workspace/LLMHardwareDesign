module div3_proof(input [10:0] index, output ok);
 wire [20:0] product = index * 21'd683;
 wire [10:0] q = {1'b0, product[20:11]};
 wire [10:0] r = index - (q + (q << 1));
 assign ok = (q == index / 11'd3) && (r == index % 11'd3);
endmodule
