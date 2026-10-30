// One physical S/byte/S32/SFU/link bank, four mutually exclusive controller leases.
module block_v1_vs(input wire clk,reset,cmd,input wire [1:0] command_kind,
 input wire soft_abort,output wire abort_ready,abort_accept,
 output wire cmd_ready,cmd_accept,busy,done,input wire ack,output reg [7:0] status,output wire [7:0] debug_state,output reg [1:0] owner,
 input wire [31:0] gateup_address,records_address,gamma_address,m_owner,m_version,epsilon,coefficient,
 input wire [10:0] length,position,input wire [15:0] window,input wire [63:0] query_units,input wire signed [7:0] key_unit,value_unit,
 input wire [31:0] key_address,value_address,a_owner,a_version,score_multiplier,
 input wire [1:0] r_command,input wire [4:0] r_head,input wire signed [15:0] r_initial_unit,input wire [31:0] r_expected_position,
 input wire g_command,input wire [31:0] g_owner,input wire [63:0] g_context_id,g_expected_position,g_expected_version,input wire [4:0] g_slot,
 output wire [63:0] g_position,g_version,g_context_saved,output wire [31:0] g_numeric_epoch,g_owner_saved,output wire [15:0] g_units,g_value_units,g_candidate_units,output wire [31:0] g_candidate_epoch,output wire g_bank,g_state_validated,
 output wire [7:0] gdebug,output wire [63:0] g_cycles,output wire [31:0] g_reads,g_writes,g_sreads,g_swrites,g_wide_calls,output wire [3:0] g_retries,
 output wire g_obs_valid,output wire [2:0] g_obs_kind,output wire g_obs_head,output wire [6:0] g_obs_pair,g_obs_i,output wire signed [63:0] g_obs_lo,g_obs_hi,
 input wire accept_candidate,reject_candidate,output wire candidate_ready,
 output wire [31:0] r_position,r_numeric_epoch,output wire signed [15:0] r_unit,output wire r_bank,output wire [31:0] candidate_epoch,output wire signed [15:0] candidate_unit,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 output wire result_valid,result_candidate,output wire [9:0] result_index,output wire [127:0] result_data,input wire result_take,
 input wire mem_hold,mul_hold,input wire ext_ready,ext_valid,output wire ext_req,ext_wr,output wire [31:0] ext_addr,output wire [127:0] ext_wdata,output wire ext_take,input wire [127:0] ext_data,
 output reg [31:0] epoch,output wire [31:0] ext_epoch,input wire [31:0] response_epoch,output reg [31:0] stale_responses,aborts,leases,
 output reg [63:0] cycles,export_cycles,drain_cycles,output wire [31:0] wire_beats,transactions,mul_grants0,mul_grants1,mul_wait0,mul_wait1,mul_contested,
 output reg [31:0] sreads,swrites,fgrants,result_lines,output wire [4:0] service_accept,output wire services_drained,
 output wire swrite_event,output wire [9:0] swrite_addr,output wire [127:0] swrite_data,
 output wire [7:0] mdebug,adebug,rdebug,vdebug,ndebug,output wire [4:0] mfront_debug,
 output wire obs_mid_valid,obs_a_valid,output wire [11:0] obs_index,output wire signed [31:0] obs_mid,output wire signed [7:0] obs_a,
 output wire m_obs_valid,output wire [10:0] m_obs_row,output wire [2:0] m_obs_rank,output wire signed [31:0] m_obs_acc,m_obs_down,
 output wire a_obs_valid,output wire [1:0] a_obs_kind,output wire [2:0] a_obs_head,output wire [10:0] a_obs_key,output wire signed [31:0] a_obs_x,a_obs_y,output wire [63:0] a_obs_sum,
 output wire [31:0] cache_owner,cache_version,output wire [10:0] cache_length,output wire signed [7:0] cache_key_unit,cache_value_unit,
 output wire [127:0] deltas,observed_sum,observed_den,output wire [7:0] expert_valid,
 output wire [63:0] m_cycles,a_cycles,r_cycles,output wire [31:0] r_reads,r_writes,r_sreads,r_swrites,output wire [3:0] r_retries,
 output wire lib_s_req,lib_s_wr,output wire [9:0] lib_s_addr,
 output wire [127:0] lib_s_din,input wire lib_s_ready,lib_s_valid,
 output wire lib_s_take,input wire [127:0] lib_s_dout,
 output wire [63:0] lib_byte_a,lib_byte_b,input wire [127:0] lib_byte_p);
 localparam IDLE=0,RUN=1,EXPORT_REQ=2,EXPORT_WAIT=3,DECIDE=4,CANCEL=5,LOCAL_RESET=6,R_CANCEL=7,DONE=8;
 reg [3:0] state;reg cfg_pending,export_candidate,export_pending;reg [31:0] export_external_base;reg [9:0] export_base,export_last,export_index;
 wire [3:0] crdy,cdone;wire [7:0] cstatus[0:3];wire r_offer,r_abort_ready,r_abort_accept,g_offer,g_abort_ready,g_abort_accept;
 wire [3:0] sq,sw,st,mq0,mq1,mt0,mt1,fq,ft,eq,ew,et;
 wire [9:0] sa[0:3];wire [127:0] si[0:3],fx[0:3],fy[0:3],ei[0:3];wire [1:0] fo[0:3];wire [31:0] ea[0:3];
 wire signed [31:0] mx0[0:3],my0[0:3],mx1[0:3],my1[0:3];wire [63:0] ba[0:1],bb[0:1];wire [127:0] bp;
 wire sr,sv,mr0,mr1,mv0,mv1,fr,fv,ferr,er,ev;wire [127:0] so,fz,frem,eo;wire signed [63:0] mz0,mz1;
 wire abort_ma=abort_accept&&owner<2;wire aborted=state==CANCEL||state==LOCAL_RESET;
 wire active=state==RUN||state==DECIDE||state==EXPORT_REQ||state==EXPORT_WAIT||state==R_CANCEL;
 wire allow_ctrl=active&&!abort_ma&&!aborted;
 wire m_active=allow_ctrl&&owner==0,a_active=allow_ctrl&&owner==1,r_active=allow_ctrl&&owner==2,g_active=allow_ctrl&&owner==3;
 wire cfg_use=!reset&&state==IDLE&&!cfg_pending&&cfg&&!soft_abort;
 wire exporting=state==EXPORT_REQ||state==EXPORT_WAIT;
 wire controller_s_allowed=state==RUN||state==DECIDE||state==R_CANCEL;
 wire route_s=allow_ctrl&&controller_s_allowed;
 wire exp_req=state==EXPORT_REQ&&!abort_accept;
 wire s_request=!reset&&!mem_hold&&(cfg_use||(exp_req&&owner!=3)||(route_s&&sq[owner]));
 wire s_write=cfg_use?cfg_wr:exp_req?1'b0:sw[owner];
 wire [9:0] s_address=cfg_use?cfg_addr:exp_req?export_base+export_index:sa[owner];
 wire [127:0] s_input=cfg_use?cfg_din:si[owner];
 wire s_take=cfg_pending?(!reset&&!soft_abort&&cfg_take):aborted||state==R_CANCEL?1'b1:state==EXPORT_WAIT?(result_take&&!abort_accept):route_s?st[owner]:1'b0;
 assign cmd_ready=!reset&&!soft_abort&&state==IDLE&&!cfg_pending&&!cfg&&epoch!=32'hffffffff&&crdy[command_kind];
 assign cmd_accept=cmd&&cmd_ready;assign busy=state!=IDLE;assign done=!reset&&state==DONE;assign debug_state={4'b0,state};
 assign abort_ready=!reset&&((owner<2&&(state==RUN||exporting))||(owner>=2&&(state==RUN||exporting||state==DECIDE)&&(owner==2?r_abort_ready:g_abort_ready)));
 assign abort_accept=soft_abort&&abort_ready;
 assign cfg_ready=!reset&&!soft_abort&&state==IDLE&&!cfg_pending&&sr&&!mem_hold;assign cfg_valid=!reset&&!soft_abort&&cfg_pending&&sv;assign cfg_dout=so;
 assign result_valid=!reset&&state==EXPORT_WAIT&&(owner==3?ev:sv)&&!abort_accept;assign result_data=owner==3?eo:so;assign result_candidate=export_candidate;assign result_index=export_index;
 assign candidate_ready=!reset&&state==DECIDE&&(owner==2?r_offer:g_offer)&&!abort_accept;
 wire sel_mq0=allow_ctrl&&mq0[owner],sel_mq1=allow_ctrl&&mq1[owner];
 wire sel_fq=allow_ctrl&&fq[owner],sel_eq=(exp_req&&owner==3)||(allow_ctrl&&eq[owner]);
 wire take0=aborted?1'b1:allow_ctrl?mt0[owner]:1'b0,take1=aborted?1'b1:allow_ctrl?mt1[owner]:1'b0;
 wire takef=aborted?1'b1:allow_ctrl?ft[owner]:1'b0,takee=export_pending?(state==R_CANCEL||abort_accept||result_take):aborted?1'b1:allow_ctrl?et[owner]:1'b0;
 assign services_drained=sr&&!sv&&!mv0&&!mv1&&fr&&!fv&&er&&!ev&&!export_pending;
 assign service_accept=reset?5'b0:{sel_eq&&er,sel_fq&&fr,sel_mq1&&mr1,sel_mq0&&mr0,s_request&&sr};
 assign swrite_event=!reset&&s_request&&sr&&s_write;assign swrite_addr=s_address;assign swrite_data=s_input;
 wire raw_req,raw_wr,raw_take,wire_valid;wire [31:0] raw_addr;wire [127:0] raw_data,wire_data;
 wire drop_response=response_epoch!=epoch||state==IDLE||state==DONE;
 assign ext_req=!reset&&raw_req;assign ext_wr=raw_wr;assign ext_addr=raw_addr;assign ext_wdata=raw_data;assign ext_epoch=epoch;
 assign ext_take=!reset&&(drop_response||raw_take);
 assign lib_s_req=s_request;assign lib_s_wr=s_write;assign lib_s_addr=s_address;
 assign lib_s_din=s_input;assign lib_s_take=s_take;
 assign sr=lib_s_ready;assign sv=lib_s_valid;assign so=lib_s_dout;
 mul84 #(1) shared_s32(clk,reset,mul_hold,!reset&&sel_mq0,mx0[owner],my0[owner],mr0,mv0,take0,mz0,!reset&&sel_mq1,mx1[owner],my1[owner],mr1,mv1,take1,mz1,mul_grants0,mul_grants1,mul_wait0,mul_wait1,mul_contested);
 sfu84 #(1) shared_sfu(clk,reset,!reset&&sel_fq,fo[owner],fx[owner],fy[owner],fr,fv,takef,fz,frem,ferr);
 memory_link shared_link(clk,reset,!reset&&sel_eq,exp_req&&owner==3?1'b0:ew[owner],exp_req&&owner==3?export_external_base+({22'd0,export_index}<<4):ea[owner],ei[owner],er,ev,takee,eo,raw_req,raw_wr,raw_addr,raw_data,ext_ready&&!reset,ext_valid&&!reset&&!drop_response,raw_take,ext_data,wire_valid,wire_data,wire_beats,transactions);
 wire [63:0] byte_a=owner==0?ba[0]:owner==1?ba[1]:64'b0,byte_b=owner==0?bb[0]:owner==1?bb[1]:64'b0;
 assign lib_byte_a=byte_a;assign lib_byte_b=byte_b;assign bp=lib_byte_p;
 always @(posedge clk)begin
 if(reset)begin state<=IDLE;owner<=0;status<=0;epoch<=0;stale_responses<=0;aborts<=0;leases<=0;cfg_pending<=0;export_candidate<=0;export_pending<=0;export_external_base<=0;export_base<=0;export_last<=0;export_index<=0;cycles<=0;export_cycles<=0;drain_cycles<=0;sreads<=0;swrites<=0;fgrants<=0;result_lines<=0;end
 else begin
 if(exp_req&&owner==3&&er)export_pending<=1;else if(export_pending&&ev&&takee)export_pending<=0;
 if(cfg&&cfg_ready)cfg_pending<=1;else if(cfg_valid&&cfg_take)cfg_pending<=0;
 if(ext_valid&&ext_take&&drop_response)stale_responses<=stale_responses+1;
 if(s_request&&sr)begin if(s_write)swrites<=swrites+1;else sreads<=sreads+1;end
 if(sel_fq&&fr)fgrants<=fgrants+1;
 if(state!=IDLE&&state!=DONE)cycles<=cycles+1;
 if(exporting)export_cycles<=export_cycles+1;
 if(state==CANCEL||state==R_CANCEL)drain_cycles<=drain_cycles+1;
 if(result_valid&&result_take)result_lines<=result_lines+1;
 if(abort_accept)begin aborts<=aborts+1;state<=owner>=2?R_CANCEL:CANCEL;end
 else case(state)
 IDLE:if(cmd_accept)begin owner<=command_kind;epoch<=epoch+1;leases<=leases+1;status<=0;cycles<=0;export_cycles<=0;drain_cycles<=0;export_index<=0;export_candidate<=0;state<=RUN;end
 RUN:if(owner>=2&&(owner==2?r_offer:g_offer)&&services_drained)begin export_candidate<=1;export_base<=482;export_external_base<=32'h062a0000+({31'd0,!g_bank}<<11);export_last<=owner==2?31:127;export_index<=0;state<=EXPORT_REQ;end
 else if(cdone[owner]&&services_drained)begin status<=cstatus[owner];if(cstatus[owner]!=0||owner>=2)state<=DONE;else begin export_candidate<=0;export_base<=owner==0?0:732;export_last<=owner==0?383:255;export_index<=0;state<=EXPORT_REQ;end end
 EXPORT_REQ:if(owner==3?(sel_eq&&er):(s_request&&sr))state<=EXPORT_WAIT;
 EXPORT_WAIT:if(result_valid&&result_take)begin if(export_index==export_last)state<=export_candidate?DECIDE:DONE;else begin export_index<=export_index+1;state<=EXPORT_REQ;end end
 DECIDE:if(candidate_ready&&(accept_candidate||reject_candidate))state<=RUN;
 CANCEL:if(services_drained)state<=LOCAL_RESET;
 LOCAL_RESET:begin status<=2;state<=DONE;end
 R_CANCEL:if(cdone[owner]&&services_drained)begin status<=cstatus[owner];state<=DONE;end
 DONE:if(ack&&services_drained)state<=IDLE;
 default:begin status<=255;state<=DONE;end
 endcase end end
 m106 m(.clk(clk),.reset(reset),.soft_abort(state==LOCAL_RESET&&owner==0),.cmd(cmd_accept&&command_kind==0),.prep_only(1'b0),.mem_hold(1'b0),.mul_hold(1'b0),
 .gateup_address(gateup_address),.records_address(records_address),.gamma_address(gamma_address),.owner(m_owner),.input_version(m_version),.epsilon(epsilon),.coefficient(coefficient),
 .cmd_ready(crdy[0]),.done(cdone[0]),.ack(state==DONE&&ack&&owner==0),.status(cstatus[0]),.debug_state(mdebug),.epoch(epoch),.ext_response_epoch(epoch),.ext_req(eq[0]),.ext_addr(ea[0]),.ext_ready(m_active&&er),.ext_valid(m_active&&ev),.ext_take(et[0]),.ext_data(eo),
 .cfg(1'b0),.cfg_wr(1'b0),.cfg_addr(10'd0),.cfg_din(128'd0),.cfg_take(1'b0),.cycles(m_cycles),.deltas(deltas),.expert_valid(expert_valid),.observed_sum(observed_sum),.observed_den(observed_den),
 .obs_mid_valid(obs_mid_valid),.obs_a_valid(obs_a_valid),.obs_index(obs_index),.obs_mid(obs_mid),.obs_a(obs_a),.obs_valid(m_obs_valid),.obs_row(m_obs_row),.obs_rank(m_obs_rank),.obs_acc(m_obs_acc),.obs_down(m_obs_down),.vdebug(vdebug),.ndebug(ndebug),.mdebug(mfront_debug),
 .sq(sq[0]),.sw(sw[0]),.sa(sa[0]),.si(si[0]),.sr_in(m_active&&controller_s_allowed&&sr&&!mem_hold),.sv_in(m_active&&controller_s_allowed&&sv),.st(st[0]),.so(so),
 .mq0(mq0[0]),.mq1(mq1[0]),.mx0(mx0[0]),.my0(my0[0]),.mx1(mx1[0]),.my1(my1[0]),.mr0(m_active&&mr0),.mr1(m_active&&mr1),.mv0(m_active&&mv0),.mv1(m_active&&mv1),.mt0(mt0[0]),.mt1(mt1[0]),.mz0(mz0),.mz1(mz1),
 .byte_a(ba[0]),.byte_b(bb[0]),.byte_p(bp),.fq(fq[0]),.fo(fo[0]),.fx(fx[0]),.fy(fy[0]),.fr(m_active&&fr),.fv(m_active&&fv),.ft(ft[0]),.fz(fz),.frem_in(frem),.ferr(ferr));
 assign ew[0]=0;assign ei[0]=0;
 a106 a(.clk(clk),.reset(reset),.soft_abort(state==LOCAL_RESET&&owner==1),.cmd(cmd_accept&&command_kind==1),.mem_hold(1'b0),.mul_hold(1'b0),
 .length(length),.position(position),.window(window),.query_units(query_units),.key_unit(key_unit),.value_unit(value_unit),.key_address(key_address),.value_address(value_address),.owner(a_owner),.input_version(a_version),.score_multiplier(score_multiplier),
 .cmd_ready(crdy[1]),.done(cdone[1]),.ack(state==DONE&&ack&&owner==1),.status(cstatus[1]),.adebug(adebug),.epoch(epoch),.ext_response_epoch(epoch),.ext_req(eq[1]),.ext_addr(ea[1]),.ext_ready(a_active&&er),.ext_valid(a_active&&ev),.ext_take(et[1]),.ext_data(eo),
 .cfg(1'b0),.cfg_wr(1'b0),.cfg_addr(10'd0),.cfg_din(128'd0),.cfg_take(1'b0),.cycles(a_cycles),.cache_owner(cache_owner),.cache_version(cache_version),.cache_length(cache_length),.cache_key_unit(cache_key_unit),.cache_value_unit(cache_value_unit),
 .obs_valid(a_obs_valid),.obs_kind(a_obs_kind),.obs_head(a_obs_head),.obs_key(a_obs_key),.obs_x(a_obs_x),.obs_y(a_obs_y),.obs_sum(a_obs_sum),
 .sq(sq[1]),.sw(sw[1]),.sa(sa[1]),.si(si[1]),.sr_in(a_active&&controller_s_allowed&&sr&&!mem_hold),.sv_in(a_active&&controller_s_allowed&&sv),.st(st[1]),.so(so),
 .mq0(mq0[1]),.mq1(mq1[1]),.mx0(mx0[1]),.my0(my0[1]),.mx1(mx1[1]),.my1(my1[1]),.mr0(a_active&&mr0),.mr1(a_active&&mr1),.mv0(a_active&&mv0),.mv1(a_active&&mv1),.mt0(mt0[1]),.mt1(mt1[1]),.mz0(mz0),.mz1(mz1),
 .byte_a(ba[1]),.byte_b(bb[1]),.byte_p(bp),.fq(fq[1]),.fo(fo[1]),.fx(fx[1]),.fy(fy[1]),.fr_in(a_active&&fr),.fv(a_active&&fv),.ft(ft[1]),.fz(fz),.frem_in(frem),.ferr(ferr));
 assign ew[1]=0;assign ei[1]=0;
 r106 r(.clk(clk),.reset(reset),.cmd(cmd_accept&&command_kind==2),.command(r_command),.head(r_head),.initial_unit(r_initial_unit),.expected_position(r_expected_position),
 .cmd_ready(crdy[2]),.done(cdone[2]),.ack(state==DONE&&ack&&owner==2),.status(cstatus[2]),.abort_request(abort_accept&&owner==2),.abort_ready(r_abort_ready),.abort_accept(r_abort_accept),
 .accept_candidate(candidate_ready&&owner==2&&accept_candidate),.reject_candidate(candidate_ready&&owner==2&&reject_candidate),.offer(r_offer),.position(r_position),.numeric_epoch(r_numeric_epoch),.unit(r_unit),.bank(r_bank),.candidate_epoch(candidate_epoch),.candidate_unit(candidate_unit),
 .cfg(1'b0),.cfg_wr(1'b0),.cfg_addr(10'd0),.cfg_din(128'd0),.cfg_take(1'b0),.mem_hold(1'b0),.mul_hold(1'b0),
 .ext_req(eq[2]),.ext_wr(ew[2]),.ext_addr(ea[2]),.ext_wdata(ei[2]),.ext_ready(r_active&&er),.ext_valid(r_active&&ev),.ext_take(et[2]),.ext_rdata(eo),.generation(epoch),.response_generation(epoch),
 .peer_req(1'b0),.peer_a(32'sd0),.peer_b(32'sd0),.peer_take(1'b1),.cycles(r_cycles),.ext_reads(r_reads),.ext_writes(r_writes),.s_reads(r_sreads),.s_writes(r_swrites),.retries(r_retries),.debug_state(rdebug),
 .sq(sq[2]),.sw(sw[2]),.sa(sa[2]),.si(si[2]),.sr_in(r_active&&controller_s_allowed&&sr&&!mem_hold),.sv_in(r_active&&controller_s_allowed&&sv),.st(st[2]),.so(so),
 .mq0(mq0[2]),.mq1(mq1[2]),.mx0(mx0[2]),.my0(my0[2]),.mx1(mx1[2]),.my1(my1[2]),.mr0(r_active&&mr0),.mr1(r_active&&mr1),.mv0(r_active&&mv0),.mv1(r_active&&mv1),.mt0(mt0[2]),.mt1(mt1[2]),.mz0(mz0),.mz1(mz1));
 assign fq[2]=0;assign fo[2]=0;assign fx[2]=0;assign fy[2]=0;assign ft[2]=1;

 gdn109 g(.clk(clk),.reset(reset),.cmd(cmd_accept&&command_kind==3),.command(g_command),.owner(g_owner),.context_id(g_context_id),.expected_position(g_expected_position),.expected_version(g_expected_version),.slot(g_slot),
 .cmd_ready(crdy[3]),.done(cdone[3]),.ack(state==DONE&&ack&&owner==3),.status(cstatus[3]),.abort_request(abort_accept&&owner==3),.abort_ready(g_abort_ready),.abort_accept(g_abort_accept),
 .accept_candidate(candidate_ready&&owner==3&&accept_candidate),.reject_candidate(candidate_ready&&owner==3&&reject_candidate),.offer(g_offer),
 .position(g_position),.version(g_version),.numeric_epoch(g_numeric_epoch),.units(g_units),.value_units(g_value_units),.bank(g_bank),.state_validated(g_state_validated),.candidate_epoch(g_candidate_epoch),.candidate_units(g_candidate_units),.saved_owner(g_owner_saved),.saved_context(g_context_saved),
 .cfg(1'b0),.cfg_wr(1'b0),.cfg_addr(10'd0),.cfg_din(128'd0),.cfg_take(1'b0),.mem_hold(1'b0),.mul_hold(1'b0),
 .ext_req(eq[3]),.ext_wr(ew[3]),.ext_addr(ea[3]),.ext_wdata(ei[3]),.ext_ready(g_active&&!exporting&&!export_pending&&er),.ext_valid(g_active&&!exporting&&!export_pending&&ev),.ext_take(et[3]),.ext_rdata(eo),.generation(epoch),.response_generation(epoch),
 .peer_req(1'b0),.peer_a(32'sd0),.peer_b(32'sd0),.peer_take(1'b1),.cycles(g_cycles),.ext_reads(g_reads),.ext_writes(g_writes),.s_reads(g_sreads),.s_writes(g_swrites),.wide_calls(g_wide_calls),.retries(g_retries),.debug_state(gdebug),
 .obs_valid(g_obs_valid),.obs_kind(g_obs_kind),.obs_head(g_obs_head),.obs_pair(g_obs_pair),.obs_i(g_obs_i),.obs_lo(g_obs_lo),.obs_hi(g_obs_hi),
 .sq(sq[3]),.sw(sw[3]),.sa(sa[3]),.si(si[3]),.sr_in(g_active&&controller_s_allowed&&sr&&!mem_hold),.sv_in(g_active&&controller_s_allowed&&sv),.st(st[3]),.so(so),
 .mq0(mq0[3]),.mq1(mq1[3]),.mx0(mx0[3]),.my0(my0[3]),.mx1(mx1[3]),.my1(my1[3]),.mr0(g_active&&mr0),.mr1(g_active&&mr1),.mv0(g_active&&mv0),.mv1(g_active&&mv1),.mt0(mt0[3]),.mt1(mt1[3]),.mz0(mz0),.mz1(mz1));
 assign fq[3]=0;assign fo[3]=0;assign fx[3]=0;assign fy[3]=0;assign ft[3]=1;
endmodule
