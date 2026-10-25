// Full two-head K128 V128 GDN; one 16KiB 1RW, one signed32 multiplier.
module gdn104(input wire clk,reset,cmd,input wire command,input wire [31:0] owner,input wire [63:0] context_id,expected_position,expected_version,input wire [4:0] slot,
 output wire cmd_ready,cmd_accept,busy,done,input wire ack,output reg [7:0] status,
 input wire abort_request,output wire abort_ready,abort_accept,input wire accept_candidate,reject_candidate,output wire offer,
 output reg [63:0] position,version,output reg [31:0] numeric_epoch,output reg [15:0] units,value_units,output reg bank,state_validated,
 output wire [31:0] candidate_epoch,output wire [15:0] candidate_units,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 input wire mem_hold,mul_hold,output wire ext_req,ext_wr,output wire [31:0] ext_addr,output wire [127:0] ext_wdata,input wire ext_ready,ext_valid,output wire ext_take,input wire [127:0] ext_rdata,
 output reg [31:0] generation,output wire [31:0] ext_generation,input wire [31:0] response_generation,
 input wire peer_req,input wire signed [31:0] peer_a,peer_b,output wire peer_ready,peer_valid,input wire peer_take,output wire signed [63:0] peer_y,
 output reg [63:0] cycles,output wire [31:0] beats,transactions,mul_grants,peer_grants,contested,
 output reg [31:0] ext_reads,ext_writes,s_reads,s_writes,alpha_bypass,aborts,stale,wide_calls,
 output reg [3:0] retries,output wire [7:0] debug_state,
 output reg obs_valid,output reg [2:0] obs_kind,output reg obs_head,output reg [6:0] obs_pair,obs_i,output reg signed [63:0] obs_lo,obs_hi);
 localparam BASE=32'h04000000,TRIAL=32'h04040000,PROP=32'h04060000,YBASE=32'h040a0000,META=32'h040a1000,ROOT=32'h040a1080,COEFF=32'h040b0000;
 localparam IDLE=0,DONE=1,ER=2,EW=3,SR=4,SW=5,MR=6,MW=7,ROUND=8,WR=9,WW=10,ABORTED=11,
 REST0=12,REST1=13,REST2=14,REST3=15,REST4=16,REST5=17,REST6=18,
 LOAD0=20,LOAD1=21,LOAD2=22,CLONE0=23,CLONE1=24,CLONE2=25,ATTEMPT=26,
 DT0=30,DT1=31,DT2=32,DT3=33,DT4=34,DT5=35,DT6=36,DT7=37,DT8=38,
 PN0=40,PN1=41,PN2=42,PN3=43,PN4=44,PN5=45,PN6=46,PN7=47,PN8=48,PN9=49,
 CV0=50,CV1=51,CV2=52,CV3=53,CV4=54,CV5=55,CV6=56,CV7=57,CV8=58,CV9=59,
 PS0=60,PS1=61,PS2=62,PS3=63,PS4=64,PS5=65,PS6=66,PS7=67,PS8=68,PS9=69,PS10=70,PS11=71,CHECK=72,
 RE0=74,RE1=75,RE2=76,RE3=77,RE4=78,RE5=79,
 SH0=80,SH1=81,SH2=82,SH3=83,SH4=84,
 RD0=90,RD1=91,RD2=92,RD3=93,RD4=94,RD5=95,RD6=96,RD7=97,RD8=98,RD9=99,RY0=100,RY1=101,
 META0=102,META1=103,OFFER=104,COMMIT0=105,COMMIT1=106;
 reg [7:0] state,ret;reg cfg_pending,abort_pending,context_valid,head;reg [31:0] owner_latched,context_owner;reg [63:0] context_latched,context_saved;reg [4:0] slot_latched;
 reg [15:0] work_units;reg [31:0] work_epoch;reg [13:0] idx;reg [6:0] i,pair;reg [1:0] lane,badmask,meta_index;reg rest_bank;
 reg [127:0] line_data,pack,pack2,meta0,meta1,meta2,meta3;reg [63:0] root_version;
 reg [31:0] decay0,decay1;reg [15:0] beta0,beta1;reg signed [31:0] old0,old1,dec0,dec1;reg signed [15:0] key;
 reg signed [63:0] acc0,acc1,pred0,pred1,corr0,corr1,p0,p1,v0,v1,product;
 reg signed [63:0] round_in,round_out,wide_a,wide_result;reg signed [15:0] round_shift;reg round_bad,wide_error;reg signed [31:0] wide_b;
 reg [31:0] e_addr;reg e_wr;reg [127:0] e_data;wire erdy,ev;wire [127:0] ed;
 reg [9:0] s_addr;reg s_wr;reg [127:0] s_data;wire srdy,sv;wire [127:0] sd;
 reg signed [31:0] ma,mb;wire mrdy,mv;wire signed [63:0] my;wire [31:0] unused0,unused1;
 wire safe=!reset,issuing=!abort_pending&&!abort_accept;
 wire irreversible=state==COMMIT0||state==COMMIT1||((state==ER||state==EW)&&ret==COMMIT1);
 assign cmd_ready=safe&&state==IDLE&&!cfg_pending&&!cfg&&generation!=32'hffffffff;assign cmd_accept=cmd&&cmd_ready;assign busy=state!=IDLE;assign done=safe&&state==DONE;
 assign abort_ready=safe&&state!=IDLE&&state!=DONE&&!abort_pending&&!irreversible;assign abort_accept=abort_request&&abort_ready;
 assign offer=safe&&state==OFFER&&!abort_pending&&!abort_accept;assign candidate_units=work_units;assign candidate_epoch=work_epoch;assign debug_state=state;
 assign cfg_ready=safe&&state==IDLE&&!cfg_pending&&srdy;assign cfg_valid=safe&&cfg_pending&&sv;assign cfg_dout=sd;
 wire cfg_use=safe&&state==IDLE&&cfg&&!cfg_pending;
 wire sreq=safe&&(cfg_use||(state==SR&&issuing&&!mem_hold));
 store82 scratch(clk,reset,sreq,cfg_use?cfg_wr:s_wr,cfg_use?cfg_addr:s_addr,cfg_use?cfg_din:s_data,srdy,sv,cfg_pending?cfg_take:state==SW,sd);
 wire mlreq=safe&&state==ER&&issuing,lt,lr,lw,wv;wire [31:0] la;wire [127:0] ld,wd;
 wire drop_response=response_generation!=generation||(generation==32'hffffffff&&state==IDLE);
 memory_link link(clk,reset,mlreq,e_wr,e_addr,e_data,erdy,ev,state==EW,ed,lr,lw,la,ld,ext_ready&&safe,ext_valid&&!drop_response&&safe,lt,ext_rdata,wv,wd,beats,transactions);
 assign ext_req=safe&&lr;assign ext_wr=lw;assign ext_addr=la;assign ext_wdata=ld;assign ext_take=safe&&(drop_response||lt);assign ext_generation=generation;
 wire wrdy,wb,wvld,werr,wmreq,wmtake;wire signed [63:0] wy;wire signed [31:0] wma,wmb;
 wide104 lowerer(clk,reset,safe&&state==WR&&issuing,abort_pending||abort_accept,wide_a,wide_b,wrdy,wb,wvld,state==WW,wy,werr,wmreq,wma,wmb,mrdy,mv,wmtake,my);
 wire wselect=wb||state==WR||state==WW;wire peer_ready_raw,peer_valid_raw;assign peer_ready=safe&&peer_ready_raw;assign peer_valid=safe&&peer_valid_raw;
 mul84 #(1) service(clk,reset,mul_hold,safe&&(wselect?wmreq:state==MR&&issuing),wselect?wma:ma,wselect?wmb:mb,mrdy,mv,wselect?wmtake:state==MW,my,safe&&peer_req,peer_a,peer_b,peer_ready_raw,peer_valid_raw,peer_take,peer_y,mul_grants,peer_grants,unused0,unused1,contested);
 function [63:0] mag(input signed [63:0] v);begin mag=v[63]?-v:v;end endfunction
 function fits(input signed [63:0] v);begin fits=v>=-64'sd2147483648&&v<=64'sd2147418112;end endfunction
 function valid_line(input [127:0] v);begin valid_line=fits($signed(v[31:0]))&&fits($signed(v[63:32]))&&fits($signed(v[95:64]))&&fits($signed(v[127:96]));end endfunction
 function valid_coeff(input [127:0] v);integer t;begin valid_coeff=1;for(t=0;t<8;t=t+1)if(v[t*16+:16]==16'h8000)valid_coeff=0;end endfunction
 function [64:0] rounded(input signed [63:0] v,input signed [15:0] sh);reg [63:0] a,q,rm,half,mask;reg f;integer t;
 begin a=mag(v);q=0;rm=0;half=0;mask=0;f=v==64'sh8000000000000000;t=0;
 if(sh<0)begin t=-sh;if(t>62)begin f=1;q=0;end else begin f=f||(a>(64'h7fffffffffffffff>>t));q=a<<t;end end
 else if(sh==0)q=a;else if(sh>62)begin f=1;q=0;end else begin mask=(64'h1<<sh)-1;half=64'h1<<(sh-1);q=a>>sh;rm=a&mask;if(rm>half||(rm==half&&q[0]))q=q+1;end
 rounded={f,v[63]?(~q+64'd1):q};end endfunction
 wire [64:0] rounded_value=rounded(round_in,round_shift);
 wire signed [15:0] u0=$signed(work_units[7:0]),u1=$signed(work_units[15:8]),vu0=$signed(value_units[7:0]),vu1=$signed(value_units[15:8]);
 wire signed [15:0] ush=head?u1-vu1:u0-vu0;wire [31:0] alpha=head?decay1:decay0;wire [15:0] beta=head?beta1:beta0;
 wire [31:0] trial_pair_addr=TRIAL+({31'b0,head}<<16)+({25'b0,i}<<9)+({26'b0,pair[6:1]}<<4);
 wire [31:0] state_pair_addr=BASE+({31'b0,!bank}<<17)+({31'b0,head}<<16)+({25'b0,i}<<9)+({26'b0,pair[6:1]}<<4);
 wire [31:0] prop_pair_addr=PROP+({31'b0,head}<<17)+({25'b0,i}<<10)+({25'b0,pair}<<4);
 function [127:0] mdword(input [1:0] which);reg [127:0] x;begin x=0;case(which)
 0:begin x[31:0]=32'h47444e31;x[47:32]=1;x[79:48]=context_owner;x[84:80]=0;x[89:85]=1;x[103:96]=work_units[7:0];x[111:104]=work_units[15:8];x[119:112]=value_units[7:0];x[127:120]=value_units[15:8];end
 1:x={version+64'd1,position+64'd1};
 2:begin x[31:0]=work_epoch;x[95:32]=context_saved;x[96]=!bank;end
 3:x={YBASE+({31'b0,!bank}<<11),BASE+({31'b0,!bank}<<17),32'd32,COEFF};endcase mdword=x;end endfunction
 task ex(input wr,input [31:0] addr,input [127:0] value,input [7:0] target);begin e_wr<=wr;e_addr<=addr;e_data<=value;ret<=target;state<=ER;end endtask
 task ss(input wr,input [9:0] addr,input [127:0] value,input [7:0] target);begin s_wr<=wr;s_addr<=addr;s_data<=value;ret<=target;state<=SR;end endtask
 task mm(input signed [31:0] a,b,input [7:0] target);begin ma<=a;mb<=b;ret<=target;state<=MR;end endtask
 task rr(input signed [63:0] v,input signed [15:0] sh,input [7:0] target);begin round_in<=v;round_shift<=sh;ret<=target;state<=ROUND;end endtask
 task ww(input signed [63:0] a,input signed [31:0] b,input [7:0] target);begin wide_a<=a;wide_b<=b;ret<=target;state<=WR;wide_calls<=wide_calls+1;end endtask
 task fail(input [7:0] code);begin status<=code;state<=DONE;end endtask
 task observe(input [2:0] kind,input signed [63:0] lo,hi);begin obs_valid<=1;obs_kind<=kind;obs_lo<=lo;obs_hi<=hi;obs_head<=head;obs_pair<=pair;obs_i<=i;end endtask
 always @(posedge clk)begin
 if(reset)begin
 state<=IDLE;ret<=0;cfg_pending<=0;abort_pending<=0;context_valid<=0;head<=0;owner_latched<=0;context_owner<=0;context_latched<=0;context_saved<=0;slot_latched<=0;
 position<=0;version<=0;numeric_epoch<=0;units<=0;value_units<=0;bank<=0;state_validated<=0;work_units<=0;work_epoch<=0;idx<=0;i<=0;pair<=0;lane<=0;badmask<=0;meta_index<=0;rest_bank<=0;
 line_data<=0;pack<=0;pack2<=0;meta0<=0;meta1<=0;meta2<=0;meta3<=0;root_version<=0;decay0<=0;decay1<=0;beta0<=0;beta1<=0;old0<=0;old1<=0;dec0<=0;dec1<=0;key<=0;
 acc0<=0;acc1<=0;pred0<=0;pred1<=0;corr0<=0;corr1<=0;p0<=0;p1<=0;v0<=0;v1<=0;product<=0;round_in<=0;round_out<=0;wide_a<=0;wide_result<=0;round_shift<=0;round_bad<=0;wide_error<=0;wide_b<=0;
 e_addr<=0;e_wr<=0;e_data<=0;s_addr<=0;s_wr<=0;s_data<=0;ma<=0;mb<=0;generation<=0;status<=0;cycles<=0;ext_reads<=0;ext_writes<=0;s_reads<=0;s_writes<=0;alpha_bypass<=0;aborts<=0;stale<=0;wide_calls<=0;retries<=0;
 obs_valid<=0;obs_kind<=0;obs_head<=0;obs_pair<=0;obs_i<=0;obs_lo<=0;obs_hi<=0;
 end else begin
 obs_valid<=0;if(cfg&&cfg_ready)cfg_pending<=1;else if(cfg_valid&&cfg_take)cfg_pending<=0;
 if(state!=IDLE&&state!=DONE)cycles<=cycles+1;if(ext_valid&&ext_take&&drop_response)stale<=stale+1;
 if(state==ER&&mlreq&&erdy)begin if(e_wr)ext_writes<=ext_writes+1;else ext_reads<=ext_reads+1;end
 if(state==SR&&sreq&&srdy)begin if(s_wr)s_writes<=s_writes+1;else s_reads<=s_reads+1;end
 if(abort_accept)begin abort_pending<=1;aborts<=aborts+1;if((state!=EW&&state!=SW&&state!=MW&&state!=WW)||(state==EW&&ev)||(state==SW&&sv)||(state==MW&&mv)||(state==WW&&wvld))state<=ABORTED;end
 else if(abort_pending)begin if(state==ABORTED)begin abort_pending<=0;fail(2);end else if((state==EW&&ev)||(state==SW&&sv)||(state==MW&&mv)||(state==WW&&wvld))state<=ABORTED;end
 else case(state)
 IDLE:if(cmd_accept)begin generation<=generation+1;cycles<=0;status<=0;ext_reads<=0;ext_writes<=0;s_reads<=0;s_writes<=0;alpha_bypass<=0;wide_calls<=0;retries<=0;
 owner_latched<=owner;context_latched<=context_id;slot_latched<=slot;work_units<=units;work_epoch<=numeric_epoch;idx<=0;head<=0;pair<=0;i<=0;badmask<=0;
 if(!command)begin context_valid<=0;state_validated<=0;state<=REST0;end
 else if(!context_valid||owner!=context_owner||context_id!=context_saved||expected_position!=position||expected_version!=version||position==64'hffffffffffffffff||version==64'hffffffffffffffff)fail(4);else state<=LOAD0;end
 DONE:if(ack)state<=IDLE;
 ER:if(erdy)state<=EW;
 EW:if(ev)begin line_data<=ed;state<=ret;end
 SR:if(srdy&&!mem_hold)state<=SW;
 SW:if(sv)begin line_data<=sd;state<=ret;end
 MR:if(mrdy)state<=MW;
 MW:if(mv)begin product<=my;state<=ret;end
 ROUND:begin round_out<=rounded_value[63:0];round_bad<=rounded_value[64];state<=ret;end
 WR:if(wrdy)state<=WW;
 WW:if(wvld)begin wide_result<=wy;wide_error<=werr;state<=ret;end
 REST0:ex(0,ROOT,0,REST1);
 REST1:if(line_data[31:0]!=32'h47445231||!line_data[33]||line_data[63:34]!=0)fail(9);else begin rest_bank<=line_data[32];root_version<=line_data[127:64];state<=REST2;end
 REST2:ex(0,META+({31'b0,rest_bank}<<6),0,REST3);
 REST3:begin meta0<=line_data;ex(0,META+({31'b0,rest_bank}<<6)+16,0,REST4);end
 REST4:begin meta1<=line_data;ex(0,META+({31'b0,rest_bank}<<6)+32,0,REST5);end
 REST5:begin meta2<=line_data;ex(0,META+({31'b0,rest_bank}<<6)+48,0,REST6);end
 REST6:if(meta0[31:0]!=32'h47444e31||meta0[47:32]!=1||meta0[79:48]!=owner_latched||meta0[84:80]!=0||meta0[89:85]!=1||meta0[95:90]!=0||meta1[127:64]!=root_version||meta2[95:32]!=context_latched||meta2[96]!=rest_bank||meta2[127:97]!=0||line_data[31:0]!=COEFF||line_data[63:32]!=32||line_data[95:64]!=BASE+({31'b0,rest_bank}<<17)||line_data[127:96]!=YBASE+({31'b0,rest_bank}<<11))fail(9);
 else begin position<=meta1[63:0];version<=meta1[127:64];numeric_epoch<=meta2[31:0];units<=meta0[111:96];value_units<=meta0[127:112];bank<=rest_bank;context_owner<=owner_latched;context_saved<=context_latched;context_valid<=1;fail(0);end
 LOAD0:ex(0,COEFF+slot_latched*32'd1568+({18'b0,idx}<<4),0,LOAD1);
 LOAD1:if((idx==0&&(line_data[31:0]!=32'h47444331||line_data[63:32]!={27'd0,slot_latched}||line_data[127:64]!=position))||(idx==1&&(line_data[31:0]>32'h80000000||line_data[63:32]>32'h80000000||line_data[79:64]>32768||line_data[95:80]>32768||line_data[127:96]!=0))||(idx>=2&&!valid_coeff(line_data)))fail(10);
 else begin if(idx==1)begin decay0<=line_data[31:0];decay1<=line_data[63:32];beta0<=line_data[79:64];beta1<=line_data[95:80];end ss(1,idx[9:0],line_data,LOAD2);end
 LOAD2:if(idx==97)begin idx<=0;state<=CLONE0;end else begin idx<=idx+1;state<=LOAD0;end
 CLONE0:ex(0,BASE+({31'b0,bank}<<17)+({18'b0,idx}<<4),0,CLONE1);
 CLONE1:if(!valid_line(line_data))begin state_validated<=0;fail(11);end else ex(1,TRIAL+({18'b0,idx}<<4),line_data,CLONE2);
 CLONE2:if(idx==8191)begin state_validated<=1;state<=ATTEMPT;end else begin idx<=idx+1;state<=CLONE0;end
 ATTEMPT:if(u0-vu0>62||u1-vu1>62)fail(12);else if(u0-vu0< -32||u1-vu1< -32)begin badmask<=3;state<=RE0;end else begin head<=0;pair<=0;i<=0;badmask<=0;state<=DT0;end
 DT0:ex(0,trial_pair_addr,0,DT1);
 DT1:begin old0<=pair[0]?$signed(line_data[95:64]):$signed(line_data[31:0]);old1<=pair[0]?$signed(line_data[127:96]):$signed(line_data[63:32]);state<=DT2;end
 DT2:if(alpha==32'h80000000)begin dec0<=old0;dec1<=old1;alpha_bypass<=alpha_bypass+2;state<=DT7;end else mm(old0,$signed(alpha),DT3);
 DT3:rr(product,31,DT4);
 DT4:if(round_bad)begin badmask<=3;state<=RE0;end else begin dec0<=round_out[31:0];mm(old1,$signed(alpha),DT5);end
 DT5:rr(product,31,DT6);
 DT6:if(round_bad)begin badmask<=3;state<=RE0;end else begin dec1<=round_out[31:0];state<=DT7;end
 DT7:ss(1,10'd128+{3'b0,i},{64'd0,dec1,dec0},DT8);
 DT8:if(i==127)begin i<=0;acc0<=0;acc1<=0;state<=PN0;end else begin i<=i+1;state<=DT0;end
 PN0:ss(0,10'd128+{3'b0,i},0,PN1);
 PN1:begin dec0<=line_data[31:0];dec1<=line_data[63:32];ss(0,10'd34+({9'd0,head}<<4)+{6'd0,i[6:3]},0,PN2);end
 PN2:begin key<=line_data[{i[2:0],4'b0}+:16];state<=PN3;end
 PN3:mm(dec0,{{16{key[15]}},key},PN4);
 PN4:begin acc0<=acc0+product;mm(dec1,{{16{key[15]}},key},PN5);end
 PN5:begin acc1<=acc1+product;if(i==127)state<=PN6;else begin i<=i+1;state<=PN0;end end
 PN6:rr(acc0,15,PN7);
 PN7:if(round_bad)begin badmask<=3;state<=RE0;end else begin pred0<=round_out;rr(acc1,15,PN8);end
 PN8:if(round_bad)begin badmask<=3;state<=RE0;end else begin pred1<=round_out;state<=PN9;end
 PN9:begin observe(0,pred0,pred1);state<=CV0;end
 CV0:ss(0,10'd66+({9'd0,head}<<4)+{5'd0,pair[6:2]},0,CV1);
 CV1:begin v0<=$signed(line_data[{pair[1:0],5'b0}+:16]);v1<=$signed(line_data[{pair[1:0],5'b0}+16+:16]);state<=CV2;end
 CV2:rr(v0,ush,CV3);
 CV3:if(round_bad)begin badmask<=3;state<=RE0;end else begin v0<=round_out-pred0;rr(v1,ush,CV4);end
 CV4:if(round_bad)begin badmask<=3;state<=RE0;end else begin v1<=round_out-pred1;state<=CV5;end
 CV5:begin observe(1,v0,v1);ww(v0,{16'd0,beta},CV6);end
 CV6:if(wide_error)begin badmask<=3;state<=RE0;end else rr(wide_result,15,CV7);
 CV7:if(round_bad)begin badmask<=3;state<=RE0;end else begin corr0<=round_out;ww(v1,{16'd0,beta},CV8);end
 CV8:if(wide_error)begin badmask<=3;state<=RE0;end else rr(wide_result,15,CV9);
 CV9:if(round_bad)begin badmask<=3;state<=RE0;end else begin corr1<=round_out;state<=PS0;i<=0;end
 PS0:begin observe(2,corr0,corr1);state<=PS1;end
 PS1:ss(0,10'd128+{3'b0,i},0,PS2);
 PS2:begin dec0<=line_data[31:0];dec1<=line_data[63:32];ss(0,10'd34+({9'd0,head}<<4)+{6'd0,i[6:3]},0,PS3);end
 PS3:begin key<=line_data[{i[2:0],4'b0}+:16];state<=PS4;end
 PS4:ww(corr0,{{16{key[15]}},key},PS5);
 PS5:if(wide_error)begin badmask<=3;state<=RE0;end else rr(wide_result,15,PS6);
 PS6:if(round_bad)begin badmask<=3;state<=RE0;end else begin p0<=round_out+$signed(dec0);ww(corr1,{{16{key[15]}},key},PS7);end
 PS7:if(wide_error)begin badmask<=3;state<=RE0;end else rr(wide_result,15,PS8);
 PS8:if(round_bad)begin badmask<=3;state<=RE0;end else begin p1<=round_out+$signed(dec1);state<=PS9;end
 PS9:begin observe(3,p0,p1);if(!fits(p0)||!fits(p1))badmask[head]<=1;ex(1,prop_pair_addr,{p1,p0},PS10);end
 PS10:if(i!=127)begin i<=i+1;state<=PS1;end else if(pair!=63)begin pair<=pair+1;i<=0;state<=DT0;end else if(!head)begin head<=1;pair<=0;i<=0;state<=DT0;end else state<=CHECK;
 CHECK:if(badmask!=0)state<=RE0;else begin idx<=0;state<=SH0;end
 RE0:if(retries==8)fail(6);else if((badmask[0]&&u0==127)||(badmask[1]&&u1==127))fail(7);else if(work_epoch==32'hffffffff)fail(8);else begin head<=0;idx<=0;lane<=0;state<=RE1;end
 RE1:if(!badmask[head])state<=RE5;else ex(0,TRIAL+({31'b0,head}<<16)+({18'b0,idx}<<4),0,RE2);
 RE2:begin pack<=line_data;lane<=0;state<=RE3;end
 RE3:rr($signed(pack[{lane,5'b0}+:32]),1,RE4);
 RE4:if(round_bad)fail(12);else begin pack[{lane,5'b0}+:32]<=round_out[31:0];if(lane==3)state<=RE5;else begin lane<=lane+1;state<=RE3;end end
 RE5:if(badmask[head]&&idx<4096)begin ex(1,TRIAL+({31'b0,head}<<16)+({18'b0,idx}<<4),pack,PS11);end else if(!head)begin head<=1;idx<=0;state<=RE1;end else begin retries<=retries+1;work_epoch<=work_epoch+1;state<=ATTEMPT;end
 PS11:if(idx==4095)begin idx<=4096;if(head)work_units[15:8]<=work_units[15:8]+1;else work_units[7:0]<=work_units[7:0]+1;state<=RE5;end else begin idx<=idx+1;state<=RE1;end
 SH0:ex(0,PROP+({18'b0,idx}<<5),0,SH1);
 SH1:begin pack<=line_data;ex(0,PROP+({18'b0,idx}<<5)+16,0,SH2);end
 SH2:ex(1,BASE+({31'b0,!bank}<<17)+({18'b0,idx}<<4),{line_data[95:64],line_data[31:0],pack[95:64],pack[31:0]},SH3);
 SH3:if(idx==8191)begin head<=0;pair<=0;i<=0;acc0<=0;acc1<=0;state<=RD0;end else begin idx<=idx+1;state<=SH0;end
 RD0:ex(0,state_pair_addr,0,RD1);
 RD1:begin old0<=pair[0]?$signed(line_data[95:64]):$signed(line_data[31:0]);old1<=pair[0]?$signed(line_data[127:96]):$signed(line_data[63:32]);ss(0,10'd2+({9'd0,head}<<4)+{6'd0,i[6:3]},0,RD2);end
 RD2:begin key<=line_data[{i[2:0],4'b0}+:16];state<=RD3;end
 RD3:mm(old0,{{16{key[15]}},key},RD4);
 RD4:begin acc0<=acc0+product;mm(old1,{{16{key[15]}},key},RD5);end
 RD5:begin acc1<=acc1+product;if(i==127)state<=RD6;else begin i<=i+1;state<=RD0;end end
 RD6:rr(acc0,15,RD7);
 RD7:if(round_bad)begin badmask<=3;state<=RE0;end else begin p0<=round_out;rr(acc1,15,RD8);end
 RD8:if(round_bad)begin badmask<=3;state<=RE0;end else begin p1<=round_out;state<=RD9;end
 RD9:begin observe(4,p0,p1);ex(1,YBASE+({31'b0,!bank}<<11)+({31'b0,head}<<10)+({25'b0,pair}<<4),{p1,p0},RY0);end
 RY0:begin i<=0;acc0<=0;acc1<=0;if(pair!=63)begin pair<=pair+1;state<=RD0;end else if(!head)begin head<=1;pair<=0;state<=RD0;end else begin meta_index<=0;state<=META0;end end
 META0:ex(1,META+({31'b0,!bank}<<6)+{26'd0,meta_index,4'd0},mdword(meta_index),META1);
 META1:if(meta_index==3)state<=OFFER;else begin meta_index<=meta_index+1;state<=META0;end
 OFFER:if(reject_candidate)fail(3);else if(accept_candidate)state<=COMMIT0;
 COMMIT0:ex(1,ROOT,{version+64'd1,30'd0,1'b1,!bank,32'h47445231},COMMIT1);
 COMMIT1:begin position<=position+1;version<=version+1;numeric_epoch<=work_epoch;units<=work_units;bank<=!bank;fail(0);end
 default:fail(255);
 endcase end end
endmodule
