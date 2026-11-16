"""Halt real COPY after a partial prefix, drain stream/M, then reuse owners."""
from pathlib import Path

root = Path(__file__).parent / 'rtl'
s = (root / 'tb_p_copy_stream.sv').read_text().replace('module tb_p_copy_stream;', 'module tb_p_copy_stream_cancel;')
s = s.replace(' integer cycle,seed,case_id,', ' integer cycle,seed,case_id,case_iteration,')
s = s.replace(' logic copy_start,copy_start_ready,', ' logic copy_halt,release_cancel;integer cancelled_A_reads,cancelled_copy_ACKs;\n logic copy_start,copy_start_ready,')
s = s.replace('copier(.clk,.reset,.halt(1\'b0)', 'copier(.clk,.reset,.halt(copy_halt)')
s = s.replace('.release_cancel(1\'b0)', '.release_cancel')
s = s.replace('if(ar_valid&&ar_ready)assert(copy_identity', 'if(ar_valid&&ar_ready&&!copy_halt)assert(copy_identity')
s = s.replace('  reset=1;', '  copy_halt=0;release_cancel=0;cancelled_A_reads=0;cancelled_copy_ACKs=0;reset=1;')
s = s.replace('case_id=0;seed=1;', 'case_id=0;case_iteration=0;seed=1;')
s = s.replace('for(integer ci=0;ci<8;ci=ci+1)', 'for(integer ci=0;ci<2;ci=ci+1)')
s = s.replace('case_id=ci;scope_data=scopes[ci];', 'case_iteration=ci;case_id=2;scope_data=scopes[case_id];copy_halt=0;release_cancel=0;')
s = s.replace('expect_memory[ci*4+', 'expect_memory[case_id*4+')
s = s.replace('tile<(int\'(scope_data[608+:16])>>7)', "tile<(ci==0?1:(int'(scope_data[608+:16])>>7))")
s = s.replace('    assert(!complete_error)', '    assert(complete_error==(case_iteration==0))')
s = s.replace('service_done_status==0)', "service_done_status==(ci==0?16'd1:16'd0))")
s = s.replace('      while(!copy_done)@(negedge clk);assert(!copy_error);', '''
      if(ci==0)begin
       while(copy_prefix[0+:11]<4)@(negedge clk);
       copy_halt=1;scope_cancel=1;release_cancel=1;
       $fwrite(trace_file,"%0d,HALT_ACTUAL_COPY,%0d,%0d,0,0\\n",cycle,case_id,copy_prefix[0+:11]);
      end
      while(!copy_done)@(negedge clk);assert(copy_error==(ci==0));''')
s = s.replace('assert(!a_load_proof_error&&a_source_reads_drained', 'assert(a_load_proof_error==(ci==0)&&a_source_reads_drained')
s = s.replace('      assert(rx_idle&&A_live!=0)', '      assert(rx_idle&&(ci==0||A_live!=0))')
s = s.replace('   service_done_ready=1;', '   if(ci==0)begin cancelled_A_reads=A_reads;cancelled_copy_ACKs=real_copy_ACKs;assert(cancelled_A_reads>0&&cancelled_A_reads<16&&cancelled_copy_ACKs>=cancelled_A_reads&&cancelled_copy_ACKs<16&&copy_idle&&rx_idle&&uowners==0&&owners==0&&M.scope_live==0&&exec.contexts_live==0)else $fatal(1,"actual partial COPY cancel leak");end\n   scope_cancel=0;service_done_ready=1;')
s = s.replace('   for(integer outword=0;', '   if(ci!=0)for(integer outword=0;')
s = s.replace('load_proofs==12&&poison_writes==192&&stale_prefix_checks==60&&real_copy_ACKs==192&&real_copy_reads==192&&real_headers==24&&real_quantizations==12', 'load_proofs==3&&poison_writes==48&&stale_prefix_checks==15&&real_copy_ACKs==cancelled_copy_ACKs+32&&real_copy_reads>=real_copy_ACKs&&real_copy_reads<=real_copy_ACKs+1&&real_headers==6&&real_quantizations==3')
s = s.replace('ACKs==24&&writes==24&&completed==18&&record_count==18&&A_reads==192', 'ACKs==2&&writes==2&&completed==4&&record_count==4&&A_reads==cancelled_A_reads+32')
s = s.replace('PASS p_copy_stream seed=%0d cases=8', 'PASS p_copy_stream_cancel seed=%0d real_copy_halt+same_owner_reuse')
(root / 'tb_p_copy_stream_cancel.sv').write_text(s)
