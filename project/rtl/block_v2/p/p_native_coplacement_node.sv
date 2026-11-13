`timescale 1ns/1ps
// Test wiring for one real P.S, real stream LC provider and separately
// instantiated native M2. No shadow S/weights; only the external DDR peer
// belongs to the test. The auxiliary port reuses idle logical mux clients.
module p_native_coplacement_node #(
 parameter bit SHARED_MID_SOURCE=1'b0,FOUR_BANK_LOOKAHEAD=1'b0,EARLY_EXEC=1'b0
)(
 input logic clk,reset,
 output logic mc_fence_req_valid,input logic mc_fence_req_ready,
 output logic [31:0] mc_fence_req_cookie,output logic [8:0] mc_fence_req_epoch,
 input logic mc_fence_done_valid,output logic mc_fence_done_ready,
 input logic [31:0] mc_fence_done_cookie,input logic [8:0] mc_fence_done_epoch,
 input logic service_valid,output logic service_ready,
 input logic service_cancel_valid,output logic service_cancel_ready,
 input logic [127:0] service_owner,input logic [1023:0] service_descriptor,
 output logic service_done_valid,input logic service_done_ready,
 output logic [127:0] service_done_owner,output logic [31:0] service_done_ticket,
 output logic [15:0] service_done_status,
 output logic [31:0] service_done_read_bytes,service_done_write_bytes,
 output logic [5:0] committed_gate_words,committed_up_words,
 output logic window_need_valid,output logic [15:0] window_need_k,
 output logic [127:0] window_need_key,
 input logic lease_valid,output logic lease_ready,
 input logic [127:0] lease_key,input logic [15:0] lease_generation,lease_k,
 input logic [31:0] lease_session,lease_ticket,
 input logic header_valid,output logic header_ready,input logic [31:0] header_tag,
 input logic [127:0] header_data,
 output logic header_ack_valid,input logic header_ack_ready,output logic [31:0] header_ack_tag,
 output logic header_ack_error,
 input logic release_window,output logic release_ready,
 input logic copy_drained,input logic copy_progress_valid,input logic [127:0] copy_key,
 input logic [15:0] copy_progress_generation,copy_progress_k_elements,
 input logic [31:0] copy_progress_session,copy_progress_ticket,
 input logic [10:0] copy_committed_prefix,
 input logic cp_valid,output logic cp_ready,input logic [9:0] cp_address,
 input logic [31:0] cp_tag,input logic [127:0] cp_data,
 output logic cp_ack_valid,input logic cp_ack_ready,output logic [31:0] cp_ack_tag,
 output logic a_load_proof_valid,input logic a_load_proof_ready,
 output logic [5:0] a_load_proof_shift,
 output logic a_source_reads_drained,output logic quiescent,window_enabled,window_idle,
 input logic aux_valid,aux_write,input logic [9:0] aux_address,input logic [127:0] aux_data,
 input logic [31:0] aux_tag,output logic aux_ready,aux_rsp_valid,
 input logic aux_rsp_ready,output logic [31:0] aux_rsp_tag,output logic [127:0] aux_rsp_data,
 input logic aux2_valid,aux2_write,input logic [9:0] aux2_address,input logic [127:0] aux2_data,
 input logic [31:0] aux2_tag,output logic aux2_ready,aux2_rsp_valid,
 input logic aux2_rsp_ready,output logic [31:0] aux2_rsp_tag,
 output logic mc_req_valid,input logic mc_req_ready,output logic [63:0] mc_req_address,
 output logic [31:0] mc_req_tag,output logic mc_req_channel,output logic [4:0] mc_req_record_beats,
 output logic mc_close_valid,output logic [31:0] mc_close_tag_base,input logic mc_close_ready,
 input logic mc_rsp_valid,output logic mc_rsp_ready,input logic [31:0] mc_rsp_tag,input logic [511:0] mc_rsp_data
);
 wire allow_req=1'b1,allow_rsp=1'b1;
 logic [127:0] stream_window_key,a_load_proof_key;
 logic [15:0] stream_window_generation,stream_window_k_elements,a_load_proof_window_generation;
 logic [31:0] stream_window_session,stream_window_ticket,a_load_proof_window_session,a_load_proof_window_ticket;
 logic [15:0] a_load_proof_k_elements,a_load_proof_A_generation;
 logic a_load_proof_A_slot,a_load_proof_error,lease_error,metadata_valid,proof_accepted;
 logic [31:0] rejected_frames;
 logic [5:0] metadata_shift;
 logic [1:0] owners;
 copy_scale_header_rx rx(.clk,.reset,.lease_valid,.lease_ready,.lease_key,.lease_generation,
  .lease_kk(lease_k),.lease_session,.lease_ticket,.lease_error,
  .frame_valid(header_valid),.frame_ready(header_ready),.frame_tag(header_tag),.frame_data(header_data),
  .ack_valid(header_ack_valid),.ack_ready(header_ack_ready),.ack_tag(header_ack_tag),.ack_error(header_ack_error),
  .metadata_valid,.metadata_ready(1'b1),.metadata_key(stream_window_key),.metadata_generation(stream_window_generation),
  .metadata_kk(stream_window_k_elements),.metadata_session(stream_window_session),.metadata_ticket(stream_window_ticket),
  .metadata_shift,.data_enabled(window_enabled),.release_valid(release_window),.release_ready,
  .release_key(lease_key),.release_generation(lease_generation),.release_cancel(1'b0),
  .data_drained(copy_drained&&owners==0),.consumer_drained(proof_accepted&&a_source_reads_drained),
  .quiescent(window_idle),.rejected_frames);
 logic [127:0] scale_lookup_key;
 logic [15:0] scale_lookup_kk;
 wire scale_lookup_valid=window_enabled&&stream_window_key==scale_lookup_key&&stream_window_k_elements==scale_lookup_kk;
 wire [5:0] scale_lookup_shift=metadata_shift;

 logic lc_valid,lc_ready,lc_sop,lc_eop,lr_valid,lr_ready,lr_sop,lr_eop,a_valid,a_ready;
 logic [127:0] lc_data,lr_data;
 logic [255:0] a_data;
 logic [31:0] a_session;
 logic [2:0] a_beat;
 logic quarantine,fault_interrupt;
 logic [31:0] protocol_faults;
 logic [1:0] A_live,result_occupied,command_occupied;
 logic ar_valid,ar_ready,ar_rsp_valid,ar_rsp_ready;
 logic [9:0] ar_address;
 logic [31:0] ar_tag,ar_rsp_tag;
 logic [127:0] ar_rsp_data;
 logic sw_valid,sw_ready,sw_ack_valid,sw_ack_ready,sw_word,sw_ack_word,sw_ack_error;
 logic [511:0] sw_ticket,sw_ack_ticket;
 logic [9:0] sw_address;
 logic [127:0] sw_data;
 p_stream_scope_node #(.FOUR_BANK_LOOKAHEAD(FOUR_BANK_LOOKAHEAD),.EARLY_EXEC(EARLY_EXEC)) exec(.service_ticket(service_owner[31:0]),
  .stream_window_valid(window_enabled),.*);
 m_native_leaf_s32 M(.*);

 logic [2:0] s_client_ready,v;
 logic [95:0] tag;
 logic extra_ready,extra_rsp;
 logic [31:0] extra_tag;
 logic [127:0] data,native_data,native_rsp_data;
 logic [9:0] native_address;
 logic native_valid,native_write,native_ready,native_rsp_valid,native_rsp_ready;
 wire store_up=service_descriptor[656+:2]==2&&sw_address>=service_descriptor[704+:10]&&
     sw_address<service_descriptor[704+:10]+10'd16;
 wire native_phase=!quiescent;
 if(SHARED_MID_SOURCE)begin: four_logical_clients
 native_s128_mux4 mux(.clk,.reset,
  .c_valid({aux_valid&&allow_req,ar_valid&&allow_req,cp_valid&&window_enabled&&allow_req,
            (native_phase?sw_valid:aux2_valid)&&allow_req}),
  .c_write({aux_write,1'b0,1'b1,native_phase||aux2_write}),
  .c_address({aux_address,ar_address,cp_address,native_phase?sw_address:aux2_address}),
  .c_data({aux_data,128'd0,cp_data,native_phase?sw_data:aux2_data}),
  .c_tag({aux_tag,ar_tag,cp_tag,native_phase?{30'd0,store_up,sw_word}:aux2_tag}),
  .c_ready({extra_ready,s_client_ready}),.c_response_valid({extra_rsp,v}),
  .c_response_ready({aux_rsp_ready&&allow_rsp,ar_rsp_ready&&allow_rsp,
                     cp_ack_ready&&allow_rsp,(native_phase?sw_ack_ready:aux2_rsp_ready)&&allow_rsp}),
  .c_response_data(data),.c_response_tag({extra_tag,tag}),.owners_occupied(owners),
  .req_valid(native_valid),.req_write(native_write),.req_address(native_address),.req_data(native_data),.req_ready(native_ready),
  .rsp_valid(native_rsp_valid),.rsp_ready(native_rsp_ready),.rsp_data(native_rsp_data));
 end else begin: three_logical_clients
 assign extra_ready=1'b0;
 assign extra_rsp=1'b0;
 assign extra_tag=32'd0;
 native_s128_mux3 mux(.clk,.reset,
  .c_valid({(native_phase?ar_valid:aux_valid)&&allow_req,
            cp_valid&&window_enabled&&allow_req,(native_phase?sw_valid:aux2_valid)&&allow_req}),
  .c_write({!native_phase&&aux_write,1'b1,native_phase||aux2_write}),
  .c_address({native_phase?ar_address:aux_address,cp_address,native_phase?sw_address:aux2_address}),
  .c_data({native_phase?128'd0:aux_data,cp_data,native_phase?sw_data:aux2_data}),
  .c_tag({native_phase?ar_tag:aux_tag,cp_tag,native_phase?{30'd0,store_up,sw_word}:aux2_tag}),
  .c_ready(s_client_ready),.c_response_valid(v),
  .c_response_ready({(native_phase?ar_rsp_ready:aux_rsp_ready)&&allow_rsp,
                     cp_ack_ready&&allow_rsp,(native_phase?sw_ack_ready:aux2_rsp_ready)&&allow_rsp}),
  .c_response_data(data),.c_response_tag(tag),.owners_occupied(owners),
  .req_valid(native_valid),.req_write(native_write),.req_address(native_address),.req_data(native_data),.req_ready(native_ready),
  .rsp_valid(native_rsp_valid),.rsp_ready(native_rsp_ready),.rsp_data(native_rsp_data));
 end
 local_s_base storage(.clk,.reset,.req_valid(native_valid),.req_write(native_write),.req_addr(native_address),
  .req_data(native_data),.req_ready(native_ready),.rsp_valid(native_rsp_valid),.rsp_ready(native_rsp_ready),.rsp_data(native_rsp_data));
 assign cp_ready=window_enabled&&s_client_ready[1]&&allow_req;
 assign cp_ack_valid=v[1]&&allow_rsp;
 assign cp_ack_tag=tag[63:32];
 assign ar_ready=native_phase&&s_client_ready[2]&&allow_req;
 assign ar_rsp_valid=native_phase&&v[2]&&allow_rsp;
 assign ar_rsp_tag=tag[95:64];
 assign ar_rsp_data=data;
 assign sw_ready=native_phase&&s_client_ready[0]&&allow_req;
 assign sw_ack_valid=native_phase&&v[0]&&allow_rsp;
 assign sw_ack_ticket=sw_ticket;
 assign sw_ack_word=tag[0];
 assign sw_ack_error=1'b0;
 assign aux_ready=(SHARED_MID_SOURCE?extra_ready:!native_phase&&s_client_ready[2])&&allow_req;
 assign aux_rsp_valid=(SHARED_MID_SOURCE?extra_rsp:!native_phase&&v[2])&&allow_rsp;
 assign aux_rsp_tag=SHARED_MID_SOURCE?extra_tag:tag[95:64];
 assign aux_rsp_data=data;
 assign aux2_ready=!native_phase&&s_client_ready[0]&&allow_req;
 assign aux2_rsp_valid=!native_phase&&v[0]&&allow_rsp;
 assign aux2_rsp_tag=tag[31:0];
 always_ff @(posedge clk)begin
  if(reset)begin
   proof_accepted<=0;committed_gate_words<=0;committed_up_words<=0;
  end else begin
   if(lease_valid&&lease_ready)proof_accepted<=0;
   if(a_load_proof_valid&&a_load_proof_ready)begin
    assert(!a_load_proof_error&&a_source_reads_drained&&a_load_proof_key==lease_key&&
      a_load_proof_window_generation==lease_generation&&a_load_proof_window_session==lease_session&&
      a_load_proof_window_ticket==lease_ticket&&a_load_proof_k_elements==lease_k&&a_load_proof_A_generation!=0&&
      a_load_proof_A_slot==lease_k[7]&&a_load_proof_shift==metadata_shift)
      else $fatal(1,"three-P actual A LOAD proof");
    proof_accepted<=1;
   end
   if(service_valid&&service_ready)begin
    assert(owners==0&&!aux_valid&&!aux2_valid)else $fatal(1,"P has undrained S owners");
    committed_gate_words<=0;committed_up_words<=0;
   end
   if(sw_ack_valid&&sw_ack_ready)
    if(tag[1])committed_up_words<=committed_up_words+1'b1;
    else committed_gate_words<=committed_gate_words+1'b1;
   if(ar_valid&&ar_ready)
    assert(scale_lookup_valid&&copy_progress_valid&&copy_progress_k_elements==scale_lookup_kk&&
      ar_address>=service_descriptor[672+:10]&&
      {1'b0,ar_address}-{1'b0,service_descriptor[672+:10]}<copy_committed_prefix)
      else $fatal(1,"P reads before actual COPY acknowledgment");
   assert(!fault_interrupt&&!quarantine&&protocol_faults==0&&!lease_error&&rejected_frames==0)
      else $fatal(1,"three-P physical provider fixture fault");
  end
 end
 wire _unused=^{metadata_valid,A_live,result_occupied,command_occupied,service_cancel_ready,
    mc_fence_req_cookie,mc_fence_req_epoch,mc_fence_done_ready};
endmodule
