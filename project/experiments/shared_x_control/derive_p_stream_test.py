"""Native stream adapter with actual M/S and stale same-key COPY prefixes.

The unchanged typed range provider is used only as a K128/256 record source;
this fixture does not claim service2, LC outer, or COPY producer qualification.
"""
from pathlib import Path

root = Path(__file__).parent / 'rtl'
s = (root / 'tb_p_native_record_executor.sv').read_text().replace(
    'module tb_p_native_record_executor;', 'module tb_p_native_stream_executor;')
s = s.replace(' p_native_record_executor exec(.*);', '''
 logic stream_window_valid,copy_progress_valid,a_load_proof_valid,a_load_proof_ready;
 logic [127:0] stream_window_key,a_load_proof_key;
 logic [15:0] stream_window_generation,copy_progress_generation,a_load_proof_window_generation;
 logic [31:0] stream_window_session,stream_window_ticket,copy_progress_session,copy_progress_ticket,a_load_proof_window_session,a_load_proof_window_ticket;
 logic [15:0] stream_window_k_elements,copy_progress_k_elements,a_load_proof_k_elements,a_load_proof_A_generation;
 logic a_load_proof_A_slot,a_load_proof_error,a_source_reads_drained;
 logic [5:0] a_load_proof_shift;
 logic allow_native_A,m_a_ready;
 integer load_proofs,poison_writes,stale_prefix_checks;
 p_native_stream_record_executor exec(.*);''')
s = s.replace('.a_valid,.a_ready,.a_data', '.a_valid(a_valid&&allow_native_A),.a_ready(m_a_ready),.a_data')
s = s.replace(' assign mc_close_ready=1;', ' assign a_ready=m_a_ready&&allow_native_A;\n assign mc_close_ready=1;')
s = s.replace('  reset=1;', '''
  stream_window_valid=0;stream_window_key=0;stream_window_generation=0;stream_window_k_elements=0;
  stream_window_session=0;stream_window_ticket=0;copy_progress_session=0;copy_progress_ticket=0;
  copy_progress_valid=0;copy_progress_generation=0;copy_progress_k_elements=0;
  a_load_proof_ready=0;allow_native_A=0;load_proofs=0;poison_writes=0;stale_prefix_checks=0;
  reset=1;''')
begin = s.index('   for(integer word_id=0;')
end = s.index('   host_mode=0;pause();', begin)
s = s[:begin] + '''
   stream_window_key=scope_data[128+:128];stream_window_generation=1;stream_window_session=32'(ci+1);stream_window_ticket=32'(ci+100);stream_window_k_elements=0;stream_window_valid=1;
   // A command/header may already be admitted while COPY still describes a
   // previous generation or another K tile of the same key.
   copy_progress_valid=1;copy_progress_generation=0;copy_progress_k_elements=128;copy_committed_prefix=16;
   publish_k=0;directory_publish=1;
   do @(posedge clk);while(!directory_publish_ready);@(negedge clk);directory_publish=0;
''' + s[end:]
s = s.replace('   fork\n', '''   fork
    begin
     for(integer tile=0;tile<(int'(scope_data[608+:16])>>7);tile=tile+1)begin
      allow_native_A=0;
      // The initial/next header is current, but old COPY prefix16 is not.
      while(!exec.A_front.data_front.data_front.state[0]&&!exec.A_front.data_front.data_front.state[1])@(negedge clk);
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
       while(exec.k==16'(tile*128)||exec.state!=exec.IDLE)@(negedge clk);
      end
     end
    end
''', 1)
# Wait until the next first-record command has really been accepted, rather
# than peeking at an enum from a preceding active slot.
s = s.replace('      while(!exec.A_front.data_front.data_front.state[0]&&!exec.A_front.data_front.data_front.state[1])@(negedge clk);', "      while(!(exec.k==16'(tile*128)&&exec.load_pending==0&&exec.A_front.data_front.data_front.state[1'(tile)]==1))@(negedge clk);")
s = s.replace('       while(exec.k==16\'(tile*128)||exec.state!=exec.IDLE)@(negedge clk);', "       while(exec.k==16'(tile*128))@(negedge clk);")
s = s.replace('  assert(accepted==returned', '  assert(load_proofs==12&&poison_writes==192&&stale_prefix_checks==48)else $fatal(1,"stream finite proof accounting");\n  assert(accepted==returned')
s = s.replace('PASS p_native_record_executor', 'PASS p_native_stream_executor')
(root / 'tb_p_native_stream_executor.sv').write_text(s)
