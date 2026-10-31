// Complete D128 N256 R state. One head, one 16KiB 1RW, one shared signed32 multiplier.
module r106(input wire clk,reset,cmd,input wire [1:0] command,input wire [4:0] head,
 input wire signed [15:0] initial_unit,input wire [31:0] expected_position,
 output wire cmd_ready,cmd_accept,output wire busy,done,input wire ack,output reg [7:0] status,
 input wire abort_request,output wire abort_ready,abort_accept,
 input wire accept_candidate,reject_candidate,output wire offer,
 output reg [31:0] position,numeric_epoch,output reg signed [15:0] unit,output reg bank,
 output wire [31:0] candidate_epoch,output wire signed [15:0] candidate_unit,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,
 output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 input wire mem_hold,mul_hold,
 output wire ext_req,ext_wr,output wire [31:0] ext_addr,output wire [127:0] ext_wdata,
 input wire ext_ready,ext_valid,output wire ext_take,input wire [127:0] ext_rdata,
 input wire [31:0] generation,output wire [31:0] ext_generation,input wire [31:0] response_generation,
 input wire peer_req,input wire signed [31:0] peer_a,peer_b,output wire peer_ready,peer_valid,input wire peer_take,output wire signed [63:0] peer_y,
 output reg [63:0] cycles,output wire [31:0] beats,transactions,mul_grants,peer_grants,contested,
 output reg [31:0] ext_reads,ext_writes,s_reads,s_writes,alpha_bypass,aborts,stale,
 output reg [3:0] retries,output wire [7:0] debug_state,
 output wire sq,sw,output wire [9:0] sa,output wire [127:0] si,input wire sr_in,sv_in,output wire st,input wire [127:0] so,
 output wire mq0,mq1,output wire signed [31:0] mx0,my0,mx1,my1,input wire mr0,mr1,mv0,mv1,output wire mt0,mt1,input wire signed [63:0] mz0,mz1);
 localparam BASE=32'h06000000,TRIAL=32'h06040000,PROP=32'h06060000,YBASE=32'h060a0000,DESC=32'h060a0400,COEFF=32'h060b0000;
 localparam IDLE=0,DONE=1,ER=2,EW=3,SR=4,SW=5,MR=6,MW=7,ROUND=8,
 INIT0=10,INIT1=11,INIT2=12,INIT3=13,REST0=14,REST1=15,LOAD0=16,LOAD1=17,LOAD2=18,LOAD3=19,
 CLONE0=20,CLONE1=21,CLONE2=22,CLONE3=23,ATTEMPT=24,DT0=25,DT1=26,DT2=27,DT3=28,DT4=29,
 PD0=30,PD1=31,PL0=32,PL1=33,PL2=34,PL3=35,PN0=36,PN1=37,PN2=38,PN3=39,PN4=40,PN5=41,PN6=42,PN7=43,PN8=44,
 PS0=45,PS1=46,PS2=47,PS3=48,CHECK=49,RE0=50,RE1=51,RE2=52,RE3=53,RE4=54,
 SH0=55,SH1=56,SH2=57,SH3=58,SH4=59,RD0=60,RD1=61,RL0=62,RL1=63,RL2=64,RL3=65,
 RN0=66,RN1=67,RN2=68,RN3=69,RN4=70,RN5=71,RN6=72,RN7=73,RN8=74,RN9=75,RY0=76,RY1=77,RY2=78,
 OFFER=79,COMMIT0=80,COMMIT1=81,ABORTED=82;
 reg [7:0] state,ret;reg [4:0] owner_head;reg context_valid,cfg_pending,abort_pending;
 reg [31:0] want_position;reg signed [15:0] work_unit;reg [31:0] work_epoch;
 reg [13:0] line_index;reg [7:0] n;reg [6:0] d;reg [7:0] rowline;reg [1:0] lane;
 reg [127:0] line_data,pack,pack2;reg [63:0] maxdec,maxinj,maxscan,maxskip;
 reg bad,range_bad;reg signed [31:0] dt,skip,xvalue,oldvalue;reg [31:0] alpha;
 reg signed [63:0] decay,injection,sum,scan_value,skip_value,product;
 reg signed [63:0] round_in,round_out;reg signed [15:0] round_shift;reg round_bad;
 reg [31:0] e_addr;reg e_wr;reg [127:0] e_data;wire erdy,ev;wire [127:0] ed;
 reg [9:0] s_addr;reg s_wr;reg [127:0] s_data;wire srdy,sv;wire [127:0] sd;
 reg signed [31:0] ma,mb;wire mrdy,mv;wire signed [63:0] my;wire [31:0] unused0,unused1;
 wire safe=(!reset);wire issuing=!abort_pending&&!abort_accept;
 wire irreversible=state==COMMIT0||state==COMMIT1||(state==ER&&ret==COMMIT1)||(state==EW&&ret==COMMIT1);
 assign cmd_ready=safe&&state==IDLE&&!cfg_pending&&!cfg&&generation!=32'hffffffff;
 assign cmd_accept=cmd&&cmd_ready;assign busy=state!=IDLE;assign done=safe&&state==DONE;
 assign abort_ready=safe&&state!=IDLE&&state!=DONE&&!abort_pending&&!irreversible;
 assign abort_accept=abort_request&&abort_ready;assign offer=safe&&state==OFFER&&!abort_pending&&!abort_accept;
 assign candidate_unit=work_unit;assign candidate_epoch=work_epoch;assign debug_state=state;
 assign cfg_ready=safe&&state==IDLE&&!cfg_pending&&srdy;assign cfg_valid=safe&&cfg_pending&&sv;assign cfg_dout=sd;
 wire cfg_use=safe&&state==IDLE&&cfg&&!cfg_pending;
 wire sreq=safe&&((cfg_use)||(state==SR&&issuing&&!mem_hold));
 assign sq=sreq;assign sw=cfg_use?cfg_wr:s_wr;assign sa=cfg_use?cfg_addr:s_addr;assign si=cfg_use?cfg_din:s_data;
 assign srdy=sr_in;assign sv=sv_in;assign sd=so;assign st=cfg_pending?cfg_take:state==SW;

 wire mlreq=safe&&state==ER&&issuing;wire lt;wire lr, lw;wire [31:0] la;wire [127:0] ld;
 wire matching=response_generation==generation;wire drop_response=!matching||(generation==32'hffffffff&&state==IDLE);wire wv;wire [127:0] wd;
 assign lr=mlreq;assign lw=e_wr;assign la=e_addr;assign ld=e_data;assign erdy=ext_ready&&safe;assign ev=ext_valid&&!drop_response&&safe;assign ed=ext_rdata;assign lt=state==EW;assign beats=0;assign transactions=0;

 assign ext_req=safe&&lr;assign ext_wr=lw;assign ext_addr=la;assign ext_wdata=ld;assign ext_take=safe&&(drop_response||lt);assign ext_generation=generation;
 wire peer_ready_raw,peer_valid_raw;assign peer_ready=safe&&peer_ready_raw;assign peer_valid=safe&&peer_valid_raw;
 assign mq0=safe&&state==MR&&issuing;assign mx0=ma;assign my0=mb;assign mt0=state==MW;assign mrdy=mr0;assign mv=mv0;assign my=mz0;
 assign mq1=safe&&peer_req;assign mx1=peer_a;assign my1=peer_b;assign mt1=peer_take;assign peer_ready_raw=mr1;assign peer_valid_raw=mv1;assign peer_y=mz1;assign mul_grants=0;assign peer_grants=0;assign contested=0;

 function [63:0] mag(input signed [63:0] v);begin mag=v[63]?-v:v;end endfunction
 function fit32(input signed [63:0] v);begin fit32=(v>=-64'sd2147483648&&v<=64'sd2147483647);end endfunction
 // One explicitly shared round/shift datapath; 65th bit is failure, never saturation.
 function [64:0] rounded(input signed [63:0] v,input signed [15:0] sh);
 reg [63:0] a,q,remn,half,mask;reg fail;integer t;
 begin a=mag(v);q=0;remn=0;half=0;mask=0;fail=v==64'sh8000000000000000;t=0;
 if(sh<0)begin t=-sh;if(t>63)begin fail=fail||(a!=0);q=0;end else begin fail=fail||(a>(64'h7fffffffffffffff>>t));q=a<<t;end end
 else if(sh==0)q=a;
 else if(sh>63)q=0;
 else begin mask=(64'h1<<sh)-1;half=64'h1<<(sh-1);q=a>>sh;remn=a&mask;if(remn>half||(remn==half&&q[0]))q=q+1;end
 rounded={fail,v[63]?(~q+64'd1):q};end endfunction
 function [127:0] descriptor(input [31:0] pos,ep,input signed [15:0] un,input bk,input [4:0] hd);
 begin descriptor={5'd0,4'd1,1'b1,hd,bk,un,ep,pos,32'h52393901};end endfunction
 task ex(input wr,input [31:0] addr,input [127:0] value,input [7:0] target);
 begin e_wr<=wr;e_addr<=addr;e_data<=value;ret<=target;state<=ER;end endtask
 task ss(input wr,input [9:0] addr,input [127:0] value,input [7:0] target);
 begin s_wr<=wr;s_addr<=addr;s_data<=value;ret<=target;state<=SR;end endtask
 task mm(input signed [31:0] a,b,input [7:0] target);
 begin ma<=a;mb<=b;ret<=target;state<=MR;end endtask
 task rr(input signed [63:0] v,input signed [15:0] sh,input [7:0] target);
 begin round_in<=v;round_shift<=sh;ret<=target;state<=ROUND;end endtask
 task fail(input [7:0] code);begin status<=code;state<=DONE;end endtask
 wire [64:0] rounded_value=rounded(round_in,round_shift);
 wire signed [63:0] proposal=decay+injection;wire signed [63:0] outvalue=scan_value+skip_value;
 wire [64:0] guard_sum={1'b0,maxdec}+{1'b0,maxinj};wire [64:0] out_guard={1'b0,maxscan}+{1'b0,maxskip};
 always @(posedge clk)begin
 if(reset)begin
 state<=IDLE;ret<=0;position<=0;numeric_epoch<=0;unit<=0;bank<=0;owner_head<=0;context_valid<=0;cfg_pending<=0;abort_pending<=0;
 status<=0;cycles<=0;ext_reads<=0;ext_writes<=0;s_reads<=0;s_writes<=0;alpha_bypass<=0;aborts<=0;stale<=0;retries<=0;
 work_unit<=0;work_epoch<=0;want_position<=0;line_index<=0;n<=0;d<=0;rowline<=0;lane<=0;line_data<=0;pack<=0;pack2<=0;maxdec<=0;maxinj<=0;maxscan<=0;maxskip<=0;bad<=0;range_bad<=0;
 dt<=0;skip<=0;alpha<=0;xvalue<=0;oldvalue<=0;decay<=0;injection<=0;sum<=0;scan_value<=0;skip_value<=0;product<=0;
 round_in<=0;round_out<=0;round_shift<=0;round_bad<=0;e_addr<=0;e_wr<=0;e_data<=0;s_addr<=0;s_wr<=0;s_data<=0;ma<=0;mb<=0;
 end else begin
 if(cfg&&cfg_ready)cfg_pending<=1;else if(cfg_valid&&cfg_take)cfg_pending<=0;
 if(state!=IDLE&&state!=DONE)cycles<=cycles+1;
 if(ext_valid&&ext_take&&drop_response)stale<=stale+1;
 if(state==ER&&mlreq&&erdy)begin if(e_wr)ext_writes<=ext_writes+1;else ext_reads<=ext_reads+1;end
 if(state==SR&&sreq&&srdy)begin if(s_wr)s_writes<=s_writes+1;else s_reads<=s_reads+1;end
 if(abort_accept)begin abort_pending<=1;aborts<=aborts+1;if((state!=EW&&state!=SW&&state!=MW)||(state==EW&&ev)||(state==SW&&sv)||(state==MW&&mv))state<=ABORTED;end
 else if(abort_pending)begin
 if(state==ABORTED)begin abort_pending<=0;fail(2);end
 else if((state==EW&&ev)||(state==SW&&sv)||(state==MW&&mv))state<=ABORTED;
 end else case(state)
 IDLE:if(cmd_accept)begin
 cycles<=0;status<=0;ext_reads<=0;ext_writes<=0;s_reads<=0;s_writes<=0;alpha_bypass<=0;retries<=0;
 want_position<=expected_position;line_index<=0;work_unit<=unit;work_epoch<=numeric_epoch;
 if(command==0)begin owner_head<=head;context_valid<=0;work_unit<=initial_unit;work_epoch<=0;
 if(initial_unit< -127||initial_unit>127)fail(4);else state<=INIT0;end
 else if(command==2)begin owner_head<=head;context_valid<=0;state<=REST0;end
 else if(command!=1||!context_valid||head!=owner_head||expected_position!=position||position>=72)fail(4);
 else state<=LOAD0;
 end
 DONE:if(ack)state<=IDLE;
 ER:if(erdy)state<=EW;
 EW:if(ev)begin line_data<=ed;state<=ret;end
 SR:if(srdy&&!mem_hold)state<=SW;
 SW:if(sv)begin line_data<=sd;state<=ret;end
 MR:if(mrdy)state<=MW;
 MW:if(mv)begin product<=my;state<=ret;end
 ROUND:begin round_out<=rounded_value[63:0];round_bad<=rounded_value[64];state<=ret;end
 INIT0:ex(1,BASE+{line_index,4'b0},0,INIT1);
 INIT1:if(line_index==8191)begin line_index<=0;state<=INIT2;end else begin line_index<=line_index+1;state<=INIT0;end
 INIT2:ex(1,YBASE+{line_index,4'b0},0,INIT3);
 INIT3:if(line_index==31)begin position<=0;numeric_epoch<=0;unit<=work_unit;bank<=0;state<=COMMIT0;end else begin line_index<=line_index+1;state<=INIT2;end
 REST0:ex(0,DESC,0,REST1);
 REST1:if(line_data[31:0]!=32'h52393901||line_data[127:123]!=0||line_data[122:119]!=1||!line_data[118]||line_data[117:113]!=owner_head||$signed(line_data[111:96])< -127||$signed(line_data[111:96])>127||line_data[63:32]>72)fail(9);
 else begin position<=line_data[63:32];numeric_epoch<=line_data[95:64];unit<=line_data[111:96];bank<=line_data[112];context_valid<=1;fail(0);end
 LOAD0:ex(0,COEFF+(position<<11)+(position<<9)+(position<<5)+{line_index,4'b0},0,LOAD1);
 LOAD1:begin
 if(line_index==0&&(line_data[31:0]!=32'h52393943||line_data[63:32]!=position||line_data[95:64]!={27'b0,owner_head}||line_data[127:96]!=0))fail(4);
 else if(line_index==1&&(line_data[63:32]>32'h80000000||line_data[127:96]!=0))fail(4);
 else begin if(line_index==1)begin dt<=line_data[31:0];alpha<=line_data[63:32];skip<=line_data[95:64];end ss(1,line_index[9:0],line_data,LOAD2);end end
 LOAD2:if(line_index==161)begin line_index<=0;state<=CLONE0;end else begin line_index<=line_index+1;state<=LOAD0;end
 CLONE0:ex(0,BASE+(bank?32'h20000:0)+{line_index,4'b0},0,CLONE1);
 CLONE1:ex(1,TRIAL+{line_index,4'b0},line_data,CLONE2);
 CLONE2:if(line_index==8191)state<=ATTEMPT;else begin line_index<=line_index+1;state<=CLONE0;end
 ATTEMPT:begin n<=0;d<=0;bad<=0;range_bad<=0;maxdec<=0;maxinj<=0;pack<=0;state<=DT0;end
 DT0:ss(0,10'd34+{2'b0,n[7:2]},0,DT1);
 DT1:mm(dt,$signed(line_data[n[1:0]*32+:32]),DT2);
 DT2:rr(product,16'sd12,DT3);
 DT3:begin if(round_bad||!fit32(round_out))bad<=1;pack[n[1:0]*32+:32]<=round_out[31:0];state<=DT4;end
 DT4:if(n[1:0]==3)ss(1,10'd162+{2'b0,n[7:2]},pack,PN8);else begin n<=n+1;state<=DT0;end
 PN8:if(n==255)begin if(bad)state<=CHECK;else state<=PD0;end else begin n<=n+1;state<=DT0;end
 PD0:ss(0,10'd2+{3'b0,d[6:2]},0,PD1);
 PD1:begin xvalue<=line_data[d[1:0]*32+:32];rowline<=0;state<=PL0;end
 PL0:ex(0,TRIAL+{d,10'b0}+{rowline,4'b0},0,PL1);
 PL1:ss(1,10'd226+rowline,line_data,PL2);
 PL2:if(rowline==63)begin n<=0;pack<=0;state<=PN0;end else begin rowline<=rowline+1;state<=PL0;end
 PN0:ss(0,10'd226+{2'b0,n[7:2]},0,PN1);
 PN1:begin oldvalue<=line_data[n[1:0]*32+:32];if(alpha==32'h80000000)begin decay<={{32{line_data[n[1:0]*32+31]}},line_data[n[1:0]*32+:32]};alpha_bypass<=alpha_bypass+1;state<=PN3;end else mm($signed(line_data[n[1:0]*32+:32]),$signed(alpha),PN2);end
 PN2:rr(product,16'sd31,PL3);
 PL3:begin decay<=round_out;if(round_bad)bad<=1;state<=PN3;end
 PN3:ss(0,10'd162+{2'b0,n[7:2]},0,PN4);
 PN4:mm(xvalue,$signed(line_data[n[1:0]*32+:32]),PN5);
 PN5:rr(product,16'sd32+work_unit,PN6);
 PN6:begin injection<=round_out;if(round_bad)bad<=1;state<=PN7;end
 PN7:begin
 if(mag(decay)>maxdec)maxdec<=mag(decay);if(mag(injection)>maxinj)maxinj<=mag(injection);
 if(!fit32(proposal))range_bad<=1;pack[n[0]*64+:64]<=proposal;state<=PS0;end
 PS0:if(n[0])ss(1,10'd290+{1'b0,n[7:1]},pack,PS1);else begin n<=n+1;state<=PN0;end
 PS1:if(n==255)begin rowline<=0;state<=PS2;end else begin n<=n+1;state<=PN0;end
 PS2:ss(0,10'd290+rowline,0,PS3);
 PS3:ex(1,PROP+{d,11'b0}+{rowline,4'b0},line_data,LOAD3);
 LOAD3:if(rowline==127)begin if(d==127)state<=CHECK;else begin d<=d+1;state<=PD0;end end else begin rowline<=rowline+1;state<=PS2;end
 CHECK:if(bad||range_bad||guard_sum>65'h07fffffffffffffff)begin
 if(retries==8)fail(5);else if(work_unit==127)fail(6);else if(work_epoch==32'hffffffff)fail(7);else begin line_index<=0;state<=RE0;end end
 else begin line_index<=0;state<=SH0;end
 RE0:ex(0,TRIAL+{line_index,4'b0},0,RE1);
 RE1:begin pack<=line_data;lane<=0;state<=RE2;end
 RE2:rr({{32{pack[lane*32+31]}},pack[lane*32+:32]},16'sd1,RE3);
 RE3:begin pack[lane*32+:32]<=round_out[31:0];if(lane==3)state<=RE4;else begin lane<=lane+1;state<=RE2;end end
 RE4:ex(1,TRIAL+{line_index,4'b0},pack,CLONE3);
 CLONE3:if(line_index==8191)begin work_unit<=work_unit+1;work_epoch<=work_epoch+1;retries<=retries+1;state<=ATTEMPT;end else begin line_index<=line_index+1;state<=RE0;end
 SH0:ex(0,PROP+{line_index,5'b0},0,SH1);
 SH1:begin pack[31:0]<=line_data[31:0];pack[63:32]<=line_data[95:64];state<=SH2;end
 SH2:ex(0,PROP+{line_index,5'b0}+16,0,SH3);
 SH3:begin pack[95:64]<=line_data[31:0];pack[127:96]<=line_data[95:64];state<=SH4;end
 SH4:ex(1,BASE+(bank?0:32'h20000)+{line_index,4'b0},pack,RY2);
 RY2:if(line_index==8191)begin d<=0;maxscan<=0;maxskip<=0;state<=RD0;end else begin line_index<=line_index+1;state<=SH0;end
 RD0:ss(0,10'd2+{3'b0,d[6:2]},0,RD1);
 RD1:begin xvalue<=line_data[d[1:0]*32+:32];rowline<=0;sum<=0;state<=RL0;end
 RL0:ex(0,BASE+(bank?0:32'h20000)+{d,10'b0}+{rowline,4'b0},0,RL1);
 RL1:ss(1,10'd418+rowline,line_data,RL2);
 RL2:if(rowline==63)begin n<=0;state<=RN0;end else begin rowline<=rowline+1;state<=RL0;end
 RN0:ss(0,10'd418+{2'b0,n[7:2]},0,RN1);
 RN1:begin oldvalue<=line_data[n[1:0]*32+:32];state<=RN2;end
 RN2:ss(0,10'd98+{2'b0,n[7:2]},0,RN3);
 RN3:mm(oldvalue,$signed(line_data[n[1:0]*32+:32]),RN4);
 RN4:if(mag(product)>64'h007fffffffffffff)fail(8);else begin sum<=sum+product;if(n==255)state<=RN5;else begin n<=n+1;state<=RN0;end end
 RN5:rr(sum,-work_unit,RN6);
 RN6:if(round_bad)fail(8);else begin scan_value<=round_out;if(mag(round_out)>maxscan)maxscan<=mag(round_out);mm(xvalue,skip,RN7);end
 RN7:rr(product,16'sd20,RN8);
 RN8:if(round_bad)fail(8);else begin skip_value<=round_out;if(mag(round_out)>maxskip)maxskip<=mag(round_out);state<=RN9;end
 RN9:if(!fit32(outvalue)||out_guard>65'h07fffffffffffffff)fail(8);else begin pack2[d[1:0]*32+:32]<=outvalue[31:0];state<=RY0;end
 RY0:if(d[1:0]==3)ss(1,10'd482+{3'b0,d[6:2]},pack2,RL3);else begin d<=d+1;state<=RD0;end
 RL3:ex(1,YBASE+(bank?0:32'h200)+{d[6:2],4'b0},pack2,RY1);
 RY1:if(d==127)state<=OFFER;else begin d<=d+1;state<=RD0;end
 OFFER:if(reject_candidate)fail(3);else if(accept_candidate)state<=COMMIT0;
 COMMIT0:ex(1,DESC,context_valid?descriptor(position+1,work_epoch,work_unit,!bank,owner_head):descriptor(0,0,work_unit,0,owner_head),COMMIT1);
 COMMIT1:begin if(context_valid)begin position<=position+1;bank<=!bank;end else begin position<=0;bank<=0;end unit<=work_unit;numeric_epoch<=work_epoch;context_valid<=1;fail(0);end
 default:fail(10);
 endcase
 end
 end
endmodule
