// Independent group arithmetic: exact U128 division and integer square root.
// No sharing with the eight elementwise or two function-lane multipliers.
module block_v1_v_group(
 input wire clk,reset,in_valid,output wire in_ready,input wire square_root,
 input wire [127:0] numerator,denominator,
 output reg out_valid,input wire out_ready,output reg [127:0] quotient,remainder,
 output reg error
);
 reg running,sqrt_mode;reg [7:0] count;
 reg [127:0] digits,divisor,q;
 reg [129:0] remn;
 reg [63:0] root;
 reg [129:0] shifted,trial,next_rem;
 reg [130:0] difference;
 reg [127:0] next_q;reg [63:0] next_root;
 // One unsigned subtract supplies both the difference and no-borrow decision.
 // Byte-local sums and group carries retain all130 bits without serializing
 // a separate full-width comparison ahead of the subtract result mux.
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
 assign in_ready=!reset&&!running&&!out_valid;
 always @* begin
  shifted=sqrt_mode?(remn<<2)|{128'b0,digits[127:126]}:(remn<<1)|{129'b0,digits[127]};
  trial=sqrt_mode?({66'b0,root}<<2)|130'd1:{2'b0,divisor};
  difference=subtract130_grouped(shifted,trial);
  next_rem=difference[130]?difference[129:0]:shifted;
  next_q=(q<<1)|difference[130];
  next_root=(root<<1)|difference[130];
 end
 always @(posedge clk)begin
  if(reset)begin running<=0;out_valid<=0;error<=0;quotient<=0;remainder<=0;end
  else begin
   if(out_valid&&out_ready)out_valid<=0;
   if(in_valid&&in_ready)begin
    error<=0;count<=0;digits<=numerator;divisor<=denominator;q<=0;remn<=0;root<=0;sqrt_mode<=square_root;
    if(!square_root&&denominator==0)begin out_valid<=1;error<=1;quotient<=0;remainder<=0;end
    else running<=1;
   end else if(running)begin
    remn<=next_rem;q<=next_q;root<=next_root;digits<=sqrt_mode?digits<<2:digits<<1;
    if((sqrt_mode&&count==63)||(!sqrt_mode&&count==127))begin
     running<=0;out_valid<=1;quotient<=sqrt_mode?{64'b0,next_root}:next_q;remainder<=next_rem[127:0];
    end else count<=count+1;
   end
  end
 end
endmodule
