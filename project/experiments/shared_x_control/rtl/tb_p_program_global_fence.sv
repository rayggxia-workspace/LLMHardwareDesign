`timescale 1ns/1ps
// Real serialized M + real S bank fixture, functional10ns not300MHzSTA.
module tb_p_program_global_fence;
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
 p_native_record_executor #(.SESSION_LIMIT(32),.A_GENERATION_LIMIT(2),.W_GENERATION_LIMIT(1)) exec(.*);
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
 p_scope_range_service #(.NATIVE_LOCAL_CONTIG(1'b1)) ranges(
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
  .publish_valid(directory_publish),.publish_ready(directory_publish_ready),.publish_key(scopes[case_id][128+:128]),
  .publish_kk(publish_k),.publish_shift(6'd8),.publish_written_mask(16'hffff),.publish_error(1'b0),
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
  .lr_valid,.lr_ready,.lr_sop,.lr_eop,.lr_data,.a_valid,.a_ready,.a_data,.a_session,.a_beat,
  .mc_req_valid,.mc_req_ready,.mc_req_address,.mc_req_tag,.mc_req_channel,.mc_req_record_beats,
  .mc_close_valid,.mc_close_ready,.mc_close_tag_base,.mc_rsp_valid,.mc_rsp_ready,.mc_rsp_tag,.mc_rsp_data,
  .mc_fence_req_valid,.mc_fence_req_ready,.mc_fence_req_cookie,.mc_fence_req_epoch,
  .mc_fence_done_valid,.mc_fence_done_ready,.mc_fence_done_cookie,.mc_fence_done_epoch,.fault_interrupt);
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
 native_s128_mux2 mux(.clk,.reset,.c_valid({ar_valid,(host_mode?host_valid:(sw_valid&&allow_request))}),
  .c_write({1'b0,(host_mode?host_write:1'b1)}),.c_address({ar_address,(host_mode?host_address:sw_address)}),
  .c_data({128'd0,(host_mode?host_data:sw_data)}),.c_tag({ar_tag,(host_mode?32'd0:{31'd0,sw_word})}),
  .c_ready,.c_response_valid,.c_response_ready({ar_rsp_ready&&allow_A_response,(host_mode?host_response_ready:(sw_ack_ready&&allow_ACK))}),
  .c_response_data,.c_response_tag,.req_valid,.req_write,.req_address,.req_data,.req_ready,.rsp_valid,.rsp_ready,.rsp_data,.owners_occupied(owners));
 local_s_base storage(.clk,.reset,.req_valid,.req_write,.req_addr(req_address),.req_data,.req_ready,.rsp_valid,.rsp_ready,.rsp_data);
 assign host_ready=host_mode&&c_ready[0];
 assign host_response_valid=host_mode&&c_response_valid[0];
 assign ar_ready=c_ready[1];assign ar_rsp_valid=c_response_valid[1]&&allow_A_response;
 assign ar_rsp_tag=c_response_tag[63:32];assign ar_rsp_data=c_response_data;
 assign sw_ready=!host_mode&&c_ready[0]&&allow_request;
 // Guard's C_ACK owner/ticket and piece remain stable until the real S reply.
 // The ordinary S tag carries the word; no 512-bit ticket copy is added.
 assign sw_ack_valid=!host_mode&&c_response_valid[0]&&allow_ACK;
 assign sw_ack_ticket=sw_ticket;assign sw_ack_word=c_response_tag[0];assign sw_ack_error=0;
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
 logic backend_fence_live,wrong_purge_sent;integer backend_fence_due,wrong_purge_packets,dma_diagnostics;
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
 wire bad_purge_phase=backend_fence_live&&backend_purges==2&&!wrong_purge_sent;
 assign d_fence_done_valid=backend_fence_live&&(bad_purge_phase||cycle>=backend_fence_due);
 assign d_fence_done_generation=backend_fence_generation^(bad_purge_phase?32'd1:32'd0);
 always @(posedge clk)begin
  if(reset)begin
   backend_pending<=0;backend_requests<=0;backend_returns<=0;backend_purges<=0;backend_fence_live<=0;backend_fence_due<=0;backend_fence_generation<=0;wrong_purge_sent<=0;wrong_purge_packets<=0;dma_diagnostics<=0;
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
   if(d_fence_done_valid&&d_fence_done_ready)begin
    if(bad_purge_phase)begin wrong_purge_sent<=1;wrong_purge_packets<=wrong_purge_packets+1;end
    else backend_fence_live<=0;$fwrite(trace_file,"%0d,DDR_PURGE_DONE,%0d,%0d,0,0\n",cycle,case_id,d_fence_done_generation);end
   if(backend_purges==0||backend_fence_live)assert(c_req_ready==0)else $fatal(1,"client accepted before actual startup purge done");
   if(dma_fault_valid)begin
    assert(dma_fault_kind==2&&dma_fault_client==15&&dma_fault_local_tag==0&&dma_fault_global_tag=={32'd0,(backend_fence_generation^32'd1)}&&wrong_purge_packets==1)else $fatal(1,"unexpected real DMA ownership fault");
    dma_diagnostics<=dma_diagnostics+1;
   end
   if(backend_fence_live&&backend_purges>1)assert(!record_ready)else $fatal(1,"new record accepted before actual global purge done");
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
  copy_key=0;copy_committed_prefix=0;directory_cfg=0;directory_publish=0;publish_k=0;
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
   copy_key=scopes[ci][128+:128];copy_committed_prefix=0;directory_cfg=1;
   do @(posedge clk);while(!directory_ready);@(negedge clk);directory_cfg=0;
   for(integer word_id=0;word_id<(int'(scopes[ci][608+:16])>>3);word_id=word_id+1)begin
    host_word(1,word_id,A_memory[ci*32+word_id]);
    copy_committed_prefix=11'(word_id+1);
    if(word_id%16==15)begin
     publish_k=16'((word_id/16)*128);directory_publish=1;
     do @(posedge clk);while(!directory_publish_ready);@(negedge clk);directory_publish=0;
    end
   end
   host_mode=0;pause();start_cycle=32'(cycle);source_prepared=1;
   fork
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
  assert(accepted==returned&&ACKs==24&&writes==24&&completed==18&&record_count==18&&A_reads==192&&directory_faults==0)else $fatal(1,"accounting req%0d rsp%0d ACK%0d writes%0d completed%0d records%0d Areads%0d",accepted,returned,ACKs,writes,completed,record_count,A_reads);
  while(!result_valid_o)@(negedge clk);
  assert(result_status_o==0&&result_confirmed_read_bytes_o==21184&&result_confirmed_write_bytes_o==384&&MC_calls==8&&MC_returns==8&&LC_PM_reads==184&&scope_returns==16&&l_retired_instructions==3)else $fatal(1,"actual MC LC accounting status%0d reads%0d writes%0d CALL%0d return%0d LCpm%0d scope%0d instr%0d",result_status_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,MC_calls,MC_returns,LC_PM_reads,scope_returns,l_retired_instructions);
  assert(backend_requests==331&&backend_returns==331&&backend_purges==int'(exec.fence_count)+1&&exec.fence_count>=17&&wrong_purge_packets==1&&dma_diagnostics==1&&debug_beats==0&&debug_descriptors==0)else $fatal(1,"global real backend conservation");
  result_ready_i=1;pause();result_ready_i=0;
  $display("PASS p_program_global_fence seed=%0d cases=8 cycles=%0d requests=%0d returns=%0d S128ACK=%0d records=%0d Areads=%0d",seed,cycle,accepted,returned,ACKs,completed,A_reads);
  $fclose(trace_file);$finish;
 end
 initial begin #2000000;$fatal(1,"real P timeout state=%0d case=%0d pending=%h",exec.state,case_id,backend_pending);end
 wire unused_diagnostics=^{service_done_read_bytes,service_done_write_bytes,decoded_key,rf0,rf1,out_version,bias0,bias1,
  inS,outS0,outS1,scratchS,snapshotS,record_bytes,cancel_ready,mc_close_valid,mc_close_tag_base,
  mc_fence_req_valid,mc_fence_req_cookie,mc_fence_req_epoch,mc_fence_done_ready,owners,c_response_tag[31:1],last_complete_cycle};
endmodule
