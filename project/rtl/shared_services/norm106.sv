module norm106 #(parameter PROFILE=1)(input wire clk,reset,cmd,input wire [11:0] h,input wire [31:0] epsilon,input wire gamma_stream,input wire [31:0] gamma_address,
 output wire ereq,output wire [31:0] eaddr,input wire eready,evalid,output wire etake,input wire [127:0] edata,
 output reg [31:0] gamma_loads,gamma_stores,den_events,output wire [127:0] observed_sum,observed_den,
 output wire busy,done,input wire ack,output reg [7:0] status,
 output wire req,wr,output wire [9:0] addr,output wire [127:0] din,input wire ready,valid,output wire take,input wire [127:0] dout,
 output reg [63:0] cycles,output reg [31:0] reads,writes,output wire [7:0] debug_state,
 output wire mul_req,output wire signed [31:0] mul_a,mul_b,input wire mul_ready,mul_valid,input wire signed [63:0] mul_value,
 output wire fq,output wire [1:0] fo,output wire [127:0] fx,fy,input wire fr,fv,output wire ft,input wire [127:0] fz,frem_in,input wire ferr);
 localparam IDLE=0,XR=1,XWAIT=2,MUL=3,MWAIT=4,MEAN=5,MEANWAIT=6,SQRT=7,SQRTWAIT=8,
 YR=9,YWAIT=10,GR=11,GWAIT=12,GMUL=13,GMWAIT=14,DIV=15,DWAIT=16,STORE=17,SWAIT=18,DONE=19,GREQ=20,GRESP=21,GSTORE=22,GSWAIT=23;
 reg stream;reg [31:0] gbase;reg [5:0] load_line;wire [9:0] gamma_bank=size==2560?10'd640:10'd384;
 assign ereq=state==GREQ;assign etake=state==GRESP;assign eaddr=gbase+{18'b0,index[11:8],10'b0}+{22'b0,load_line,4'b0};
 assign observed_sum=sum;assign observed_den=den;
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
 assign fq=areq&&!mul_phase;assign fo=aop;assign fx=aa;assign fy=ab;assign ft=1'b1;assign fready=fr;assign fvalid=fv;assign fvalue=fz;assign frem=frem_in;assign ferror=ferr;
 assign busy=state!=IDLE;assign done=state==DONE;assign debug_state=state;
 assign req=state==XR||state==YR||state==GR||state==STORE||state==GSTORE;assign wr=state==STORE||state==GSTORE;
 assign addr=state==GSTORE?gamma_bank+{4'b0,load_line}:state==GR?(stream?gamma_bank+{4'b0,index[7:2]}:10'd384+index[11:2]):index[11:2];assign din=state==GSTORE?gline:oline;
 assign take=state==XWAIT||state==YWAIT||state==GWAIT||state==SWAIT||state==GSWAIT;
 wire [128:0] rounded={1'b0,av}+((({1'b0,ar}<<1)>{1'b0,den})||((({1'b0,ar}<<1)=={1'b0,den})&&av[0]));
 wire outbad=rounded>(signum?129'd2147483648:129'd2147483647);
 wire [31:0] outword=signum?-rounded[31:0]:rounded[31:0];
 always @(posedge clk)begin
  if(reset)begin stream<=0;gbase<=0;load_line<=0;gamma_loads<=0;gamma_stores<=0;den_events<=0;state<=IDLE;status<=0;cycles<=0;reads<=0;writes<=0;size<=0;index<=0;eps<=0;xline<=0;gline<=0;oline<=0;sum<=0;rad<=0;numer<=0;den<=0;signum<=0;end
  else begin
   if(state!=IDLE&&state!=DONE)cycles<=cycles+1;
   case(state)
   IDLE:if(cmd)begin stream<=gamma_stream;gbase<=gamma_address;load_line<=0;gamma_loads<=0;gamma_stores<=0;den_events<=0;cycles<=0;reads<=0;writes<=0;status<=0;size<=h;eps<=epsilon;sum<=0;index<=0;if((h!=1536&&h!=2560)||(h==2560&&!gamma_stream))begin status<=1;state<=DONE;end else state<=XR;end
   XR:if(ready)begin reads<=reads+1;state<=XWAIT;end
   XWAIT:if(valid)begin xline<=dout;state<=MUL;end
   MUL:if(aready)state<=MWAIT;
   MWAIT:if(aval)begin sum<=sum+av;if(index+1==size)state<=MEAN;else begin index<=index+1;state<=index[1:0]==3?XR:MUL;end end
   MEAN:if(aready)state<=MEANWAIT;
   MEANWAIT:if(aval)begin rad<=(av+eps)<<40;state<=SQRT;end
   SQRT:if(aready)state<=SQRTWAIT;
   SQRTWAIT:if(aval)begin den<=av;den_events<=den_events+1;index<=0;if(av==0)begin status<=2;state<=DONE;end else state<=stream?GREQ:YR;end
   GREQ:if(eready)begin gamma_loads<=gamma_loads+1;state<=GRESP;end
   GRESP:if(evalid)begin gline<=edata;state<=GSTORE;end
   GSTORE:if(ready)begin writes<=writes+1;gamma_stores<=gamma_stores+1;state<=GSWAIT;end
   GSWAIT:if(valid)begin if(load_line==63)begin load_line<=0;state<=YR;end else begin load_line<=load_line+1;state<=GREQ;end end
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
   SWAIT:if(valid)begin if(index+1==size)state<=DONE;else begin index<=index+1;state<=(stream&&index[7:0]==8'hff)?GREQ:YR;end end
   DONE:if(ack)state<=IDLE;
   default:begin status<=255;state<=DONE;end
   endcase
  end
 end
endmodule
