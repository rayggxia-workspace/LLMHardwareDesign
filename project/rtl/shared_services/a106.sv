// Bounded standalone A inventory. No claim of integrated physical M/A bank.
module a106(input wire clk,reset,soft_abort,cmd,mem_hold,mul_hold,input wire [10:0] length,position,input wire [15:0] window,
 input wire [63:0] query_units,input wire signed [7:0] key_unit,value_unit,input wire [31:0] key_address,value_address,owner,input_version,score_multiplier,
 output wire cmd_ready,cmd_accept,busy,done,input wire ack,output reg [7:0] status,output wire [7:0] debug_state,adebug,
 input wire [31:0] epoch,output reg [31:0] stale_responses,aborts,output wire [31:0] ext_epoch,input wire [31:0] ext_response_epoch,
 output wire ext_req,output wire [31:0] ext_addr,input wire ext_ready,ext_valid,output wire ext_take,input wire [127:0] ext_data,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 output wire [63:0] cycles,output wire [31:0] macs,sreads,swrites,kloads,vloads,lut_reads,divides,score_products,wire_beats,transactions,mul_grants,
 output wire obs_valid,output wire [1:0] obs_kind,output wire [2:0] obs_head,output wire [10:0] obs_key,output wire signed [31:0] obs_x,obs_y,output wire [63:0] obs_sum,
 output wire [31:0] cache_owner,cache_version,output wire [10:0] cache_length,output wire signed [7:0] cache_key_unit,cache_value_unit,
 output wire mem_request,mul_request,output wire swrite_event,output wire [9:0] swrite_addr,
 output wire sq,sw,output wire [9:0] sa,output wire [127:0] si,input wire sr_in,sv_in,output wire st,input wire [127:0] so,
 output wire mq0,mq1,output wire signed [31:0] mx0,my0,mx1,my1,input wire mr0,mr1,mv0,mv1,output wire mt0,mt1,input wire signed [63:0] mz0,mz1,
 output wire [63:0] byte_a,byte_b,input wire [127:0] byte_p,
 output wire fq,output wire [1:0] fo,output wire [127:0] fx,fy,input wire fr_in,fv,output wire ft,input wire [127:0] fz,frem_in,input wire ferr);
 reg [10:0] last_length;assign cache_owner=last_owner;assign cache_version=last_version;assign cache_length=last_length;assign cache_key_unit=last_ke;assign cache_value_unit=last_ve;
 reg [2:0] state;localparam IDLE=0,START=1,ACTIVE=2,DRAIN=3,DONE=4;
 reg pending,cache_registered;reg [31:0] last_owner,last_version,last_k,last_v;reg signed [7:0] last_ke,last_ve;
 reg [10:0] len;reg [63:0] qe;reg signed [7:0] ke;reg [31:0] ka,va,multiplier;
 wire core_reset=reset||soft_abort,active=state==ACTIVE;
 wire ar,aw,at,sr,sv,er,et,lr,lv,lt,mr,mt,mready,mvalid,fr,ft_inner,fready,fvalid,ferror,ad;
 wire [9:0] aa;wire [127:0] ai,sd,ld,fa,fb,fvalue,fremainder;wire [31:0] ea;wire signed [31:0] ma,mb;wire signed [63:0] mv;wire [7:0] ast;
 assign busy=state!=IDLE;assign debug_state={5'b0,state};assign done=!core_reset&&state==DONE;
 assign cmd_ready=!core_reset&&state==IDLE&&!pending&&!cfg&&epoch!=32'hffffffff;assign cmd_accept=cmd&&cmd_ready;
 assign cfg_ready=!core_reset&&state==IDLE&&!pending&&sr;assign cfg_valid=!core_reset&&pending&&sv;assign cfg_dout=sd;
 wire config_select=!core_reset&&state==IDLE&&!pending&&cfg;
 wire drop_response=ext_response_epoch!=epoch||state==IDLE||state==DONE;
 wire raw_req,raw_take;assign ext_req=!core_reset&&raw_req;assign ext_take=!core_reset&&(drop_response||raw_take);assign ext_epoch=epoch;
 wire [31:0] bytes={21'b0,length}<<8;
 function legal(input [31:0] a,n);begin legal=a[3:0]==0&&a>=32'h05000000&&({1'b0,a}+{1'b0,n})<=33'h005200000;end endfunction
 wire alias_kv=({1'b0,key_address}<{1'b0,value_address}+{1'b0,bytes})&&({1'b0,value_address}<{1'b0,key_address}+{1'b0,bytes});
 wire context_bad=cache_registered&&(owner!=last_owner||input_version<last_version);
 wire same_cache=cache_registered&&owner==last_owner&&input_version==last_version;
 wire metadata_changed=key_address!=last_k||value_address!=last_v||key_unit!=last_ke||value_unit!=last_ve;
 wire invalid=input_version==0||length==0||length>1056||position+12'd1!={1'b0,length}||window!=0||score_multiplier!=94906266||!legal(key_address,bytes)||!legal(value_address,bytes)||alias_kv;
 wire drained=lr&&!lv&&sr&&!sv&&mready&&!mvalid&&fready&&!fvalid;
 always @(posedge clk)begin
  if(reset)begin stale_responses<=0;aborts<=0;end else begin

   if(soft_abort)aborts<=aborts+1;
   if(ext_valid&&ext_take&&drop_response)stale_responses<=stale_responses+1;
  end
  if(reset)begin cache_registered<=0;last_owner<=0;last_version<=0;last_k<=0;last_v<=0;last_ke<=0;last_ve<=0;last_length<=0;end
  if(core_reset)begin state<=IDLE;pending<=0;len<=0;qe<=0;ke<=0;ka<=0;va<=0;multiplier<=0;status<=0;end
  else begin
   if(cfg&&cfg_ready)pending<=1;else if(cfg_valid&&cfg_take)pending<=0;
   case(state)
    IDLE:if(cmd_accept)begin status<=0;len<=length;qe<=query_units;ke<=key_unit;ka<=key_address;va<=value_address;multiplier<=score_multiplier;
     if(invalid)begin status<=16;state<=DONE;end else if(context_bad||(same_cache&&(metadata_changed||length<last_length)))begin status<=17;state<=DONE;end
     else begin cache_registered<=1;last_owner<=owner;last_version<=input_version;last_k<=key_address;last_v<=value_address;last_ke<=key_unit;last_ve<=value_unit;last_length<=length;state<=START;end end
    START:state<=ACTIVE;
    ACTIVE:if(ad)begin status<=ast;state<=DRAIN;end
    DRAIN:if(drained)state<=DONE;
    DONE:if(ack)state<=IDLE;
    default:begin status<=255;state<=DONE;end
   endcase
  end
 end
 attention106 a(clk,core_reset,state==START,state==DONE&&ack,len,qe,ke,ka,va,multiplier,ad,ast,adebug,
 er,ea,active&&lr,active&&lv,et,ld,ar,aw,aa,ai,active&&sr&&!mem_hold,active&&sv,at,sd,
 mr,ma,mb,active&&mready,active&&mvalid,mt,mv,fr,fa,fb,active&&fready,active&&fvalid,ft_inner,fvalue,fremainder,ferror,
 cycles,macs,sreads,swrites,kloads,vloads,lut_reads,divides,score_products,obs_valid,obs_kind,obs_head,obs_key,obs_x,obs_y,obs_sum,byte_a,byte_b,byte_p);
 wire unused_v1,unused_r1;wire signed [63:0] unused_y1;wire [31:0] mg1,mw0,mw1,mc;
 assign mq0=active&&mr;assign mx0=ma;assign my0=mb;assign mt0=mt;assign mq1=0;assign mx1=0;assign my1=0;assign mt1=1;
 assign mready=mr0;assign mvalid=mv0;assign mv=mz0;assign mul_grants=0;
 assign fq=active&&fr;assign fo=1;assign fx=fa;assign fy=fb;assign ft=ft_inner;
 assign fready=fr_in;assign fvalid=fv;assign fvalue=fz;assign fremainder=frem_in;assign ferror=ferr;
 assign raw_req=active&&er;assign ext_addr=ea;assign lr=ext_ready&&!core_reset;assign lv=ext_valid&&!core_reset&&!drop_response;assign raw_take=et;assign ld=ext_data;assign wire_beats=0;assign transactions=0;

 assign mem_request=active&&ar;assign mul_request=active&&mr;
 assign swrite_event=!core_reset&&active&&ar&&aw&&sr&&!mem_hold;assign swrite_addr=aa;
 assign sq=config_select?cfg:(!core_reset&&active&&!mem_hold&&ar);assign sw=config_select?cfg_wr:aw;assign sa=config_select?cfg_addr:aa;assign si=config_select?cfg_din:ai;
 assign sr=sr_in;assign sv=sv_in;assign sd=so;assign st=pending?cfg_take:at;

endmodule
