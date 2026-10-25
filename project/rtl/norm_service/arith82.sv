// Exact integer resources. PROFILE0: one U8 multiplier;1: S32 multiplier;2: 4 SFU steps/cycle.
module arith82 #(parameter PROFILE=0)(input wire clk,reset,req,input wire [1:0] op,
 input wire [127:0] a,b,output wire ready,output reg valid,input wire take,
 output reg [127:0] value,remainder,output reg error);
 reg [1:0] busy;reg [7:0] left;reg [127:0] n,q,den;reg [128:0] rem;
 reg [63:0] accum;reg [31:0] ma,mb;reg neg;reg [3:0] digit;
 wire [7:0] da=ma[8*digit[3:2]+:8],db=mb[8*digit[1:0]+:8];
 wire [15:0] small_product=da*db;wire signed [63:0] large_product=$signed(a[31:0])*$signed(b[31:0]);
 reg [127:0] nn,qq;reg [128:0] rr,trial;integer i;
 localparam STEPS=PROFILE==2?4:1;
 assign ready=busy==0&&!valid;
 always @* begin
  nn=n;qq=q;rr=rem;trial=0;
  for(i=0;i<STEPS;i=i+1)begin
   if(busy==2)begin rr={rr[127:0],nn[127]};nn=nn<<1;qq=qq<<1;if(rr>={1'b0,den})begin rr=rr-{1'b0,den};qq[0]=1;end end
   else if(busy==3)begin rr=(rr<<2)|{127'b0,nn[127:126]};nn=nn<<2;trial=({1'b0,qq}<<2)|129'd1;
    if(rr>=trial)begin rr=rr-trial;qq=(qq<<1)|1;end else qq=qq<<1;
   end
  end
 end
 reg [63:0] total;
 always @* total=accum+({48'b0,small_product}<<(8*(digit[3:2]+{1'b0,digit[1:0]})));
 always @(posedge clk)begin
  if(reset)begin busy<=0;valid<=0;value<=0;remainder<=0;error<=0;left<=0;n<=0;q<=0;den<=0;rem<=0;accum<=0;ma<=0;mb<=0;neg<=0;digit<=0;end
  else if(req&&ready)begin error<=0;remainder<=0;
   if(op==0)begin
    if(PROFILE!=0)begin value<={{64{large_product[63]}},large_product};valid<=1;end
    else begin ma<=a[31]?-a[31:0]:a[31:0];mb<=b[31]?-b[31:0]:b[31:0];neg<=a[31]^b[31];accum<=0;digit<=0;busy<=1;end
   end else if(op==1&&b==0)begin error<=1;valid<=1;value<=0;end
   else begin busy<=op==1?2:3;left<=op==1?128:64;n<=a;den<=b;q<=0;rem<=0;end
  end else if(busy==1)begin
   if(digit==15)begin value<=neg?{{64{1'b1}},-total}:{64'b0,total};if(total==0)value<=0;busy<=0;valid<=1;end
   else begin accum<=total;digit<=digit+1;end
  end else if(busy==2||busy==3)begin n<=nn;q<=qq;rem<=rr;left<=left-STEPS;
   if(left<=STEPS)begin value<=qq;remainder<=rr[127:0];busy<=0;valid<=1;end
  end else if(valid&&take)valid<=0;
 end
endmodule
