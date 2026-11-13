"""Join real S32 quantizer, serial headers, epoch COPY, native M and S.

One P destination is selected; no three-P throughput qualification. The range
source remains the limited K128/256 fixture, not registered service2 outer.
"""
from pathlib import Path

root = Path(__file__).parent / 'rtl'
s = (root / 'tb_p_native_stream_executor.sv').read_text().replace(
    'module tb_p_native_stream_executor;', 'module tb_p_copy_stream;')
begin = s.index(' native_s128_mux2 mux(')
end = s.index(' logic [1023:0] scopes', begin)
connections = r'''
 logic q_cmd,q_ready,q_done,q_take,q_error,q_cancelled;
 logic [15:0] tile_generation,tile_k,q_done_k,q_written_mask;
 logic [31:0] tile_session,tile_ticket;
 logic [127:0] q_done_key;
 logic [4:0] q_done_words;logic [5:0] q_shift;
 logic q_valid,q_s_ready,q_write,q_rsp_valid,q_rsp_ready;
 logic [9:0] q_address;logic [127:0] q_data,q_rsp_data;logic [31:0] q_tag,q_rsp_tag,q_rejected;
 s32_a16_tile_quantizer quant(.clk,.reset,.cmd_valid(q_cmd),.cmd_ready(q_ready),
  .cmd_key(scope_data[128+:128]),.cmd_generation(tile_generation),.cmd_kk(tile_k),
  .cmd_source(10'd32),.cmd_destination(10'd256),.cmd_shift_known(1'b0),.cmd_shift(6'd0),
  .cancel_valid(1'b0),.cancel_key(128'd0),.s_valid(q_valid),.s_ready(q_s_ready),.s_write(q_write),
  .s_address(q_address),.s_data(q_data),.s_tag(q_tag),.rsp_valid(q_rsp_valid),.rsp_ready(q_rsp_ready),
  .rsp_tag(q_rsp_tag),.rsp_data(q_rsp_data),.rsp_error(1'b0),.done_valid(q_done),.done_ready(q_take),
  .done_key(q_done_key),.done_kk(q_done_k),.done_error(q_error),.done_cancelled(q_cancelled),
  .done_words(q_done_words),.done_written_mask(q_written_mask),.done_shift(q_shift),.rejected_responses(q_rejected));
 logic h_start,h_start_ready,h_done,h_take,h_error,h_quiescent;
 logic [2:0] h_valid,h_ready,h_ack_valid,h_ack_ready,h_ack_error;
 logic [95:0] h_tag,h_ack_tag;logic [383:0] h_data;logic [31:0] h_rejected;
 copy_scale_header_tx tx_header(.clk,.reset,.halt(1'b0),.start_valid(h_start),.start_ready(h_start_ready),
  .start_key(q_done_key),.start_generation(tile_generation),.start_kk(q_done_k),.start_written_mask(q_written_mask),
  .start_session(tile_session),.start_ticket(tile_ticket),.start_shift(q_shift),.start_mask(3'b001),
  .start_producer_error(q_error||q_cancelled),.frame_valid(h_valid),.frame_ready(h_ready),.frame_tag(h_tag),.frame_data(h_data),
  .ack_valid(h_ack_valid),.ack_ready(h_ack_ready),.ack_tag(h_ack_tag),.ack_error(h_ack_error),
  .done_valid(h_done),.done_ready(h_take),.done_error(h_error),.quiescent(h_quiescent),.rejected_ack(h_rejected));
 logic lease_start,lease_ready,lease_error,release_window,release_ready,rx_idle,meta_valid,meta_ready,data_enabled;
 logic [127:0] meta_key;logic [15:0] meta_gen,meta_k;logic [31:0] meta_session,meta_ticket,rx_rejected;
 logic [5:0] meta_shift;
 logic link_valid,link_ready,link_header,rx_frame_ready;
 logic [31:0] link_tag;logic [127:0] link_data;
 logic proof_accepted;
 copy_scale_header_rx rx_header(.clk,.reset,.lease_valid(lease_start),.lease_ready,
  .lease_key(scope_data[128+:128]),.lease_generation(tile_generation),.lease_kk(tile_k),
  .lease_session(tile_session),.lease_ticket(tile_ticket),.lease_error,
  .frame_valid(link_valid&&link_header),.frame_ready(rx_frame_ready),.frame_tag(link_tag),.frame_data(link_data),
  .ack_valid(h_ack_valid[0]),.ack_ready(h_ack_ready[0]),.ack_tag(h_ack_tag[0+:32]),.ack_error(h_ack_error[0]),
  .metadata_valid(meta_valid),.metadata_ready(meta_ready),.metadata_key(meta_key),.metadata_generation(meta_gen),
  .metadata_kk(meta_k),.metadata_session(meta_session),.metadata_ticket(meta_ticket),.metadata_shift(meta_shift),.data_enabled,
  .release_valid(release_window),.release_ready,.release_key(scope_data[128+:128]),.release_generation(tile_generation),
  .release_cancel(1'b0),.data_drained(copy_idle&&owners==0),
  .consumer_drained(proof_accepted&&a_source_reads_drained),.quiescent(rx_idle),.rejected_frames(rx_rejected));
 assign h_ack_valid[2:1]=0;assign h_ack_tag[95:32]=0;assign h_ack_error[2:1]=0;
 assign h_ready[2:1]=0;
 assign directory_publish=meta_valid;assign publish_k=meta_k;assign meta_ready=directory_publish_ready;
 assign stream_window_valid=data_enabled;assign stream_window_key=meta_key;
 assign stream_window_generation=meta_gen;assign stream_window_k_elements=meta_k;
 assign stream_window_session=meta_session;assign stream_window_ticket=meta_ticket;
 logic copy_start,copy_start_ready,copy_done,copy_take,copy_error,copy_idle,copy_identity;
 logic [15:0] copy_gen,copy_k;logic [31:0] copy_session,copy_ticket,copy_faults,copy_words;
 logic [32:0] copy_prefix;
 logic copy_u_valid,copy_u_ready,copy_u_rsp_valid,copy_u_rsp_ready;
 logic [9:0] copy_u_address;logic [31:0] copy_u_tag,copy_u_rsp_tag;logic [127:0] copy_u_rsp_data;
 logic [2:0] cp_valid,cp_ready,cp_ack_valid,cp_ack_ready;
 logic [29:0] cp_address;logic [95:0] cp_tag,cp_ack_tag;logic [383:0] cp_data;
 early_copy_epoch_3p copier(.clk,.reset,.halt(1'b0),.start_valid(copy_start),.start_ready(copy_start_ready),
  .start_key(scope_data[128+:128]),.start_generation(tile_generation),.start_kk(tile_k),.start_session(tile_session),.start_ticket(tile_ticket),
  .start_U_base(10'd256),.start_P_bases(30'd0),.start_words(11'd16),.start_P_mask(3'b001),.destination_window_released(data_enabled),
  .u_valid(copy_u_valid),.u_ready(copy_u_ready),.u_address(copy_u_address),.u_tag(copy_u_tag),
  .u_response_valid(copy_u_rsp_valid),.u_response_ready(copy_u_rsp_ready),.u_response_tag(copy_u_rsp_tag),.u_response_data(copy_u_rsp_data),.u_response_error(1'b0),
  .p_valid(cp_valid),.p_ready(cp_ready),.p_address(cp_address),.p_tag(cp_tag),.p_data(cp_data),
  .p_ack_valid(cp_ack_valid),.p_ack_ready(cp_ack_ready),.p_ack_tag(cp_ack_tag),.p_ack_error(3'd0),
  .copy_key,.copy_committed_prefix(copy_prefix),.copy_generation(copy_gen),.copy_kk(copy_k),.copy_identity_valid(copy_identity),.copy_session,.copy_ticket,
  .done_valid(copy_done),.done_ready(copy_take),.done_error(copy_error),.quiescent(copy_idle),.fault_cycles(copy_faults),.committed_words(copy_words));
 assign copy_progress_valid=copy_identity;assign copy_progress_generation=copy_gen;assign copy_progress_k_elements=copy_k;
 assign copy_progress_session=copy_session;assign copy_progress_ticket=copy_ticket;assign copy_committed_prefix=copy_prefix[0+:11];
 assign link_valid=h_valid[0]||cp_valid[0];assign link_tag=h_valid[0]?h_tag[0+:32]:cp_tag[0+:32];
 assign link_data=h_valid[0]?h_data[0+:128]:cp_data[0+:128];assign link_header=link_tag[15];
 assign link_ready=link_header?rx_frame_ready:(p_ready[1]&&data_enabled);
 assign h_ready[0]=link_ready&&link_header;assign cp_ready={2'd0,link_ready&&!link_header};
 logic [2:0] p_ready,p_response_valid;logic [95:0] p_response_tag;
 native_s128_mux3 mux(.clk,.reset,.c_valid({ar_valid,link_valid&&!link_header&&data_enabled,(host_mode?host_valid:(sw_valid&&allow_request))}),
  .c_write({2'b01,(host_mode?host_write:1'b1)}),.c_address({ar_address,cp_address[0+:10],(host_mode?host_address:sw_address)}),
  .c_data({128'd0,link_data,(host_mode?host_data:sw_data)}),.c_tag({ar_tag,link_tag,(host_mode?32'd0:{31'd0,sw_word})}),
  .c_ready(p_ready),.c_response_valid(p_response_valid),.c_response_ready({ar_rsp_ready&&allow_A_response,cp_ack_ready[0],(host_mode?host_response_ready:(sw_ack_ready&&allow_ACK))}),
  .c_response_data,.c_response_tag(p_response_tag),.req_valid,.req_write,.req_address,.req_data,.req_ready,.rsp_valid,.rsp_ready,.rsp_data,.owners_occupied(owners));
 local_s_base storage(.clk,.reset,.req_valid,.req_write,.req_addr(req_address),.req_data,.req_ready,.rsp_valid,.rsp_ready,.rsp_data);
 assign c_ready={p_ready[2],p_ready[0]};assign c_response_valid={p_response_valid[2],p_response_valid[0]};
 assign c_response_tag={p_response_tag[95:64],p_response_tag[31:0]};
 assign cp_ack_valid={2'd0,p_response_valid[1]};assign cp_ack_tag={64'd0,p_response_tag[63:32]};
 assign host_ready=host_mode&&c_ready[0];assign host_response_valid=host_mode&&c_response_valid[0];
 assign ar_ready=c_ready[1];assign ar_rsp_valid=c_response_valid[1]&&allow_A_response;
 assign ar_rsp_tag=c_response_tag[63:32];assign ar_rsp_data=c_response_data;
 assign sw_ready=!host_mode&&c_ready[0]&&allow_request;
 assign sw_ack_valid=!host_mode&&c_response_valid[0]&&allow_ACK;
 assign sw_ack_ticket=sw_ticket;assign sw_ack_word=c_response_tag[0];assign sw_ack_error=0;
 logic uh_valid,uh_write,uh_ready,uh_rsp_valid,uh_rsp_ready;
 logic [9:0] uh_address;logic [127:0] uh_data;
 logic [2:0] ur,uv;logic [95:0] ut;logic [127:0] ud;
 logic unv,unw,unready,unrv,unrr;logic [9:0] una;logic [127:0] und,unrd;logic [1:0] uowners;
 native_s128_mux3 umux(.clk,.reset,.c_valid({q_valid,copy_u_valid,uh_valid}),.c_write({q_write,1'b0,uh_write}),
  .c_address({q_address,copy_u_address,uh_address}),.c_data({q_data,128'd0,uh_data}),.c_tag({q_tag,copy_u_tag,32'd0}),
  .c_ready(ur),.c_response_valid(uv),.c_response_ready({q_rsp_ready,copy_u_rsp_ready,uh_rsp_ready}),.c_response_data(ud),.c_response_tag(ut),
  .req_valid(unv),.req_write(unw),.req_address(una),.req_data(und),.req_ready(unready),.rsp_valid(unrv),.rsp_ready(unrr),.rsp_data(unrd),.owners_occupied(uowners));
 local_s_base U_storage(.clk,.reset,.req_valid(unv),.req_write(unw),.req_addr(una),.req_data(und),.req_ready(unready),.rsp_valid(unrv),.rsp_ready(unrr),.rsp_data(unrd));
 assign q_s_ready=ur[2];assign q_rsp_valid=uv[2];assign q_rsp_tag=ut[95:64];assign q_rsp_data=ud;
 assign copy_u_ready=ur[1];assign copy_u_rsp_valid=uv[1];assign copy_u_rsp_tag=ut[63:32];assign copy_u_rsp_data=ud;
 assign uh_ready=ur[0];assign uh_rsp_valid=uv[0];
 integer real_copy_ACKs,real_copy_reads,real_headers,real_quantizations;
 always @(posedge clk)if(!reset)begin
  if(q_done&&q_take)begin real_quantizations<=real_quantizations+1;$fwrite(trace_file,"%0d,QUANT_DONE,%0d,%0d,%0d,0\n",cycle,case_id,q_done_k,q_shift);end
  if(copy_u_valid&&copy_u_ready)real_copy_reads<=real_copy_reads+1;
  if(cp_ack_valid[0]&&cp_ack_ready[0])real_copy_ACKs<=real_copy_ACKs+1;
  if(h_valid[0]&&h_ready[0])real_headers<=real_headers+1;
  if(h_valid[0]&&cp_valid[0])$fatal(1,"header and data alias shared128 wires");
  if(ar_valid&&ar_ready)assert(copy_identity&&copy_gen==stream_window_generation&&copy_k==scale_lookup_kk&&
      {1'b0,ar_address}<copy_prefix[0+:11])else $fatal(1,"A read before true matching COPY write ACK");
  assert(copy_faults==0&&rx_rejected==0&&h_rejected==0&&q_rejected==0&&!lease_error)else $fatal(1,"real COPY/header/quantizer fault");
 end
 wire unused_copy_diagnostics=^{cp_valid[2:1],cp_address,cp_data,cp_tag,cp_ack_ready[2:1],h_ready,h_valid[2:1],h_ack_ready[2:1],h_tag[95:32],h_data[383:128],h_quiescent,copy_words,copy_prefix[32:11],uowners,und,unrd,meta_key,ut[31:0]};
'''
s = s[:begin] + connections + s[end:]
s = s.replace('.publish_shift(6\'d8)', '.publish_shift(meta_shift)')
s = s.replace('  stream_window_valid=0;stream_window_key=0;stream_window_generation=0;stream_window_k_elements=0;\n', '')
s = s.replace('  stream_window_session=0;stream_window_ticket=0;copy_progress_session=0;copy_progress_ticket=0;\n', '')
s = s.replace('  copy_progress_valid=0;copy_progress_generation=0;copy_progress_k_elements=0;\n', '')
s = s.replace('  copy_key=0;copy_committed_prefix=0;directory_cfg=0;directory_publish=0;publish_k=0;', '  directory_cfg=0;q_cmd=0;q_take=0;h_start=0;h_take=0;lease_start=0;release_window=0;copy_start=0;copy_take=0;tile_generation=0;tile_k=0;tile_session=0;tile_ticket=0;proof_accepted=0;uh_valid=0;uh_write=1;uh_rsp_ready=0;uh_address=0;uh_data=0;real_copy_ACKs=0;real_copy_reads=0;real_headers=0;real_quantizations=0;')
begin = s.index('   copy_key=scope_data[128+:128];')
end = s.index('   host_mode=0;pause();', begin)
s = s[:begin] + '''
   directory_cfg=1;do @(posedge clk);while(!directory_ready);@(negedge clk);directory_cfg=0;
''' + s[end:]
begin = s.index('     for(integer tile=0;')
end = s.index('    end\n    begin\n     while(!service_done_valid)', begin)
producer = r'''
     for(integer tile=0;tile<(int'(scope_data[608+:16])>>7);tile=tile+1)begin
      tile_generation=tile_generation+1;tile_k=16'(tile*128);tile_session=32'(ci+1);tile_ticket=32'(ci*4+tile+1);proof_accepted=0;
      for(integer wi=0;wi<32;wi=wi+1)u_host_word(32+wi,make_S32(tile,wi));
      q_cmd=1;do @(posedge clk);while(!q_ready);@(negedge clk);q_cmd=0;
      while(!q_done)@(negedge clk);
      assert(!q_error&&!q_cancelled&&q_done_key==scope_data[128+:128]&&q_done_k==tile_k&&q_done_words==16&&q_written_mask==16'hffff&&q_shift==0)else $fatal(1,"real dynamic normalizer completion");
      lease_start=1;do @(posedge clk);while(!lease_ready);@(negedge clk);lease_start=0;
      h_start=1;do @(posedge clk);while(!h_start_ready);@(negedge clk);h_start=0;
      while(!h_done)@(negedge clk);assert(!h_error);h_take=1;pause();h_take=0;
      // RX has a new header while COPY still advertises previous nonzero ACK
      // prefix. Neither that prefix nor command admission proves source data.
      repeat(5)begin pause();assert(!ar_valid)else $fatal(1,"old COPY prefix authorized next header tile");stale_prefix_checks=stale_prefix_checks+1;end
      copy_start=1;do @(posedge clk);while(!copy_start_ready);@(negedge clk);copy_start=0;
      while(!copy_done)@(negedge clk);assert(!copy_error);copy_take=1;pause();copy_take=0;
      while(!a_load_proof_valid)@(negedge clk);allow_native_A=0;
      assert(!a_load_proof_error&&a_source_reads_drained&&a_load_proof_key==meta_key&&
          a_load_proof_window_generation==meta_gen&&a_load_proof_window_session==meta_session&&a_load_proof_window_ticket==meta_ticket&&
          a_load_proof_k_elements==meta_k&&a_load_proof_A_generation!=0&&a_load_proof_A_slot==1'(tile)&&a_load_proof_shift==q_shift)else $fatal(1,"true header COPY LOAD proof mismatch");
      pause(3);a_load_proof_ready=1;pause();a_load_proof_ready=0;load_proofs=load_proofs+1;proof_accepted=1;
      release_window=1;do @(posedge clk);while(!release_ready);@(negedge clk);release_window=0;
      assert(rx_idle&&A_live!=0)else $fatal(1,"S stage release confused with A FREE");
      for(integer wi=0;wi<16;wi=wi+1)begin host_word(1,wi,128'hfeedface0123456789abcdef76543210);poison_writes=poison_writes+1;end
      host_mode=0;allow_native_A=1;
      q_take=1;pause();q_take=0;
     end
'''
s = s[:begin] + producer + s[end:]
tasks = r'''
 function automatic [127:0] make_S32(input integer tile,word_index);
  logic signed [15:0] lane16;logic signed [31:0] widened;logic [127:0] value;
  value=0;
  for(integer lane=0;lane<4;lane=lane+1)begin
   lane16=16'(A_memory[case_id*32+tile*16+word_index/2]>>(16*(4*(word_index%2)+lane)));
   widened={{16{lane16[15]}},lane16}<<<8;value[lane*32+:32]=widened;
  end
  return value;
 endfunction
 task automatic u_host_word(input integer address_word,input logic [127:0] value);
  assert(address_word>=0&&address_word<1024)else $fatal(1,"U boot address out of bounds");
  uh_valid=1;uh_address=10'(address_word);uh_data=value;
  do @(posedge clk);while(!uh_ready);@(negedge clk);uh_valid=0;
  while(!uh_rsp_valid)@(negedge clk);uh_rsp_ready=1;pause();uh_rsp_ready=0;
 endtask
'''
location = s.index(' initial begin', s.index(' task automatic host_word'))
s = s[:location] + tasks + s[location:]
s = s.replace('stale_prefix_checks==48', 'stale_prefix_checks==60&&real_copy_ACKs==192&&real_copy_reads==192&&real_headers==24&&real_quantizations==12')
s = s.replace('PASS p_native_stream_executor', 'PASS p_copy_stream')
(root / 'tb_p_copy_stream.sv').write_text(s)
