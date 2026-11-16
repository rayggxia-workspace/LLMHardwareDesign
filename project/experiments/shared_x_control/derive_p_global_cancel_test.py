"""Actual MC wrong-source fault -> LC CANCEL -> real P/M/S/global drain.

The injected frame is an external protocol error; all legitimate descriptor,
weight, operand, RF and store completion paths remain the production RTL.
"""
from pathlib import Path

root = Path(__file__).parent / 'rtl'
s = (root / 'tb_p_program_fabric.sv').read_text().replace(
    'module tb_p_program_fabric;', 'module tb_p_program_global_cancel;')
s = s.replace(' integer MC_calls,MC_returns,MC_PM_reads,LC_PM_reads,scope_returns;', '''
 integer MC_calls,MC_cancels,MC_returns,MC_PM_reads,LC_PM_reads,scope_returns;
 logic inject_valid;logic [1:0] inject_word;logic [511:0] inject_packet;
 wire mother_rx_valid=inject_valid||l_tx_valid;
 wire [127:0] mother_rx_data=inject_valid?inject_packet[128*inject_word+:128]:l_tx_data;
 wire [7:0] mother_rx_source=inject_valid?8'd8:l_tx_source;
 wire mother_rx_sop=inject_valid?inject_word==0:l_tx_sop;
 wire mother_rx_eop=inject_valid?inject_word==3:l_tx_eop;
 logic mother_rx_ready;
 assign l_tx_ready=mother_rx_ready&&!inject_valid;
''')
s = s.replace('.rx_valid(l_tx_valid)', '.rx_valid(mother_rx_valid)').replace(
    '.rx_ready(l_tx_ready)', '.rx_ready(mother_rx_ready)').replace(
    '.rx_data(l_tx_data)', '.rx_data(mother_rx_data)').replace(
    '.rx_source(l_tx_source)', '.rx_source(mother_rx_source)').replace(
    '.rx_sop(l_tx_sop)', '.rx_sop(mother_rx_sop)').replace(
    '.rx_eop(l_tx_eop)', '.rx_eop(mother_rx_eop)')
s = s.replace('MC_calls<=0;MC_returns<=0;', 'MC_calls<=0;MC_cancels<=0;MC_returns<=0;')
s = s.replace('    assert(l_rx_data[23:16]==0&&l_rx_target==0)else $fatal(1,"unexpected task/cancel");MC_calls<=MC_calls+1;', '''
    assert(l_rx_target==0&&l_rx_data[23:16]<=1)else $fatal(1,"unexpected task/cancel");
    if(l_rx_data[23:16]==0)MC_calls<=MC_calls+1;else MC_cancels<=MC_cancels+1;''')
s = s.replace('    assert(l_retired_instructions==3)', '    if(case_id<2)assert(l_retired_instructions==3)')
s = s.replace('protocol_fault_count_o==0)', 'protocol_fault_count_o<=(case_id==2?32\'d1:32\'d0))')
s = s.replace('    assert(!complete_error)', '    assert(!complete_error||case_id==2)')
s = s.replace('  reset=1;', '  inject_valid=0;inject_word=0;inject_packet=0;reset=1;')
s = s.replace('for(integer ci=0;ci<8;ci=ci+1)', 'for(integer ci=0;ci<3;ci=ci+1)')
s = s.replace('   fork\n', '''   fork
    begin
     if(ci==2)begin
      do @(posedge clk);while(!(a_valid&&a_ready&&a_beat==3));
      @(negedge clk);
      inject_packet=0;inject_packet[0+:16]=2;inject_packet[16+:8]=2;inject_packet[24+:8]=8;
      inject_packet[32+:32]=7;inject_packet[64+:32]=8;inject_packet[96+:32]=1;
      inject_packet[136+:8]=255;inject_packet[320+:32]=32'hffffffff;
      inject_packet[352+:32]=1;inject_packet[384+:32]=25001;inject_valid=1;
      $fwrite(trace_file,"%0d,INJECT_WRONG_SOURCE,%0d,8,0,0\\n",cycle,case_id);
      for(integer w=0;w<4;w=w+1)begin inject_word=2'(w);do @(posedge clk);while(!mother_rx_ready);@(negedge clk);end
      inject_valid=0;
     end
    end
''', 1)
s = s.replace('service_done_status==0)', "service_done_status==(ci==2?16'd1:16'd0))")
s = s.replace('   for(integer outword=0;', '   if(ci!=2)for(integer outword=0;')
begin = s.index('  assert(accepted==returned&&ACKs==24')
end = s.index('  result_ready_i=1;', begin)
s = s[:begin] + '''
  while(!result_valid_o)@(negedge clk);
  assert(result_status_o==17&&MC_calls==3&&MC_cancels==1&&MC_returns==3&&scope_returns==6&&
      protocol_fault_count_o==1&&frame_fault_count==0&&l_protocol_fault_cycles==0&&
      trace_live_tokens_o==0&&trace_block_active_o==0&&trace_aborting_o)else
    $fatal(1,"real MC cancellation status%0d calls%0d cancel%0d return%0d fault%0d",result_status_o,MC_calls,MC_cancels,MC_returns,protocol_fault_count_o);
  assert(accepted==returned&&backend_requests==backend_returns&&backend_pending==0&&debug_beats==0&&debug_descriptors==0&&
      ACKs==6&&writes==6&&A_reads==48&&completed==5&&record_count==5&&directory_faults==0&&M.scope_live==0&&exec.contexts_live==0&&
      quiescent&&A_live==0&&command_occupied==0&&result_occupied==0&&l_idle)else $fatal(1,"real MC cancellation owner leak");
''' + s[end:]
s = s.replace('PASS p_program_fabric seed=%0d cases=8', 'PASS p_program_global_cancel seed=%0d cases=2+cancel')
s = s.replace('  result_ready_i=1;pause();result_ready_i=0;', '  result_ready_i=1;pause();result_ready_i=0;pause();assert(!trace_aborting_o&&life_o==5)else $fatal(1,"MC abort status not released by true result ACK");')
(root / 'tb_p_program_global_cancel.sv').write_text(s)
