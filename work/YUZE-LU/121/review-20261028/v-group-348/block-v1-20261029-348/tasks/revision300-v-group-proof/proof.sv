module proof(input [129:0] a,b,output ok,bad_ok);
 function automatic [130:0] subtract130_grouped;
  input [129:0] left,right;
  reg [8:0] subtotal[0:15];reg [2:0] top;
  reg [16:0] propagate;reg [17:0] carry;
  reg [129:0] result;integer g;
  begin
   for(g=0;g<16;g=g+1)begin
    subtotal[g]={1'b0,left[8*g+:8]}+{1'b0,~right[8*g+:8]};
    propagate[g]=&(left[8*g+:8]^~right[8*g+:8]);
   end
   top={1'b0,left[129:128]}+{1'b0,~right[129:128]};
   propagate[16]=&(left[129:128]^~right[129:128]);
   carry[0]=1'b1;
   for(g=0;g<16;g=g+1)begin
    carry[g+1]=subtotal[g][8]|(propagate[g]&carry[g]);
    result[8*g+:8]=subtotal[g][7:0]+carry[g];
   end
   carry[17]=top[2]|(propagate[16]&carry[16]);
   result[129:128]=top[1:0]+carry[16];
   subtract130_grouped={carry[17],result};
  end
 endfunction
wire [130:0] actual=subtract130_grouped(a,b);
wire [130:0] reference={1'b0,a}+{1'b0,~b}+131'd1;
wire [129:0] selected=actual[130]?actual[129:0]:a;
wire [129:0] expected=(a>=b)?a-b:a;
assign ok=(actual==reference)&&(actual[130]==(a>=b))&&(selected==expected);
assign bad_ok=((actual^131'h40000)==reference);
endmodule
