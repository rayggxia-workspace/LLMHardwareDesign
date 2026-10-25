// Full K512, all8 selected experts, H1536. No host intermediate arithmetic.
module mfront85(input wire clk,reset,start,ack,input wire cache_mode,input wire [31:0] coefficient,output wire done,output reg [7:0] status,
 output wire req,output wire [31:0] addr,input wire ready,valid,output wire take,input wire [127:0] data,
 output wire sreq,output wire swr,output wire [9:0] saddr,output wire [127:0] sdata,input wire sready,svalid,output wire stake,input wire [127:0] sdout,
 output reg [31:0] packets,macs,store_lines,output reg obs_valid,output reg [10:0] obs_row,output reg [2:0] obs_rank,output reg signed [31:0] obs_acc,obs_down,
 output wire mul_req,output wire signed [31:0] mul_a,mul_b,input wire mul_ready,mul_valid,input wire signed [63:0] mul_value,
 output reg [31:0] cache_reads,cache_writes,output wire [4:0] debug_state);
 reg CACHE;
 localparam IDLE=0,HR=1,HW=2,DR=3,DW=4,MAC=5,PM=6,RQ=7,GM=8,MERGE=9,SM=10,JOIN=11,SW=12,SWAIT=13,DONE=14,CR=15,CW=16,CS=17,CSW=18,AR=19,AW=20,PWAIT=21,GWAIT=22,SCWAIT=23;
 reg [4:0] state;assign debug_state=state;reg [7:0] cache_index;reg half;reg [127:0] aline;reg [10:0] row;reg [2:0] rank;reg [5:0] chunk;reg [31:0] pointer;
 reg signed [31:0] accum,mant,residual,scale,ma,mb;reg [15:0] shift,gate;
 reg [127:0] blockdata,oline;reg signed [63:0] product,merge;
 wire signed [15:0] p[0:7];genvar j;generate for(j=0;j<8;j=j+1)begin:LANE
 assign p[j]=$signed(CACHE?aline[8*j+:8]:blockdata[8*j+:8])*$signed(blockdata[(CACHE?0:64)+8*j+:8]);end endgenerate
 wire signed [31:0] part={{16{p[0][15]}},p[0]}+{{16{p[1][15]}},p[1]}+{{16{p[2][15]}},p[2]}+{{16{p[3][15]}},p[3]}+{{16{p[4][15]}},p[4]}+{{16{p[5][15]}},p[5]}+{{16{p[6][15]}},p[6]}+{{16{p[7][15]}},p[7]};
 assign mul_req=state==PM||state==GM||state==SM;assign mul_a=ma;assign mul_b=mb;
 wire signed [17:0] unit_shift=18'sd31-$signed({{2{data[47]}},data[47:32]})-$signed({{2{data[63]}},data[63:48]});
 function signed [63:0] rne(input signed [63:0] v,input [15:0] s);
 reg [63:0] mag,q,r,half;
 begin mag=v[63]?-v:v;if(s==0)rne=v;else if(s>=64)rne=0;else begin q=mag>>s;r=mag-(q<<s);half=64'd1<<(s-1);if(r>half||(r==half&&q[0]))q=q+1; rne=v[63]?-$signed(q):$signed(q);end end endfunction
 function bad32(input signed [63:0] v);begin bad32=v>64'sd2147483647||v< -64'sd2147483648;end endfunction
 wire signed [63:0] rqv=rne(product,shift),nextmerge=merge+product;
 wire signed [63:0] mergeword=rne(nextmerge,15),joined=rne(product,20)+{{32{residual[31]}},residual};
 assign done=state==DONE;assign req=state==HR||state==DR||state==CR;assign addr=pointer<<4;assign take=state==HW||state==DW||state==CW;
 assign sreq=state==SW||state==CS||state==AR;assign swr=state!=AR;
 assign saddr=state==CS?10'd768+cache_index:state==AR?10'd768+{rank,chunk[5:1]}:{1'b0,row[10:2]};
 assign sdata=state==CS?blockdata:oline;assign stake=state==SWAIT||state==CSW||state==AW;
 always @(posedge clk)begin
  if(reset)begin CACHE<=0;cache_index<=0;half<=0;aline<=0;cache_reads<=0;cache_writes<=0;state<=IDLE;status<=0;row<=0;rank<=0;chunk<=0;pointer<=0;accum<=0;mant<=0;residual<=0;scale<=0;ma<=0;mb<=0;shift<=0;gate<=0;blockdata<=0;oline<=0;product<=0;merge<=0;packets<=0;macs<=0;store_lines<=0;obs_valid<=0;obs_row<=0;obs_rank<=0;obs_acc<=0;obs_down<=0;end
  else begin obs_valid<=0;case(state)
   IDLE:if(start)begin CACHE<=cache_mode;cache_reads<=0;cache_writes<=0;cache_index<=0;half<=0;state<=cache_mode?CR:HR;status<=0;row<=0;rank<=0;pointer<=0;merge<=0;packets<=0;macs<=0;store_lines<=0;end
   HR:if(ready)begin state<=HW;packets<=packets+1;end
   HW:if(valid)begin mant<=data[31:0];shift<=unit_shift>=64?16'd64:unit_shift[15:0];gate<=data[79:64];residual<=data[111:80];scale<=coefficient;chunk<=0;accum<=0;pointer<=pointer+1;
    if(unit_shift<0||data[127:112]!=0)begin status<=1;state<=DONE;end else state<=DR;end
   DR:if(ready)begin state<=DW;packets<=packets+1;end
   DW:if(valid)begin blockdata<=data;pointer<=pointer+1;half<=0;state<=CACHE?AR:MAC;end
   CR:if(ready)begin state<=CW;packets<=packets+1;end
   CW:if(valid)begin blockdata<=data;pointer<=pointer+1;state<=CS;end
   CS:if(sready)begin cache_writes<=cache_writes+1;state<=CSW;end
   CSW:if(svalid)begin if(cache_index==255)state<=HR;else begin cache_index<=cache_index+1;state<=CR;end end
   AR:if(sready)begin cache_reads<=cache_reads+1;state<=AW;end
   AW:if(svalid)begin aline<=sdout;state<=MAC;end
   MAC:begin macs<=macs+8;accum<=accum+part;if(chunk==63)begin ma<=accum+part;mb<=mant;state<=PM;end else begin chunk<=chunk+1;if(CACHE&&!half)begin half<=1;blockdata<=blockdata>>64;aline<=aline>>64;state<=MAC;end else state<=DR;end end
   PM:if(mul_ready)state<=PWAIT;
   PWAIT:if(mul_valid)begin product<=mul_value;state<=RQ;end
   RQ:if(bad32(rqv))begin status<=2;state<=DONE;end else begin ma<=rqv[31:0];mb<={16'b0,gate};state<=GM;end
   GM:if(mul_ready)state<=GWAIT;
   GWAIT:if(mul_valid)begin product<=mul_value;state<=MERGE;end
   MERGE:begin obs_valid<=1;obs_acc<=accum;obs_down<=ma;obs_row<=row;obs_rank<=rank;
    if(rank==7)begin if(bad32(mergeword))begin status<=3;state<=DONE;end else begin ma<=mergeword[31:0];mb<=scale;state<=SM;end end
    else begin rank<=rank+1;merge<=nextmerge;state<=HR;end
   end
   SM:if(mul_ready)state<=SCWAIT;
   SCWAIT:if(mul_valid)begin product<=mul_value;state<=JOIN;end
   JOIN:if(bad32(joined))begin status<=4;state<=DONE;end else begin oline[32*row[1:0]+:32]<=joined[31:0];if(row[1:0]==3)state<=SW;else begin row<=row+1;rank<=0;merge<=0;state<=HR;end end
   SW:if(sready)begin state<=SWAIT;store_lines<=store_lines+1;end
   SWAIT:if(svalid)begin if(row==1535)state<=DONE;else begin row<=row+1;rank<=0;merge<=0;state<=HR;end end
   DONE:if(ack)state<=IDLE;
   default:begin status<=255;state<=DONE;end
  endcase end
 end
endmodule
