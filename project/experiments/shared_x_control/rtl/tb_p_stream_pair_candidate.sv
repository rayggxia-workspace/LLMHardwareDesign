`timescale 1ns/1ps
// Real serialized M + real S bank fixture, functional10ns not300MHzSTA.
module tb_p_stream_pair_candidate;
logic clk,reset;
 logic scope_valid;
 logic scope_ready;
 logic scope_end,scope_cancel;
 logic [127:0] scope_owner;
 logic [1023:0] scope_data;
 logic record_valid;
 logic record_ready;
 logic [31:0] record_sequence;
 logic [127:0] record_owner;
 logic [63:0] record_address;
 logic [15:0] record_full_k,record_k;
 logic [31:0] record_col;
 logic [3:0] record_context,record_n;
 logic record_way,record_head16;
 logic record_create,record_restore,record_final,record_spill,record_A_first,record_A_last;
 logic [4:0] record_A_uses;
 logic complete_valid;
 logic complete_ready;
 logic [127:0] complete_owner;
 logic [31:0] complete_sequence;
 logic [3:0] complete_context;
 logic [15:0] complete_next_k;
 logic complete_error;
 logic [127:0] copy_key;
 logic [10:0] copy_committed_prefix;
 logic [127:0] scale_lookup_key;
 logic [15:0] scale_lookup_kk;
 logic scale_lookup_valid;
 logic [5:0] scale_lookup_shift;
 logic ar_valid;
 logic ar_ready;
 logic [9:0] ar_address;
 logic [31:0] ar_tag;
 logic ar_rsp_valid;
 logic ar_rsp_ready;
 logic [31:0] ar_rsp_tag;
 logic [127:0] ar_rsp_data;
 logic sw_valid;
 logic sw_ready;
 logic [511:0] sw_ticket;
 logic sw_word;
 logic [9:0] sw_address;
 logic [127:0] sw_data;
 logic sw_ack_valid;
 logic sw_ack_ready;
 logic [511:0] sw_ack_ticket;
 logic sw_ack_word,sw_ack_error;
 logic lc_valid;
 logic lc_ready;
 logic lc_sop,lc_eop;
 logic [127:0] lc_data;
 logic lr_valid;
 logic lr_ready;
 logic lr_sop,lr_eop;
 logic [127:0] lr_data;
 logic a_valid;
 logic a_ready;
 logic [255:0] a_data;
 logic [31:0] a_session;
 logic [2:0] a_beat;
 logic quiescent,quarantine;
 logic [31:0] protocol_faults;
 logic [31:0] confirmed_weight_read_bytes,confirmed_result_write_bytes;
 logic [1:0] A_live,result_occupied,command_occupied;

 initial clk=0;always #5 clk=~clk;

 logic stream_window_valid,copy_progress_valid,a_load_proof_valid,a_load_proof_ready;
 logic [127:0] stream_window_key,a_load_proof_key;
 logic [15:0] stream_window_generation,copy_progress_generation,a_load_proof_window_generation;
 logic [31:0] stream_window_session,stream_window_ticket,copy_progress_session,copy_progress_ticket,a_load_proof_window_session,a_load_proof_window_ticket;
 logic [15:0] stream_window_k_elements,copy_progress_k_elements,a_load_proof_k_elements,a_load_proof_A_generation;
 logic a_load_proof_A_slot,a_load_proof_error,a_source_reads_drained;
 logic [5:0] a_load_proof_shift;
 logic allow_native_A,m_a_ready;
 integer load_proofs,poison_writes,stale_prefix_checks;
 p_native_stream_pair_candidate exec(.*);
 logic service_valid,service_ready,service_done_valid,service_done_ready;
 logic [127:0] service_done_owner;
 logic [31:0] service_done_ticket,service_done_read_bytes,service_done_write_bytes;
 logic [15:0] service_done_status;
 logic [127:0] decoded_key;
 logic [31:0] rf0,rf1,out_version;
 logic [63:0] bias0,bias1;
 logic [9:0] inS,outS0,outS1,scratchS,snapshotS;
 logic [15:0] record_bytes;
 logic cancel_ready,rejected_complete;
 p_scope_range_service #(.NATIVE_STREAM_A16(1'b1)) ranges(
  .clk,.reset,.service_valid(service_valid&&scope_ready),.service_ready,
  .service_owner(scope_owner),.service_ticket(scope_owner[31:0]),.service_descriptor(scope_data),
  .expected_topology(32'd25001),.service_cancel_valid(scope_cancel),.service_cancel_ready(cancel_ready),
  .service_done_valid,.service_done_ready,.service_done_owner,.service_done_ticket,.service_done_status,
  .native_confirmed_read_bytes(confirmed_weight_read_bytes),.native_confirmed_write_bytes(confirmed_result_write_bytes),
  .service_done_read_bytes,.service_done_write_bytes,.input_key(decoded_key),
  .rf_object_base0(rf0),.rf_object_base1(rf1),.output_version(out_version),
  .bias_address0(bias0),.bias_address1(bias1),.input_s_base(inS),.output_s_base0(outS0),
  .output_s_base1(outS1),.scratch_s_base(scratchS),.snapshot_s_base(snapshotS),
  .record_valid,.record_ready,.record_owner,.record_sequence,.record_address,.record_bytes,.record_full_k,
  .record_k,.record_col,.record_context,.record_n,.record_way,.record_head16,.record_create,.record_restore,
  .record_final,.record_spill,.record_A_first,.record_A_last,.record_A_uses,
  .complete_valid,.complete_ready,.complete_owner,.complete_sequence,.complete_context,.complete_next_k,.complete_error,.rejected_complete);
 assign scope_valid=service_valid&&service_ready;
 assign scope_end=service_done_valid&&service_done_ready;
 logic directory_cfg,directory_ready,directory_publish,directory_publish_ready,directory_bad,directory_pub_bad;
 logic [15:0] publish_k;
 logic [31:0] directory_faults;
 a_scale_directory32 directory(.clk,.reset,.cfg_valid(directory_cfg),.cfg_ready(directory_ready),
  .cfg_key(scope_data[128+:128]),.cfg_first_kk(16'd0),.cfg_tiles(6'(scope_data[608+:16]>>7)),.cfg_stride3(1'b0),
  .storage_released(quiescent),.leases_drained(quiescent),.cfg_rejected(directory_bad),
  .publish_valid(directory_publish),.publish_ready(directory_publish_ready),.publish_key(scope_data[128+:128]),
  .publish_kk(publish_k),.publish_shift(meta_shift),.publish_written_mask(16'hffff),.publish_error(1'b0),
  .publish_rejected(directory_pub_bad),.lookup_key(scale_lookup_key),.lookup_kk(scale_lookup_kk),
  .lookup_valid(scale_lookup_valid),.lookup_shift(scale_lookup_shift),.rejected_publications(directory_faults));
 logic mc_req_valid,mc_req_ready,mc_req_channel,mc_rsp_valid,mc_rsp_ready;
 logic [63:0] mc_req_address;
 logic [31:0] mc_req_tag,mc_rsp_tag;
 logic [4:0] mc_req_record_beats;
 logic [511:0] mc_rsp_data;
 logic mc_close_valid,mc_close_ready;
 logic [31:0] mc_close_tag_base;
 logic mc_fence_req_valid,mc_fence_req_ready,mc_fence_done_valid,mc_fence_done_ready;
 logic [31:0] mc_fence_req_cookie,mc_fence_done_cookie;
 logic [8:0] mc_fence_req_epoch,mc_fence_done_epoch;
 logic fault_interrupt;
 m_native_leaf_s32 M(.clk,.reset,.lc_valid,.lc_ready,.lc_sop,.lc_eop,.lc_data,
  .lr_valid,.lr_ready,.lr_sop,.lr_eop,.lr_data,.a_valid(a_valid&&allow_native_A),.a_ready(m_a_ready),.a_data,.a_session,.a_beat,
  .mc_req_valid,.mc_req_ready,.mc_req_address,.mc_req_tag,.mc_req_channel,.mc_req_record_beats,
  .mc_close_valid,.mc_close_ready,.mc_close_tag_base,.mc_rsp_valid,.mc_rsp_ready,.mc_rsp_tag,.mc_rsp_data,
  .mc_fence_req_valid,.mc_fence_req_ready,.mc_fence_req_cookie,.mc_fence_req_epoch,
  .mc_fence_done_valid,.mc_fence_done_ready,.mc_fence_done_cookie,.mc_fence_done_epoch,.fault_interrupt);
 assign a_ready=m_a_ready&&allow_native_A;
 assign mc_close_ready=1;
 assign mc_fence_req_ready=0;assign mc_fence_done_valid=0;
 assign mc_fence_done_cookie=0;assign mc_fence_done_epoch=0;
 logic host_mode,host_valid,host_ready,host_write,host_response_valid,host_response_ready;
 logic [9:0] host_address;
 logic [127:0] host_data;
 logic [1:0] c_ready,c_response_valid,owners;
 logic [63:0] c_response_tag;
 logic [127:0] c_response_data;
 logic req_valid,req_ready,req_write,rsp_valid,rsp_ready;
 logic [9:0] req_address;
 logic [127:0] req_data,rsp_data;
 logic allow_request,allow_ACK,allow_A_response;

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
 logic [1023:0] scopes[0:7];logic [127:0] A_memory[0:255],expect_memory[0:31];
 logic [511:0] DDR_memory[0:1023];
 logic [31:0] pending_mask,pending_tags[0:31];
 logic [511:0] pending_data[0:31];logic pending_channel[0:31];integer pending_due[0:31];
 integer response_slot,response_candidate,free_slot;
 integer pair_first_core,pair_second_core,pair_first_rf,pair_core_count;
 logic pair_first_rf_frame;
 integer cycle,seed,case_id,trace_file,accepted,returned,A_reads,writes,ACKs,completed,record_count;
 integer channel_live[2],last_ACK_cycle,last_complete_cycle;
 logic [31:0] start_cycle;
 string vectors,trace_path;
 always_comb begin
  free_slot=-1;response_candidate=-1;
  for(integer j=0;j<32;j=j+1)begin
   if(!pending_mask[j]&&free_slot<0)free_slot=j;
   if(pending_mask[j]&&pending_due[j]<=cycle&&response_candidate<0)response_candidate=j;
  end
  mc_req_ready=!reset&&free_slot>=0&&(cycle%5!=seed%5)&&channel_live[mc_req_channel]<32;
  mc_rsp_valid=!reset&&response_slot>=0;
  mc_rsp_tag=0;mc_rsp_data=0;
  if(response_slot>=0)begin mc_rsp_tag=pending_tags[response_slot];mc_rsp_data=pending_data[response_slot];end
 end
 always @(posedge clk)begin
  if(reset)begin
   pair_first_core<=0;pair_second_core<=0;pair_first_rf<=0;pair_core_count<=0;pair_first_rf_frame<=0;
   cycle<=0;pending_mask<=0;response_slot<=-1;accepted<=0;returned<=0;A_reads<=0;writes<=0;ACKs<=0;completed<=0;record_count<=0;
   channel_live[0]<=0;channel_live[1]<=0;last_ACK_cycle<=0;last_complete_cycle<=0;
  end else begin
   cycle<=cycle+1;
   if(case_id==5)begin
    if(M.n_exec_valid&&M.n_exec_ready)begin
     pair_core_count<=pair_core_count+1;
     if(pair_core_count==0)pair_first_core<=cycle;else pair_second_core<=cycle;
     $fwrite(trace_file,"%0d,PAIR_CORE,%0d,%0d,0,0\n",cycle,case_id,pair_core_count);
    end
    if(lr_valid&&lr_ready&&lr_sop)pair_first_rf_frame<=lr_data[39:32]==4&&lr_data[111:80]==scope_data[352+:32];
    if(lr_valid&&lr_ready&&lr_eop&&pair_first_rf_frame)begin
     pair_first_rf<=cycle;pair_first_rf_frame<=0;
     $fwrite(trace_file,"%0d,PAIR_FIRST_RF,%0d,0,0,0\n",cycle,case_id);
    end
   end
   if(mc_req_valid&&mc_req_ready)begin
    assert(mc_req_address>=64'h100000+64'(case_id)*64'h10000&&mc_req_address<64'h102000+64'(case_id)*64'h10000) else $fatal(1,"undeployed weight address");
    assert(mc_req_tag[4:0]<mc_req_record_beats&&mc_req_record_beats==(scope_data[664]?18:17)) else $fatal(1,"real W tag/record size");
    pending_mask[free_slot]<=1;pending_tags[free_slot]<=mc_req_tag;pending_channel[free_slot]<=mc_req_channel;
    pending_data[free_slot]<=DDR_memory[case_id*128+int'((mc_req_address-(64'h100000+64'(case_id)*64'h10000))>>6)];
    pending_due[free_slot]<=cycle+7+(seed%4);accepted<=accepted+1;
    $fwrite(trace_file,"%0d,DDR_REQ,%0d,%0d,%0d,%0d\n",cycle,case_id,mc_req_tag,mc_req_address,mc_req_channel);
   end
   if(response_slot<0&&response_candidate>=0)response_slot<=response_candidate;
   if(mc_rsp_valid&&mc_rsp_ready)begin pending_mask[response_slot]<=0;response_slot<=-1;returned<=returned+1;$fwrite(trace_file,"%0d,DDR_RSP,%0d,%0d,0,0\n",cycle,case_id,mc_rsp_tag);end
   for(integer ch=0;ch<2;ch=ch+1)
    channel_live[ch]<=channel_live[ch]+((mc_req_valid&&mc_req_ready&&int'(mc_req_channel)==ch)?1:0)-((mc_rsp_valid&&mc_rsp_ready&&response_slot>=0&&int'(pending_channel[response_slot])==ch)?1:0);
   if(ar_valid&&ar_ready)begin A_reads<=A_reads+1;$fwrite(trace_file,"%0d,A_S_REQ,%0d,%0d,%0d,0\n",cycle,case_id,ar_tag,ar_address);end
   if(a_valid&&a_ready)$fwrite(trace_file,"%0d,A_M,%0d,%0d,%0d,0\n",cycle,case_id,a_session,a_beat);
   if(sw_valid&&sw_ready)begin writes<=writes+1;$fwrite(trace_file,"%0d,S_WRITE,%0d,%0d,%0d,0\n",cycle,case_id,sw_word,sw_address);end
   if(sw_ack_valid&&sw_ack_ready)begin ACKs<=ACKs+1;last_ACK_cycle<=cycle;$fwrite(trace_file,"%0d,S_ACK,%0d,%0d,0,0\n",cycle,case_id,sw_ack_word);end
   if(record_valid&&record_ready)begin record_count<=record_count+1;$fwrite(trace_file,"%0d,RECORD,%0d,%0d,%0d,%0d\n",cycle,case_id,record_sequence,record_k,record_context);end
   if(complete_valid&&complete_ready)begin
    assert(!complete_error)else $fatal(1,"real native completion error");completed<=completed+1;last_complete_cycle<=cycle;
    if(complete_next_k==scope_data[608+:16])assert(last_ACK_cycle<cycle)else $fatal(1,"FINAL before true S ACK");
    $fwrite(trace_file,"%0d,COMPLETE,%0d,%0d,%0d,%0d\n",cycle,case_id,complete_sequence,complete_next_k,complete_context);
   end
   if(lc_valid&&lc_ready)$fwrite(trace_file,"%0d,LC_M,%0d,%0d,%0d,%0d\n",cycle,case_id,lc_sop,lc_eop,lc_data[19:16]);
   if(lr_valid&&lr_ready)$fwrite(trace_file,"%0d,M_LR,%0d,%0d,%0d,%0d\n",cycle,case_id,lr_sop,lr_eop,lr_data[39:32]);
   assert(!quarantine&&!fault_interrupt&&protocol_faults==0&&!rejected_complete&&!directory_bad&&!directory_pub_bad)else $fatal(1,"real P quarantine/fault state=%0d ctrl=%0d M=%0d",exec.state,protocol_faults,fault_interrupt);
  end
 end
 task automatic pause(input int n=1);repeat(n)@(negedge clk);endtask
 task automatic host_word(input bit wr,input int address_word,input logic[127:0] value);
  host_mode=1;host_write=wr;host_address=10'(address_word);host_data=value;host_valid=1;
  do @(posedge clk);while(!host_ready);@(negedge clk);host_valid=0;
  while(!host_response_valid)@(negedge clk);
  if(!wr)assert(c_response_data==value)else $fatal(1,"true S numeric readback case%0d address%0d got%h expected%h",case_id,address_word,c_response_data,value);
  host_response_ready=1;pause();host_response_ready=0;
 endtask

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
 initial begin

  a_load_proof_ready=0;allow_native_A=0;load_proofs=0;poison_writes=0;stale_prefix_checks=0;
  reset=1;service_valid=0;service_done_ready=0;scope_cancel=0;scope_owner=0;scope_data=0;
  directory_cfg=0;q_cmd=0;q_take=0;h_start=0;h_take=0;lease_start=0;release_window=0;copy_start=0;copy_take=0;tile_generation=0;tile_k=0;tile_session=0;tile_ticket=0;proof_accepted=0;uh_valid=0;uh_write=1;uh_rsp_ready=0;uh_address=0;uh_data=0;real_copy_ACKs=0;real_copy_reads=0;real_headers=0;real_quantizations=0;
  host_mode=1;host_valid=0;host_write=1;host_address=0;host_data=0;host_response_ready=0;
  allow_request=1;allow_ACK=1;allow_A_response=1;case_id=0;seed=1;
  if($value$plusargs("SEED=%d",seed))begin end
  vectors="results/p-vectors";if($value$plusargs("VECTORS=%s",vectors))begin end
  trace_path="p-executor.csv";if($value$plusargs("TRACE=%s",trace_path))begin end
  $readmemh({vectors,"/scopes.mem"},scopes);$readmemh({vectors,"/A.mem"},A_memory);
  $readmemh({vectors,"/DDR.mem"},DDR_memory);$readmemh({vectors,"/expected.mem"},expect_memory);
  trace_file=$fopen(trace_path,"w");assert(trace_file!=0);$fwrite(trace_file,"cycle,event,case,identity,detail,value\n");
  pause(4);reset=0;pause();
  for(integer ci=0;ci<8;ci=ci+1)begin
   case_id=ci;scope_data=scopes[ci];scope_data[48+:16]=16'd2;scope_owner={32'd1,32'd7,32'd8,32'(ci+1)};

   directory_cfg=1;do @(posedge clk);while(!directory_ready);@(negedge clk);directory_cfg=0;
   host_mode=0;pause();start_cycle=32'(cycle);service_valid=1;
   do @(posedge clk);while(!(service_ready&&scope_ready));@(negedge clk);service_valid=0;
   fork
    begin

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
    end
    begin
     while(!service_done_valid)begin
      pause(2+(seed%3));allow_ACK=0;allow_A_response=0;pause(1);allow_ACK=1;allow_A_response=1;
     end
    end
    begin
     while(!service_done_valid)@(negedge clk);
     assert(service_done_owner==scope_owner&&service_done_ticket==scope_owner[31:0]&&service_done_status==0)else $fatal(1,"true range terminal status %0d",service_done_status);
    end
   join
   service_done_ready=1;pause();service_done_ready=0;pause(2);
   assert(quiescent&&A_live==0&&command_occupied==0&&result_occupied==0&&pending_mask==0)else $fatal(1,"real owner leak");
   for(integer outword=0;outword<int'(scope_data[592+:5])*2;outword=outword+1)host_word(0,128+outword,expect_memory[ci*4+outword]);
   $fwrite(trace_file,"%0d,CASE_DONE,%0d,%0d,%0d,%0d\n",cycle,ci,cycle-int'(start_cycle),A_reads,ACKs);
  end
  assert(load_proofs==12&&poison_writes==192&&stale_prefix_checks==60&&real_copy_ACKs==192&&real_copy_reads==192&&real_headers==24&&real_quantizations==12)else $fatal(1,"stream finite proof accounting");
  assert(accepted==returned&&ACKs==24&&writes==24&&completed==18&&record_count==18&&A_reads==192&&directory_faults==0)else $fatal(1,"accounting req%0d rsp%0d ACK%0d writes%0d completed%0d records%0d Areads%0d",accepted,returned,ACKs,writes,completed,record_count,A_reads);
  assert(pair_core_count==2&&pair_first_core>0&&pair_second_core>pair_first_core&&pair_second_core<pair_first_rf)
    else $fatal(1,"M2 pair overlap not observed first%0d second%0d RF1%0d",pair_first_core,pair_second_core,pair_first_rf);
  $display("pair_head_II=%0d first_core=%0d second_core=%0d first_RF_EOP=%0d",pair_second_core-pair_first_core,pair_first_core,pair_second_core,pair_first_rf);
  $display("PASS p_stream_pair_candidate seed=%0d cases=8 cycles=%0d requests=%0d returns=%0d S128ACK=%0d records=%0d Areads=%0d",seed,cycle,accepted,returned,ACKs,completed,A_reads);
  $fclose(trace_file);$finish;
 end
 initial begin #2000000;$fatal(1,"real P timeout state=%0d case=%0d pending=%h",exec.state,case_id,pending_mask);end
 wire unused_diagnostics=^{service_done_read_bytes,service_done_write_bytes,decoded_key,rf0,rf1,out_version,bias0,bias1,
  inS,outS0,outS1,scratchS,snapshotS,record_bytes,cancel_ready,mc_close_valid,mc_close_tag_base,
  mc_fence_req_valid,mc_fence_req_cookie,mc_fence_req_epoch,mc_fence_done_ready,owners,c_response_tag[31:1],last_complete_cycle};
endmodule
