`timescale 1ns/1ps
// Actual ordinary S banks. The 10ns functional clock accommodates their
// behavioural delay; this is not 300MHz timing qualification.
module test_g_quant_copy_a_joint;
 reg clk;initial clk=0;always #5 clk=!clk;
 reg reset=1,cmd_valid=0,done_ready=0;
 wire cmd_ready,done_valid,done_error,done_cancelled;
 reg [127:0] cmd_key=0;
 reg [15:0] cmd_generation=0,cmd_kk=0;
 reg cmd_shift_known=0;
 reg [5:0] cmd_shift=0;
 wire s_valid,s_ready,s_write,rsp_valid,rsp_ready;
 wire [9:0] s_address;
 wire [127:0] s_data,rsp_data,done_key;
 wire [31:0] s_tag,rsp_tag,rejected_responses;
 wire [15:0] done_kk,done_written_mask;
 wire [4:0] done_words;
 wire [5:0] done_shift;
 s32_a16_tile_quantizer quantizer(.clk,.reset,.cmd_valid,.cmd_ready,
  .cmd_key,.cmd_generation,.cmd_kk,.cmd_source(10'd32),.cmd_destination(10'd256),
  .cmd_shift_known,.cmd_shift,.cancel_valid(1'b0),.cancel_key(128'd0),
  .s_valid,.s_ready,.s_write,.s_address,.s_data,.s_tag,.rsp_valid,.rsp_ready,
  .rsp_data,.rsp_tag,.rsp_error(1'b0),.done_valid,.done_ready,.done_key,.done_kk,
  .done_error,.done_cancelled,.done_words,.done_written_mask,.done_shift,.rejected_responses);

 reg g_cmd=0,g_take=0;
 reg [9:0] g_gate_base=512,g_up_base=576,g_mid_base=32;
 wire g_cmd_ready,g_done_valid,g_done_error;
 wire [5:0] g_done_words,g_done_shift;
 wire [127:0] g_done_key;
 wire [15:0] g_done_kk;
 wire gs_valid,gs_write,gs_ready,gs_rsp_valid,gs_rsp_ready;
 wire [9:0] gs_address;
 wire [127:0] gs_data;
 wire g_in_valid,g_in_ready,g_in_gated,g_out_valid,g_out_ready,g_out_error;
 wire [63:0] g_in_gate,g_in_up,g_out_data;
 wire [1:0] g_in_mask,g_out_mask;
 g_s128_observed_scale gfront(.clk,.reset,.cmd_key,.cmd_kk,.done_key(g_done_key),.done_kk(g_done_kk),
  .done_a_shift(g_done_shift),.cmd_valid(g_cmd),.cmd_ready(g_cmd_ready),.cmd_gate_base(g_gate_base),
  .cmd_up_base(g_up_base),.cmd_mid_base(g_mid_base),.cmd_words(6'd16),.cmd_gated(1'b1),
  .done_valid(g_done_valid),.done_take(g_take),.done_error(g_done_error),.done_words(g_done_words),
  .s_req_valid(gs_valid),.s_req_write(gs_write),.s_req_addr(gs_address),.s_req_data(gs_data),.s_req_ready(gs_ready),
  .s_rsp_valid(gs_rsp_valid),.s_rsp_ready(gs_rsp_ready),.s_rsp_data(rd[0]),
  .g_in_valid,.g_in_ready,.g_in_gate,.g_in_up,.g_in_gated,.g_in_mask,.g_out_valid,.g_out_ready,.g_out_data,.g_out_mask,.g_out_error);
 g_s32 kernel(.clk,.reset,.in_valid(g_in_valid),.in_ready(g_in_ready),.in_gate(g_in_gate),.in_up(g_in_up),
  .in_gated(g_in_gated),.in_mask(g_in_mask),.out_valid(g_out_valid),.out_ready(g_out_ready),.out_data(g_out_data),
  .out_mask(g_out_mask),.out_error(g_out_error));

 reg header_start=0,header_take=0;
 reg [2:0] lease_valid=0,lease_release=0;
 wire [2:0] lease_ready,lease_error,rx_quiescent,lease_release_ready;
 wire [2:0] h_valid,h_ready,h_ack_valid,h_ack_ready,h_ack_error;
 wire [95:0] h_tag,h_ack_tag;
 wire [383:0] h_data;
 wire header_ready,header_done,header_error,header_quiescent;
 wire [31:0] rejected_ack;
 reg [31:0] session=0,ticket=0;
 copy_scale_header_tx header_tx(.clk,.reset,.halt(1'b0),.start_valid(header_start),.start_ready(header_ready),
  .start_key(done_key),.start_generation(cmd_generation),.start_kk(done_kk),
  .start_written_mask(done_written_mask),.start_session(session),.start_ticket(ticket),
  .start_shift(done_shift),.start_mask(3'b111),.start_producer_error(done_error||done_cancelled),
  .frame_valid(h_valid),.frame_ready(h_ready),.frame_tag(h_tag),.frame_data(h_data),
  .ack_valid(h_ack_valid),.ack_ready(h_ack_ready),.ack_tag(h_ack_tag),.ack_error(h_ack_error),
  .done_valid(header_done),.done_ready(header_take),.done_error(header_error),
  .quiescent(header_quiescent),.rejected_ack);

 reg copy_start=0,copy_take=0;
 wire copy_ready,copy_done,copy_error,copy_quiescent;
 wire [31:0] copy_faults,committed_words;
 wire [127:0] copy_key;
 wire [32:0] copy_prefix;
 wire u_valid,u_ready,u_rsp_valid,u_rsp_ready;
 wire [9:0] u_address;
 wire [31:0] u_tag,u_rsp_tag;
 wire [127:0] u_rsp_data;
 wire [2:0] d_valid,d_ready,d_ack_valid,d_ack_ready;
 wire [29:0] d_address;
 wire [95:0] d_tag,d_ack_tag;
 wire [383:0] d_data;
 early_copy_3p copier(.clk,.reset,.halt(1'b0),.start_valid(copy_start),.start_ready(copy_ready),
  .start_key(cmd_key),.start_generation(cmd_generation),.start_U_base(10'd256),
  .start_P_bases({10'd100,10'd100,10'd100}),.start_words(11'd16),.start_P_mask(3'b111),
  .destination_window_released(&data_enabled),.u_valid,.u_ready,.u_address,.u_tag,
  .u_response_valid(u_rsp_valid),.u_response_ready(u_rsp_ready),.u_response_tag(u_rsp_tag),
  .u_response_data(u_rsp_data),.u_response_error(1'b0),.p_valid(d_valid),.p_ready(d_ready),
  .p_address(d_address),.p_tag(d_tag),.p_data(d_data),.p_ack_valid(d_ack_valid),
  .p_ack_ready(d_ack_ready),.p_ack_tag(d_ack_tag),.p_ack_error(3'd0),.copy_key,
  .copy_committed_prefix(copy_prefix),.done_valid(copy_done),.done_ready(copy_take),
  .done_error(copy_error),.quiescent(copy_quiescent),.fault_cycles(copy_faults),.committed_words);

 // The headers and payload share these very same 128 wires and tag wires.
 // Header tags are demultiplexed before the ordinary SRAM write interface.
 wire [2:0] link_valid,link_ready,link_header;
 wire [95:0] link_tag;
 wire [383:0] link_data;
 wire [2:0] meta_valid,meta_ready,data_enabled;
 wire [383:0] meta_key;
 wire [47:0] meta_generation,meta_kk;
 wire [95:0] meta_session,meta_ticket;
 wire [17:0] meta_shift;
 wire [95:0] rx_rejected;

 reg [2:0] a_cmd=0,a_load_take=0,a_w=0,a_use=0,a_take=0,a_close=0,a_release=0;
 reg a_slot=0;
 reg [15:0] use_sequence=1;
 wire [2:0] a_cmd_ready,a_load_valid,a_load_error,a_load_slot,a_w_ready,a_use_ready,
  a_valid,a_close_ready,a_release_ready,a_quiescent,a_reads_drained,a_active_slot;
 wire [383:0] a_load_key,a_key;
 wire [47:0] a_load_generation,a_generation,a_kk,a_use_sequence;
 wire [767:0] a_data;
 wire [8:0] a_step;
 wire [95:0] a_record,a_faults;
 wire [17:0] a_shift;
 wire [1:0] a_live[3];
 wire [2:0] a_s_valid,a_s_ready,a_rsp_valid,a_rsp_ready;
 wire [29:0] a_s_address;
 wire [95:0] a_s_tag;

 reg host_valid=0,host_write=0,host_take=0;
 reg [9:0] host_address=0;
 reg [127:0] host_data=0;
 wire host_ready,host_response;
 wire [2:0] cv[4],cw[4],cr[4],rv[4],rr[4];
 wire [29:0] ca[4];wire [383:0] cd[4];wire [95:0] ct[4],rt[4];
 wire [127:0] rd[4];wire [1:0] occupied[4];
 wire [3:0] nv,nw,nready,nrv,nrr;
 wire [9:0] na[4];wire [127:0] nd[4],nrd[4];
 integer cycle,mode=0,seed=1;
 wire gate_response=mode==0||cycle%7>=3;
 assign cv[0]={s_valid,u_valid,host_valid||gs_valid};assign cw[0]={s_write,1'b0,host_valid?host_write:gs_write};
 assign ca[0]={s_address,u_address,host_valid?host_address:gs_address};assign cd[0]={s_data,128'd0,host_valid?host_data:gs_data};
 assign ct[0]={s_tag,u_tag,host_valid?32'h80000000:32'h40000000};
 assign rr[0]={rsp_ready,u_rsp_ready,rt[0][31:0]==32'h40000000 ? gs_rsp_ready : host_take}&{3{gate_response}};
 assign {s_ready,u_ready}=cr[0][2:1];assign host_ready=cr[0][0]&&!gs_valid;assign gs_ready=cr[0][0]&&!host_valid;
 assign {rsp_valid,u_rsp_valid}=rv[0][2:1]&{2{gate_response}};assign host_response=rv[0][0]&&gate_response&&rt[0][31:0]==32'h80000000;assign gs_rsp_valid=rv[0][0]&&gate_response&&rt[0][31:0]==32'h40000000;
 assign rsp_data=rd[0];assign u_rsp_data=rd[0];assign rsp_tag=rt[0][95:64];assign u_rsp_tag=rt[0][63:32];
 for(genvar p=0;p<3;p=p+1)begin: receivers
  wire allow_link=mode==0||(cycle+p)%5!=2;
  wire h_rx_ready;
  assign link_valid[p]=h_valid[p]||d_valid[p];
  assign link_tag[p*32+:32]=h_valid[p]?h_tag[p*32+:32]:d_tag[p*32+:32];
  assign link_data[p*128+:128]=h_valid[p]?h_data[p*128+:128]:d_data[p*128+:128];
  assign link_header[p]=link_tag[p*32+15];
  assign link_ready[p]=allow_link&&(link_header[p]?h_rx_ready:cr[p+1][0]&&data_enabled[p]);
  assign h_ready[p]=link_ready[p]&&link_header[p];assign d_ready[p]=link_ready[p]&&!link_header[p];
  assign meta_ready[p]=a_cmd[p]&&a_cmd_ready[p];
  copy_scale_header_rx rx(.clk,.reset,.lease_valid(lease_valid[p]),.lease_ready(lease_ready[p]),
   .lease_key(cmd_key),.lease_generation(cmd_generation),.lease_kk(cmd_kk),.lease_session(session),.lease_ticket(ticket),
   .lease_error(lease_error[p]),.frame_valid(link_valid[p]&&link_header[p]&&allow_link),.frame_ready(h_rx_ready),
   .frame_tag(link_tag[p*32+:32]),.frame_data(link_data[p*128+:128]),
   .ack_valid(h_ack_valid[p]),.ack_ready(h_ack_ready[p]),.ack_tag(h_ack_tag[p*32+:32]),.ack_error(h_ack_error[p]),
   .metadata_valid(meta_valid[p]),.metadata_ready(meta_ready[p]),.metadata_key(meta_key[p*128+:128]),
   .metadata_generation(meta_generation[p*16+:16]),.metadata_kk(meta_kk[p*16+:16]),
   .metadata_session(meta_session[p*32+:32]),.metadata_ticket(meta_ticket[p*32+:32]),.metadata_shift(meta_shift[p*6+:6]),
   .data_enabled(data_enabled[p]),.release_valid(lease_release[p]),.release_ready(lease_release_ready[p]),
   .release_key(cmd_key),.release_generation(cmd_generation),.release_cancel(1'b0),
   .data_drained(copy_quiescent&&occupied[p+1]==0),.consumer_drained(a_quiescent[p]&&a_reads_drained[p]),
   .quiescent(rx_quiescent[p]),.rejected_frames(rx_rejected[p*32+:32]));
  private_a_scaled_frontend front(.clk,.reset,.halt(1'b0),.flush(1'b0),
   .scale_valid(meta_valid[p]),.scale_key(meta_key[p*128+:128]),
   .scale_kk(meta_kk[p*16+:16]>>7),.scale_shift(meta_shift[p*6+:6]),
   .cmd_valid(a_cmd[p]),.cmd_ready(a_cmd_ready[p]),.cmd_slot(a_slot),.cmd_generation,
   .cmd_kk(cmd_kk>>7),.cmd_planned_uses(16'd2),.cmd_key,.cmd_S_base(10'd100),.cmd_copy_offset(10'd0),
   .copy_key,.copy_committed_prefix(copy_prefix[p*11+:11]),
   .load_done_valid(a_load_valid[p]),.load_done_ready(a_load_take[p]),.load_done_slot(a_load_slot[p]),
   .load_done_error(a_load_error[p]),.load_done_generation(a_load_generation[p*16+:16]),.load_done_key(a_load_key[p*128+:128]),
   .s_valid(a_s_valid[p]),.s_ready(a_s_ready[p]),.s_address(a_s_address[p*10+:10]),.s_tag(a_s_tag[p*32+:32]),
   .response_valid(a_rsp_valid[p]),.response_ready(a_rsp_ready[p]),.response_tag(rt[p+1][63:32]),.response_data(rd[p+1]),
   .w_valid(a_w[p]),.w_ready(a_w_ready[p]),.w_slot(a_slot),.w_generation(cmd_generation),.w_kk(cmd_kk>>7),
   .w_use_sequence(use_sequence),.w_key(cmd_key),.w_record(32'd1984),
   .use_valid(a_use[p]),.use_ready(a_use_ready[p]),.use_slot(a_slot),.use_generation(cmd_generation),
   .use_kk(cmd_kk>>7),.use_sequence,.use_key(cmd_key),.a_valid(a_valid[p]),.a_ready(a_take[p]),
   .a_data(a_data[p*256+:256]),.a_step(a_step[p*3+:3]),.a_weight_record(a_record[p*32+:32]),
   .a_key(a_key[p*128+:128]),.a_slot(a_active_slot[p]),.a_generation(a_generation[p*16+:16]),
   .a_kk(a_kk[p*16+:16]),.a_use_sequence(a_use_sequence[p*16+:16]),.a_shift(a_shift[p*6+:6]),
   .close_valid(a_close[p]),.close_ready(a_close_ready[p]),.close_slot(a_slot),.close_generation(cmd_generation),
   .release_valid(a_release[p]),.release_ready(a_release_ready[p]),.release_slot(a_slot),.release_generation(cmd_generation),
   .quiescent(a_quiescent[p]),.source_reads_drained(a_reads_drained[p]),.live_slots(a_live[p]),.fault_cycles(a_faults[p*32+:32]));
  assign cv[p+1]={1'b0,a_s_valid[p],link_valid[p]&&!link_header[p]&&allow_link&&data_enabled[p]};
  assign cw[p+1]=3'b001;assign ca[p+1]={10'd0,a_s_address[p*10+:10],d_address[p*10+:10]};
  assign cd[p+1]={256'd0,link_data[p*128+:128]};assign ct[p+1]={32'd0,a_s_tag[p*32+:32],link_tag[p*32+:32]};
  assign rr[p+1]={1'b1,a_rsp_ready[p],d_ack_ready[p]}&{3{gate_response}};
  assign a_s_ready[p]=cr[p+1][1];assign a_rsp_valid[p]=rv[p+1][1]&&gate_response;
  assign d_ack_valid[p]=rv[p+1][0]&&gate_response;assign d_ack_tag[p*32+:32]=rt[p+1][31:0];
 end
 for(genvar m=0;m<4;m=m+1)begin: memories
  native_s128_mux3 mux(.clk,.reset,.c_valid(cv[m]),.c_write(cw[m]),.c_address(ca[m]),.c_data(cd[m]),.c_tag(ct[m]),
   .c_ready(cr[m]),.c_response_valid(rv[m]),.c_response_ready(rr[m]),.c_response_data(rd[m]),.c_response_tag(rt[m]),
   .req_valid(nv[m]),.req_write(nw[m]),.req_address(na[m]),.req_data(nd[m]),.req_ready(nready[m]),
   .rsp_valid(nrv[m]),.rsp_ready(nrr[m]),.rsp_data(nrd[m]),.owners_occupied(occupied[m]));
  local_s_base storage(.clk,.reset,.req_valid(nv[m]),.req_write(nw[m]),.req_addr(na[m]),.req_data(nd[m]),
   .req_ready(nready[m]),.rsp_valid(nrv[m]),.rsp_ready(nrr[m]),.rsp_data(nrd[m]));
 end
 integer a_reads[3],p_writes[3],headers[3],source_reads;
 integer g_started,g_requests,g_writes,g_responses,g_inputs,g_outputs;
 reg g_measuring=0;
 reg measuring=0;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(cycle>150000)$fatal(1,"COPY/S/A watchdog");
  if(!reset&&g_measuring)begin
   if(gs_valid&&gs_ready)begin g_requests=g_requests+1;if(gs_write)g_writes=g_writes+1;end
   if(gs_rsp_valid&&gs_rsp_ready)g_responses=g_responses+1;
   if(g_in_valid&&g_in_ready)g_inputs=g_inputs+1;
   if(g_out_valid&&g_out_ready)g_outputs=g_outputs+1;
  end
  if(!reset&&measuring)begin
   if(gs_valid&&host_valid)$fatal(1,"host/G ownership overlap");
   if(u_valid&&u_ready)source_reads=source_reads+1;
   for(integer p=0;p<3;p=p+1)begin
    if(h_valid[p]&&d_valid[p])$fatal(1,"two owners for shared data wires");
    if(link_valid[p]&&link_ready[p]&&link_header[p])headers[p]=headers[p]+1;
    if(d_ack_valid[p]&&d_ack_ready[p])p_writes[p]=p_writes[p]+1;
    if(a_s_valid[p]&&a_s_ready[p])begin
     a_reads[p]=a_reads[p]+1;
     if({1'b0,a_s_address[p*10+:10]}-11'd100>=copy_prefix[p*11+:11])$fatal(1,"A read preceding real write ACK");
    end
    if(meta_ready[p]&&(!meta_valid[p]||meta_key[p*128+:128]!=cmd_key||meta_kk[p*16+:16]!=cmd_kk||
       meta_generation[p*16+:16]!=cmd_generation||meta_session[p*32+:32]!=session||meta_ticket[p*32+:32]!=ticket))
     $fatal(1,"A admission without full metadata owner");
    if(occupied[p+1]>2)$fatal(1,"ordinary S owner overflow");
   end
  end
 end
 task automatic host_put(input integer address,input reg[127:0] data);
  if(address<0||address>=1024)$fatal(1,"host address outside actual S");
  @(negedge clk);host_valid=1;host_write=1;host_address=10'(address);host_data=data;
  do @(posedge clk);while(!host_ready);
  @(negedge clk);host_valid=0;
  while(!host_response)@(negedge clk);
  if(rt[0][31:0]!=32'h80000000||rd[0]!==0)$fatal(1,"host write ACK");
  host_take=1;@(negedge clk);host_take=0;
 endtask
 function automatic signed[63:0] rne(input signed[31:0] value,input integer amount);
  reg signed[63:0] divisor,q,r;
  divisor=64'sd1<<amount;q=64'(value)/divisor;r=64'(value)%divisor;
  if(r<0)begin q=q-1;r=r+divisor;end
  return q+64'(2*r>divisor||(2*r==divisor&&q[0]));
 endfunction
 reg signed[31:0] values[128];reg signed[63:0] expected;
 reg [63:0] gates[768],ups[768],golden[768],file_gate,file_up,file_result;
 reg [1:0] file_mask;
 integer fd,scan,count,file_gated,file_error,shift_part;
 string vector_file;
 integer amount,read_snapshot,begin_cycle,independent_shift;
 reg [63:0] independent_max,magnitude;
 initial begin
  cycle=0;
  if(!$value$plusargs("mode=%d",mode))mode=0;
  if(!$value$plusargs("seed=%d",seed))seed=1;
  seed=$urandom(seed);
  if(!$value$plusargs("vectors=%s",vector_file))$fatal(1,"missing G oracle vectors");
  fd=$fopen(vector_file,"r");if(fd==0)$fatal(1,"G oracle open");scan=$fscanf(fd,"%d\n",count);
  if(scan!=1||count!=8048)$fatal(1,"G oracle count");
  for(integer i=0;i<count;i=i+1)begin
   scan=$fscanf(fd,"%h %h %d %h %h %d\n",file_gate,file_up,file_gated,file_mask,file_result,file_error);
   if(scan!=6)$fatal(1,"G oracle row");
   if(i>=count-2048&&i<count-2048+768)begin
    if(file_gated!=1||file_mask!=3||file_error!=0)$fatal(1,"G historical model scope");
    gates[i-(count-2048)]=file_gate;ups[i-(count-2048)]=file_up;golden[i-(count-2048)]=file_result;
   end
  end
  $fclose(fd);
  repeat(4)@(negedge clk);reset=0;
  for(integer t=0;t<12;t=t+1)begin
   for(integer i=0;i<32;i=i+1)begin
    host_put(512+i,{gates[t*64+2*i+1],gates[t*64+2*i]});
    host_put(576+i,{ups[t*64+2*i+1],ups[t*64+2*i]});
    values[4*i]=golden[t*64+2*i][31:0];values[4*i+1]=golden[t*64+2*i][63:32];
    values[4*i+2]=golden[t*64+2*i+1][31:0];values[4*i+3]=golden[t*64+2*i+1][63:32];
   end
   @(negedge clk);cmd_key={32'h250,32'd4,32'(t),32'd1};cmd_generation=16'(t+1);cmd_kk=16'(t*128);
   amount=0;
   g_started=cycle;g_requests=0;g_writes=0;g_responses=0;g_inputs=0;g_outputs=0;g_measuring=1;
   for(integer half_index=0;half_index<2;half_index=half_index+1)begin
    g_gate_base=10'(512+16*half_index);g_up_base=10'(576+16*half_index);g_mid_base=10'(32+16*half_index);g_cmd=1;
    do @(posedge clk);while(!g_cmd_ready);@(negedge clk);g_cmd=0;
    while(!g_done_valid)@(negedge clk);
    if(g_done_error||g_done_words!=16||g_done_key!=cmd_key||g_done_kk!=cmd_kk)$fatal(1,"G partial tile real S commit");
    shift_part=int'(g_done_shift);if(shift_part>amount)amount=shift_part;
    g_take=1;@(negedge clk);g_take=0;
   end
   g_measuring=0;
   if(g_requests!=96||g_writes!=32||g_responses!=96||g_inputs!=64||g_outputs!=64)$fatal(1,"two G64 true S transaction conservation");
   independent_max=0;
   for(integer i=0;i<128;i=i+1)begin
    magnitude=64'($signed(values[i]));if(values[i][31])magnitude=0-magnitude;
    if(magnitude>independent_max)independent_max=magnitude;
   end
   independent_shift=0;while(independent_max>(64'd32767<<independent_shift))independent_shift=independent_shift+1;
   if(amount!=independent_shift)$fatal(1,"two observed half-shifts differ from whole K128 oracle");
   cmd_shift_known=1;cmd_shift=6'(amount);a_slot=1'(t%2);session=32'h249;ticket=32'(t+80);
   for(integer p=0;p<3;p=p+1)begin a_reads[p]=0;p_writes[p]=0;headers[p]=0;end
   source_reads=0;measuring=1;begin_cycle=cycle;cmd_valid=1;
   do @(posedge clk);while(!cmd_ready);@(negedge clk);cmd_valid=0;
   while(!done_valid)@(negedge clk);
   if(done_error||done_cancelled||done_written_mask!=16'hffff||done_words!=16||done_shift!=6'(amount)||
      done_key!=cmd_key||done_kk!=cmd_kk||rejected_responses!=0)$fatal(1,"producer qualification");
   lease_valid=7;
   do @(posedge clk);while(lease_ready!=7);@(negedge clk);lease_valid=0;
   a_cmd=7;header_start=1;
   do @(posedge clk);while(!header_ready);@(negedge clk);header_start=0;
   while(!header_done)@(negedge clk);
   if(header_error||lease_error!=0||rejected_ack!=0||rx_rejected!=0)$fatal(1,"header failed");
   header_take=1;done_ready=1;@(negedge clk);header_take=0;done_ready=0;copy_start=1;
   do @(posedge clk);while(!copy_ready);@(negedge clk);copy_start=0;
   for(integer p=0;p<3;p=p+1)begin
    while(!a_load_valid[p])@(negedge clk);
    a_cmd[p]=0;
    if(a_load_error[p]||a_load_key[p*128+:128]!=cmd_key||a_load_generation[p*16+:16]!=cmd_generation||a_load_slot[p]!=a_slot)
     $fatal(1,"A load identity");
    a_load_take[p]=1;@(negedge clk);a_load_take[p]=0;
    read_snapshot=a_reads[p];
    for(integer use_id=1;use_id<=2;use_id=use_id+1)begin
     use_sequence=16'(use_id);a_w[p]=1;
     do @(posedge clk);while(!a_w_ready[p]);@(negedge clk);a_w[p]=0;a_use[p]=1;
     do @(posedge clk);while(!a_use_ready[p]);@(negedge clk);a_use[p]=0;
     for(integer beat=0;beat<8;beat=beat+1)begin
      while(!a_valid[p])@(negedge clk);
      if(a_shift[p*6+:6]!=6'(amount)||a_step[p*3+:3]!=3'(beat)||a_key[p*128+:128]!=cmd_key||
        a_generation[p*16+:16]!=cmd_generation||a_kk[p*16+:16]!=(cmd_kk>>7)||a_use_sequence[p*16+:16]!=16'(use_id)||
        a_record[p*32+:32]!=1984||a_active_slot[p]!=a_slot)$fatal(1,"A use owner/scale");
      for(integer lane=0;lane<16;lane=lane+1)begin
       expected=rne(values[16*beat+lane],amount);
       if(expected< -32768||expected>32767||a_data[p*256+lane*16+:16]!==16'(expected))$fatal(1,"COPY true A numeric");
      end
      repeat(t%3)@(negedge clk);a_take[p]=1;@(negedge clk);a_take[p]=0;
     end
     if(a_reads[p]!=read_snapshot||read_snapshot!=16)$fatal(1,"second A use reread S");
    end
    a_close[p]=1;do @(posedge clk);while(!a_close_ready[p]);@(negedge clk);a_close[p]=0;a_release[p]=1;
    do @(posedge clk);while(!a_release_ready[p]);@(negedge clk);a_release[p]=0;
   end
   while(!copy_done)@(negedge clk);
   if(copy_error||copy_faults!=0||committed_words!=32'((t+1)*48)||copy_prefix!={11'd16,11'd16,11'd16}||source_reads!=16)
    $fatal(1,"copy terminal conservation t=%0d error=%0d faults=%0d accumulated=%0d prefix=%h reads=%0d",t,copy_error,copy_faults,committed_words,copy_prefix,source_reads);
   copy_take=1;@(negedge clk);copy_take=0;
   lease_release=7;
   do @(posedge clk);while(lease_release_ready!=7);@(negedge clk);lease_release=0;
   if(!header_quiescent||!copy_quiescent||rx_quiescent!=7||a_quiescent!=7||a_reads_drained!=7||a_faults!=0)
    $fatal(1,"true source/window lease drain");
   for(integer p=0;p<3;p=p+1)if(headers[p]!=2||p_writes[p]!=16||a_reads[p]!=16||a_live[p]!=0)$fatal(1,"per destination conservation");
   $display("G_COPY_A_REAL_S case=%0d mode=%0d shift=%0d total_cycle=%0d quant_copy_a_cycle=%0d G_reads=64 G_writes=32 G_ACK=96 G_packets=64 headers=6 U_reads=16 P_writes=48 A_reads=48 A_uses=6",t,mode,amount,cycle-g_started,cycle-begin_cycle);
   measuring=0;
  end
  $display("PASS g_quant_copy_a_joint cases=12 actual_banks=16 shared_header_data_wires=1 A_uses=72 extra_SRAM=0 mode=%0d",mode);
  $finish;
 end
endmodule
