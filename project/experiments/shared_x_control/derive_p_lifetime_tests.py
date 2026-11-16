"""Real M/S tests for drained namespace fences and ordinary scope cancellation."""
from pathlib import Path
root = Path(__file__).parent / 'rtl'
base = (root / 'tb_p_native_record_executor.sv').read_text()
f = base.replace('module tb_p_native_record_executor;', 'module tb_p_native_fence;')
f = f.replace('p_native_record_executor exec(.*);', 'p_native_record_executor #(.SESSION_LIMIT(32),.A_GENERATION_LIMIT(2),.W_GENERATION_LIMIT(1)) exec(.*);')
begin = f.index(' assign mc_fence_req_ready=0;')
end = f.index(' logic host_mode', begin)
f = f[:begin] + '''
 logic backend_fence_live,wrong_fence_sent;
 logic [31:0] backend_fence_cookie;
 logic [8:0] backend_fence_epoch;
 integer backend_fence_due,fence_requests,fence_returns,wrong_fence_returns;
 assign mc_fence_req_ready=!backend_fence_live;
 assign mc_fence_done_valid=backend_fence_live&&(!wrong_fence_sent||cycle>=backend_fence_due);
 assign mc_fence_done_cookie=backend_fence_cookie^(wrong_fence_sent?32'd0:32'd1);
 assign mc_fence_done_epoch=backend_fence_epoch;
 always @(posedge clk)begin
  if(reset)begin backend_fence_live<=0;wrong_fence_sent<=0;backend_fence_cookie<=0;backend_fence_epoch<=0;
   backend_fence_due<=0;fence_requests<=0;fence_returns<=0;wrong_fence_returns<=0;end
  else begin
   if(mc_fence_req_valid&&mc_fence_req_ready)begin
    assert(pending_mask==0&&channel_live[0]==0&&channel_live[1]==0)else $fatal(1,"FENCE before true backend drain");
    backend_fence_live<=1;backend_fence_cookie<=mc_fence_req_cookie;backend_fence_epoch<=mc_fence_req_epoch;
    backend_fence_due<=cycle+8+seed;fence_requests<=fence_requests+1;
    // A single deliberate invalid-cookie packet must not release/rearm owner.
    if(fence_requests!=0)wrong_fence_sent<=1;
    $fwrite(trace_file,"%0d,FENCE_REQ,%0d,%0d,%0d,0\\n",cycle,case_id,mc_fence_req_cookie,mc_fence_req_epoch);
   end
   if(mc_fence_done_valid&&mc_fence_done_ready)begin
    if(!wrong_fence_sent)begin wrong_fence_sent<=1;wrong_fence_returns<=wrong_fence_returns+1;end
    else begin backend_fence_live<=0;fence_returns<=fence_returns+1;end
    $fwrite(trace_file,"%0d,FENCE_BACKEND_DONE,%0d,%0d,%0d,0\\n",cycle,case_id,mc_fence_done_cookie,wrong_fence_sent);
   end
   if(backend_fence_live)assert(!record_ready)else $fatal(1,"namespace rearmed before actual purge proof");
   if(fault_interrupt)assert(M.local_valid&&M.local_frame[39:32]==7&&M.local_frame[47:40]==14&&M.local_frame[111:48]==0)else $fatal(1,"unexpected owned M fault");
  end
 end
''' + f[end:]
f = f.replace('&&!fault_interrupt&&protocol_faults==0', '&&protocol_faults<=1')
f = f.replace('  $display("PASS p_native_record_executor', '''  assert(fence_requests>=17&&fence_returns==fence_requests&&wrong_fence_returns==1&&protocol_faults==1&&!backend_fence_live&&exec.fence_count==32'(fence_returns))else $fatal(1,"real namespace fence accounting");
  $display("PASS p_native_fence''')
(root / 'tb_p_native_fence.sv').write_text(f)

