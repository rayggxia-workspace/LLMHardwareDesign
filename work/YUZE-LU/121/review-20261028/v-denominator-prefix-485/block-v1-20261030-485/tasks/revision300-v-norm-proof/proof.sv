module proof(input signed [64:0] high,low,output ok,bad_ok);
 function automatic signed [127:0] add128_grouped;
  input [127:0] left,right;input carry_in;
  reg [8:0] subtotal[0:15];reg [15:0] propagate;
  reg [16:0] carry;reg [127:0] result;integer g;
  begin
   for(g=0;g<16;g=g+1)begin
    subtotal[g]={1'b0,left[8*g+:8]}+{1'b0,right[8*g+:8]};
    propagate[g]=&(left[8*g+:8]^right[8*g+:8]);
   end
   carry[0]=carry_in;
   for(g=0;g<16;g=g+1)begin
    carry[g+1]=subtotal[g][8]|(propagate[g]&carry[g]);
    result[8*g+:8]=subtotal[g][7:0]+carry[g];
   end
   add128_grouped=result;
  end
 endfunction
 function automatic signed [127:0] norm_merge_rne;
  input signed [64:0] high,low;
  reg increment;
  begin
   increment=(low[31:0]>32'h80000000)||
             ((low[31:0]==32'h80000000)&&(high[0]^low[32]));
   norm_merge_rne=add128_grouped({{63{high[64]}},high},
       $signed({{63{low[64]}},low})>>>32,increment);
  end
 endfunction
wire signed [127:0] high128={{63{high[64]}},high};
wire signed [127:0] low128={{63{low[64]}},low};
wire signed [127:0] merged=(high128<<<32)+low128;
wire signed [127:0] q=merged>>>32;
wire increment=(merged[31:0]>32'h80000000)||
               ((merged[31:0]==32'h80000000)&&q[0]);
wire signed [127:0] reference=q+increment;
wire signed [127:0] actual=norm_merge_rne(high,low);
assign ok=actual==reference;
assign bad_ok=(actual^128'h40000)==reference;
endmodule
