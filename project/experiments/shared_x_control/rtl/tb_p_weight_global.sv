`timescale 1ns/1ps
// Real serialized M + real S bank fixture, functional10ns not300MHzSTA.
module tb_p_weight_global #(parameter logic [2:0] MODE=3'd6, parameter int GROUPS=8, parameter logic [31:0] SESSION_LIMIT=32'hffffffe0);
 localparam bit FOUR_BANK=(MODE==3'd6), WEIGHT_PREFILL=(MODE==3'd5||FOUR_BANK), RESIDENT=(MODE==3'd1), SOURCE_REUSE=(MODE==3'd2||MODE==3'd4||WEIGHT_PREFILL), COMBINED=(MODE==3'd3), LAZY_SOURCE=(MODE==3'd4||WEIGHT_PREFILL), HAS_RESIDENT=RESIDENT||COMBINED;
 wire source_tile_reuse=SOURCE_REUSE&&(!LAZY_SOURCE||case_id!=0);
 wire use_resident=HAS_RESIDENT&&scope_data[48+:16]==16'd1;
 logic source_cfg,source_cfg_ready,source_cfg_bad,source_publish_ready,source_publish_bad,source_scale_valid,source_fill_done;
 logic [5:0] source_shift;
 logic [31:0] source_rejections;
 wire [9:0] source_base=10'd256+(SOURCE_REUSE?{2'd0,tile_k[10:7],4'd0}:10'd0);
 if(SOURCE_REUSE)begin:source_directory
  a_scale_directory32 source_X_directory(.clk,.reset,.cfg_valid(source_cfg),.cfg_ready(source_cfg_ready),
    .cfg_key(scope_data[128+:128]),.cfg_first_kk(16'd0),.cfg_tiles(6'd16),.cfg_stride3(1'b0),
    .storage_released(!source_fill_done&&rx_idle&&copy_idle&&uowners==0),.leases_drained(quiescent&&!resident_scope_live),
    .cfg_rejected(source_cfg_bad),.publish_valid(q_done&&q_take),.publish_ready(source_publish_ready),
    .publish_key(q_done_key),.publish_kk(q_done_k),.publish_shift(q_shift),.publish_written_mask(q_written_mask),
    .publish_error(q_error||q_cancelled),.publish_rejected(source_publish_bad),.lookup_key(scope_data[128+:128]),
    .lookup_kk(tile_k),.lookup_valid(source_scale_valid),.lookup_shift(source_shift),.rejected_publications(source_rejections));
 end else begin:no_source_directory
  assign source_cfg_ready=0;assign source_cfg_bad=0;assign source_publish_ready=0;assign source_publish_bad=0;
  assign source_scale_valid=0;assign source_shift=0;assign source_rejections=0;
 end
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
 integer load_proofs;
 logic resident_sealed;
 logic [127:0] resident_key;
 logic [9:0] resident_base;
 wire [9:0] copy_destination=use_resident?(10'd256+{2'd0,tile_k[10:7],4'd0}):10'd0;
 logic resident_publish,resident_scope_live,bad_copy_ticket;
 if(COMBINED)begin:dual_provider
   p_native_a16_dual_profile exec(.*);
   assign exec_contexts=exec.contexts_live;
   assign exec_detached=exec.pair_detached;
   assign exec_state=exec.state;
 end else if(RESIDENT)begin:resident_provider
   p_native_resident_x_candidate exec(.*);
   assign exec_contexts=exec.contexts_live;
   assign exec_detached=exec.pair_detached;
   assign exec_state=exec.state;
 end else if(WEIGHT_PREFILL)begin:prefill_provider
   p_native_weight_prefill #(.FOUR_BANK_LOOKAHEAD(FOUR_BANK),.SESSION_LIMIT(SESSION_LIMIT)) exec(.*);
   assign exec_contexts=exec.contexts_live;
   assign exec_detached=exec.pair_detached;
   assign exec_state=exec.state;
 end else begin:stream_provider
   p_native_stream_m2_bounded #(.SESSION_LIMIT(SESSION_LIMIT)) exec(.*);
   assign exec_contexts=exec.contexts_live;
   assign exec_detached=exec.pair_detached;
   assign exec_state=exec.state;
 end
 if(HAS_RESIDENT)begin:resident_directory
   logic dir_lookup_valid;
   logic [5:0] dir_shift;
   resident_x16_directory dir(
    .clk,.reset,.cfg_valid(directory_cfg),.cfg_ready(directory_ready),.cfg_key(scope_data[128+:128]),.cfg_base(10'd256),
    .storage_and_consumers_drained(rx_idle&&copy_idle&&owners==0&&quiescent&&!resident_scope_live),
    .cfg_error(directory_bad),.publish_valid(resident_publish),.publish_ready(directory_publish_ready),.publish_error(directory_pub_bad),
    .header_key(meta_key),.copy_key,.header_k(meta_k),.copy_k,.header_gen(meta_gen),.copy_gen,
    .header_session(meta_session),.copy_session,.header_ticket(meta_ticket),.copy_ticket(copy_ticket^{31'd0,bad_copy_ticket}),
    .header_shift(meta_shift),.copy_base(copy_destination),.copy_ack_prefix(copy_committed_prefix),.copy_done,.copy_error,
    .resident_sealed,.resident_key,.resident_base,.lookup_key(scale_lookup_key),.lookup_k(scale_lookup_kk),
    .lookup_valid(dir_lookup_valid),.lookup_shift(dir_shift));
   assign scale_lookup_valid=use_resident?dir_lookup_valid:(data_enabled&&meta_key==scale_lookup_key&&meta_k==scale_lookup_kk);
   assign scale_lookup_shift=use_resident?dir_shift:meta_shift;
 end else begin:no_resident_directory
   assign directory_ready=1;assign directory_publish_ready=1;assign directory_bad=0;assign directory_pub_bad=0;
   assign scale_lookup_valid=data_enabled&&meta_key==scale_lookup_key&&meta_k==scale_lookup_kk;
   assign scale_lookup_shift=meta_shift;
   assign resident_sealed=0;assign resident_key=0;assign resident_base=0;
 end
 logic [15:0] exec_contexts;
 logic [4:0] exec_state;
 logic exec_detached;
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
 p_scope_range_service #(.NATIVE_STREAM_A16(!HAS_RESIDENT),.NATIVE_RESIDENT_X_K2048(RESIDENT),.NATIVE_DUAL_A16(COMBINED)) ranges(
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
 logic directory_cfg,directory_ready,directory_publish_ready,directory_bad,directory_pub_bad;
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
  .cmd_source(10'd32),.cmd_destination(source_base),.cmd_shift_known(1'b0),.cmd_shift(6'd0),
  .cancel_valid(1'b0),.cancel_key(128'd0),.s_valid(q_valid),.s_ready(q_s_ready),.s_write(q_write),
  .s_address(q_address),.s_data(q_data),.s_tag(q_tag),.rsp_valid(q_rsp_valid),.rsp_ready(q_rsp_ready),
  .rsp_tag(q_rsp_tag),.rsp_data(q_rsp_data),.rsp_error(1'b0),.done_valid(q_done),.done_ready(q_take),
  .done_key(q_done_key),.done_kk(q_done_k),.done_error(q_error),.done_cancelled(q_cancelled),
  .done_words(q_done_words),.done_written_mask(q_written_mask),.done_shift(q_shift),.rejected_responses(q_rejected));
 logic h_start,h_start_ready,h_done,h_take,h_error,h_quiescent;
 logic [2:0] h_valid,h_ready,h_ack_valid,h_ack_ready,h_ack_error;
 logic [95:0] h_tag,h_ack_tag;logic [383:0] h_data;logic [31:0] h_rejected;
 copy_scale_header_tx tx_header(.clk,.reset,.halt(1'b0),.start_valid(h_start),.start_ready(h_start_ready),
   .start_key(source_tile_reuse?scope_data[128+:128]:q_done_key),.start_generation(tile_generation),
  .start_kk(source_tile_reuse?tile_k:q_done_k),.start_written_mask(source_tile_reuse?(source_scale_valid?16'hffff:16'd0):q_written_mask),
  .start_session(tile_session),.start_ticket(tile_ticket),.start_shift(source_tile_reuse?source_shift:q_shift),.start_mask(3'b001),
  .start_producer_error(source_tile_reuse?!source_scale_valid:(q_error||q_cancelled)),.frame_valid(h_valid),.frame_ready(h_ready),.frame_tag(h_tag),.frame_data(h_data),
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
 assign meta_ready=1;
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
  .start_U_base(source_base),.start_P_bases({20'd0,copy_destination}),.start_words(11'd16),.start_P_mask(3'b001),.destination_window_released(data_enabled),
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
  if(ar_valid&&ar_ready)begin
   if(use_resident)begin assert(resident_sealed&&scale_lookup_valid&&ar_address[9:4]==6'd16+{2'd0,scale_lookup_kk[10:7]})
       else $fatal(1,"resident read outside true committed tile");end
   else begin assert(copy_identity&&copy_gen==stream_window_generation&&copy_k==scale_lookup_kk&&
     {1'b0,ar_address}<copy_prefix[0+:11])else $fatal(1,"stream read before true matching COPY ACK");end
  end
  if(HAS_RESIDENT&&req_valid&&req_ready&&req_write&&req_address>=256&&req_address<512)
    assert(!resident_sealed&&cp_valid[0]&&cp_ready[0]&&req_address[9:4]==copy_destination[9:4])
      else $fatal(1,"unexpected overwrite of resident input");
  if(SOURCE_REUSE&&source_fill_done)begin
   assert(source_rejections==0&&!source_cfg_ready);
   if(unv&&unready&&unw&&una>=256&&una<512)$fatal(1,"source resident window overwritten");
  end
  assert(copy_faults==0&&rx_rejected==0&&h_rejected==0&&q_rejected==0&&!lease_error)else $fatal(1,"real COPY/header/quantizer fault");
 end
 wire unused_copy_diagnostics=^{cp_valid[2:1],cp_address,cp_data,cp_tag,cp_ack_ready[2:1],h_ready,h_valid[2:1],h_ack_ready[2:1],h_tag[95:32],h_data[383:128],h_quiescent,copy_words,copy_prefix[32:11],uowners,und,unrd,meta_key,ut[31:0]};
 logic [1023:0] scopes[0:1],resident_scopes[0:1];logic [127:0] A_memory[0:255],expect_memory[0:8*GROUPS-1];
 logic [511:0] DDR_memory[0:1088*GROUPS-1];
 integer boot_cycles,quant_cycles,header_cycles,copy_cycles,load_wait_cycles,scope_cycles,peak_contexts,pair_detaches;
 integer stage_start,fill_start,fill_cycles,scope0_cycles,scope1_cycles,service_terminal_cycle;
 logic old_detached;
 integer cycle,seed,case_id,trace_file,accepted,returned,A_reads,writes,ACKs,completed,record_count;
 integer last_ACK_cycle,last_complete_cycle,peak_weight_banks,peak_weight_inflight,weight_inflight;
 integer native_execs,drain_commands,cancel_error_count;
 bit cancel_test,cancel_phase;
 always_comb begin
   weight_inflight=0;
   for(integer b=0;b<4;b=b+1)
     if(M.table_valid[b]&&M.table_issued[b]!=M.table_received[b])weight_inflight=weight_inflight+1;
 end
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
 assign c_req_valid={2'd0,mc_req_valid,9'd0};
 assign c_req_address={128'd0,mc_req_address,576'd0};
 assign c_req_tag={64'd0,mc_req_tag,288'd0};
 assign c_req_channel={2'd0,mc_req_channel,9'd0};
 assign c_req_record_beats={10'd0,mc_req_record_beats,45'd0};
 assign c_rsp_ready={2'd0,mc_rsp_ready,9'd0};
 assign c_close_valid={2'd0,mc_close_valid,9'd0};
 assign c_close_tag_base={64'd0,mc_close_tag_base,288'd0};
 assign c_fence_valid={2'd0,mc_fence_req_valid,9'd0};
 assign c_fence_cookie={64'd0,mc_fence_req_cookie,288'd0};
 assign c_fence_epoch={18'd0,mc_fence_req_epoch,81'd0};
 assign c_fence_done_ready={2'd0,mc_fence_done_ready,9'd0};
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
   planned_data[lane]=0;
   if(d_req_address[lane*64+20+:3]>=1&&d_req_address[lane*64+20+:3]<=4&&d_req_address[lane*64+:20]<20'(GROUPS*17408))
     planned_data[lane]=DDR_memory[(int'(d_req_address[lane*64+20+:3])-1)*272*GROUPS+int'(d_req_address[lane*64+6+:14])];
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
     assert(d_req_address[lane*64+23+:41]==0&&d_req_address[lane*64+20+:3]>=1&&d_req_address[lane*64+20+:3]<=4&&
       d_req_address[lane*64+:20]<20'(GROUPS*17408)&&d_req_address[lane*64+:6]==0&&d_req_tag[lane*64+6+:4]==9)
       else $fatal(1,"W global client/address");
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
    assert(backend_pending==0&&d_req_valid==0&&d_rsp_valid==0&&M.table_valid==0&&command_occupied==0&&result_occupied==0)else $fatal(1,"backend purge before drain");
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
   peak_contexts<=0;pair_detaches<=0;old_detached<=0;
   cycle<=0;accepted<=0;returned<=0;A_reads<=0;writes<=0;ACKs<=0;completed<=0;record_count<=0;
   last_ACK_cycle<=0;last_complete_cycle<=0;peak_weight_banks<=0;peak_weight_inflight<=0;
   native_execs<=0;drain_commands<=0;cancel_error_count<=0;
  end else begin
   cycle<=cycle+1;
   old_detached<=exec_detached;
   if(exec_detached&&!old_detached)pair_detaches<=pair_detaches+1;
   if($countones(exec_contexts)>peak_contexts)peak_contexts<=$countones(exec_contexts);
   if($countones(M.table_valid)>peak_weight_banks)peak_weight_banks<=$countones(M.table_valid);
   if(weight_inflight>peak_weight_inflight)peak_weight_inflight<=weight_inflight;
   if(M.n_alloc_valid&&M.n_alloc_ready)$fwrite(trace_file,"%0d,W_ALLOC,%0d,%0d,%0d,0\n",cycle,case_id,M.n_alloc_record,M.handle);
   if(M.n_fill_ack_valid&&M.n_fill_ack_ready)$fwrite(trace_file,"%0d,W_FILL,%0d,%0d,%0d,%0d\n",cycle,case_id,M.n_fill_ack_record,M.n_fill_ack_bank,M.n_fill_ack_generation);
   if(M.n_exec_valid&&M.n_exec_ready)begin native_execs<=native_execs+1;
    $fwrite(trace_file,"%0d,M_EXEC,%0d,%0d,%0d,%0d\n",cycle,case_id,M.n_exec_record,M.n_exec_context,M.n_exec_k_offset);end
   if(lc_valid&&lc_ready&&lc_sop&&lc_eop&&lc_data[19:16]==7)drain_commands<=drain_commands+1;
   if(mc_req_valid&&mc_req_ready)begin
    assert(mc_req_address[63:23]==0&&mc_req_address[19:0]<20'(GROUPS*17408)&&
           mc_req_address[22:20]>=1&&mc_req_address[22:20]<=4&&mc_req_address[5:0]==0)else $fatal(1,"DDR address");
    assert(mc_req_tag[4:0]<mc_req_record_beats&&mc_req_record_beats==(scope_data[664]?18:17)) else $fatal(1,"real W tag/record size");
    accepted<=accepted+1;
    $fwrite(trace_file,"%0d,DDR_REQ,%0d,%0d,%0d,%0d\n",cycle,case_id,mc_req_tag,mc_req_address,mc_req_channel);
   end
   if(mc_rsp_valid&&mc_rsp_ready)begin returned<=returned+1;$fwrite(trace_file,"%0d,DDR_RSP,%0d,%0d,0,0\n",cycle,case_id,mc_rsp_tag);end
   if(ar_valid&&ar_ready)begin A_reads<=A_reads+1;$fwrite(trace_file,"%0d,A_S_REQ,%0d,%0d,%0d,0\n",cycle,case_id,ar_tag,ar_address);end
   if(a_valid&&a_ready)$fwrite(trace_file,"%0d,A_M,%0d,%0d,%0d,0\n",cycle,case_id,a_session,a_beat);
   if(sw_valid&&sw_ready)begin writes<=writes+1;$fwrite(trace_file,"%0d,S_WRITE,%0d,%0d,%0d,0\n",cycle,case_id,sw_word,sw_address);end
   if(sw_ack_valid&&sw_ack_ready)begin ACKs<=ACKs+1;last_ACK_cycle<=cycle;$fwrite(trace_file,"%0d,S_ACK,%0d,%0d,0,0\n",cycle,case_id,sw_ack_word);end
   if(record_valid&&record_ready)begin record_count<=record_count+1;$fwrite(trace_file,"%0d,RECORD,%0d,%0d,%0d,%0d\n",cycle,case_id,record_sequence,record_k,record_context);end
   if(complete_valid&&complete_ready)begin
    assert(!complete_error||cancel_phase)else $fatal(1,"real native completion error");completed<=completed+1;last_complete_cycle<=cycle;
    if(complete_error)cancel_error_count<=cancel_error_count+1;
    if(complete_next_k==scope_data[608+:16])assert(last_ACK_cycle<cycle)else $fatal(1,"FINAL before true S ACK");
    $fwrite(trace_file,"%0d,COMPLETE,%0d,%0d,%0d,%0d\n",cycle,case_id,complete_sequence,complete_next_k,complete_context);
   end
   if(lc_valid&&lc_ready)$fwrite(trace_file,"%0d,LC_M,%0d,%0d,%0d,%0d\n",cycle,case_id,lc_sop,lc_eop,lc_data[19:16]);
   if(lr_valid&&lr_ready)$fwrite(trace_file,"%0d,M_LR,%0d,%0d,%0d,%0d\n",cycle,case_id,lr_sop,lr_eop,lr_data[39:32]);
   assert(!quarantine&&!fault_interrupt&&protocol_faults==0&&!rejected_complete&&!directory_bad&&(!directory_pub_bad||bad_copy_ticket))else $fatal(1,"real P quarantine/fault state=%0d ctrl=%0d M=%0d",exec_state,protocol_faults,fault_interrupt);
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
   lane16=16'(A_memory[tile*16+word_index/2]>>(16*(4*(word_index%2)+lane)));
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
 task automatic quantize_tile(input integer tile);
  stage_start=cycle;
  for(integer wi=0;wi<32;wi=wi+1)u_host_word(32+wi,make_S32(tile,wi));
  boot_cycles=boot_cycles+cycle-stage_start;stage_start=cycle;
  q_cmd=1;do @(posedge clk);while(!q_ready);@(negedge clk);q_cmd=0;
  while(!q_done)@(negedge clk);
  assert(!q_error&&!q_cancelled&&q_done_key==scope_data[128+:128]&&q_done_k==tile_k&&q_done_words==16&&q_written_mask==16'hffff&&q_shift==0)
    else $fatal(1,"true S32 producer");
  quant_cycles=quant_cycles+cycle-stage_start;stage_start=cycle;
 endtask
 task automatic transfer_tile(input integer tile,input integer stripe);
  tile_generation=tile_generation+1;tile_k=16'(tile*128);tile_session=32'(stripe+1);tile_ticket=32'(stripe*16+tile+1);proof_accepted=0;
  if(!source_tile_reuse)quantize_tile(tile);
  else begin assert(source_fill_done&&source_scale_valid);stage_start=cycle;end
  lease_start=1;do @(posedge clk);while(!lease_ready);@(negedge clk);lease_start=0;
  h_start=1;do @(posedge clk);while(!h_start_ready);@(negedge clk);h_start=0;
  while(!h_done)@(negedge clk);assert(!h_error);h_take=1;pause();h_take=0;
  header_cycles=header_cycles+cycle-stage_start;stage_start=cycle;
  copy_start=1;do @(posedge clk);while(!copy_start_ready);@(negedge clk);copy_start=0;
  while(!copy_done)@(negedge clk);assert(!copy_error);
  if(use_resident)begin
   if(tile==0)begin
    bad_copy_ticket=1;resident_publish=1;pause();
    assert(directory_pub_bad&&!resident_sealed)else $fatal(1,"wrong COPY ticket published");
    resident_publish=0;pause();bad_copy_ticket=0;
   end
   resident_publish=1;assert(directory_publish_ready);pause();resident_publish=0;
   assert(!directory_pub_bad&&resident_sealed==(tile==15))else $fatal(1,"seal without all sixteen true tiles");
  end
  copy_take=1;pause();copy_take=0;
  copy_cycles=copy_cycles+cycle-stage_start;stage_start=cycle;
  if(!use_resident)begin
   while(!a_load_proof_valid)@(negedge clk);
   assert(!a_load_proof_error&&a_source_reads_drained&&a_load_proof_key==meta_key&&
    a_load_proof_window_generation==meta_gen&&a_load_proof_window_session==meta_session&&a_load_proof_window_ticket==meta_ticket&&
    a_load_proof_k_elements==meta_k&&a_load_proof_A_generation!=0&&a_load_proof_A_slot==1'(tile)&&a_load_proof_shift==(source_tile_reuse?source_shift:q_shift))
      else $fatal(1,"true streaming LOAD proof");
   a_load_proof_ready=1;pause();a_load_proof_ready=0;load_proofs=load_proofs+1;
   load_wait_cycles=load_wait_cycles+cycle-stage_start;
  end
  proof_accepted=1;release_window=1;do @(posedge clk);while(!release_ready);@(negedge clk);release_window=0;
  assert(rx_idle);if(!source_tile_reuse)begin
   if(SOURCE_REUSE)assert(source_publish_ready);
   q_take=1;pause();q_take=0;
   if(SOURCE_REUSE)assert(!source_publish_bad&&source_scale_valid&&source_shift==q_shift);
  end
 endtask
 initial begin
  boot_cycles=0;quant_cycles=0;header_cycles=0;copy_cycles=0;load_wait_cycles=0;scope_cycles=0;stage_start=0;
  fill_start=0;fill_cycles=0;scope0_cycles=0;scope1_cycles=0;service_terminal_cycle=0;
  resident_publish=0;resident_scope_live=0;bad_copy_ticket=0;source_cfg=0;source_fill_done=0;
  a_load_proof_ready=RESIDENT;allow_native_A=1;load_proofs=0;
  reset=1;service_valid=0;service_done_ready=0;scope_cancel=0;scope_owner=0;scope_data=0;
  cancel_test=$test$plusargs("CANCEL_FOUR");cancel_phase=0;
  directory_cfg=0;q_cmd=0;q_take=0;h_start=0;h_take=0;lease_start=0;release_window=0;copy_start=0;copy_take=0;
  tile_generation=0;tile_k=0;tile_session=0;tile_ticket=0;proof_accepted=0;
  uh_valid=0;uh_write=1;uh_rsp_ready=0;uh_address=0;uh_data=0;real_copy_ACKs=0;real_copy_reads=0;real_headers=0;real_quantizations=0;
  host_mode=1;host_valid=0;host_write=1;host_address=0;host_data=0;host_response_ready=0;
  allow_request=1;allow_ACK=1;allow_A_response=1;case_id=0;seed=1;
  if($value$plusargs("SEED=%d",seed))begin end
  vectors="results/p-vectors";if($value$plusargs("VECTORS=%s",vectors))begin end
  trace_path="p-resident.csv";if($value$plusargs("TRACE=%s",trace_path))begin end
  $readmemh({vectors,"/scopes.mem"},scopes);$readmemh({vectors,"/resident-scopes.mem"},resident_scopes);
  $readmemh({vectors,"/A.mem"},A_memory);$readmemh({vectors,"/DDR.mem"},DDR_memory);$readmemh({vectors,"/expected.mem"},expect_memory);
  trace_file=$fopen(trace_path,"w");assert(trace_file!=0);$fwrite(trace_file,"cycle,event,case,identity,detail,value\n");
  pause(4);reset=0;pause();scope_data=HAS_RESIDENT?resident_scopes[0]:scopes[0];host_mode=0;
  if(HAS_RESIDENT)begin
   fill_start=cycle;directory_cfg=1;do @(posedge clk);while(!directory_ready);@(negedge clk);directory_cfg=0;
   assert(!directory_bad&&!resident_sealed&&resident_base==256);
   for(integer tile=0;tile<16;tile=tile+1)transfer_tile(tile,0);
   fill_cycles=cycle-fill_start;
   assert(resident_sealed&&resident_key==scope_data[128+:128]&&real_copy_ACKs==256);
  end
  if(SOURCE_REUSE)begin
   fill_start=cycle;source_cfg=1;do @(posedge clk);while(!source_cfg_ready);@(negedge clk);source_cfg=0;
   assert(!source_cfg_bad);
   if(!LAZY_SOURCE)for(integer tile=0;tile<16;tile=tile+1)begin
    tile_generation=tile_generation+1;tile_k=16'(tile*128);quantize_tile(tile);
    assert(source_publish_ready);q_take=1;pause();q_take=0;
    assert(!source_publish_bad&&source_scale_valid&&source_shift==q_shift);
   end
   source_fill_done=!LAZY_SOURCE;fill_cycles=cycle-fill_start;
  end
  for(integer ci=0;ci<2;ci=ci+1)begin
   case_id=ci;scope_data=(RESIDENT||(COMBINED&&ci==0))?resident_scopes[ci]:scopes[ci];scope_owner={32'd1,32'd7,32'd8,32'(ci+1)};host_mode=0;
   pause();start_cycle=32'(cycle);service_valid=1;
   do @(posedge clk);while(!(service_ready&&scope_ready));@(negedge clk);service_valid=0;resident_scope_live=1;a_load_proof_ready=use_resident;
   fork
    begin if(!use_resident)for(integer tile=0;tile<16;tile=tile+1)transfer_tile(tile,ci);end
    begin
     while(!service_done_valid)begin
      pause(2+(seed%3));allow_ACK=0;allow_A_response=0;pause(1);allow_ACK=1;allow_A_response=1;
      if(HAS_RESIDENT)assert(!directory_ready);
     end
    end
    begin
     while(!service_done_valid)@(negedge clk);
     service_terminal_cycle=cycle;
     assert(service_done_owner==scope_owner&&service_done_ticket==scope_owner[31:0]&&service_done_status==0)
       else $fatal(1,"scope terminal failed status=%0d",service_done_status);
    end
   join
   scope_cycles=service_terminal_cycle-int'(start_cycle);if(ci==0)scope0_cycles=scope_cycles;else scope1_cycles=scope_cycles;
   service_done_ready=1;pause();service_done_ready=0;resident_scope_live=0;if(LAZY_SOURCE)source_fill_done=1;pause(2);
   assert(quiescent&&A_live==0&&command_occupied==0&&result_occupied==0&&backend_pending==0)else $fatal(1,"owner leak");
   for(integer way=0;way<2;way=way+1)for(integer outword=0;outword<2*GROUPS;outword=outword+1)
    host_word(0,128+64*ci+32*way+outword,expect_memory[4*GROUPS*ci+2*GROUPS*way+outword]);
   $fwrite(trace_file,"%0d,CASE_DONE,%0d,%0d,%0d,%0d\n",cycle,ci,scope_cycles,A_reads,ACKs);
  end
  assert(real_quantizations==((RESIDENT||SOURCE_REUSE)?16:32)&&real_copy_ACKs==(RESIDENT?256:512)&&real_copy_ACKs==real_copy_reads&&
    real_headers==(RESIDENT?32:64)&&load_proofs==(RESIDENT?0:(COMBINED?16:32)))else $fatal(1,"input accounting");
  assert(accepted==1088*GROUPS&&accepted==returned&&ACKs==8*GROUPS&&writes==8*GROUPS&&completed==64*GROUPS&&record_count==64*GROUPS&&A_reads==512&&(SESSION_LIMIT==32'hffffffe0 ? pair_detaches==32*GROUPS : (pair_detaches>0&&pair_detaches<=32*GROUPS))&&peak_contexts==2*GROUPS)
    else $fatal(1,"execution accounting req=%0d ack=%0d records=%0d reads=%0d pairs=%0d",accepted,ACKs,completed,A_reads,pair_detaches);
  if(WEIGHT_PREFILL)assert(peak_weight_inflight>=2)else $fatal(1,"W overlap never reached two real banks");
  if(FOUR_BANK&&GROUPS>=4)assert(peak_weight_banks==4)else $fatal(1,"W lookahead never allocated all four real banks");
  $display("W_BANK_TIMING mode=%0d live=%0d actual_inflight=%0d",MODE,peak_weight_banks,peak_weight_inflight);
  $display("RESIDENT_X_TIMING mode=%0d startup=%0d first=%0d second=%0d accounted_total=%0d fixture_source_boot=%0d quant=%0d header=%0d copy=%0d post_copy_load_wait=%0d",
    MODE,fill_cycles,scope0_cycles,scope1_cycles,fill_cycles+scope0_cycles+scope1_cycles,boot_cycles,quant_cycles,header_cycles,copy_cycles,load_wait_cycles);
  if(cancel_test)begin
   integer cancel_start,cancel_latency,old_exec,old_drains,old_acks,old_errors;
   assert(FOUR_BANK&&GROUPS==8);
   case_id=2;scope_data=scopes[0];scope_owner={32'd1,32'd7,32'd8,32'd3};host_mode=0;
   pause();service_valid=1;do @(posedge clk);while(!(service_ready&&scope_ready));@(negedge clk);service_valid=0;
   resident_scope_live=1;
   transfer_tile(0,2);transfer_tile(1,2);
   while($countones(M.table_valid)!=4||weight_inflight<2||command_occupied!=0||exec_state!=5'd8)@(negedge clk);
   old_exec=native_execs;old_drains=drain_commands;old_acks=ACKs;old_errors=cancel_error_count;cancel_start=cycle;
   $fwrite(trace_file,"%0d,CANCEL_FOUR,%0d,%0d,%0d,%0d\n",cycle,case_id,old_exec,weight_inflight,old_drains);
   cancel_phase=1;scope_cancel=1;assert(cancel_ready);pause();scope_cancel=0;
   while(!service_done_valid)@(negedge clk);
   assert(service_done_owner==scope_owner&&service_done_ticket==3&&service_done_status!=0&&
       native_execs==old_exec&&ACKs==old_acks&&drain_commands==old_drains+4&&cancel_error_count>=old_errors+4&&
       backend_pending==0&&M.table_valid==0&&A_live==0&&command_occupied==0&&result_occupied==0)
     else $fatal(1,"four W cancel incomplete native=%0d drain=%0d error=%0d",native_execs-old_exec,drain_commands-old_drains,cancel_error_count-old_errors);
   cancel_latency=cycle-cancel_start;
   $fwrite(trace_file,"%0d,CANCEL_DONE,%0d,%0d,%0d,%0d\n",cycle,case_id,cancel_latency,drain_commands-old_drains,cancel_error_count-old_errors);
   service_done_ready=1;pause();service_done_ready=0;cancel_phase=0;resident_scope_live=0;pause(2);
   assert(quiescent&&accepted==returned&&rx_idle&&copy_idle)else $fatal(1,"cancel still owns a source");
   // Re-run the identical weight/A addresses on the same physical four banks.
   // Old positive results are first overwritten so a skipped computation fails.
   for(integer way=0;way<2;way=way+1)for(integer word_id=0;word_id<2*GROUPS;word_id=word_id+1)
    host_word(1,128+32*way+word_id,128'hdabe_4e11_5eed_cafe_dead_5555_ffff_cafe);
   case_id=3;scope_owner={32'd1,32'd7,32'd8,32'd4};host_mode=0;pause();service_valid=1;
   do @(posedge clk);while(!(service_ready&&scope_ready));@(negedge clk);service_valid=0;resident_scope_live=1;
   old_exec=native_execs;old_acks=ACKs;
   for(integer tile=0;tile<16;tile=tile+1)transfer_tile(tile,3);
   while(!service_done_valid)@(negedge clk);
   assert(service_done_owner==scope_owner&&service_done_ticket==4&&service_done_status==0&&
       native_execs==old_exec+32*GROUPS&&ACKs==old_acks+4*GROUPS&&accepted==returned)
     else $fatal(1,"post-cancel true retry failed");
   service_done_ready=1;pause();service_done_ready=0;resident_scope_live=0;pause(2);assert(quiescent);
   for(integer way=0;way<2;way=way+1)for(integer word_id=0;word_id<2*GROUPS;word_id=word_id+1)
    host_word(0,128+32*way+word_id,expect_memory[2*GROUPS*way+word_id]);
   $display("FOUR_CANCEL_PASS cycles=%0d drains=%0d errors=%0d retry_W64=%0d retry_S128ACK=%0d",cancel_latency,4,cancel_error_count-old_errors,32*GROUPS*17,ACKs-old_acks);
  end
  $display("PASS p_resident_x_compare mode=%0d seed=%0d scopes=2 groups=%0d W64=%0d S128ACK=%0d Aread=%0d copy=%0d",
    MODE,seed,GROUPS,accepted,ACKs,A_reads,real_copy_ACKs);
  assert(backend_requests==accepted&&backend_returns==returned&&debug_beats==0&&debug_descriptors==0)
    else $fatal(1,"actual global DMA conservation");
  assert(SESSION_LIMIT==32'hffffffe0 ? backend_purges==1 : backend_purges>1)
    else $fatal(1,"FENCE coverage missing");
  $display("REAL_WEIGHT_GLOBAL_PASS requests=%0d returns=%0d purges=%0d",backend_requests,backend_returns,backend_purges);
  $fclose(trace_file);$finish;
 end
 initial begin #2000000;$fatal(1,"real P timeout state=%0d case=%0d pending=%h",exec_state,case_id,backend_pending);end
 wire unused_diagnostics=^{source_cfg,source_fill_done,source_cfg_ready,source_cfg_bad,source_publish_ready,source_publish_bad,source_rejections,directory_cfg,meta_valid,resident_publish,stream_window_valid,stream_window_key,stream_window_k_elements,stream_window_session,stream_window_ticket,copy_progress_valid,copy_progress_generation,copy_progress_session,copy_progress_ticket,copy_progress_k_elements,resident_scope_live,bad_copy_ticket,directory_pub_bad,service_done_read_bytes,service_done_write_bytes,decoded_key,rf0,rf1,out_version,bias0,bias1,
  inS,outS0,outS1,scratchS,snapshotS,record_bytes,cancel_ready,mc_close_valid,mc_close_tag_base,
  mc_fence_req_valid,mc_fence_req_cookie,mc_fence_req_epoch,mc_fence_done_ready,owners,c_response_tag[31:1],last_complete_cycle};
endmodule
