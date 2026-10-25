module chain82 #(parameter PROFILE=0)(input wire clk,reset,cmd,mem_hold,output wire mem_request,
 input wire [31:0] epsilon,output wire busy,done,input wire ack,output reg [7:0] status,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 output reg [63:0] cycles,output wire [63:0] norm_cycles,output wire [31:0] reads,writes,packets,macs,mwrites,
 output wire ext_req,output wire [31:0] ext_addr,input wire ext_ready,ext_valid,output wire ext_take,input wire [127:0] ext_data,
 output wire [31:0] wire_beats,transactions,output wire obs_valid,output wire [10:0] obs_row,output wire [2:0] obs_rank,output wire signed [31:0] obs_acc,obs_down,
 output wire mwrite,output wire [9:0] maddr,output wire [127:0] mdata,output wire [7:0] debug_state);
 reg [2:0] state;reg pending;wire mdone,ndone,nbusy;wire [7:0] ms,ns;wire mreq,mready,mvalid,mtake;wire [31:0] m_address;wire [127:0] mreply;
 wire sr,st,sready,svalid;wire nr,nw,nready,nvalid,nt;wire [9:0] na;wire [127:0] ni,sd;
 wire [7:0] normdebug;wire rready,rvalid;wire [127:0] rd;wire usecfg=!busy&&cfg;
 assign busy=state!=0;assign done=state==5;assign cfg_ready=!busy&&!pending&&rready;assign cfg_valid=pending&&rvalid;assign cfg_dout=rd;assign debug_state={5'b0,state};
 assign mem_request=state==1?sr:nr;
 always @(posedge clk)begin
  if(reset)begin state<=0;status<=0;cycles<=0;pending<=0;end
  else begin
   if(cfg&&cfg_ready)pending<=1;else if(cfg_valid&&cfg_take)pending<=0;
   if(state!=0&&state!=5)cycles<=cycles+1;
   case(state)
    0:if(cmd&&!pending&&!cfg)begin state<=1;cycles<=0;status<=0;end
    1:if(mdone)begin if(ms!=0)begin status<=ms;state<=5;end else state<=2;end
    2:state<=3;
    3:if(ndone)begin status<=ns;state<=5;end
    5:if(ack)state<=0;
   endcase
  end
 end
 mfront82 m(clk,reset,cmd&&!busy&&!pending&&!cfg,state==1&&mdone,mdone,ms,mreq,m_address,mready,mvalid,mtake,mreply,sr,maddr,mdata,sready,svalid,st,packets,macs,mwrites,obs_valid,obs_row,obs_rank,obs_acc,obs_down);
 wire unused_wr;wire [127:0] unused_wdata;wire wire_valid;wire [127:0] wire_data;
 memory_link link(clk,reset,mreq,1'b0,m_address,128'b0,mready,mvalid,mtake,mreply,ext_req,unused_wr,ext_addr,unused_wdata,ext_ready,ext_valid,ext_take,ext_data,wire_valid,wire_data,wire_beats,transactions);
 norm82 #(PROFILE) n(clk,reset,state==2,12'd1536,epsilon,nbusy,ndone,state==5&&ack,ns,nr,nw,na,ni,nready,nvalid,nt,rd,norm_cycles,reads,writes,normdebug);
 assign sready=rready&&!pending&&!mem_hold&&state==1;assign svalid=rvalid&&!pending&&state==1;
 assign nready=rready&&!pending&&!mem_hold&&state==3;assign nvalid=rvalid&&!pending&&state==3;
 assign mwrite=sr&&sready;
 store82 frame(clk,reset,usecfg?cfg:((state==1?sr:nr)&&!mem_hold),usecfg?cfg_wr:(state==1?1'b1:nw),usecfg?cfg_addr:(state==1?maddr:na),usecfg?cfg_din:(state==1?mdata:ni),rready,rvalid,pending?cfg_take:(state==1?st:nt),rd);
endmodule
