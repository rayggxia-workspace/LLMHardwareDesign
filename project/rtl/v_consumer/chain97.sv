// One physical shared S/MUL/link; Vprep -> resident M -> streamed93 norm.
module chain97(input wire clk,reset,soft_abort,cmd,prep_only,mem_hold,mul_hold,input wire [31:0] gateup_address,records_address,gamma_address,owner,input_version,epsilon,coefficient,
 output wire cmd_ready,cmd_accept,busy,done,input wire ack,output reg [7:0] status,output wire [7:0] debug_state,
 output reg [31:0] epoch,stale_responses,aborts,output wire [31:0] ext_epoch,input wire [31:0] ext_response_epoch,
 output wire ext_req,output wire [31:0] ext_addr,input wire ext_ready,ext_valid,output wire ext_take,input wire [127:0] ext_data,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 output reg a_valid,output reg [31:0] a_owner,a_version,a_epoch,output wire [127:0] deltas,output wire [7:0] expert_valid,
 output reg [63:0] cycles,output wire [63:0] v_cycles,norm_cycles,output wire [31:0] gate_reads,up_reads,lut_reads,v_sreads,v_swrites,gamma_loads,gamma_stores,den_events,reads,writes,
 output wire [127:0] observed_sum,observed_den,output wire [31:0] packets,macs,mwrites,cache_reads,cache_writes,wire_beats,transactions,
 output wire [31:0] mul_grants0,mul_grants1,mul_wait0,mul_wait1,mul_contested,
 output wire obs_mid_valid,obs_a_valid,output wire [11:0] obs_index,output wire signed [31:0] obs_mid,output wire signed [7:0] obs_a,
 output wire obs_valid,output wire [10:0] obs_row,output wire [2:0] obs_rank,output wire signed [31:0] obs_acc,obs_down,
 output wire mem_request,mul_request,output wire swrite_event,output wire [9:0] swrite_addr,output wire [127:0] swrite_data,output wire [7:0] vdebug,ndebug,output wire [4:0] mdebug);
 localparam IDLE=0,VSTART=1,VACTIVE=2,VDRAIN=3,MSTART=4,MACTIVE=5,MDRAIN=6,NSTART=7,NACTIVE=8,DONE=9;
 reg [3:0] state;reg pending,only_prep;reg [31:0] saved_gu,saved_records,saved_gamma,saved_owner,saved_version,saved_eps,saved_coef;
 wire core_reset=reset||soft_abort;wire va=state==VACTIVE,ma=state==MACTIVE,na=state==NACTIVE;
 wire vb,vd,md,nb,nd;wire [7:0] vs,ms,ns;wire vr,vw,vt,mr,mw,mt,nr,nw,nt;wire [9:0] vad,mad,nad;wire [127:0] vdin,mdin,ndin;
 wire ve,vet,me,met,ne,net;wire [31:0] vea,mea,nea;wire lr,lv,lt;wire [127:0] ld;
 wire sr,sv;wire [127:0] sd;wire cfg_select=!core_reset&&!busy&&!pending&&cfg;
 wire vmr,vmt,mmr,nmr,ready0,ready1,val0,val1;wire signed [31:0] vma,vmb,mma,mmb,nma,nmb;wire signed [63:0] y0,y1;
 wire qualified_a=a_valid&&expert_valid==8'hff&&a_owner==saved_owner&&a_version==saved_version&&a_epoch==epoch;
 assign debug_state={4'b0,state};assign busy=state!=IDLE;assign done=!core_reset&&state==DONE;
 assign cmd_ready=!core_reset&&state==IDLE&&!pending&&!cfg&&epoch!=32'hffffffff;assign cmd_accept=cmd&&cmd_ready;
 assign cfg_ready=!core_reset&&!busy&&!pending&&sr;assign cfg_valid=!core_reset&&pending&&sv;assign cfg_dout=sd;
 assign ext_epoch=epoch;wire response_match=ext_response_epoch==epoch;wire drop_response=!response_match||((epoch==32'hffffffff)&&(soft_abort||state==IDLE));wire link_take;assign ext_take=drop_response?1'b1:link_take;
 function legal(input [31:0] a,input [31:0] n);begin legal=a[3:0]==0&&a>=32'h04000000&&({1'b0,a}+{1'b0,n})<=33'h008000000;end endfunction
 function overlap(input [31:0] a,n,b,m);begin overlap=({1'b0,a}<{1'b0,b}+{1'b0,m})&&({1'b0,b}<{1'b0,a}+{1'b0,n});end endfunction
 wire addr_ok=legal(gateup_address,32768)&&legal(records_address,6488064)&&legal(gamma_address,6144)&&!overlap(gateup_address,32768,records_address,6488064)&&!overlap(gateup_address,32768,gamma_address,6144)&&!overlap(records_address,6488064,gamma_address,6144);
 wire drained=lr&&!lv&&sr&&!sv&&!val0&&!val1;
 always @(posedge clk)begin
 if(reset)begin epoch<=0;stale_responses<=0;aborts<=0;end else begin if((soft_abort||cmd_accept)&&epoch!=32'hffffffff)epoch<=epoch+1;if(soft_abort)aborts<=aborts+1;if(ext_valid&&ext_take&&drop_response)stale_responses<=stale_responses+1;end
 if(core_reset)begin state<=IDLE;pending<=0;only_prep<=0;saved_gu<=0;saved_records<=0;saved_gamma<=0;saved_owner<=0;saved_version<=0;saved_eps<=0;saved_coef<=0;status<=0;cycles<=0;a_valid<=0;a_owner<=0;a_version<=0;a_epoch<=0;end
 else begin
 if(cfg&&cfg_ready)pending<=1;else if(cfg_valid&&cfg_take)pending<=0;
 if(state!=IDLE&&state!=DONE)cycles<=cycles+1;
 case(state)
 IDLE:if(cmd_accept)begin status<=0;cycles<=0;a_valid<=0;only_prep<=prep_only;saved_gu<=gateup_address;saved_records<=records_address;saved_gamma<=gamma_address;saved_owner<=owner;saved_version<=input_version;saved_eps<=epsilon;saved_coef<=coefficient;
  if(!addr_ok||epsilon!=17||coefficient!=230687)begin status<=16;state<=DONE;end else state<=VSTART;end
 VSTART:state<=VACTIVE;
 VACTIVE:if(vd)begin if(vs!=0)begin status<=vs;state<=DONE;end else begin a_valid<=expert_valid==8'hff;a_owner<=saved_owner;a_version<=saved_version;a_epoch<=epoch;state<=VDRAIN;end end
 VDRAIN:if(drained)state<=only_prep?DONE:MSTART;
 MSTART:if(!qualified_a)begin status<=17;state<=DONE;end else state<=MACTIVE;
 MACTIVE:if(md)begin if(ms!=0)begin status<=ms;state<=DONE;end else state<=MDRAIN;end
 MDRAIN:if(drained)state<=NSTART;
 NSTART:state<=NACTIVE;
 NACTIVE:if(nd)begin status<=ns;state<=DONE;end
 DONE:if(ack)state<=IDLE;
 default:begin status<=255;state<=DONE;end
 endcase end end
 vprep97 v(clk,core_reset,state==VSTART,state==VDRAIN||(state==DONE&&ack),saved_gu,vb,vd,vs,vdebug,
 ve,vea,va&&lr,va&&lv,vet,ld,vr,vw,vad,vdin,va&&sr&&!pending&&!mem_hold,va&&sv&&!pending,vt,sd,
 vmr,vma,vmb,va&&ready1,va&&val1,vmt,y1,deltas,expert_valid,v_cycles,gate_reads,up_reads,lut_reads,v_sreads,v_swrites,obs_mid_valid,obs_a_valid,obs_index,obs_mid,obs_a);
 mfront97 m(clk,core_reset,state==MSTART&&qualified_a,state==MDRAIN||(state==DONE&&ack),saved_records,deltas,saved_coef,md,ms,
 me,mea,ma&&lr,ma&&lv,met,ld,mr,mw,mad,mdin,ma&&sr&&!pending&&!mem_hold,ma&&sv&&!pending,mt,sd,packets,macs,mwrites,obs_valid,obs_row,obs_rank,obs_acc,obs_down,
 mmr,mma,mmb,ma&&ready0,ma&&val0,y0,cache_reads,cache_writes,mdebug);
 norm93 #(1) n(clk,core_reset,state==NSTART,12'd1536,saved_eps,1'b1,saved_gamma,ne,nea,na&&lr,na&&lv,net,ld,gamma_loads,gamma_stores,den_events,observed_sum,observed_den,
 nb,nd,state==DONE&&ack,ns,nr,nw,nad,ndin,na&&sr&&!pending&&!mem_hold,na&&sv&&!pending,nt,sd,norm_cycles,reads,writes,ndebug,nmr,nma,nmb,na&&ready1,na&&val1,y1);
 mul84 #(1) multipliers(clk,core_reset,mul_hold,ma&&mmr,mma,mmb,ready0,val0,1'b1,y0,(va&&vmr)||(na&&nmr),va?vma:nma,va?vmb:nmb,ready1,val1,va?vmt:1'b1,y1,mul_grants0,mul_grants1,mul_wait0,mul_wait1,mul_contested);
 wire unused_wr,wire_valid;wire [127:0] unused_data,wire_data;
 assign lt=va?vet:ma?met:na?net:1'b0;
 memory_link link(clk,core_reset,(va&&ve)||(ma&&me)||(na&&ne),1'b0,va?vea:ma?mea:nea,128'b0,lr,lv,lt,ld,ext_req,unused_wr,ext_addr,unused_data,ext_ready,ext_valid&&!drop_response,link_take,ext_data,wire_valid,wire_data,wire_beats,transactions);
 wire service_req=(va&&vr)||(ma&&mr)||(na&&nr);wire service_wr=va?vw:ma?mw:nw;wire [9:0] service_addr=va?vad:ma?mad:nad;wire [127:0] service_data=va?vdin:ma?mdin:ndin;
 assign mem_request=service_req;assign mul_request=(va&&vmr)||(ma&&mmr)||(na&&nmr);
 assign swrite_event=!core_reset&&!pending&&!mem_hold&&service_req&&service_wr&&sr;assign swrite_addr=service_addr;assign swrite_data=service_data;
 store82 frame(clk,core_reset,cfg_select?cfg:(!pending&&!mem_hold&&service_req),cfg_select?cfg_wr:service_wr,cfg_select?cfg_addr:service_addr,cfg_select?cfg_din:service_data,sr,sv,pending?cfg_take:va?vt:ma?mt:na?nt:1'b0,sd);
endmodule