c = base.replace('module tb_p_native_record_executor;', 'module tb_p_native_cancel;')
c = c.replace(' integer cycle,seed,case_id,', ' integer cycle,seed,case_id,case_iteration,')
c = c.replace('assert(!complete_error)', 'assert(complete_error==(case_iteration==8))')
c = c.replace('for(integer ci=0;ci<8;ci=ci+1)', 'for(integer ci=0;ci<10;ci=ci+1)')
c = c.replace("case_id=ci;scope_data=scopes[ci];", "case_iteration=ci;case_id=ci<8?ci:3;scope_data=scopes[case_id];")
c = c.replace('A_memory[ci*32+word_id]', 'A_memory[case_id*32+word_id]')
c = c.replace('expect_memory[ci*4+outword]', 'expect_memory[case_id*4+outword]')
c = c.replace('case_id=0;seed=1;', 'case_id=0;case_iteration=0;seed=1;')
c = c.replace('   fork\n', '''   fork
    begin
     if(ci==8)begin
      do @(posedge clk);while(!(a_valid&&a_ready&&a_beat==3));
      @(negedge clk);scope_cancel=1;
      $fwrite(trace_file,"%0d,CANCEL_SCOPE,%0d,%0d,0,0\\n",cycle,case_id,record_sequence);
     end
    end
''', 1)
c = c.replace('service_done_status==0)', 'service_done_status==(ci==8?16\'d1:16\'d0))')
c = c.replace('   service_done_ready=1;', '   if(ci==8)assert(M.scope_live==0&&exec.contexts_live==0&&A_live==0)else $fatal(1,"cancel left real RF/A owner live");\n   scope_cancel=0;service_done_ready=1;')
c = c.replace('   for(integer outword=0;', '   if(ci!=8)for(integer outword=0;')
c = c.replace('ACKs==24&&writes==24&&completed==18&&record_count==18&&A_reads==192', 'ACKs==28&&writes==28&&completed==24&&record_count==24&&A_reads==240')
c = c.replace('PASS p_native_record_executor seed=%0d cases=8', 'PASS p_native_cancel seed=%0d cases=8+cancel+reuse')
(root / 'tb_p_native_cancel.sv').write_text(c)

a = base.replace('module tb_p_native_record_executor;', 'module tb_p_native_admission;')
a = a.replace(' logic [1023:0] scopes[0:7];', ' logic [1023:0] invalid_scopes[2];logic bad_profile_phase;\n logic [1023:0] scopes[0:7];')
a = a.replace('  reset=1;', '  bad_profile_phase=0;reset=1;')
a = a.replace('  $readmemh({vectors,"/scopes.mem"},scopes);', '  $readmemh({vectors,"/invalid-native.mem"},invalid_scopes);\n  $readmemh({vectors,"/scopes.mem"},scopes);')
a = a.replace('   assert(!quarantine', '   if(bad_profile_phase)assert(!record_valid&&!ar_valid&&!sw_valid&&!lc_valid&&!mc_req_valid)else $fatal(1,"unregistered native profile issued work");\n   assert(!quarantine')
a = a.replace('  assert(accepted==returned', '''  bad_profile_phase=1;
  for(integer bad=0;bad<2;bad=bad+1)begin
   case_id=2;scope_data=invalid_scopes[bad];scope_owner={32'd1,32'd7,32'd8,32'(9+bad)};
   host_mode=0;service_valid=1;do @(posedge clk);while(!(service_ready&&scope_ready));@(negedge clk);service_valid=0;
   while(!service_done_valid)@(negedge clk);
   assert(service_done_status==43&&service_done_owner==scope_owner)else $fatal(1,"native shape/restore admission status %0d",service_done_status);
   service_done_ready=1;pause();service_done_ready=0;pause(2);assert(quiescent);
  end
  bad_profile_phase=0;
  assert(accepted==returned''')
a = a.replace('PASS p_native_record_executor', 'PASS p_native_admission')
(root / 'tb_p_native_admission.sv').write_text(a)
