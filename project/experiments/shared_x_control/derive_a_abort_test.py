"""Extend the already real-SRAM A/copy fixture with explicit abort cases."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'rtl/tb_native_s_a_copy.sv').read_text().replace('module tb_native_s_a_copy;','module tb_native_s_a_abort;')
s=s.replace('  private_a_tile_frontend front(','''  logic abort_valid,abort_ready,abort_transport_drained,abort_slot;
  logic [127:0] abort_key;
  logic [15:0] abort_generation,abort_kk,abort_use_sequence;
  private_a_tile_abort_frontend front(''',1)
s=s.replace('    reset=1;halt=0;flush=0;', '''    abort_valid=0;abort_transport_drained=0;abort_slot=0;abort_key=0;
    abort_generation=0;abort_kk=0;abort_use_sequence=0;
    reset=1;halt=0;flush=0;''',1)
anchor='    $display("PASS native_s_a_copy'
start=s.index(anchor)
extra='''    // Execute a real partially consumed A tile, then receive a verified
    // M ABORT identity. The fixture supplies that proof; actual M join follows.
    cmd_slot=0;cmd_generation=2;cmd_kk=0;cmd_planned_uses=1;cmd_key=start_key;
    cmd_S_base=100;cmd_copy_offset=0;cmd_valid=1;
    do @(posedge clk);while(!cmd_ready);@(negedge clk);cmd_valid=0;
    while(!load_done_valid)@(negedge clk);
    assert(!load_done_error&&load_done_generation==2);load_done_ready=1;pause();load_done_ready=0;
    w_slot=0;w_generation=2;w_kk=0;w_use_sequence=1;w_key=start_key;w_record=2001;w_valid=1;
    do @(posedge clk);while(!w_ready);@(negedge clk);w_valid=0;
    use_slot=0;use_generation=2;use_kk=0;use_sequence=1;use_key=start_key;use_valid=1;
    do @(posedge clk);while(!use_ready);@(negedge clk);use_valid=0;
    for(integer step=0;step<3;step=step+1)begin
      assert(a_valid&&a_step==3'(step)&&a_data=={source_word(2*step+1),source_word(2*step)});
      a_ready=1;pause();a_ready=0;
    end
    assert(a_valid&&a_step==3&&!quiescent);halt=1;
    abort_valid=1;abort_slot=0;abort_key=start_key^128'd1;abort_generation=2;abort_kk=0;abort_use_sequence=1;
    abort_transport_drained=1;pause();assert(!abort_ready&&a_valid&&live_slots[0]);
    abort_key=start_key;abort_generation=1;pause();assert(!abort_ready&&a_valid&&live_slots[0]);
    abort_generation=2;abort_kk=1;pause();assert(!abort_ready&&a_valid&&live_slots[0]);
    abort_kk=0;abort_use_sequence=2;pause();assert(!abort_ready&&a_valid&&live_slots[0]);
    abort_use_sequence=1;abort_transport_drained=0;pause(7);
    assert(!abort_ready&&!a_valid&&!quiescent&&live_slots[0]);
    flush=1;pause();flush=0;assert(live_slots[0]);
    // Actual no-more-issue/return drain proof finally arrives. Missing five
    // operand beats are never counted, and the lease is still not FREE.
    abort_transport_drained=1;do @(posedge clk);while(!abort_ready);@(negedge clk);abort_valid=0;
    assert(!a_valid&&quiescent&&source_reads_drained&&live_slots[0]);
    assert(front.issued[0]==1&&front.completed[0]==0);
    flush=1;pause();flush=0;halt=0;assert(live_slots==0&&quiescent);
    // Reuse with a new generation. A late old ABORT cannot kill the new use.
    cmd_generation=3;cmd_valid=1;do @(posedge clk);while(!cmd_ready);@(negedge clk);cmd_valid=0;
    while(!load_done_valid)@(negedge clk);
    assert(load_done_generation==3&&!load_done_error);load_done_ready=1;pause();load_done_ready=0;
    w_generation=3;w_record=3001;w_valid=1;do @(posedge clk);while(!w_ready);@(negedge clk);w_valid=0;
    use_generation=3;use_valid=1;do @(posedge clk);while(!use_ready);@(negedge clk);use_valid=0;
    halt=1;abort_generation=2;abort_valid=1;pause();assert(!abort_ready&&a_valid&&live_slots[0]);
    abort_valid=0;halt=0;
    for(integer step=0;step<8;step=step+1)begin
      assert(a_valid&&a_generation==3&&a_step==3'(step)&&a_data=={source_word(2*step+1),source_word(2*step)});
      a_ready=1;pause();a_ready=0;
    end
    close_generation=3;close_slot=0;close_valid=1;do @(posedge clk);while(!close_ready);@(negedge clk);close_valid=0;
    release_generation=3;release_slot=0;release_valid=1;do @(posedge clk);while(!release_ready);@(negedge clk);release_valid=0;
    assert(live_slots==0&&quiescent&&Areads==64&&fault_cycles==7);
'''
s=s[:start]+extra+s[start:]
s=s.replace('PASS native_s_a_copy','PASS native_s_a_abort')
(HERE/'rtl/tb_native_s_a_abort.sv').write_text(s)
