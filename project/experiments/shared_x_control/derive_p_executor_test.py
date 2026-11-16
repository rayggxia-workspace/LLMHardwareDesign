"""Derive the real leaf/SRAM integration fixture's executor port declarations."""
from pathlib import Path
import re

root = Path(__file__).parent
source = (root / 'rtl/p_native_record_executor.sv').read_text()
ports = source.split(')(\n', 1)[1].split('\n);', 1)[0]
ports = re.sub(r',\s*(?=(?:input|output)\s+logic)', ';\n ', ports)
ports = re.sub(r'\b(?:input|output)\s+logic', 'logic', ports).strip() + ';\n'
body = r'''
 initial clk=0;always #5 clk=~clk;
 p_native_record_executor exec(.*);
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
  .lr_valid,.lr_ready,.lr_sop,.lr_eop,.lr_data,.a_valid,.a_ready,.a_data,.a_session,.a_beat,
  .mc_req_valid,.mc_req_ready,.mc_req_address,.mc_req_tag,.mc_req_channel,.mc_req_record_beats,
  .mc_close_valid,.mc_close_ready,.mc_close_tag_base,.mc_rsp_valid,.mc_rsp_ready,.mc_rsp_tag,.mc_rsp_data,
  .mc_fence_req_valid,.mc_fence_req_ready,.mc_fence_req_cookie,.mc_fence_req_epoch,
  .mc_fence_done_valid,.mc_fence_done_ready,.mc_fence_done_cookie,.mc_fence_done_epoch,.fault_interrupt);
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
 logic [511:0] pending_data[0:31];integer pending_due[0:31];
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
    pending_mask[free_slot]<=1;pending_tags[free_slot]<=mc_req_tag;
    pending_data[free_slot]<=DDR_memory[case_id*128+int'((mc_req_address-(64'h100000+64'(case_id)*64'h10000))>>6)];
    pending_due[free_slot]<=cycle+7+(seed%4);accepted<=accepted+1;
    $fwrite(trace_file,"%0d,DDR_REQ,%0d,%0d,%0d,%0d\n",cycle,case_id,mc_req_tag,mc_req_address,mc_req_channel);
   end
   if(response_slot<0&&response_candidate>=0)response_slot<=response_candidate;
   if(mc_rsp_valid&&mc_rsp_ready)begin pending_mask[response_slot]<=0;response_slot<=-1;returned<=returned+1;$fwrite(trace_file,"%0d,DDR_RSP,%0d,%0d,0,0\n",cycle,case_id,mc_rsp_tag);end
   for(integer ch=0;ch<2;ch=ch+1)
    channel_live[ch]<=channel_live[ch]+((mc_req_valid&&mc_req_ready&&int'(mc_req_channel)==ch)?1:0)-((mc_rsp_valid&&mc_rsp_ready&&int'(mc_rsp_tag[23])==ch)?1:0);
   // No channel is inferred from tag epoch. The bounded return table carries
   // its own actual channel in the next revision; single active record keeps
   // total32 bound here, with channel comparison checked on each request.
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
   for(integer word_id=0;word_id<(int'(scope_data[608+:16])>>3);word_id=word_id+1)begin
    host_word(1,word_id,A_memory[ci*32+word_id]);
    copy_committed_prefix=11'(word_id+1);
    if(word_id%16==15)begin
     publish_k=16'((word_id/16)*128);directory_publish=1;
     do @(posedge clk);while(!directory_publish_ready);@(negedge clk);directory_publish=0;
    end
   end
   host_mode=0;pause();start_cycle=32'(cycle);service_valid=1;
   do @(posedge clk);while(!(service_ready&&scope_ready));@(negedge clk);service_valid=0;
   fork
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
  assert(accepted==returned&&ACKs==24&&writes==24&&completed==18&&record_count==18&&A_reads==192&&directory_faults==0)else $fatal(1,"accounting req%0d rsp%0d ACK%0d writes%0d completed%0d records%0d Areads%0d",accepted,returned,ACKs,writes,completed,record_count,A_reads);
  $display("PASS p_native_record_executor seed=%0d cases=8 cycles=%0d requests=%0d returns=%0d S128ACK=%0d records=%0d Areads=%0d",seed,cycle,accepted,returned,ACKs,completed,A_reads);
  $fclose(trace_file);$finish;
 end
 initial begin #2000000;$fatal(1,"real P timeout state=%0d case=%0d pending=%h",exec.state,case_id,pending_mask);end
 wire unused_diagnostics=^{service_done_read_bytes,service_done_write_bytes,decoded_key,rf0,rf1,out_version,bias0,bias1,
  inS,outS0,outS1,scratchS,snapshotS,record_bytes,cancel_ready,mc_close_valid,mc_close_tag_base,
  mc_fence_req_valid,mc_fence_req_cookie,mc_fence_req_epoch,mc_fence_done_ready,owners,c_response_tag[31:1],last_complete_cycle};
endmodule
'''
# The return slot stores its true channel; never decode it from an epoch tag.
body = body.replace('logic [511:0] pending_data[0:31];integer pending_due[0:31];',
                    'logic [511:0] pending_data[0:31];logic pending_channel[0:31];integer pending_due[0:31];')
body = body.replace('pending_mask[free_slot]<=1;pending_tags[free_slot]<=mc_req_tag;',
                    'pending_mask[free_slot]<=1;pending_tags[free_slot]<=mc_req_tag;pending_channel[free_slot]<=mc_req_channel;')
body = body.replace("int'(mc_rsp_tag[23])", "int'(pending_channel[response_slot])")
body = body.replace('   // No channel is inferred from tag epoch. The bounded return table carries\n'
                    '   // its own actual channel in the next revision; single active record keeps\n'
                    '   // total32 bound here, with channel comparison checked on each request.\n', '')
body = body.replace('mc_rsp_valid&&mc_rsp_ready&&int\'(pending_channel[response_slot])==ch',
                    "mc_rsp_valid&&mc_rsp_ready&&response_slot>=0&&int'(pending_channel[response_slot])==ch")
(root / 'rtl/tb_p_native_record_executor.sv').write_text('`timescale 1ns/1ps\n// Real serialized M + real S bank fixture, functional10ns not300MHzSTA.\nmodule tb_p_native_record_executor;\n' + ports + body)
