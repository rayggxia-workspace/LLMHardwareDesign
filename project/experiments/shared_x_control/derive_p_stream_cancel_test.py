"""Stop a real streamed A LOAD after four words, cancel W, then reuse RF."""
from pathlib import Path

root = Path(__file__).parent / 'rtl'
s = (root / 'tb_p_native_stream_executor.sv').read_text().replace(
    'module tb_p_native_stream_executor;', 'module tb_p_native_stream_cancel;')
s = s.replace(' integer cycle,seed,case_id,', ' integer cycle,seed,case_id,case_iteration,')
s = s.replace('for(integer ci=0;ci<8;ci=ci+1)', 'for(integer ci=0;ci<2;ci=ci+1)')
s = s.replace('case_id=ci;scope_data=scopes[ci];', 'case_iteration=ci;case_id=2;scope_data=scopes[case_id];')
s = s.replace('A_memory[ci*32+', 'A_memory[case_id*32+').replace('expect_memory[ci*4+', 'expect_memory[case_id*4+')
s = s.replace('case_id=0;seed=1;', 'case_id=0;case_iteration=0;seed=1;')
s = s.replace('stream_window_generation=1;', "stream_window_generation=16'(ci+1);")
s = s.replace('    assert(!complete_error)', '    assert(complete_error==(case_iteration==0))')
s = s.replace('service_done_status==0)', "service_done_status==(ci==0?16'd1:16'd0))")
s = s.replace('     for(integer tile=0;', '''
     if(ci==0)begin
      while(!(exec.load_pending==0&&exec.A_front.data_front.data_front.state[0]==1))@(negedge clk);
      copy_progress_generation=stream_window_generation;copy_progress_k_elements=0;
      copy_progress_session=stream_window_session;copy_progress_ticket=stream_window_ticket;copy_committed_prefix=0;
      for(integer wi=0;wi<4;wi=wi+1)begin host_word(1,wi,A_memory[case_id*32+wi]);copy_committed_prefix=11'(wi+1);end
      host_mode=0;
      while(A_reads!=4)@(negedge clk);pause(3);
      assert(!a_valid&&!a_load_proof_valid)else $fatal(1,"partial source tile became executable");
      scope_cancel=1;
      while(!a_load_proof_valid)@(negedge clk);
      assert(a_load_proof_error&&a_source_reads_drained&&a_load_proof_key==stream_window_key&&
          a_load_proof_window_generation==stream_window_generation&&a_load_proof_window_session==stream_window_session&&
          a_load_proof_window_ticket==stream_window_ticket&&a_load_proof_k_elements==0&&a_load_proof_A_slot==0)else $fatal(1,"cancelled LOAD terminal identity");
      pause(3);assert(a_load_proof_valid&&!a_valid);a_load_proof_ready=1;pause();a_load_proof_ready=0;load_proofs=load_proofs+1;
     end else for(integer tile=0;''', 1)
s = s.replace('   service_done_ready=1;', '   scope_cancel=0;service_done_ready=1;')
s = s.replace('   for(integer outword=0;', '   if(ci!=0)for(integer outword=0;')
s = s.replace('load_proofs==12&&poison_writes==192&&stale_prefix_checks==48', 'load_proofs==3&&poison_writes==32&&stale_prefix_checks==8')
s = s.replace('ACKs==24&&writes==24&&completed==18&&record_count==18&&A_reads==192', 'ACKs==2&&writes==2&&completed==4&&record_count==4&&A_reads==36')
s = s.replace('PASS p_native_stream_executor seed=%0d cases=8', 'PASS p_native_stream_cancel seed=%0d partial_cancel+same_context_reuse')
(root / 'tb_p_native_stream_cancel.sv').write_text(s)
