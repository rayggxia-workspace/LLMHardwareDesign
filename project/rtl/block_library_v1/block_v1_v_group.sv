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
 reg [127:0] next_q;reg [63:0] next_root;
 assign in_ready=!reset&&!running&&!out_valid;
 always @* begin
  shifted=sqrt_mode?(remn<<2)|{128'b0,digits[127:126]}:(remn<<1)|{129'b0,digits[127]};
  trial=sqrt_mode?({66'b0,root}<<2)|130'd1:{2'b0,divisor};
  next_rem=shifted>=trial?shifted-trial:shifted;
  next_q=(q<<1)|(shifted>=trial);
  next_root=(root<<1)|(shifted>=trial);
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
