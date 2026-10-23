// Independent C1-RNE candidate: exactly one signed8 multiplier, 25 radix128
// partials. Explicit additional 64-bit add/shift/sign/round/saturation logic.
// No bias input. Not a measured PPA model or an imported llaccel implementation.
module requant_serial(
 input wire clk,input wire reset,
 input wire in_valid,output wire in_ready,
 input wire signed [31:0] in_acc,input wire [30:0] in_m,
 input wire [5:0] in_shift,input wire in_i16,
 output reg out_valid,input wire out_ready,output reg signed [15:0] out_data
);
 localparam IDLE=0,RUN=1,ROUND=2,HOLD=3;
 reg [1:0] state;
 reg [31:0] amag,bmag;
 reg negative,mode16;
 reg [5:0] shift;
 reg [2:0] ai,bi;
 reg [63:0] accumulator;
 wire [31:0] shifted_a=amag >> (ai*7);
 wire [31:0] shifted_b=bmag >> (bi*7);
 wire signed [7:0] digit_a=$signed({1'b0,shifted_a[6:0]});
 wire signed [7:0] digit_b=$signed({1'b0,shifted_b[6:0]});
 wire signed [15:0] partial=digit_a*digit_b;
 wire [63:0] extended_partial={{48{1'b0}},partial};
 wire [63:0] added=accumulator+(extended_partial << ((ai+bi)*7));
 reg [63:0] quotient,remainder,half,rounded,limit;
 reg signed [15:0] rounded_output;
 assign in_ready=(state==IDLE);
 always @* begin
   quotient=accumulator >> shift;
   remainder=0;half=0;rounded=quotient;
   if(shift!=0) begin
     remainder=accumulator & ((64'h1 << shift)-1);
     half=64'h1 << (shift-1);
     if((remainder>half)||((remainder==half)&&quotient[0])) rounded=quotient+1;
   end
   if(mode16) limit=negative?64'd32768:64'd32767;
   else limit=negative?64'd128:64'd127;
   if(rounded>limit) rounded=limit;
   if(negative) rounded_output=-$signed(rounded[15:0]);
   else rounded_output=$signed(rounded[15:0]);
 end
 always @(posedge clk) begin
   if(reset) begin
     state<=IDLE;out_valid<=0;out_data<=0;accumulator<=0;
     amag<=0;bmag<=0;negative<=0;mode16<=0;shift<=0;ai<=0;bi<=0;
   end else case(state)
     IDLE: if(in_valid) begin
       amag<=in_acc[31] ? (~$unsigned(in_acc)+32'd1) : $unsigned(in_acc);
       bmag<={1'b0,in_m};negative<=in_acc[31];mode16<=in_i16;shift<=in_shift;
       ai<=0;bi<=0;accumulator<=0;state<=RUN;
     end
     RUN: begin
       accumulator<=added;
       if(ai==4 && bi==4) state<=ROUND;
       else if(bi==4) begin bi<=0;ai<=ai+1;end
       else bi<=bi+1;
     end
     ROUND: begin out_data<=rounded_output;out_valid<=1;state<=HOLD;end
     HOLD: if(out_ready) begin out_valid<=0;state<=IDLE;end
   endcase
 end
endmodule
