"""Replace both DMA peers with the production finite global fabric.

The only external DDR model is a finite64-entry return table and four held
return lanes, behind real two-channel/two-lane rolling issue arbitration.
"""
from pathlib import Path
root = Path(__file__).parent / 'rtl'
s = (root / 'tb_p_program_numeric.sv').read_text().replace('module tb_p_program_numeric;', 'module tb_p_program_fabric;')
start = s.index(' assign mc_close_ready=1;')
end = s.index(' logic host_mode', start)
s = s[:start] + s[end:]
start = s.index(' logic [31:0] pending_mask,')
end = s.index(' always @(posedge clk)begin', start)
common = '''
 integer cycle,seed,case_id,trace_file,accepted,returned,A_reads,writes,ACKs,completed,record_count;
 integer last_ACK_cycle,last_complete_cycle;
 logic [31:0] start_cycle;
 string vectors,trace_path;
'''
fabric = r'''
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
'''
s = s[:start] + common + fabric + s[end:]
s = s.replace('pending_mask<=0;response_slot<=-1;', '')
s = s.replace('   channel_live[0]<=0;channel_live[1]<=0;', '')
start = s.index('   if(mc_req_valid&&mc_req_ready)begin')
end = s.index('   if(ar_valid&&ar_ready)', start)
s = s[:start] + '''
   if(mc_req_valid&&mc_req_ready)begin accepted<=accepted+1;$fwrite(trace_file,"%0d,DDR_REQ,%0d,%0d,%0d,%0d\\n",cycle,case_id,mc_req_tag,mc_req_address,mc_req_channel);end
   if(mc_rsp_valid&&mc_rsp_ready)begin returned<=returned+1;$fwrite(trace_file,"%0d,DDR_RSP,%0d,%0d,0,0\\n",cycle,case_id,mc_rsp_tag);end
''' + s[end:]
start = s.index(' logic [1:0] scope_pending;')
end = s.index(' assign l_rx_valid', start)
s = s[:start] + s[end:]
start = s.index(' // Descriptor peer has exactly')
end = s.index(' always @(posedge clk)begin', start)
s = s[:start] + s[end:]
s = s.replace('   scope_pending<=0;l_mc_rsp_valid<=0;l_mc_rsp_data<=0;l_mc_rsp_tag<=0;scope_response_slot<=0;\n   scope_due[0]<=0;scope_due[1]<=0;\n', '')
start = s.index('   if(l_mc_req_valid&&l_mc_req_ready)begin')
end = s.index('   assert(l_protocol_fault_cycles', start)
s = s[:start] + '''
   if(l_mc_rsp_valid&&l_mc_rsp_ready)begin scope_returns<=scope_returns+1;$fwrite(trace_file,"%0d,SCOPE_RSP,%0d,%0d,0,0\\n",cycle,case_id,l_mc_rsp_tag);end
''' + s[end:]
s = s.replace('pending_mask==0', 'backend_pending==0&&debug_beats==0&&debug_descriptors==0')
s = s.replace('case_id,pending_mask', 'case_id,backend_pending')
s = s.replace('  result_ready_i=1;', '''  assert(backend_requests==331&&backend_returns==331&&backend_purges==1&&debug_beats==0&&debug_descriptors==0)else $fatal(1,"global real backend conservation");
  result_ready_i=1;''')
s = s.replace('PASS p_program_numeric', 'PASS p_program_fabric')
(root / 'tb_p_program_fabric.sv').write_text(s)
