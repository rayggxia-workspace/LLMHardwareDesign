module r_temp_proof(input [4:0] phase,input signed [64:0] product,
input signed [63:0] dot,input signed [31:0] x,error_value,product_state_base,output_value,
output ok);
reg signed [127:0] value_old;
reg signed [51:0] value_new;
 localparam IDLE=0,DEC_MUL=1,DEC_WRITE=2,PRED_MUL=3,PRED_ADD=4,
 PRED_END=5,ERR_PREP=6,ERR_MUL=7,ERR_WRITE=8,UP_MUL=9,UP_WRITE=10,
 READ_MUL=11,READ_ADD=12,READ_END=13,SKIP_MUL=14,SKIP_WRITE=15,
 CONV_MUL=16,CONV_ADD=17,CONV_END=18,FINISH=19,COPY=20,
 ERR_FETCH=21,SKIP_FETCH=22,CONV_FETCH=23;
 function automatic signed [127:0] rne_old;
  input signed [127:0] v;input [6:0] sh;
  reg signed [127:0] q;reg [127:0] remn,half;
  begin
   if(sh==0)rne_old=v;
   else begin q=v>>>sh;remn=$unsigned(v)&({128{1'b1}}>>(128-sh));
    half=128'd1<<(sh-1);rne_old=q+((remn>half)||((remn==half)&&q[0]));end
  end
 endfunction
 function automatic fits32_old;
  input signed [127:0] v;
  begin fits32_old=v[127:31]=={97{v[31]}};end
 endfunction
always @* begin case(phase)
    DEC_MUL,DEC_WRITE,ERR_WRITE:value_old=rne_old({{63{product[64]}},product},31);
    PRED_END,READ_END,CONV_END:value_old=rne_old(dot,14);
    ERR_PREP:value_old=$signed({{96{x[31]}},x})-$signed({{96{error_value[31]}},error_value});
    UP_MUL,UP_WRITE:value_old=$signed({{96{product_state_base[31]}},product_state_base})+rne_old({{63{product[64]}},product},14);
    SKIP_WRITE:value_old=$signed({{96{output_value[31]}},output_value})+rne_old({{63{product[64]}},product},16);
    default:value_old=0;
endcase end
 function automatic signed [51:0] rne_new;
  input signed [64:0] v;input [6:0] sh;
  reg signed [64:0] q;reg [64:0] remn,half;
  begin
   if(sh==0)rne_new=v[51:0];
   else begin q=v>>>sh;remn=$unsigned(v)&({65{1'b1}}>>(65-sh));
    half=65'd1<<(sh-1);rne_new=q[51:0]+{{51{1'b0}},((remn>half)||((remn==half)&&q[0]))};end
  end
 endfunction
 function automatic fits32_new;
  input signed [51:0] v;
  begin fits32_new=v[51:31]=={21{v[31]}};end
 endfunction
always @* begin case(phase)
    DEC_MUL,DEC_WRITE,ERR_WRITE:value_new=rne_new(product,31);
    PRED_END,READ_END,CONV_END:value_new=rne_new({dot[63],dot},14);
    ERR_PREP:value_new=$signed({{20{x[31]}},x})-$signed({{20{error_value[31]}},error_value});
    UP_MUL,UP_WRITE:value_new=$signed({{20{product_state_base[31]}},product_state_base})+rne_new(product,14);
    SKIP_WRITE:value_new=$signed({{20{output_value[31]}},output_value})+rne_new(product,16);
    default:value_new=0;
endcase end

assign ok=(value_old=={{76{value_new[51]}},value_new})
 && (fits32_old(value_old)==fits32_new(value_new));
endmodule
