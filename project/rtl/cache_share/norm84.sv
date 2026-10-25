module norm84 #(parameter PROFILE=1)(input wire clk,reset,cmd,input wire [11:0] h,input wire [31:0] epsilon,
 output wire busy,done,input wire ack,output reg [7:0] status,
 output wire req,wr,output wire [9:0] addr,output wire [127:0] din,input wire ready,valid,output wire take,input wire [127:0] dout,
 output reg [63:0] cycles,output reg [31:0] reads,writes,output wire [7:0] debug_state,
 output wire mul_req,output wire signed [31:0] mul_a,mul_b,input wire mul_ready,mul_valid,input wire signed [63:0] mul_value);
 localparam IDLE=0,XR=1,XWAIT=2,MUL=3,MWAIT=4,MEAN=5,MEANWAIT=6,SQRT=7,SQRTWAIT=8,
 YR=9,YWAIT=10,GR=11,GWAIT=12,GMUL=13,GMWAIT=14,DIV=15,DWAIT=16,STORE=17,SWAIT=18,DONE=19;
 reg [7:0] state;reg [11:0] size,index;reg [31:0] eps;
 reg [127:0] xline,gline,oline,sum,rad,numer,den;
 reg signum;wire [31:0] x=xline[32*index[1:0]+:32],g=gline[32*index[1:0]+:32];
 wire aready,aval,aerr;wire [127:0] av,ar;
 wire areq=state==MUL||state==MEAN||state==SQRT||state==GMUL||state==DIV;
 wire [1:0] aop=state==SQRT?2:((state==DIV||state==MEAN)?1:0);
 wire [127:0] aa=state==MEAN?sum:state==SQRT?rad:state==DIV?numer:{96'b0,x};
 wire [127:0] ab=state==MEAN?{116'b0,size}:state==DIV?den:{96'b0,(state==GMUL?g:x)};
 wire fready,fvalid,ferror;wire [127:0] fvalue,frem;
 wire mul_phase=state==MUL||state==MWAIT||state==GMUL||state==GMWAIT;
 assign mul_req=state==MUL||state==GMUL;assign mul_a=x;assign mul_b=state==GMUL?g:x;
 assign aready=mul_phase?mul_ready:fready;assign aval=mul_phase?mul_valid:fvalid;
 assign av=mul_phase?{{64{mul_value[63]}},mul_value}:fvalue;assign ar=frem;assign aerr=ferror;
 sfu84 #(PROFILE) arithmetic(clk,reset,areq&&!mul_phase,aop,aa,ab,fready,fvalid,1'b1,fvalue,frem,ferror);
 assign busy=state!=IDLE;assign done=state==DONE;assign debug_state=state;
 assign req=state==XR||state==YR||state==GR||state==STORE;assign wr=state==STORE;
 assign addr=(state==GR?10'd384:10'd0)+{1'b0,index[11:2]};assign din=oline;
 assign take=state==XWAIT||state==YWAIT||state==GWAIT||state==SWAIT;
 wire [128:0] rounded={1'b0,av}+((({1'b0,ar}<<1)>{1'b0,den})||((({1'b0,ar}<<1)=={1'b0,den})&&av[0]));
 wire outbad=rounded>(signum?129'd2147483648:129'd2147483647);
 wire [31:0] outword=signum?-rounded[31:0]:rounded[31:0];
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;status<=0;cycles<=0;reads<=0;writes<=0;size<=0;index<=0;eps<=0;xline<=0;gline<=0;oline<=0;sum<=0;rad<=0;numer<=0;den<=0;signum<=0;end
  else begin
   if(state!=IDLE&&state!=DONE)cycles<=cycles+1;
   case(state)
   IDLE:if(cmd)begin cycles<=0;reads<=0;writes<=0;status<=0;size<=h;eps<=epsilon;sum<=0;index<=0;if(h==0||h>1536)begin status<=1;state<=DONE;end else state<=XR;end
   XR:if(ready)begin reads<=reads+1;state<=XWAIT;end
   XWAIT:if(valid)begin xline<=dout;state<=MUL;end
   MUL:if(aready)state<=MWAIT;
   MWAIT:if(aval)begin sum<=sum+av;if(index+1==size)state<=MEAN;else begin index<=index+1;state<=index[1:0]==3?XR:MUL;end end
   MEAN:if(aready)state<=MEANWAIT;
   MEANWAIT:if(aval)begin rad<=(av+eps)<<40;state<=SQRT;end
   SQRT:if(aready)state<=SQRTWAIT;
   SQRTWAIT:if(aval)begin den<=av;index<=0;if(av==0)begin status<=2;state<=DONE;end else state<=YR;end
   YR:if(ready)begin reads<=reads+1;state<=YWAIT;end
   YWAIT:if(valid)begin xline<=dout;oline<=dout;state<=GR;end
   GR:if(ready)begin reads<=reads+1;state<=GWAIT;end
   GWAIT:if(valid)begin gline<=dout;state<=GMUL;end
   GMUL:if(aready)state<=GMWAIT;
   GMWAIT:if(aval)begin signum<=av[127];numer<=(av[127]?-av:av)<<12;state<=DIV;end
   DIV:if(aready)state<=DWAIT;
   DWAIT:if(aval)begin
    if(aerr||outbad)begin status<=3;state<=DONE;end
    else begin oline[32*index[1:0]+:32]<=outword;if(index+1==size||index[1:0]==3)state<=STORE;else begin index<=index+1;state<=GMUL;end end
   end
   STORE:if(ready)begin writes<=writes+1;state<=SWAIT;end
   SWAIT:if(valid)begin if(index+1==size)state<=DONE;else begin index<=index+1;state<=YR;end end
   DONE:if(ack)state<=IDLE;
   default:begin status<=255;state<=DONE;end
   endcase
  end
 end
endmodule
