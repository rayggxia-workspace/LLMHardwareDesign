`timescale 1ns/1ps
// Real serialized M + real S bank fixture, functional10ns not300MHzSTA.
module tb_p_stream_program;
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
 p_native_stream_record_executor exec(.*);

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
  .cfg_key(scopes[case_id][128+:128]),.cfg_first_kk(16'd0),.cfg_tiles(6'(scopes[case_id][608+:16]>>7)),.cfg_stride3(1'b0),
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

 integer cycle,seed,case_id,trace_file,accepted,returned,A_reads,writes,ACKs,completed,record_count;
 integer last_ACK_cycle,last_complete_cycle;
 logic [31:0] start_cycle;
 string vectors,trace_path;

 logic [11:0] c_req_valid,c_req_ready,c_req_channel,c_rsp_valid,c_rsp_ready,c_close_valid,c_close_ready;
 logic [767:0] c_req_address;logic [383:0] c_req_tag,c_rsp_tag,c_close_tag_base;
 logic [59:0] c_req_record_beats;logic [6143:0] c_rsp_data;
 logic [11:0] c_cancel_ready,c_cancel_ack_valid,c_cancel_ack_rejected,c_fence_valid,c_fence_ready,c_fence_done_valid,c_fence_done_ready;
 logic [383:0] c_cancel_ack_tag,c_fence_cookie,c_fence_done_cookie;
 logic [107:0] c_fence_epoch,c_fence_done_epoch;
 logic [3:0] d_req_valid,d_req_ready,d_rsp_valid,d_rsp_ready;
 logic [255:0] d_req_address,d_req_tag,d_rsp_tag;logic [2047:0] d_rsp_data;
 logic d_fence_valid,d_fence_ready,d_fence_done_valid,d_fence_done_ready;
 logic [31:0] d_fence_generation,d_fence_done_generation;
 logic dma_fault_valid;logic [7:0] dma_fault_kind;logic [3:0] dma_fault_client;
 logic [31:0] dma_fault_local_tag;logic [63:0] dma_fault_global_tag;
 logic [11:0] debug_beats,debug_descriptors;logic [31:0] debug_generation;
 assign c_req_valid={2'd0,mc_req_valid,8'd0,l_mc_req_valid};
 assign c_req_address={128'd0,mc_req_address,512'd0,l_mc_req_address};
 assign c_req_tag={64'd0,mc_req_tag,256'd0,l_mc_req_tag};
 assign c_req_channel={2'd0,mc_req_channel,8'd0,l_mc_req_channel};
 assign c_req_record_beats={10'd0,mc_req_record_beats,40'd0,l_mc_req_record_beats};
 assign c_rsp_ready={2'd0,mc_rsp_ready,8'd0,l_mc_rsp_ready};
 assign c_close_valid={2'd0,mc_close_valid,8'd0,l_mc_close_valid};
 assign c_close_tag_base={64'd0,mc_close_tag_base,256'd0,l_mc_close_tag_base};
 assign c_fence_valid={2'd0,mc_fence_req_valid,9'd0};
 assign c_fence_cookie={64'd0,mc_fence_req_cookie,288'd0};
 assign c_fence_epoch={18'd0,mc_fence_req_epoch,81'd0};
 assign c_fence_done_ready={2'd0,mc_fence_done_ready,9'd0};
 assign l_mc_req_ready=c_req_ready[0];assign l_mc_rsp_valid=c_rsp_valid[0];
 assign l_mc_rsp_tag=c_rsp_tag[0+:32];assign l_mc_rsp_data=c_rsp_data[0+:512];assign l_mc_close_ready=c_close_ready[0];
 assign mc_req_ready=c_req_ready[9];assign mc_rsp_valid=c_rsp_valid[9];
 assign mc_rsp_tag=c_rsp_tag[288+:32];assign mc_rsp_data=c_rsp_data[4608+:512];assign mc_close_ready=c_close_ready[9];
 assign mc_fence_req_ready=c_fence_ready[9];assign mc_fence_done_valid=c_fence_done_valid[9];
 assign mc_fence_done_cookie=c_fence_done_cookie[288+:32];assign mc_fence_done_epoch=c_fence_done_epoch[81+:9];
 mc_dma_fabric #(.SKIDS_PER_CHANNEL(3)) DMA(.clk,.reset,.c_req_valid,.c_req_ready,.c_req_address,.c_req_tag,.c_req_channel,.c_req_record_beats,
  .c_rsp_valid,.c_rsp_ready,.c_rsp_tag,.c_rsp_data,.c_close_valid,.c_close_ready,.c_close_tag_base,
  .c_cancel_valid(12'd0),.c_cancel_ready,.c_cancel_tag(384'd0),.c_cancel_ack_valid,.c_cancel_ack_ready(12'hfff),
  .c_cancel_ack_tag,.c_cancel_ack_rejected,.c_fence_valid,.c_fence_ready,.c_fence_cookie,.c_fence_epoch,
  .c_fence_done_valid,.c_fence_done_ready,.c_fence_done_cookie,.c_fence_done_epoch,
  .d_req_valid,.d_req_ready,.d_req_address,.d_req_tag,.d_rsp_valid,.d_rsp_ready,.d_rsp_tag,.d_rsp_data,
  .d_fence_valid,.d_fence_ready,.d_fence_generation,.d_fence_done_valid,.d_fence_done_ready,.d_fence_done_generation,
  .fault_valid(dma_fault_valid),.fault_ready(1'b1),.fault_kind(dma_fault_kind),.fault_client(dma_fault_client),
  .fault_local_tag(dma_fault_local_tag),.fault_global_tag(dma_fault_global_tag),.debug_beats,.debug_descriptors,.debug_generation);
 logic [63:0] backend_pending,planned_pending,response_claimed;
 logic [63:0] backend_tag[64];logic [511:0] backend_data[64];logic backend_channel[64];
 integer backend_due[64],backend_free[4],backend_response[4],backend_candidate[4];
 integer backend_requests,backend_returns,backend_purges;
 integer decode_case[4],decode_beat[4],decode_record[4],record_bytes_fixture[4];
 logic [511:0] planned_data[4];
 logic backend_fence_live;integer backend_fence_due;
 logic [31:0] backend_fence_generation;
 always_comb begin
  planned_pending=backend_pending;d_req_ready=0;
  for(integer lane=0;lane<4;lane=lane+1)begin
   backend_free[lane]=-1;
   for(integer entry=0;entry<64;entry=entry+1)if(!planned_pending[entry]&&backend_free[lane]<0)backend_free[lane]=entry;
   if(backend_free[lane]>=0&&!backend_fence_live&&cycle%7!=(seed+lane)%7)begin
    d_req_ready[lane]=1;if(d_req_valid[lane])planned_pending[backend_free[lane]]=1;
   end
  end
 end
 always_comb begin
  for(integer lane=0;lane<4;lane=lane+1)begin
   decode_case[lane]=0;decode_beat[lane]=0;decode_record[lane]=0;record_bytes_fixture[lane]=0;planned_data[lane]=0;
   if(d_req_address[lane*64+:64]>=64'h4000&&d_req_address[lane*64+:64]<64'h4400)begin
    decode_case[lane]=int'((d_req_address[lane*64+:64]-64'h4000)>>7);decode_beat[lane]=int'((d_req_address[lane*64+:64]>>6)&1);
    planned_data[lane]=decode_beat[lane]==0?scopes[decode_case[lane]][0+:512]:scopes[decode_case[lane]][512+:512];
   end else if(d_req_address[lane*64+:64]>=64'h100000&&d_req_address[lane*64+:64]<64'h180000)begin
    decode_case[lane]=int'((d_req_address[lane*64+:64]-64'h100000)>>16);
    decode_beat[lane]=int'((d_req_address[lane*64+:64]-(64'h100000+64'(decode_case[lane])*64'h10000))>>6);
    record_bytes_fixture[lane]=scopes[decode_case[lane]][664]?1152:1088;
    decode_record[lane]=(decode_beat[lane]*64)/record_bytes_fixture[lane];
    planned_data[lane]=DDR_memory[decode_case[lane]*128+decode_beat[lane]];
   end
  end
 end
 always_comb begin
  response_claimed=0;d_rsp_valid=0;d_rsp_tag=0;d_rsp_data=0;
  for(integer lane=0;lane<4;lane=lane+1)if(backend_response[lane]>=0)response_claimed[backend_response[lane]]=1;
  for(integer lane=0;lane<4;lane=lane+1)begin
   backend_candidate[lane]=-1;
   for(integer entry=0;entry<64;entry=entry+1)begin
    if(backend_pending[entry]&&!response_claimed[entry]&&int'(backend_channel[entry])==lane/2&&backend_due[entry]<=cycle&&backend_candidate[lane]<0)backend_candidate[lane]=entry;
   end
   if(backend_response[lane]>=0)begin
    d_rsp_valid[lane]=1;d_rsp_tag[lane*64+:64]=backend_tag[backend_response[lane]];
    d_rsp_data[lane*512+:512]=backend_data[backend_response[lane]];
   end else if(backend_candidate[lane]>=0)response_claimed[backend_candidate[lane]]=1;
  end
 end
 assign d_fence_ready=!backend_fence_live;
 assign d_fence_done_valid=backend_fence_live&&cycle>=backend_fence_due;
 assign d_fence_done_generation=backend_fence_generation;
 always @(posedge clk)begin
  if(reset)begin
   backend_pending<=0;backend_requests<=0;backend_returns<=0;backend_purges<=0;backend_fence_live<=0;backend_fence_due<=0;backend_fence_generation<=0;
   for(integer lane=0;lane<4;lane=lane+1)backend_response[lane]<=-1;
  end else begin
   for(integer lane=0;lane<4;lane=lane+1)begin
    if(d_req_valid[lane]&&d_req_ready[lane])begin
     backend_pending[backend_free[lane]]<=1;backend_tag[backend_free[lane]]<=d_req_tag[lane*64+:64];
     backend_channel[backend_free[lane]]<=1'(lane/2);backend_due[backend_free[lane]]<=cycle+7+(seed+lane)%5;
     if(d_req_address[lane*64+:64]>=64'h4000&&d_req_address[lane*64+:64]<64'h4400)begin
      assert(lane/2==0&&d_req_tag[lane*64+6+:4]==0)else $fatal(1,"scope global client/channel");
     end else begin
      assert(d_req_address[lane*64+:64]>=64'h100000&&d_req_address[lane*64+:64]<64'h180000&&d_req_tag[lane*64+6+:4]==9)else $fatal(1,"W global client/address");
      assert(lane/2==int'(((64'h100000+64'(decode_case[lane])*64'h10000+64'(decode_record[lane]*record_bytes_fixture[lane]))>>11)&1))else $fatal(1,"fixed whole-record stripe");
     end
     backend_data[backend_free[lane]]<=planned_data[lane];
     $fwrite(trace_file,"%0d,DDR_BACKEND_REQ,%0d,%0d,%0d,%0d\n",cycle,case_id,lane,d_req_tag[lane*64+:64],d_req_address[lane*64+:64]);
    end
    if(backend_response[lane]<0&&backend_candidate[lane]>=0)backend_response[lane]<=backend_candidate[lane];
    if(d_rsp_valid[lane]&&d_rsp_ready[lane])begin
     backend_pending[backend_response[lane]]<=0;backend_response[lane]<=-1;
     $fwrite(trace_file,"%0d,DDR_BACKEND_RSP,%0d,%0d,%0d,0\n",cycle,case_id,lane,d_rsp_tag[lane*64+:64]);
    end
   end
   backend_requests<=backend_requests+$countones(d_req_valid&d_req_ready);
   backend_returns<=backend_returns+$countones(d_rsp_valid&d_rsp_ready);
   if(d_fence_valid&&d_fence_ready)begin
    assert(backend_pending==0&&d_req_valid==0&&d_rsp_valid==0)else $fatal(1,"backend purge before drain");
    backend_fence_live<=1;backend_fence_generation<=d_fence_generation;backend_fence_due<=cycle+5+seed;backend_purges<=backend_purges+1;
    $fwrite(trace_file,"%0d,DDR_PURGE_REQ,%0d,%0d,0,0\n",cycle,case_id,d_fence_generation);
   end
   if(d_fence_done_valid&&d_fence_done_ready)begin backend_fence_live<=0;$fwrite(trace_file,"%0d,DDR_PURGE_DONE,%0d,%0d,0,0\n",cycle,case_id,d_fence_done_generation);end
   if(backend_purges==0||backend_fence_live)assert(c_req_ready==0)else $fatal(1,"client accepted before actual startup purge done");
   assert(!dma_fault_valid)else $fatal(1,"actual global DMA fault %0d client%0d local%h global%h",dma_fault_kind,dma_fault_client,dma_fault_local_tag,dma_fault_global_tag);
  end
 end
 wire unused_fabric_diagnostics=^{c_cancel_ready,c_cancel_ack_valid,c_cancel_ack_tag,c_cancel_ack_rejected,debug_generation,
  c_req_ready,c_rsp_valid,c_rsp_tag,c_rsp_data,c_close_ready,c_fence_ready,c_fence_done_valid,c_fence_done_cookie,c_fence_done_epoch};
 always @(posedge clk)begin
  if(reset)begin
   cycle<=0;accepted<=0;returned<=0;A_reads<=0;writes<=0;ACKs<=0;completed<=0;record_count<=0;
last_ACK_cycle<=0;last_complete_cycle<=0;
  end else begin
   cycle<=cycle+1;

   if(mc_req_valid&&mc_req_ready)begin accepted<=accepted+1;$fwrite(trace_file,"%0d,DDR_REQ,%0d,%0d,%0d,%0d\n",cycle,case_id,mc_req_tag,mc_req_address,mc_req_channel);end
   if(mc_rsp_valid&&mc_rsp_ready)begin returned<=returned+1;$fwrite(trace_file,"%0d,DDR_RSP,%0d,%0d,0,0\n",cycle,case_id,mc_rsp_tag);end
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

 logic  l_session_valid;
 logic  l_session_ready;
 logic [31:0] l_session_generation;
 logic [31:0] l_session_topology;
 logic  l_transport_drained;
 logic  l_cfg_valid;
 logic  l_cfg_ready;
 logic [1:0] l_cfg_op;
 logic [31:0] l_cfg_generation;
 logic [31:0] l_cfg_abi;
 logic [31:0] l_cfg_capacity;
 logic [31:0] l_cfg_crc;
 logic [15:0] l_cfg_bytes;
 logic [13:0] l_cfg_address;
 logic [127:0] l_cfg_data;
 logic  l_cfg_rsp_valid;
 logic  l_cfg_rsp_ready;
 logic [7:0] l_cfg_status;
 logic [31:0] l_cfg_actual_crc;
 logic  l_certified;
 logic  l_prepared;
 logic  l_rx_valid;
 logic  l_rx_ready;
 logic [127:0] l_rx_data;
 logic  l_rx_sop;
 logic  l_rx_eop;
 logic [7:0] l_rx_target;
 logic  l_tx_valid;
 logic  l_tx_ready;
 logic [127:0] l_tx_data;
 logic  l_tx_sop;
 logic  l_tx_eop;
 logic [7:0] l_tx_source;
 logic  l_mc_req_valid;
 logic  l_mc_req_ready;
 logic [63:0] l_mc_req_address;
 logic [31:0] l_mc_req_tag;
 logic  l_mc_req_channel;
 logic [4:0] l_mc_req_record_beats;
 logic  l_mc_close_valid;
 logic  l_mc_close_ready;
 logic [31:0] l_mc_close_tag_base;
 logic  l_mc_rsp_valid;
 logic  l_mc_rsp_ready;
 logic [31:0] l_mc_rsp_tag;
 logic [511:0] l_mc_rsp_data;
 logic [31:0] l_service_ticket;
 logic  l_idle;
 logic [31:0] l_protocol_fault_cycles;
 logic  l_pm_trace_valid;
 logic [13:0] l_pm_trace_address;
 logic [31:0] l_retired_instructions;
 logic  release_valid_i;
 logic [31:0] release_sequence_i;
 logic [31:0] release_epoch_i;
 logic  deploy_valid_i;
 logic [31:0] deploy_generation_i;
 logic  release_ready_o;
 logic  poison_o;
 logic  image_valid_o;
 logic  cfg_req_valid_i;
 logic [2:0] cfg_req_op_i;
 logic [31:0] cfg_req_generation_i;
 logic [13:0] cfg_req_address_i;
 logic [127:0] cfg_req_data_i;
 logic [15:0] cfg_req_total_bytes_i;
 logic [31:0] cfg_req_image_id_i;
 logic [31:0] cfg_req_topology_id_i;
 logic [31:0] cfg_req_abi_id_i;
 logic [31:0] cfg_req_capacity_id_i;
 logic  cfg_req_proof_i;
 logic  cfg_rsp_ready_i;
 logic  cfg_req_ready_o;
 logic  cfg_rsp_valid_o;
 logic [15:0] cfg_rsp_status_o;
 logic [127:0] cfg_rsp_data_o;
 logic [31:0] cfg_rsp_generation_o;
 logic [3:0] life_o;
 logic [3:0] seq_o;
 logic [31:0] trace_pc_o;
 logic  trace_retire_o;
 logic [7:0] trace_opcode_o;
 logic [1:0] trace_pm_owner_o;
 logic  trace_ireg_valid_o;
 logic  start_valid_i;
 logic  start_credit_i;
 logic [31:0] start_job_i;
 logic [31:0] start_epoch_i;
 logic [31:0] start_sequence_i;
 logic [31:0] start_generation_i;
 logic [287:0] local_image_ids_i;
 logic  start_ready_o;
 logic [31:0] frame_fault_count;
 logic  result_valid_o;
 logic  result_ready_i;
 logic [31:0] result_job_o;
 logic [31:0] result_epoch_o;
 logic [31:0] result_sequence_o;
 logic [15:0] result_status_o;
 logic [31:0] result_error_pc_o;
 logic [7:0] result_source_o;
 logic [31:0] result_child_error_pc_o;
 logic [31:0] result_failed_task_sequence_o;
 logic [31:0] result_confirmed_read_bytes_o;
 logic [31:0] result_confirmed_write_bytes_o;
 logic  result_counter_overflow_o;
 logic  result_saturated_o;
 logic [15:0] trace_live_tokens_o;
 logic [8:0] trace_block_active_o;
 logic [8:0] trace_terminal_full_o;
 logic [8:0] trace_READY_full_o;
 logic  trace_aborting_o;
 logic  recover_valid_i;
 logic  recover_ready_o;
 logic [31:0] protocol_fault_count_o;
 logic m_tx_valid,m_tx_ready,m_tx_credit,source_prepared;
 logic [127:0] kernel_image[22],mother_image[25];
 logic [31:0] kernel_crc;
 integer MC_calls,MC_returns,MC_PM_reads,LC_PM_reads,scope_returns;
 assign l_rx_valid=m_tx_valid&&source_prepared;
 assign m_tx_ready=l_rx_ready&&source_prepared;
 lc_native_scope_controller local_control(
  .clk(clk),
  .reset(reset),
  .session_valid(l_session_valid),
  .session_ready(l_session_ready),
  .session_generation(l_session_generation),
  .session_topology(l_session_topology),
  .transport_drained(l_transport_drained),
  .cfg_valid(l_cfg_valid),
  .cfg_ready(l_cfg_ready),
  .cfg_op(l_cfg_op),
  .cfg_generation(l_cfg_generation),
  .cfg_abi(l_cfg_abi),
  .cfg_capacity(l_cfg_capacity),
  .cfg_crc(l_cfg_crc),
  .cfg_bytes(l_cfg_bytes),
  .cfg_address(l_cfg_address),
  .cfg_data(l_cfg_data),
  .cfg_rsp_valid(l_cfg_rsp_valid),
  .cfg_rsp_ready(l_cfg_rsp_ready),
  .cfg_status(l_cfg_status),
  .cfg_actual_crc(l_cfg_actual_crc),
  .certified(l_certified),
  .prepared(l_prepared),
  .rx_valid(l_rx_valid),
  .rx_ready(l_rx_ready),
  .rx_data(l_rx_data),
  .rx_sop(l_rx_sop),
  .rx_eop(l_rx_eop),
  .rx_target(l_rx_target),
  .tx_valid(l_tx_valid),
  .tx_ready(l_tx_ready),
  .tx_data(l_tx_data),
  .tx_sop(l_tx_sop),
  .tx_eop(l_tx_eop),
  .tx_source(l_tx_source),
  .mc_req_valid(l_mc_req_valid),
  .mc_req_ready(l_mc_req_ready),
  .mc_req_address(l_mc_req_address),
  .mc_req_tag(l_mc_req_tag),
  .mc_req_channel(l_mc_req_channel),
  .mc_req_record_beats(l_mc_req_record_beats),
  .mc_close_valid(l_mc_close_valid),
  .mc_close_ready(l_mc_close_ready),
  .mc_close_tag_base(l_mc_close_tag_base),
  .mc_rsp_valid(l_mc_rsp_valid),
  .mc_rsp_ready(l_mc_rsp_ready),
  .mc_rsp_tag(l_mc_rsp_tag),
  .mc_rsp_data(l_mc_rsp_data),
  .service_valid(service_valid),
  .service_ready(service_ready&&scope_ready),
  .service_owner(scope_owner),
  .service_ticket(l_service_ticket),
  .service_descriptor(scope_data),
  .service_cancel_valid(scope_cancel),
  .service_cancel_ready(cancel_ready),
  .service_done_valid(service_done_valid),
  .service_done_ready(service_done_ready),
  .service_done_owner(service_done_owner),
  .service_done_ticket(service_done_ticket),
  .service_done_status(service_done_status),
  .service_done_read_bytes(service_done_read_bytes),
  .service_done_write_bytes(service_done_write_bytes),
  .idle(l_idle),
  .protocol_fault_cycles(l_protocol_fault_cycles),
  .pm_trace_valid(l_pm_trace_valid),
  .pm_trace_address(l_pm_trace_address),
  .retired_instructions(l_retired_instructions)
 );
 mother_control_native64_transport128 mother(
  .clk_i(clk),
  .rst_ni(!reset),
  .release_valid_i(release_valid_i),
  .release_sequence_i(release_sequence_i),
  .release_epoch_i(release_epoch_i),
  .deploy_valid_i(deploy_valid_i),
  .deploy_generation_i(deploy_generation_i),
  .release_ready_o(release_ready_o),
  .poison_o(poison_o),
  .image_valid_o(image_valid_o),
  .cfg_req_valid_i(cfg_req_valid_i),
  .cfg_req_op_i(cfg_req_op_i),
  .cfg_req_generation_i(cfg_req_generation_i),
  .cfg_req_address_i(cfg_req_address_i),
  .cfg_req_data_i(cfg_req_data_i),
  .cfg_req_total_bytes_i(cfg_req_total_bytes_i),
  .cfg_req_image_id_i(cfg_req_image_id_i),
  .cfg_req_topology_id_i(cfg_req_topology_id_i),
  .cfg_req_abi_id_i(cfg_req_abi_id_i),
  .cfg_req_capacity_id_i(cfg_req_capacity_id_i),
  .cfg_req_proof_i(cfg_req_proof_i),
  .cfg_rsp_ready_i(cfg_rsp_ready_i),
  .cfg_req_ready_o(cfg_req_ready_o),
  .cfg_rsp_valid_o(cfg_rsp_valid_o),
  .cfg_rsp_status_o(cfg_rsp_status_o),
  .cfg_rsp_data_o(cfg_rsp_data_o),
  .cfg_rsp_generation_o(cfg_rsp_generation_o),
  .life_o(life_o),
  .seq_o(seq_o),
  .trace_pc_o(trace_pc_o),
  .trace_retire_o(trace_retire_o),
  .trace_opcode_o(trace_opcode_o),
  .trace_pm_owner_o(trace_pm_owner_o),
  .trace_ireg_valid_o(trace_ireg_valid_o),
  .start_valid_i(start_valid_i),
  .start_credit_i(start_credit_i),
  .start_job_i(start_job_i),
  .start_epoch_i(start_epoch_i),
  .start_sequence_i(start_sequence_i),
  .start_generation_i(start_generation_i),
  .local_image_ids_i(local_image_ids_i),
  .local_enabled_i({8'd0,l_prepared}),
  .start_ready_o(start_ready_o),
  .tx_valid(m_tx_valid),
  .tx_ready(m_tx_ready),
  .tx_data(l_rx_data),
  .tx_target(l_rx_target),
  .tx_sop(l_rx_sop),
  .tx_eop(l_rx_eop),
  .tx_credit(m_tx_credit),
  .rx_valid(l_tx_valid),
  .rx_ready(l_tx_ready),
  .rx_data(l_tx_data),
  .rx_source(l_tx_source),
  .rx_sop(l_tx_sop),
  .rx_eop(l_tx_eop),
  .transport_drained_i(l_idle&&!m_tx_valid&&!l_tx_valid),
  .frame_fault_count(frame_fault_count),
  .result_valid_o(result_valid_o),
  .result_ready_i(result_ready_i),
  .result_job_o(result_job_o),
  .result_epoch_o(result_epoch_o),
  .result_sequence_o(result_sequence_o),
  .result_status_o(result_status_o),
  .result_error_pc_o(result_error_pc_o),
  .result_source_o(result_source_o),
  .result_child_error_pc_o(result_child_error_pc_o),
  .result_failed_task_sequence_o(result_failed_task_sequence_o),
  .result_confirmed_read_bytes_o(result_confirmed_read_bytes_o),
  .result_confirmed_write_bytes_o(result_confirmed_write_bytes_o),
  .result_counter_overflow_o(result_counter_overflow_o),
  .result_saturated_o(result_saturated_o),
  .trace_live_tokens_o(trace_live_tokens_o),
  .trace_block_active_o(trace_block_active_o),
  .trace_terminal_full_o(trace_terminal_full_o),
  .trace_READY_full_o(trace_READY_full_o),
  .trace_aborting_o(trace_aborting_o),
  .recover_valid_i(recover_valid_i),
  .recover_ready_o(recover_ready_o),
  .protocol_fault_count_o(protocol_fault_count_o)
 );
 always @(posedge clk)begin
  if(reset)begin
   MC_calls<=0;MC_returns<=0;MC_PM_reads<=0;LC_PM_reads<=0;scope_returns<=0;
  end else begin
   if(l_rx_valid&&l_rx_ready&&l_rx_sop)begin
    assert(l_rx_data[23:16]==0&&l_rx_target==0)else $fatal(1,"unexpected task/cancel");MC_calls<=MC_calls+1;
    $fwrite(trace_file,"%0d,MC_CALL,%0d,%0d,0,0\n",cycle,case_id,l_rx_data[127:96]);
   end
   if(l_tx_valid&&l_tx_ready&&l_tx_eop)begin
    assert(l_retired_instructions==3)else $fatal(1,"actual three-instruction LC kernel");
    MC_returns<=MC_returns+1;$fwrite(trace_file,"%0d,LC_RETURN,%0d,0,0,0\n",cycle,case_id);
   end
   if(l_pm_trace_valid)begin LC_PM_reads<=LC_PM_reads+1;$fwrite(trace_file,"%0d,LC_PM,%0d,%0d,0,0\n",cycle,case_id,l_pm_trace_address);end
   if(mother.mother.pm_req_valid_o&&mother.mother.pm_req_ready_i&&!mother.mother.pm_req_write_o)begin
    MC_PM_reads<=MC_PM_reads+1;$fwrite(trace_file,"%0d,MC_PM,%0d,%0d,0,0\n",cycle,case_id,mother.mother.pm_req_address_o);
   end

   if(l_mc_rsp_valid&&l_mc_rsp_ready)begin scope_returns<=scope_returns+1;$fwrite(trace_file,"%0d,SCOPE_RSP,%0d,%0d,0,0\n",cycle,case_id,l_mc_rsp_tag);end
   assert(l_protocol_fault_cycles==0&&frame_fault_count==0&&protocol_fault_count_o==0)else $fatal(1,"actual MC LC fault");
  end
 end
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
 task automatic lc_cfg_send(input logic[1:0] op);
  l_cfg_op=op;l_cfg_valid=1;do @(posedge clk);while(!l_cfg_ready);@(negedge clk);l_cfg_valid=0;
  while(!l_cfg_rsp_valid)@(negedge clk);assert(l_cfg_status==0)else $fatal(1,"LCboot status");
  l_cfg_rsp_ready=1;pause();l_cfg_rsp_ready=0;
 endtask
 task automatic mother_config(input logic[2:0] op,input logic[13:0] address_word=0,input logic[127:0] value=0);
  cfg_req_op_i=op;cfg_req_address_i=address_word;cfg_req_data_i=value;cfg_req_valid_i=1;
  do @(posedge clk);while(!cfg_req_ready_o);@(negedge clk);cfg_req_valid_i=0;
  while(!cfg_rsp_valid_o)@(negedge clk);assert(cfg_rsp_status_o==0)else $fatal(1,"MCboot status %0d",cfg_rsp_status_o);
  if(op==2)assert(cfg_rsp_data_o==mother_image[int'(address_word)>>4])else $fatal(1,"actual MC PM readback");
  cfg_rsp_ready_i=1;pause();cfg_rsp_ready_i=0;
 endtask
 wire unused_program_outputs=^{l_session_ready,l_cfg_ready,l_cfg_rsp_valid,l_cfg_status,l_cfg_actual_crc,l_certified,l_prepared,l_rx_ready,l_tx_valid,l_tx_data,l_tx_sop,l_tx_eop,l_tx_source,l_mc_req_valid,l_mc_req_address,l_mc_req_tag,l_mc_req_channel,l_mc_req_record_beats,l_mc_close_valid,l_mc_close_tag_base,l_mc_rsp_ready,l_service_ticket,l_idle,l_protocol_fault_cycles,l_pm_trace_valid,l_pm_trace_address,l_retired_instructions,release_ready_o,poison_o,image_valid_o,cfg_req_ready_o,cfg_rsp_valid_o,cfg_rsp_status_o,cfg_rsp_data_o,cfg_rsp_generation_o,life_o,seq_o,trace_pc_o,trace_retire_o,trace_opcode_o,trace_pm_owner_o,trace_ireg_valid_o,start_ready_o,frame_fault_count,result_valid_o,result_job_o,result_epoch_o,result_sequence_o,result_status_o,result_error_pc_o,result_source_o,result_child_error_pc_o,result_failed_task_sequence_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,result_counter_overflow_o,result_saturated_o,trace_live_tokens_o,trace_block_active_o,trace_terminal_full_o,trace_READY_full_o,trace_aborting_o,recover_ready_o,protocol_fault_count_o,m_tx_credit};

 initial begin
  reset=1;
  a_load_proof_ready=0;allow_native_A=0;load_proofs=0;poison_writes=0;stale_prefix_checks=0;
  reset=1;
  directory_cfg=0;q_cmd=0;q_take=0;h_start=0;h_take=0;lease_start=0;release_window=0;copy_start=0;copy_take=0;tile_generation=0;tile_k=0;tile_session=0;tile_ticket=0;proof_accepted=0;uh_valid=0;uh_write=1;uh_rsp_ready=0;uh_address=0;uh_data=0;real_copy_ACKs=0;real_copy_reads=0;real_headers=0;real_quantizations=0;

  host_mode=1;host_valid=0;host_write=1;host_address=0;host_data=0;host_response_ready=0;
  allow_request=1;allow_ACK=1;allow_A_response=1;case_id=0;seed=1;
  if($value$plusargs("SEED=%d",seed))begin end
  vectors="results/p-vectors";if($value$plusargs("VECTORS=%s",vectors))begin end
  trace_path="p-executor.csv";if($value$plusargs("TRACE=%s",trace_path))begin end
  $readmemh({vectors,"/scopes.mem"},scopes);$readmemh({vectors,"/A.mem"},A_memory);
  $readmemh({vectors,"/DDR.mem"},DDR_memory);$readmemh({vectors,"/expected.mem"},expect_memory);
  trace_file=$fopen(trace_path,"w");assert(trace_file!=0);$fwrite(trace_file,"cycle,event,case,identity,detail,value\n");

  l_session_valid=0;
  l_session_generation=0;
  l_session_topology=0;
  l_transport_drained=0;
  l_cfg_valid=0;
  l_cfg_op=0;
  l_cfg_generation=0;
  l_cfg_abi=0;
  l_cfg_capacity=0;
  l_cfg_crc=0;
  l_cfg_bytes=0;
  l_cfg_address=0;
  l_cfg_data=0;
  l_cfg_rsp_ready=0;
  release_valid_i=0;
  release_sequence_i=0;
  release_epoch_i=0;
  deploy_valid_i=0;
  deploy_generation_i=0;
  cfg_req_valid_i=0;
  cfg_req_op_i=0;
  cfg_req_generation_i=0;
  cfg_req_address_i=0;
  cfg_req_data_i=0;
  cfg_req_total_bytes_i=0;
  cfg_req_image_id_i=0;
  cfg_req_topology_id_i=0;
  cfg_req_abi_id_i=0;
  cfg_req_capacity_id_i=0;
  cfg_req_proof_i=0;
  cfg_rsp_ready_i=0;
  start_valid_i=0;
  start_credit_i=0;
  start_job_i=0;
  start_epoch_i=0;
  start_sequence_i=0;
  start_generation_i=0;
  local_image_ids_i=0;
  result_ready_i=0;
  recover_valid_i=0;
  source_prepared=0;
  l_transport_drained=1;l_session_topology=25001;
  l_cfg_generation=1;l_cfg_abi=32'h02500002;l_cfg_capacity=32'h02510001;l_cfg_bytes=352;
  $readmemh({vectors,"/kernel.mem"},kernel_image);$readmemh({vectors,"/mother.mem"},mother_image);
  if($value$plusargs("CRC=%h",kernel_crc))begin end else $fatal(1,"kernel CRC missing");
  pause(4);reset=0;pause();
  lc_cfg_send(0);
  for(integer wi=0;wi<22;wi=wi+1)begin l_cfg_address=14'(wi*16);l_cfg_data=kernel_image[wi];lc_cfg_send(1);end
  l_cfg_crc=kernel_crc;lc_cfg_send(2);assert(l_certified);
  l_session_generation=1;l_session_valid=1;do @(posedge clk);while(!l_session_ready);@(negedge clk);l_session_valid=0;
  release_valid_i=1;release_sequence_i=1;release_epoch_i=1;
  do @(posedge clk);while(!release_ready_o);@(negedge clk);release_valid_i=0;
  cfg_req_generation_i=1;cfg_req_total_bytes_i=400;cfg_req_image_id_i=900;cfg_req_topology_id_i=25001;
  cfg_req_abi_id_i=32'h02500002;cfg_req_capacity_id_i=32'h02590003;cfg_req_proof_i=1;
  mother_config(0);
  for(integer wi=0;wi<25;wi=wi+1)mother_config(1,14'(wi*16),mother_image[wi]);
  for(integer wi=0;wi<25;wi=wi+1)mother_config(2,14'(wi*16));
  mother_config(3);mother_config(4);local_image_ids_i[31:0]=25001;
  deploy_generation_i=1;deploy_valid_i=1;start_credit_i=1;while(life_o!=5)@(negedge clk);
  start_job_i=7;start_epoch_i=8;start_sequence_i=1;start_generation_i=1;start_valid_i=1;
  do @(posedge clk);while(!start_ready_o);@(negedge clk);start_valid_i=0;

  for(integer ci=0;ci<8;ci=ci+1)begin
   case_id=ci;
   directory_cfg=1;do @(posedge clk);while(!directory_ready);@(negedge clk);directory_cfg=0;
   host_mode=0;pause();start_cycle=32'(cycle);source_prepared=1;
   fork
    begin
     while(!scope_valid)@(negedge clk);
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
     while(MC_returns<ci+1)begin
      pause(2+(seed%3));allow_ACK=0;allow_A_response=0;pause(1);allow_ACK=1;allow_A_response=1;
     end
    end
    begin
     while(MC_returns<ci+1)@(negedge clk);
     assert(service_done_owner==scope_owner&&service_done_ticket==scope_owner[31:0]&&service_done_status==0)else $fatal(1,"true range terminal status %0d",service_done_status);
    end
   join
   source_prepared=0;while(MC_returns<ci+1)@(negedge clk);pause(2);
   assert(quiescent&&A_live==0&&command_occupied==0&&result_occupied==0&&backend_pending==0&&debug_beats==0&&debug_descriptors==0)else $fatal(1,"real owner leak");
   for(integer outword=0;outword<int'(scope_data[592+:5])*2;outword=outword+1)host_word(0,128+outword,expect_memory[ci*4+outword]);
   $fwrite(trace_file,"%0d,CASE_DONE,%0d,%0d,%0d,%0d\n",cycle,ci,cycle-int'(start_cycle),A_reads,ACKs);
  end
  assert(load_proofs==12&&poison_writes==192&&stale_prefix_checks==60&&real_copy_ACKs==192&&real_copy_reads==192&&real_headers==24&&real_quantizations==12)else $fatal(1,"actual streamed program proof accounting");
  assert(accepted==returned&&ACKs==24&&writes==24&&completed==18&&record_count==18&&A_reads==192&&directory_faults==0)else $fatal(1,"accounting req%0d rsp%0d ACK%0d writes%0d completed%0d records%0d Areads%0d",accepted,returned,ACKs,writes,completed,record_count,A_reads);
  while(!result_valid_o)@(negedge clk);
  assert(result_status_o==0&&result_confirmed_read_bytes_o==21184&&result_confirmed_write_bytes_o==384&&MC_calls==8&&MC_returns==8&&LC_PM_reads==184&&scope_returns==16&&l_retired_instructions==3)else $fatal(1,"actual MC LC accounting status%0d reads%0d writes%0d CALL%0d return%0d LCpm%0d scope%0d instr%0d",result_status_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,MC_calls,MC_returns,LC_PM_reads,scope_returns,l_retired_instructions);
  assert(backend_requests==331&&backend_returns==331&&backend_purges==1&&debug_beats==0&&debug_descriptors==0)else $fatal(1,"global real backend conservation");
  result_ready_i=1;pause();result_ready_i=0;
  $display("PASS p_stream_program seed=%0d cases=8 cycles=%0d requests=%0d returns=%0d S128ACK=%0d records=%0d Areads=%0d",seed,cycle,accepted,returned,ACKs,completed,A_reads);
  $fclose(trace_file);$finish;
 end
 initial begin #2000000;$fatal(1,"real P timeout state=%0d case=%0d pending=%h",exec.state,case_id,backend_pending);end
 wire unused_diagnostics=^{service_done_read_bytes,service_done_write_bytes,decoded_key,rf0,rf1,out_version,bias0,bias1,
  inS,outS0,outS1,scratchS,snapshotS,record_bytes,cancel_ready,mc_close_valid,mc_close_tag_base,
  mc_fence_req_valid,mc_fence_req_cookie,mc_fence_req_epoch,mc_fence_done_ready,owners,c_response_tag[31:1],last_complete_cycle};
endmodule
