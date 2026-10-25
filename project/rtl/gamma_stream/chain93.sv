module chain93(input wire clk,reset,soft_abort,cmd,cache_mode,mem_hold,mul_hold,output wire cmd_ready,cmd_accept,input wire norm_only,gamma_stream,input wire [11:0] h,input wire [31:0] gamma_address,
 output wire [31:0] gamma_loads,gamma_stores,den_events,output wire [127:0] observed_sum,observed_den,
 output wire swrite_event,output wire [9:0] swrite_addr,output wire [127:0] swrite_data,
 output reg [31:0] epoch,stale_responses,aborts,output wire [31:0] ext_epoch,input wire [31:0] ext_response_epoch,output wire mem_request,mul_request,
 input wire [31:0] epsilon,coefficient,output wire busy,done,input wire ack,output reg [7:0] status,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 output reg [63:0] cycles,output wire [63:0] norm_cycles,output wire [31:0] reads,writes,packets,macs,mwrites,
 output wire ext_req,output wire [31:0] ext_addr,input wire ext_ready,ext_valid,output wire ext_take,input wire [127:0] ext_data,
 output wire [31:0] wire_beats,transactions,output wire obs_valid,output wire [10:0] obs_row,output wire [2:0] obs_rank,output wire signed [31:0] obs_acc,obs_down,
 output wire mwrite,output wire [9:0] maddr,output wire [127:0] mdata,output wire [7:0] debug_state,
 output wire [31:0] cache_reads,cache_writes,mul_grants0,mul_grants1,mul_wait0,mul_wait1,mul_contested,
 output reg [31:0] port_wait_m,port_wait_n,output wire [4:0] mdebug,output wire [7:0] ndebug);
 wire core_reset=reset||soft_abort;
 reg saved_norm_only,saved_stream;reg [11:0] saved_h;reg [31:0] saved_gamma;
 reg [2:0] state;reg pending;reg [31:0] saved_epsilon,saved_coefficient;wire mdone,ndone,nbusy;wire [7:0] ms,ns;wire mreq,mready,mvalid,mtake;wire [31:0] m_address;wire [127:0] mreply;
 wire sr,sw,st,sready,svalid;wire nr,nw,nready,nvalid,nt;wire [9:0] na;wire [127:0] ni,sd;
 wire [7:0] normdebug;assign ndebug=normdebug;wire rready,rvalid;wire [127:0] rd;wire usecfg=!core_reset&&!busy&&cfg;
 assign cmd_ready=!reset&&!soft_abort&&state==0&&!pending&&!cfg&&epoch!=32'hffffffff;assign cmd_accept=cmd&&cmd_ready;
 assign ext_epoch=epoch;wire link_take;wire response_match=ext_response_epoch==epoch;
 // At exhausted idle or abort, the final epoch is invalidated without wrapping.
 wire terminal_discard=(epoch==32'hffffffff)&&(soft_abort||state==0);
 wire drop_response=!response_match||terminal_discard;
 assign ext_take=drop_response?1'b1:link_take;
 always @(posedge clk)begin
 if(reset)begin epoch<=0;stale_responses<=0;aborts<=0;end else begin
 if((soft_abort||cmd_accept)&&epoch!=32'hffffffff)epoch<=epoch+1;
 if(soft_abort)aborts<=aborts+1;
 if(ext_valid&&ext_take&&drop_response)stale_responses<=stale_responses+1;
 end end
 assign busy=state!=0;assign done=!core_reset&&state==5;assign cfg_ready=!core_reset&&!busy&&!pending&&rready;assign cfg_valid=!core_reset&&pending&&rvalid;assign cfg_dout=rd;assign debug_state={5'b0,state};
 assign mem_request=state==1?sr:nr;
 always @(posedge clk)begin
  if(core_reset)begin port_wait_m<=0;port_wait_n<=0;state<=0;status<=0;cycles<=0;pending<=0;saved_epsilon<=0;saved_coefficient<=0;saved_h<=0;saved_norm_only<=0;saved_stream<=0;saved_gamma<=0;end
  else begin
   if(state==1&&sr&&!sready)port_wait_m<=port_wait_m+1;
   if(state==3&&nr&&!nready)port_wait_n<=port_wait_n+1;
   if(cmd_accept)begin port_wait_m<=0;port_wait_n<=0;end
   if(cfg&&cfg_ready)pending<=1;else if(cfg_valid&&cfg_take)pending<=0;
   if(state!=0&&state!=5)cycles<=cycles+1;
   case(state)
    0:if(cmd_accept)begin cycles<=0;status<=0;saved_epsilon<=epsilon;saved_coefficient<=coefficient;saved_h<=h;saved_norm_only<=norm_only;saved_stream<=gamma_stream;saved_gamma<=gamma_address;
     if((h!=1536&&h!=2560)||(!norm_only&&h!=1536)||(h==2560&&!gamma_stream))begin status<=16;state<=5;end
     else if(gamma_stream&&(gamma_address[3:0]!=0||gamma_address<32'h01000000||{1'b0,gamma_address}+{19'b0,h,2'b0}>33'h002000000))begin status<=17;state<=5;end
     else state<=norm_only?2:1;end
    1:if(mdone)begin if(ms!=0)begin status<=ms;state<=5;end else state<=2;end
    2:state<=3;
    3:if(ndone)begin status<=ns;state<=5;end
    5:if(ack)state<=0;
   endcase
  end
 end
 wire mr0,mr1,mready0,mready1,mv0,mv1;wire signed [31:0] ma0,mb0,ma1,mb1;wire signed [63:0] my0,my1;
 assign mul_request=mr0||mr1;
 mul84 #(1) multipliers(clk,core_reset,mul_hold,mr0,ma0,mb0,mready0,mv0,1'b1,my0,mr1,ma1,mb1,mready1,mv1,1'b1,my1,mul_grants0,mul_grants1,mul_wait0,mul_wait1,mul_contested);
 mfront85 m(clk,core_reset,cmd_accept&&!norm_only&&h==1536&&(!gamma_stream||(gamma_address[3:0]==0&&gamma_address>=32'h01000000&&{1'b0,gamma_address}+{19'b0,h,2'b0}<=33'h002000000)),state==1&&mdone,cache_mode,saved_coefficient,mdone,ms,mreq,m_address,mready,mvalid,mtake,mreply,sr,sw,maddr,mdata,sready,svalid,st,rd,packets,macs,mwrites,obs_valid,obs_row,obs_rank,obs_acc,obs_down,mr0,ma0,mb0,mready0,mv0,my0,cache_reads,cache_writes,mdebug);
 wire gr,gready,gvalid,gtake;wire [31:0] ga;wire [127:0] gd;wire lready,lvalid,ltake;wire [127:0] ld;
 wire use_m=state==1;
 assign mready=use_m&&lready;assign mvalid=use_m&&lvalid;assign mreply=ld;
 assign gready=state==3&&lready;assign gvalid=state==3&&lvalid;assign gd=ld;assign ltake=use_m?mtake:gtake;
 wire unused_wr;wire [127:0] unused_wdata;wire wire_valid;wire [127:0] wire_data;
 memory_link link(clk,core_reset,use_m?mreq:(state==3&&gr),1'b0,use_m?m_address:ga,128'b0,lready,lvalid,ltake,ld,ext_req,unused_wr,ext_addr,unused_wdata,ext_ready,ext_valid&&!drop_response,link_take,ext_data,wire_valid,wire_data,wire_beats,transactions);
 norm93 #(1) n(clk,core_reset,state==2,saved_h,saved_epsilon,saved_stream,saved_gamma,gr,ga,gready,gvalid,gtake,gd,gamma_loads,gamma_stores,den_events,observed_sum,observed_den,nbusy,ndone,state==5&&ack,ns,nr,nw,na,ni,nready,nvalid,nt,rd,norm_cycles,reads,writes,normdebug,mr1,ma1,mb1,mready1,mv1,my1);
 assign sready=rready&&!pending&&!mem_hold&&state==1;assign svalid=rvalid&&!pending&&state==1;
 assign nready=rready&&!pending&&!mem_hold&&state==3;assign nvalid=rvalid&&!pending&&state==3;
 assign mwrite=sr&&sw&&sready&&maddr<384;
 assign swrite_event=!core_reset&&!usecfg&&!mem_hold&&rready&&((state==1&&sr&&sw)||(state==3&&nr&&nw));
 assign swrite_addr=state==1?maddr:na;assign swrite_data=state==1?mdata:ni;
 store82 frame(clk,core_reset,usecfg?cfg:((state==1?sr:nr)&&!mem_hold),usecfg?cfg_wr:(state==1?sw:nw),usecfg?cfg_addr:(state==1?maddr:na),usecfg?cfg_din:(state==1?mdata:ni),rready,rvalid,pending?cfg_take:(state==1?st:nt),rd);
endmodule
