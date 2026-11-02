// Local exact U64 divider and U64->U32 floor square root. No V-wide U128 path.
module block_v2_n_group(
 input wire clk,reset,in_valid,output wire in_ready,input wire square_root,
 input wire [63:0] numerator,denominator,
 output reg out_valid,input wire out_ready,
 output reg [63:0] quotient,remainder,output reg error
);
 reg running,root_mode;reg [5:0] count;
 reg [63:0] digits,divisor,q;reg [65:0] remn;
 reg [31:0] root;
 wire [65:0] shifted=root_mode?(remn<<2)|{64'd0,digits[63:62]}:(remn<<1)|{65'd0,digits[63]};
 wire [65:0] trial=root_mode?({34'd0,root}<<2)|66'd1:{2'd0,divisor};
 wire [66:0] difference={1'b0,shifted}+{1'b0,~trial}+67'd1;
 wire [65:0] next_rem=difference[66]?difference[65:0]:shifted;
 wire [63:0] next_q=(q<<1)|{63'd0,difference[66]};
 wire [31:0] next_root=(root<<1)|{31'd0,difference[66]};
 assign in_ready=!reset&&!running&&!out_valid;
 always @(posedge clk)begin
  if(reset)begin running<=0;out_valid<=0;quotient<=0;remainder<=0;error<=0;end
  else begin
   if(out_valid&&out_ready)out_valid<=0;
   if(in_valid&&in_ready)begin
    error<=0;count<=0;digits<=numerator;divisor<=denominator;q<=0;remn<=0;root<=0;root_mode<=square_root;
    if(!square_root&&denominator==0)begin out_valid<=1;error<=1;quotient<=0;remainder<=0;end
    else running<=1;
   end else if(running)begin
    remn<=next_rem;q<=next_q;root<=next_root;digits<=root_mode?digits<<2:digits<<1;
    if((root_mode&&count==31)||(!root_mode&&count==63))begin
     running<=0;out_valid<=1;quotient<=root_mode?{32'd0,next_root}:next_q;remainder<=next_rem[63:0];
    end else count<=count+1'b1;
   end
  end
 end
endmodule
