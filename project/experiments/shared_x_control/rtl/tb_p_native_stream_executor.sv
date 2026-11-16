`timescale 1ns/1ps
// Real serialized M + real S bank fixture, functional10ns not300MHzSTA.
module tb_p_native_stream_executor;
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
  .cfg_key(scope_data[128+:128]),.cfg_first_kk(16'd0),.cfg_tiles(6'(scope_data[608+:16]>>7)),.cfg_stride3(1'b0),
  .storage_released(quiescent),.leases_drained(quiescent),.cfg_rejected(directory_bad),
  .publish_valid(directory_publish),.publish_ready(directory_publish_ready),.publish_key(scope_data[128+:128]),
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
 logic [31:0] pending_mask,pending_tags[0:31];
 logic [511:0] pending_data[0:31];logic pending_channel[0:31];integer pending_due[0:31];
 integer response_slot,response_candidate,free_slot;
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
   cycle<=0;pending_mask<=0;response_slot<=-1;accepted<=0;returned<=0;A_reads<=0;writes<=0;ACKs<=0;completed<=0;record_count<=0;
   channel_live[0]<=0;channel_live[1]<=0;last_ACK_cycle<=0;last_complete_cycle<=0;
  end else begin
   cycle<=cycle+1;
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
 initial begin

  stream_window_valid=0;stream_window_key=0;stream_window_generation=0;stream_window_k_elements=0;
  stream_window_session=0;stream_window_ticket=0;copy_progress_session=0;copy_progress_ticket=0;
  copy_progress_valid=0;copy_progress_generation=0;copy_progress_k_elements=0;
  a_load_proof_ready=0;allow_native_A=0;load_proofs=0;poison_writes=0;stale_prefix_checks=0;
  reset=1;service_valid=0;service_done_ready=0;scope_cancel=0;scope_owner=0;scope_data=0;
  copy_key=0;copy_committed_prefix=0;directory_cfg=0;directory_publish=0;publish_k=0;
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
   case_id=ci;scope_data=scopes[ci];scope_owner={32'd1,32'd7,32'd8,32'(ci+1)};
   copy_key=scope_data[128+:128];copy_committed_prefix=0;directory_cfg=1;
   do @(posedge clk);while(!directory_ready);@(negedge clk);directory_cfg=0;

   stream_window_key=scope_data[128+:128];stream_window_generation=1;stream_window_session=32'(ci+1);stream_window_ticket=32'(ci+100);stream_window_k_elements=0;stream_window_valid=1;
   // A command/header may already be admitted while COPY still describes a
   // previous generation or another K tile of the same key.
   copy_progress_valid=1;copy_progress_generation=0;copy_progress_k_elements=128;copy_committed_prefix=16;
   publish_k=0;directory_publish=1;
   do @(posedge clk);while(!directory_publish_ready);@(negedge clk);directory_publish=0;
   host_mode=0;pause();start_cycle=32'(cycle);service_valid=1;
   do @(posedge clk);while(!(service_ready&&scope_ready));@(negedge clk);service_valid=0;
   fork
    begin
     for(integer tile=0;tile<(int'(scope_data[608+:16])>>7);tile=tile+1)begin
      allow_native_A=0;
      // The initial/next header is current, but old COPY prefix16 is not.
      while(!(exec.k==16'(tile*128)&&exec.load_pending==0&&exec.A_front.data_front.data_front.state[1'(tile)]==1))@(negedge clk);
      repeat(4)begin pause();assert(!ar_valid&&!a_load_proof_valid)else $fatal(1,"stale same-key COPY prefix authorized A read");stale_prefix_checks=stale_prefix_checks+1;end
      // Matching gen/K with the wrong actual COPY session is still stale.
      copy_progress_generation=stream_window_generation;copy_progress_k_elements=16'(tile*128);copy_progress_session=stream_window_session^32'd1;copy_progress_ticket=stream_window_ticket;
      repeat(2)begin pause();assert(!ar_valid&&!a_load_proof_valid)else $fatal(1,"stale COPY session authorized A read");end
      copy_progress_session=stream_window_session;copy_progress_ticket=stream_window_ticket^32'd1;
      repeat(2)begin pause();assert(!ar_valid&&!a_load_proof_valid)else $fatal(1,"stale COPY ticket authorized A read");end
      copy_progress_ticket=stream_window_ticket;copy_committed_prefix=0;
      for(integer wi=0;wi<16;wi=wi+1)begin host_word(1,wi,A_memory[ci*32+tile*16+wi]);copy_committed_prefix=11'(wi+1);end
      host_mode=0;
      while(!a_load_proof_valid)@(negedge clk);
      assert(!a_load_proof_error&&a_source_reads_drained&&a_load_proof_key==stream_window_key&&
          a_load_proof_window_generation==stream_window_generation&&a_load_proof_k_elements==16'(tile*128)&&
          a_load_proof_window_session==stream_window_session&&a_load_proof_window_ticket==stream_window_ticket&&
          a_load_proof_A_generation!=0&&a_load_proof_A_slot==1'(tile)&&a_load_proof_shift==8)else $fatal(1,"stream LOAD proof identity");
      repeat(3)begin pause();assert(a_load_proof_valid&&!a_valid)else $fatal(1,"unaccepted LOAD receipt launched M");end
      a_load_proof_ready=1;pause();a_load_proof_ready=0;load_proofs=load_proofs+1;
      // Only after a true matching LOAD receipt, recycle actual staging S.
      // Native A is held by legitimate downstream backpressure during host S
      // writes; the finite adapter must replay its original copied A payload.
      stream_window_valid=0;
      for(integer wi=0;wi<16;wi=wi+1)begin host_word(1,wi,128'hfeedface0123456789abcdef76543210);poison_writes=poison_writes+1;end
      host_mode=0;allow_native_A=1;
      if(tile+1<(int'(scope_data[608+:16])>>7))begin
       // Current header advances first; old progress deliberately remains16.
       stream_window_generation=stream_window_generation+1;
       stream_window_k_elements=16'((tile+1)*128);stream_window_valid=1;
       publish_k=16'((tile+1)*128);directory_publish=1;
       do @(posedge clk);while(!directory_publish_ready);@(negedge clk);directory_publish=0;
       // Let this record consume A before the next iteration blocks its port.
       while(exec.k==16'(tile*128))@(negedge clk);
      end
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
  assert(load_proofs==12&&poison_writes==192&&stale_prefix_checks==48)else $fatal(1,"stream finite proof accounting");
  assert(accepted==returned&&ACKs==24&&writes==24&&completed==18&&record_count==18&&A_reads==192&&directory_faults==0)else $fatal(1,"accounting req%0d rsp%0d ACK%0d writes%0d completed%0d records%0d Areads%0d",accepted,returned,ACKs,writes,completed,record_count,A_reads);
  $display("PASS p_native_stream_executor seed=%0d cases=8 cycles=%0d requests=%0d returns=%0d S128ACK=%0d records=%0d Areads=%0d",seed,cycle,accepted,returned,ACKs,completed,A_reads);
  $fclose(trace_file);$finish;
 end
 initial begin #2000000;$fatal(1,"real P timeout state=%0d case=%0d pending=%h",exec.state,case_id,pending_mask);end
 wire unused_diagnostics=^{service_done_read_bytes,service_done_write_bytes,decoded_key,rf0,rf1,out_version,bias0,bias1,
  inS,outS0,outS1,scratchS,snapshotS,record_bytes,cancel_ready,mc_close_valid,mc_close_tag_base,
  mc_fence_req_valid,mc_fence_req_cookie,mc_fence_req_epoch,mc_fence_done_ready,owners,c_response_tag[31:1],last_complete_cycle};
endmodule
