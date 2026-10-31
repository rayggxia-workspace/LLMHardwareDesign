module proof(input [127:0] a,b,input [6:0] sh,input carry_in,output ok,bad_ok);
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
 function automatic signed [127:0] rne;
  input signed [127:0] v;input [6:0] shift;
  reg signed [127:0] q;reg [127:0] remn,half;
  begin if(shift==0)rne=v;else begin q=v>>>shift;remn=$unsigned(v)&({128{1'b1}}>>(128-shift));half=128'd1<<(shift-1);rne=add128_grouped(q,{127'b0,((remn>half)||((remn==half)&&q[0]))},1'b0);end end
 endfunction
 function automatic point_rne_increment;
  input signed [127:0] v;input [6:0] shift;
  reg signed [127:0] q;reg [127:0] remn,half;
  begin
   q=v>>>shift;remn=$unsigned(v)&({128{1'b1}}>>(128-shift));half=128'd1<<(shift-1);
   point_rne_increment=shift!=0&&((remn>half)||((remn==half)&&q[0]));
  end
 endfunction
wire signed [127:0] q=$signed(a)>>>sh;
wire [127:0] remn=a&({128{1'b1}}>>(128-sh));
wire [127:0] half=128'd1<<(sh-1);
wire signed [127:0] reference=sh==0?$signed(a):q+((remn>half)||((remn==half)&&q[0]));
wire [127:0] actual=add128_grouped(a,b,carry_in);
wire signed [127:0] point_result=add128_grouped(q,{127'b0,point_rne_increment(a,sh)},1'b0);
assign ok=(actual==(a+b+carry_in))&&(add128_grouped(a,~b,1'b1)==(a-b))&&(rne(a,sh)==reference)&&(point_result==reference);
assign bad_ok=((actual^128'h40000)==(a+b+carry_in));
endmodule
