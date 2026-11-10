// Four explicit per-output-channel scale/RNE/clamp lanes, one held response.
// Input S64 x positive S16 multiplier, right shift 0..63; output A8/A16/S32.
// Dynamic scale discovery and coefficient approximation are outside this unit.
module w8_requantize4 #(parameter integer QBITS=8)(
 input wire clk,reset,input wire in_valid,output wire in_ready,
 input wire [255:0] in_data,input wire [63:0] in_scale,input wire [23:0] in_shift,input wire [2:0] in_count,
 output reg out_valid,input wire out_ready,output reg [4*QBITS-1:0] out_data,
 output reg [3:0] out_saturated,output reg out_error
);
 assign in_ready=!reset&&(!out_valid||out_ready);
 wire signed [79:0] product[0:3];wire [QBITS:0] converted[0:3];
 wire invalid=in_count==0||in_count>4||
   (in_count>0&&$signed(in_scale[15:0])<=0)||(in_count>1&&$signed(in_scale[31:16])<=0)||
   (in_count>2&&$signed(in_scale[47:32])<=0)||(in_count>3&&$signed(in_scale[63:48])<=0);
 function automatic [QBITS:0] round_even(input signed [79:0] value,input [5:0] shift);
  reg signed [79:0] q,remn,half;
  begin
   q=value>>>shift;remn=value-(q<<<shift);half=80'sd1<<(shift==0?0:shift-1);
   if(shift!=0&&(remn>half||(remn==half&&q[0])))q=q+1;
   if(q>((80'sd1<<(QBITS-1))-1))round_even={1'b1,{1'b0,{(QBITS-1){1'b1}}}};
   else if(q< -(80'sd1<<(QBITS-1)))round_even={1'b1,{1'b1,{(QBITS-1){1'b0}}}};
   else round_even={1'b0,q[QBITS-1:0]};
  end
 endfunction
 for(genvar n=0;n<4;n=n+1)begin: lanes
  assign product[n]=$signed(in_data[n*64+:64])*$signed(in_scale[n*16+:16]);
  assign converted[n]=round_even(product[n],in_shift[n*6+:6]);
 end
 initial if(QBITS!=8&&QBITS!=16&&QBITS!=32)$fatal(1,"QBITS must be 8,16,32");
 always @(posedge clk)begin
  if(reset)begin out_valid<=0;out_data<=0;out_saturated<=0;out_error<=0;end
  else if(in_ready)begin
   out_valid<=in_valid;
   if(in_valid)begin
    out_error<=invalid;
    for(integer n=0;n<4;n=n+1)begin
     out_data[n*QBITS+:QBITS]<=!invalid&&n<in_count?converted[n][QBITS-1:0]:{QBITS{1'b0}};
     out_saturated[n]<=!invalid&&n<in_count&&converted[n][QBITS];
    end
   end
  end
 end
endmodule
