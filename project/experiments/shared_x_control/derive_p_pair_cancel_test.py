"""Actual two-prepared-bank cancel before EXEC or after first INPUT; same-key re-use."""
from pathlib import Path
p=Path(__file__).parent
s=(p/'rtl/tb_p_stream_pair_candidate.sv').read_text(encoding='utf-8').replace('tb_p_stream_pair_candidate','tb_p_stream_pair_cancel')
s=s.replace(' integer pair_first_core,pair_second_core,pair_first_rf,pair_core_count;\n logic pair_first_rf_frame;', ' integer cancel_mode,phase,abandoned,cancel_exec,replay_exec,real_cancel,real_drain,real_drop;')
s=s.replace('   pair_first_core<=0;pair_second_core<=0;pair_first_rf<=0;pair_core_count<=0;pair_first_rf_frame<=0;', '   abandoned<=0;cancel_exec<=0;replay_exec<=0;real_cancel<=0;real_drain<=0;real_drop<=0;')
a=s.index('   if(case_id==5)begin');b=s.index('   if(mc_req_valid',a)
s=s[:a]+'''   if(M.n_exec_valid&&M.n_exec_ready)begin
    if(phase==0)cancel_exec<=cancel_exec+1;else replay_exec<=replay_exec+1;
   end
   if(lc_valid&&lc_ready&&lc_sop&&lc_eop)begin
    if(lc_data[19:16]==6)real_cancel<=real_cancel+1;
    if(lc_data[19:16]==7)real_drain<=real_drain+1;
    if(lc_data[19:16]==4&&lc_data[127:112]==4)real_drop<=real_drop+1;
   end
'''+s[b:]
s=s.replace('    assert(!complete_error)else $fatal(1,"real native completion error");completed<=completed+1;last_complete_cycle<=cycle;', '''    assert(complete_error==(phase==0&&(cancel_mode==0||complete_sequence!=scope_data[352+:32])))
        else $fatal(1,"unexpected pair terminal error=%0d sequence%0d phase%0d mode%0d",complete_error,complete_sequence,phase,cancel_mode);
    if(complete_error)begin assert(complete_next_k==0);abandoned<=abandoned+1;end
    completed<=completed+1;last_complete_cycle<=cycle;''')
s=s.replace('  if($value$plusargs("SEED=%d",seed))begin end', '''  phase=0;cancel_mode=0;if($value$plusargs("CANCEL_MODE=%d",cancel_mode))begin end
  if($value$plusargs("SEED=%d",seed))begin end''')
s=s.replace('for(integer ci=0;ci<8;ci=ci+1)begin\n   case_id=ci;scope_data=scopes[ci];scope_data[48+:16]=16\'d2;scope_owner={32\'d1,32\'d7,32\'d8,32\'(ci+1)};', '''for(integer ci=0;ci<2;ci=ci+1)begin
   phase=ci;case_id=5;scope_data=scopes[case_id];scope_data[48+:16]=16'd2;scope_owner={32'd1,32'd7,32'd8,32'(ci+11)};
   $fwrite(trace_file,"%0d,PHASE,%0d,%0d,%0d,0\\n",cycle,case_id,phase,cancel_mode);''')
s=s.replace('   fork\n    begin', '''   fork
    begin
     if(phase==0)begin
      if(cancel_mode==0)begin
       while(!(exec.pair_first_pending&&exec.pair_hold_valid))@(negedge clk);
       assert(cancel_exec==0&&cancel_ready)else $fatal(1,"already executed before first pair cancel");
      end else begin
       while(!exec.pair_detached)@(negedge clk);
       assert(cancel_exec==1&&cancel_ready)else $fatal(1,"expected exactly one INPUT-done pair owner");
      end
      scope_cancel=1;pause();scope_cancel=0;
     end
    end
    begin''',1)
s=s.replace('service_done_status==0)',"service_done_status==(phase==0?16'd1:16'd0))")
s=s.replace("   for(integer outword=0;outword<int'(scope_data[592+:5])*2;outword=outword+1)host_word(0,128+outword,expect_memory[ci*4+outword]);", "   for(integer outword=0;outword<(phase==1?4:2*cancel_mode);outword=outword+1)host_word(0,128+outword,expect_memory[case_id*4+outword]);")
a=s.index('  assert(load_proofs==12');b=s.index('  $fclose(trace_file)',a)
s=s[:a]+'''  assert(load_proofs==2&&poison_writes==32&&stale_prefix_checks==10&&real_copy_ACKs==32&&real_copy_reads==32&&real_headers==4&&real_quantizations==2)
    else $fatal(1,"actual pair S/COPY lifetime accounting");
  assert(accepted==72&&accepted==returned&&ACKs==4+2*cancel_mode&&writes==ACKs&&completed==4&&record_count==4&&A_reads==32&&directory_faults==0)
    else $fatal(1,"pair conservation req%0d rsp%0d SACK%0d complete%0d acceptedrecord%0d Areads%0d",accepted,returned,ACKs,completed,record_count,A_reads);
  assert(cancel_exec==cancel_mode&&replay_exec==2&&abandoned==2-cancel_mode&&real_cancel==abandoned&&real_drain==abandoned&&real_drop==abandoned)
    else $fatal(1,"real pair cancellation terminals exec%0d replay%0d abandoned%0d CANCEL%0d DRAIN%0d DROP%0d",cancel_exec,replay_exec,abandoned,real_cancel,real_drain,real_drop);
  $display("PASS p_stream_pair_cancel mode=%0d seed=%0d cycles=%0d W64=%0d SACK=%0d abandoned=%0d exact_drain=%0d replay=%0d",cancel_mode,seed,cycle,accepted,ACKs,abandoned,real_drain,replay_exec);
'''+s[b:]
(p/'rtl/tb_p_stream_pair_cancel.sv').write_text(s,encoding='utf-8')
s=(p/'p_stream_pair_candidate.sbatch').read_text(encoding='utf-8').replace('tb_p_stream_pair_candidate','tb_p_stream_pair_cancel').replace('build/p_stream_pair_candidate','build/p_stream_pair_cancel').replace('250M2Ppair','250M2cancel')
s=s.replace('for init in 0 1 2;do','for mode in 0 1;do\nfor init in 0 1 2;do').replace('"+SEED=${seed}"','"+SEED=${seed}" "+CANCEL_MODE=${mode}"').replace('p-copy-stream-${seed}-${init}', 'p-pair-cancel-${mode}-${seed}-${init}')+'done\n'
(p/'p_stream_pair_cancel.sbatch').write_text(s,encoding='utf-8')
