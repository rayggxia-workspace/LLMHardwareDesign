"""Derive finite nine-peer SRAM regression without touching old testbench."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OLD=ROOT/'project/experiments/mother_control_v1'
HERE=Path(__file__).resolve().parent
def replace(s,a,b):
    assert a in s,a
    return s.replace(a,b)
wires=(OLD/'tb_wires.svh').read_text()
wires=replace(wires,'reg [31:0] local_image_id0_i;\nreg [31:0] local_image_id1_i;\nreg [1:0] local_enabled_i;', 'reg [287:0] local_image_ids_i;\nreg [8:0] local_enabled_i;')
wires=wires.replace('[7:0] trace_live_tokens_o','[15:0] trace_live_tokens_o')
for sig in ('trace_block_active_o','trace_terminal_full_o','trace_READY_full_o'):
    wires=wires.replace('[1:0] '+sig,'[8:0] '+sig)
wires=replace(wires,'mother_control_64 dut(.*);','reg recover_valid_i;\nwire recover_ready_o;\nwire [31:0] protocol_fault_count_o;\nmother_control_native64 dut(.*);')
wires=replace(wires,'mother_control_native64 dut(.*);','''`ifdef MC_TRANSPORT128
wire tx_valid,tx_ready,tx_sop,tx_eop,tx_credit;
wire [127:0] tx_data,rx_data;
wire [7:0] tx_target,rx_source;
wire rx_valid,rx_ready,rx_sop,rx_eop;
wire [31:0] frame_fault_count,peer_frame_faults;
wire transport_drained_i,peer_drained,peer_tx_credit;
mother_control_native64_transport128 dut(.*);
mc_packet128_bridge peer_frame(
  .clk(clk_i),.reset(!rst_ni),.core_task_valid(return_valid_i),.core_task_ready(return_ready_o),
  .core_task_packet(return_packet_i),.core_task_target(return_packet_i[24+:8]),.core_task_credit(1'b0),
  .tx_valid(rx_valid),.tx_ready(rx_ready),.tx_data(rx_data),.tx_target(rx_source),.tx_sop(rx_sop),.tx_eop(rx_eop),.tx_credit(peer_tx_credit),
  .rx_valid(tx_valid),.rx_ready(tx_ready),.rx_data(tx_data),.rx_source(tx_target),.rx_sop(tx_sop),.rx_eop(tx_eop),
  .core_return_valid(task_valid_o),.core_return_ready(task_ready_i),.core_return_packet(task_packet_o),
  .drained(peer_drained),.frame_fault_count(peer_frame_faults));
assign task_target_o=task_packet_o[24+:8];
assign task_credit_o=task_packet_o[16+:8]==0&&task_valid_o;
`else
mother_control_native64 dut(.*);
`endif''')
(HERE/'tb_native_wires.svh').write_text(wires)
init=(OLD/'tb_init.svh').read_text()
init=replace(init,'local_image_id0_i=0;\nlocal_image_id1_i=0;', 'local_image_ids_i=0;recover_valid_i=0;')
(HERE/'tb_native_init.svh').write_text(init)
tb=(OLD/'tb_mother.sv').read_text().replace('module tb_mother;','module tb_mc_native;')
tb=tb.replace('tb_wires.svh','tb_native_wires.svh').replace('tb_init.svh','tb_native_init.svh')
tb=tb.replace('[0:1]','[0:8]').replace('[1:0] child_busy','[8:0] child_busy').replace('k<2','k<9')
start=tb.index('  reg ret_locked=')
end=tb.index('  integer k;',start)
tb=tb[:start]+'''  reg ret_locked=0;
  reg [3:0] ret_lock_source=0,ret_rr=0;
  reg [3:0] selected_source;
  integer scan,choice;
  integer min_active=1,max_active=0,active_count;
  integer ready_mask=0;
  reg [511:0] held_result,held_task;
  reg previous_result_stall=0,previous_task_stall=0;
  always @* begin
    selected_source=ret_lock_source;choice=0;
    if(!ret_locked) begin
      selected_source=ret_rr;
      for(scan=8;scan>=0;scan=scan-1) begin
        choice=int'(ret_rr)+scan;
        if(choice>=9) choice=choice-9;
        if(child_return_valid[choice]) selected_source=4'(choice);
      end
    end
  end
'''+tb[end:]
tb=replace(tb,'child_return[b][0+:16]<=1;', 'child_return[b][0+:16]<=2;')
tb=replace(tb,'child_call[b][32+:32]+(bad_return!=0 ? 1 : 0)', 'child_call[b][32+:32]+(bad_return!=0 ? 1 : 0)')
tb=replace(tb,'child_return[b][136+:8]<=kind<2 ? 0 : 255;', 'child_return[b][136+:8]<=kind<2 ? 8\'(b) : 255;\n      child_return[b][352+:32]<=child_call[b][224+:32];child_return[b][384+:32]<=child_call[b][192+:32];')
tb=replace(tb,'ret_rr<=!selected_source;', "ret_rr<=selected_source==8 ? 0 : selected_source+1'b1;")
tb=replace(tb,'task_target_o>=2', 'task_target_o>=9')
tb=replace(tb,'task_packet_o[0+:16]!=1', 'task_packet_o[0+:16]!=2')
tb=replace(tb,'(task_target_o==0 ? local_image_id0_i : local_image_id1_i)', 'local_image_ids_i[32*task_target_o+:32] || task_packet_o[224+:32]!=start_generation_i')
tb=tb.replace('task_target_o[0]', 'task_target_o[3:0]')
tb=replace(tb,'if(task_target_o==1 && ready1!=0 && error_target!=1) begin peer_phase[1]<=1; peer_timer[1]<=ready_delay; end', 'if(ready_mask[task_target_o[4:0]] && error_target!=int\'(task_target_o)) begin peer_phase[task_target_o[3:0]]<=1; peer_timer[task_target_o[3:0]]<=ready_delay; end')
tb=replace(tb,'rst_ni && deploy_valid_i && task_target_o<2', 'rst_ni && task_target_o<9')
tb=replace(tb,"32'h01930001", "32'h02500002")
tb=replace(tb,"32'h17630001", "32'h02590003")
tb=replace(tb,'local_image_id0_i=100; local_image_id1_i=101; local_enabled_i=3;', "for(n=0;n<9;n=n+1) local_image_ids_i[32*n+:32]=32'(100+n);local_enabled_i=9'h1ff;")
tb=replace(tb, 'n=$value$plusargs("READY1=%d",ready1);', 'n=$value$plusargs("READY1=%d",ready1);n=$value$plusargs("READY_MASK=%d",ready_mask);n=$value$plusargs("MIN_ACTIVE=%d",min_active);')
tb=replace(tb, 'if(result_valid_o && result_ready_i) begin', '''active_count=$countones(trace_block_active_o);
      if(active_count>max_active) max_active=active_count;
      if(previous_result_stall) assert(result_valid_o && held_result=={230'b0,result_job_o,result_epoch_o,result_sequence_o,result_status_o,result_error_pc_o,result_source_o,result_child_error_pc_o,result_failed_task_sequence_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,result_counter_overflow_o,result_saturated_o}) else $fatal(1,"native mother result changed under backpressure");
      previous_result_stall<=result_valid_o&&!result_ready_i;
      held_result<={230'b0,result_job_o,result_epoch_o,result_sequence_o,result_status_o,result_error_pc_o,result_source_o,result_child_error_pc_o,result_failed_task_sequence_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,result_counter_overflow_o,result_saturated_o};
      if(previous_task_stall) assert(task_valid_o&&held_task==task_packet_o) else $fatal(1,"native mother task withdrew/changed");
      previous_task_stall<=task_valid_o&&!task_ready_i;held_task<=task_packet_o;
      if(result_valid_o && result_ready_i) begin''')
tb=replace(tb, '    $display("PASS mother calls=', '    assert(max_active>=min_active) else $fatal(1,"native resident concurrency was not exercised");\n    $display("PASS mother calls=')
tb=replace(tb, '    $finish;\n  end', '    $display("PASS native residents=%0d protocol_faults=%0d",max_active,protocol_fault_count_o);\n    $finish;\n  end')
tb=replace(tb,'  integer ready_mask=0;', '''  integer ready_mask=0,inject_mode=0,recover_poison=0;
  integer runtime_cycles=0,runtime_PM_reads=0;
  reg inject_valid=0;
  reg [511:0] inject_packet=0,last_good_return=0;
''')
tb=replace(tb,'return_valid_i=child_return_valid[selected_source];\n    return_packet_i=child_return[selected_source];', 'return_valid_i=inject_valid || child_return_valid[selected_source];\n    return_packet_i=inject_valid ? inject_packet : child_return[selected_source];')
tb=replace(tb,'if(return_valid_i && return_ready_o) begin', 'if(return_valid_i && return_ready_o && !inject_valid) begin\n        last_good_return<=child_return[selected_source];')
tb=replace(tb,'    end else begin\n      ret_locked', '''    end else begin
      if(runtime_active) begin
        runtime_cycles<=runtime_cycles+1;
        if(dut.pm_req_valid_o && dut.pm_req_ready_i && !dut.pm_req_write_o) runtime_PM_reads<=runtime_PM_reads+1;
      end
      ret_locked''')
tb=replace(tb,'n=$value$plusargs("READY1=%d",ready1);', 'n=$value$plusargs("INJECT=%d",inject_mode);n=$value$plusargs("RECOVER_POISON=%d",recover_poison);n=$value$plusargs("READY1=%d",ready1);')
tb=replace(tb,'result_status_o!=(recover_error!=0 && ji>0 ? 0 : expect_status[15:0])', 'result_status_o!=(inject_mode==8 && ji==0 ? 16\'d0 : recover_error!=0 && ji>0 ? 16\'d0 : expect_status[15:0])')
tb=replace(tb,'      if(expected_poison!=0) begin', '''      if(inject_mode!=0 && (inject_mode!=8 || ji>0)) begin
        while(calls<(ji+1)*(expected_calls/runs)) @(negedge clk_i);
        if(inject_mode==3) while(!trace_terminal_full_o[0]) @(negedge clk_i);
        if(inject_mode==7) while(!result_valid_o) @(negedge clk_i);
        inject_packet=0;inject_packet[0+:16]=2;inject_packet[16+:8]=2;
        inject_packet[24+:8]=0;inject_packet[32+:96]=child_call[0][32+:96];
        inject_packet[128+:8]=child_call[0][136+:8];inject_packet[136+:8]=255;
        inject_packet[320+:32]=32'hffffffff;inject_packet[352+:32]=child_call[0][224+:32];
        inject_packet[384+:32]=child_call[0][192+:32];
        case(inject_mode)
          1: inject_packet[352+:32]=inject_packet[352+:32]+1;
          2: inject_packet[24+:8]=8;
          3,7,8: inject_packet=last_good_return;
          4: inject_packet[32+:32]=inject_packet[32+:32]-1;
          5: inject_packet[384+:32]=inject_packet[384+:32]^1;
          6: inject_packet[0+:16]=1;
          default: $fatal(1,"unknown injection");
        endcase
        @(negedge clk_i);inject_valid=1;@(posedge clk_i);while(!return_ready_o) @(posedge clk_i);
        assert(return_ready_o) else $fatal(1,"malformed return blocked transport drain");
        @(negedge clk_i);inject_valid=0;
      end
      if(expected_poison!=0) begin''')
tb=replace(tb,'        if(result_valid_o || image_valid_o || start_ready_o || cfg_req_ready_o) $fatal(1,"mother poison fabricated result/admission");', '''        if(result_valid_o || image_valid_o || start_ready_o || cfg_req_ready_o) $fatal(1,"mother poison fabricated result/admission");
        if(recover_poison!=0) begin
          assert(!recover_ready_o && trace_block_active_o!=0) else $fatal(1,"quarantine lost outstanding owner before late terminal");
          no_terminal=-1;
          while(!recover_ready_o) @(negedge clk_i);
          recover_valid_i=1;@(negedge clk_i);recover_valid_i=0;
          assert(!poison_o && life_o==1 && !start_ready_o && !image_valid_o && !result_valid_o && trace_block_active_o==0) else $fatal(1,"quarantine clear resumed stale PC/image");
        end''')
tb=replace(tb,'    $display("PASS native residents=%0d protocol_faults=%0d",max_active,protocol_fault_count_o);', '    $display("PASS native residents=%0d protocol_faults=%0d runtime_cycles=%0d runtime_PM_reads=%0d",max_active,protocol_fault_count_o,runtime_cycles,runtime_PM_reads);')
tb=replace(tb,'  integer k;', '''`ifdef MC_TRANSPORT128
  assign transport_drained_i=peer_drained&&child_busy==0&&child_return_valid==0&&!inject_valid;
`endif
  integer k;''')
tb=replace(tb,'        if(dut.pm_req_valid_o && dut.pm_req_ready_i && !dut.pm_req_write_o) runtime_PM_reads<=runtime_PM_reads+1;', '''`ifdef MC_TRANSPORT128
        if(dut.mother.pm_req_valid_o && dut.mother.pm_req_ready_i && !dut.mother.pm_req_write_o) runtime_PM_reads<=runtime_PM_reads+1;
`else
        if(dut.pm_req_valid_o && dut.pm_req_ready_i && !dut.pm_req_write_o) runtime_PM_reads<=runtime_PM_reads+1;
`endif''')
(HERE/'tb_mc_native.sv').write_text(tb)

# Expanded *fixture* capacity is not extra hardware memory.
path=HERE/'tb_mc_native.sv'
text=path.read_text().replace('[0:295]','[0:1024]')
text=text.replace('    config_command(0,0,0,0);', '    config_command(0,0,0,mode==6 ? 3 : 0);\n    if(mode==6) begin\n      assert(!image_valid_o&&!start_ready_o&&life_o==1);$display("PASS mother oversized PM metadata rejected");$finish;disable scenario;\n    end')
from extend_loop_testbench import extend
text=extend(text).replace('#500000;', '#5000000;')
from timing_extension import extend as timing_extend
text=timing_extend(text)
path.write_text(text)
