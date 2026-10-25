// Full K512, all8 selected experts, H1536. No host intermediate arithmetic.
module mfront82(input wire clk,reset,start,ack,output wire done,output reg [7:0] status,
 output wire req,output wire [31:0] addr,input wire ready,valid,output wire take,input wire [127:0] data,
 output wire sreq,output wire [9:0] saddr,output wire [127:0] sdata,input wire sready,svalid,output wire stake,
 output reg [31:0] packets,macs,store_lines,output reg obs_valid,output reg [10:0] obs_row,output reg [2:0] obs_rank,output reg signed [31:0] obs_acc,obs_down);
 localparam IDLE=0,HR=1,HW=2,DR=3,DW=4,MAC=5,PM=6,RQ=7,GM=8,MERGE=9,SM=10,JOIN=11,SW=12,SWAIT=13,DONE=14;
 reg [3:0] state;reg [10:0] row;reg [2:0] rank;reg [5:0] chunk;reg [31:0] pointer;
 reg signed [31:0] accum,mant,residual,scale,ma,mb;reg [15:0] shift,gate;
 reg [127:0] blockdata,oline;reg signed [63:0] product,merge;
 wire signed [15:0] p[0:7];genvar j;generate for(j=0;j<8;j=j+1)begin:LANE
 assign p[j]=$signed(blockdata[8*j+:8])*$signed(blockdata[64+8*j+:8]);end endgenerate
 wire signed [31:0] part={{16{p[0][15]}},p[0]}+{{16{p[1][15]}},p[1]}+{{16{p[2][15]}},p[2]}+{{16{p[3][15]}},p[3]}+{{16{p[4][15]}},p[4]}+{{16{p[5][15]}},p[5]}+{{16{p[6][15]}},p[6]}+{{16{p[7][15]}},p[7]};
 wire signed [63:0] mp=ma*mb;
 function signed [63:0] rne(input signed [63:0] v,input [15:0] s);
 reg [63:0] mag,q,r,half;
 begin mag=v[63]?-v:v;if(s==0)rne=v;else if(s>=64)rne=0;else begin q=mag>>s;r=mag-(q<<s);half=64'd1<<(s-1);if(r>half||(r==half&&q[0]))q=q+1; rne=v[63]?-$signed(q):$signed(q);end end endfunction
 function bad32(input signed [63:0] v);begin bad32=v>64'sd2147483647||v< -64'sd2147483648;end endfunction
 wire signed [63:0] rqv=rne(product,shift),nextmerge=merge+product;
 wire signed [63:0] mergeword=rne(nextmerge,15),joined=rne(product,20)+{{32{residual[31]}},residual};
 assign done=state==DONE;assign req=state==HR||state==DR;assign addr=pointer<<4;assign take=state==HW||state==DW;
 assign sreq=state==SW;assign saddr={1'b0,row[10:2]};assign sdata=oline;assign stake=state==SWAIT;
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;status<=0;row<=0;rank<=0;chunk<=0;pointer<=0;accum<=0;mant<=0;residual<=0;scale<=0;ma<=0;mb<=0;shift<=0;gate<=0;blockdata<=0;oline<=0;product<=0;merge<=0;packets<=0;macs<=0;store_lines<=0;obs_valid<=0;obs_row<=0;obs_rank<=0;obs_acc<=0;obs_down<=0;end
  else begin obs_valid<=0;case(state)
   IDLE:if(start)begin state<=HR;status<=0;row<=0;rank<=0;pointer<=0;merge<=0;packets<=0;macs<=0;store_lines<=0;end
   HR:if(ready)begin state<=HW;packets<=packets+1;end
   HW:if(valid)begin mant<=data[31:0];shift<=data[47:32];gate<=data[63:48];residual<=data[95:64];scale<=data[127:96];chunk<=0;accum<=0;pointer<=pointer+1;
    if(data[47])begin status<=1;state<=DONE;end else state<=DR;end
   DR:if(ready)begin state<=DW;packets<=packets+1;end
   DW:if(valid)begin blockdata<=data;pointer<=pointer+1;state<=MAC;end
   MAC:begin macs<=macs+8;accum<=accum+part;if(chunk==63)begin ma<=accum+part;mb<=mant;state<=PM;end else begin chunk<=chunk+1;state<=DR;end end
   PM:begin product<=mp;state<=RQ;end
   RQ:if(bad32(rqv))begin status<=2;state<=DONE;end else begin ma<=rqv[31:0];mb<={16'b0,gate};state<=GM;end
   GM:begin product<=mp;state<=MERGE;end
   MERGE:begin obs_valid<=1;obs_acc<=accum;obs_down<=ma;obs_row<=row;obs_rank<=rank;
    if(rank==7)begin if(bad32(mergeword))begin status<=3;state<=DONE;end else begin ma<=mergeword[31:0];mb<=scale;state<=SM;end end
    else begin rank<=rank+1;merge<=nextmerge;state<=HR;end
   end
   SM:begin product<=mp;state<=JOIN;end
   JOIN:if(bad32(joined))begin status<=4;state<=DONE;end else begin oline[32*row[1:0]+:32]<=joined[31:0];if(row[1:0]==3)state<=SW;else begin row<=row+1;rank<=0;merge<=0;state<=HR;end end
   SW:if(sready)begin state<=SWAIT;store_lines<=store_lines+1;end
   SWAIT:if(svalid)begin if(row==1535)state<=DONE;else begin row<=row+1;rank<=0;merge<=0;state<=HR;end end
   DONE:if(ack)state<=IDLE;
   default:begin status<=255;state<=DONE;end
  endcase end
 end
endmodule
