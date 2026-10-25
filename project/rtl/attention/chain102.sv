// Bounded standalone A inventory. No claim of integrated physical M/A bank.
module chain102(input wire clk,reset,soft_abort,cmd,mem_hold,mul_hold,input wire [10:0] length,position,input wire [15:0] window,
 input wire [63:0] query_units,input wire signed [7:0] key_unit,value_unit,input wire [31:0] key_address,value_address,owner,input_version,score_multiplier,
 output wire cmd_ready,cmd_accept,busy,done,input wire ack,output reg [7:0] status,output wire [7:0] debug_state,adebug,
 output reg [31:0] epoch,stale_responses,aborts,output wire [31:0] ext_epoch,input wire [31:0] ext_response_epoch,
 output wire ext_req,output wire [31:0] ext_addr,input wire ext_ready,ext_valid,output wire ext_take,input wire [127:0] ext_data,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 output wire [63:0] cycles,output wire [31:0] macs,sreads,swrites,kloads,vloads,lut_reads,divides,score_products,wire_beats,transactions,mul_grants,
 output wire obs_valid,output wire [1:0] obs_kind,output wire [2:0] obs_head,output wire [10:0] obs_key,output wire signed [31:0] obs_x,obs_y,output wire [63:0] obs_sum,
 output wire mem_request,mul_request,output wire swrite_event,output wire [9:0] swrite_addr);
 reg [2:0] state;localparam IDLE=0,START=1,ACTIVE=2,DRAIN=3,DONE=4;
 reg pending,cache_registered;reg [31:0] last_owner,last_version,last_k,last_v;reg signed [7:0] last_ke,last_ve;
 reg [10:0] len;reg [63:0] qe;reg signed [7:0] ke;reg [31:0] ka,va;
 wire core_reset=reset||soft_abort,active=state==ACTIVE;
 wire ar,aw,at,sr,sv,er,et,lr,lv,lt,mr,mt,mready,mvalid,fr,ft,fready,fvalid,ferror,ad;
 wire [9:0] aa;wire [127:0] ai,sd,ld,fa,fb,fvalue,fremainder;wire [31:0] ea;wire signed [31:0] ma,mb;wire signed [63:0] mv;wire [7:0] ast;
 assign busy=state!=IDLE;assign debug_state={5'b0,state};assign done=!core_reset&&state==DONE;
 assign cmd_ready=!core_reset&&state==IDLE&&!pending&&!cfg&&epoch!=32'hffffffff;assign cmd_accept=cmd&&cmd_ready;
 assign cfg_ready=!core_reset&&state==IDLE&&!pending&&sr;assign cfg_valid=!core_reset&&pending&&sv;assign cfg_dout=sd;
 wire config_select=!core_reset&&state==IDLE&&!pending&&cfg;
 wire drop_response=ext_response_epoch!=epoch||state==IDLE||state==DONE;
 wire raw_req,raw_take;assign ext_req=!core_reset&&raw_req;assign ext_take=!core_reset&&(drop_response||raw_take);assign ext_epoch=epoch;
 wire [31:0] bytes={21'b0,length}<<8;
 function legal(input [31:0] a,n);begin legal=a[3:0]==0&&a>=32'h04000000&&({1'b0,a}+{1'b0,n})<=33'h008000000;end endfunction
 wire alias_kv=({1'b0,key_address}<{1'b0,value_address}+{1'b0,bytes})&&({1'b0,value_address}<{1'b0,key_address}+{1'b0,bytes});
 wire same_cache=cache_registered&&owner==last_owner&&input_version==last_version;
 wire metadata_changed=key_address!=last_k||value_address!=last_v||key_unit!=last_ke||value_unit!=last_ve;
 wire invalid=length==0||length>1056||position+12'd1!={1'b0,length}||window!=0||score_multiplier!=94906266||!legal(key_address,bytes)||!legal(value_address,bytes)||alias_kv;
 wire drained=lr&&!lv&&sr&&!sv&&mready&&!mvalid&&fready&&!fvalid;
 always @(posedge clk)begin
  if(reset)begin epoch<=0;stale_responses<=0;aborts<=0;end else begin
   if((soft_abort||cmd_accept)&&epoch!=32'hffffffff)epoch<=epoch+1;
   if(soft_abort)aborts<=aborts+1;
   if(ext_valid&&ext_take&&drop_response)stale_responses<=stale_responses+1;
  end
  if(reset)begin cache_registered<=0;last_owner<=0;last_version<=0;last_k<=0;last_v<=0;last_ke<=0;last_ve<=0;end
  if(core_reset)begin state<=IDLE;pending<=0;len<=0;qe<=0;ke<=0;ka<=0;va<=0;status<=0;end
  else begin
   if(cfg&&cfg_ready)pending<=1;else if(cfg_valid&&cfg_take)pending<=0;
   case(state)
    IDLE:if(cmd_accept)begin status<=0;len<=length;qe<=query_units;ke<=key_unit;ka<=key_address;va<=value_address;
     if(invalid)begin status<=16;state<=DONE;end else if(same_cache&&metadata_changed)begin status<=17;state<=DONE;end
     else begin cache_registered<=1;last_owner<=owner;last_version<=input_version;last_k<=key_address;last_v<=value_address;last_ke<=key_unit;last_ve<=value_unit;state<=START;end end
    START:state<=ACTIVE;
    ACTIVE:if(ad)begin status<=ast;state<=DRAIN;end
    DRAIN:if(drained)state<=DONE;
    DONE:if(ack)state<=IDLE;
    default:begin status<=255;state<=DONE;end
   endcase
  end
 end
 attention102 a(clk,core_reset,state==START,state==DONE&&ack,len,qe,ke,ka,va,ad,ast,adebug,
 er,ea,active&&lr,active&&lv,et,ld,ar,aw,aa,ai,active&&sr&&!mem_hold,active&&sv,at,sd,
 mr,ma,mb,active&&mready,active&&mvalid,mt,mv,fr,fa,fb,active&&fready,active&&fvalid,ft,fvalue,fremainder,ferror,
 cycles,macs,sreads,swrites,kloads,vloads,lut_reads,divides,score_products,obs_valid,obs_kind,obs_head,obs_key,obs_x,obs_y,obs_sum);
 wire unused_v1,unused_r1;wire signed [63:0] unused_y1;wire [31:0] mg1,mw0,mw1,mc;
 mul84 #(1) mul(clk,core_reset,mul_hold,active&&mr,ma,mb,mready,mvalid,mt,mv,1'b0,32'sd0,32'sd0,unused_r1,unused_v1,1'b1,unused_y1,mul_grants,mg1,mw0,mw1,mc);
 sfu84 #(1) sfu(clk,core_reset,active&&fr,2'd1,fa,fb,fready,fvalid,ft,fvalue,fremainder,ferror);
 wire unused_wr,wv;wire [127:0] unused_d,wd;
 memory_link link(clk,core_reset,active&&er,1'b0,ea,128'd0,lr,lv,et,ld,raw_req,unused_wr,ext_addr,unused_d,ext_ready&&!core_reset,ext_valid&&!core_reset&&!drop_response,raw_take,ext_data,wv,wd,wire_beats,transactions);
 assign mem_request=active&&ar;assign mul_request=active&&mr;
 assign swrite_event=!core_reset&&active&&ar&&aw&&sr&&!mem_hold;assign swrite_addr=aa;
 store82 store(clk,core_reset,config_select?cfg:(!core_reset&&active&&!mem_hold&&ar),config_select?cfg_wr:aw,config_select?cfg_addr:aa,config_select?cfg_din:ai,sr,sv,pending?cfg_take:at,sd);
endmodule
