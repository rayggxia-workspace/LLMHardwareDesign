`timescale 1ns/1ps
module tb_mc_native;
`include "tb_native_wires.svh"
  integer cycle=0,stall=0,words=0,mode=0,runs=1,n,ji;
  integer request_wait=0,returns=0,calls=0,cancels=0,ready_count=0;
  integer ready1=0,dependency=0,error_target=-1,no_terminal=-1,hold_target=-1,hold_cycles=0,hold_age=0;
  integer delay0=20,delay1=24,ready_delay=6,ready_scalar=1,traffic=0,bad_return=0,prefix_max=0,recover_error=0;
  integer expected_calls=0,expected_cancels=0,expected_results=1,expect_status=0,expected_poison=0;
  integer cfg_expect=0,pm_error=0,peer_timer[0:8],peer_phase[0:8];
  integer timing_file=0;
  string timing_path;
  integer check_ptr=0,expect_ready=-1,check_targets=0;
  reg [63:0] ptr_start=0,ptr_stride=128;
  reg [7:0] oracle_targets[0:4095];
  string targets_path;
  reg [127:0] input_image[0:1024],memory[0:1024];
  reg [2047:0] image_path;
  reg pm_pending=0,pending_write;
  reg [13:0] pending_address;
  reg [127:0] pending_data;
  reg [8:0] child_busy=0,child_return_valid=0,child_cancelled=0,ever_called=0;
  reg [511:0] child_call[0:8],child_return[0:8];
  reg ret_locked=0;
  reg [3:0] ret_lock_source=0,ret_rr=0;
  reg [3:0] selected_source;
  integer scan,choice;
  integer min_active=1,max_active=0,active_count;
  integer ready_mask=0,inject_mode=0,recover_poison=0;
  integer runtime_cycles=0,runtime_PM_reads=0;
  reg inject_valid=0;
  reg [511:0] inject_packet=0,last_good_return=0;

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
`ifdef MC_TRANSPORT128
  assign transport_drained_i=peer_drained&&child_busy==0&&child_return_valid==0&&!inject_valid;
`endif
  integer k;
  reg [31:0] expected_image,expected_topology;
  reg [31:0] runtime_fault_addr=32'hffffffff;
  reg [127:0] runtime_fault_xor=0;
  reg runtime_active=0;
  initial clk_i=0;
  always #5 clk_i=~clk_i;
always @(posedge clk_i) cycle <= cycle+1;
  always @* begin
    return_valid_i=inject_valid || child_return_valid[selected_source];
    return_packet_i=inject_valid ? inject_packet : child_return[selected_source];
  end
  task make_peer_message;
    input integer b;
    input integer kind;
    input integer status;
    begin
      child_return[b]<=0; child_return[b][0+:16]<=2; child_return[b][16+:8]<=kind[7:0];
      child_return[b][24+:8]<=b[7:0]; child_return[b][32+:32]<=child_call[b][32+:32]+(bad_return!=0 ? 1 : 0);
      child_return[b][64+:64]<=child_call[b][64+:64];
      child_return[b][128+:8]<=kind<2 ? 8'hff : child_call[b][136+:8];
      child_return[b][136+:8]<=kind<2 ? 8'(b) : 255;
      child_return[b][352+:32]<=child_call[b][224+:32];child_return[b][384+:32]<=child_call[b][192+:32];
      child_return[b][144+:16]<=status[15:0]; child_return[b][320+:32]<=status==0 ? 32'hffffffff : 1;
      if(kind<2) begin
        child_return[b][160+:32]<=ready_scalar[31:0]; child_return[b][288+:32]<=1;
      end else if(prefix_max!=0) begin
        child_return[b][192+:32]<=32'hffffffff; child_return[b][224+:32]<=32'hffffffff;
        child_return[b][256+:32]<=1;
      end else if(traffic!=0 && status==0) begin
        child_return[b][192+:32]<=b==0 ? 16 : 0; child_return[b][224+:32]<=16;
      end
      child_return_valid[b]<=1;
    end
  endtask

  always @(posedge clk_i) begin
    if(!rst_ni) begin
      child_busy<=0; child_return_valid<=0; child_cancelled<=0; ever_called<=0; ret_locked<=0; ret_rr<=0; hold_age<=0;
      for(k=0;k<9;k=k+1) begin peer_phase[k]<=0; peer_timer[k]<=0; child_call[k]<=0; child_return[k]<=0; end
    end else begin
      if(runtime_active) begin
        runtime_cycles<=runtime_cycles+1;
`ifdef MC_TRANSPORT128
        if(dut.mother.pm_req_valid_o && dut.mother.pm_req_ready_i && !dut.mother.pm_req_write_o) runtime_PM_reads<=runtime_PM_reads+1;
`else
        if(dut.pm_req_valid_o && dut.pm_req_ready_i && !dut.pm_req_write_o) runtime_PM_reads<=runtime_PM_reads+1;
`endif
      end
      ret_locked<=return_valid_i && !return_ready_o;
      if(return_valid_i && !return_ready_o) ret_lock_source<=selected_source;
      if(return_valid_i && return_ready_o && !inject_valid) begin
        last_good_return<=child_return[selected_source];
        child_return_valid[selected_source]<=0; ret_rr<=selected_source==8 ? 0 : selected_source+1'b1;
        if(child_return[selected_source][16+:8]<2) begin
          ready_count<=ready_count+1; peer_phase[selected_source]<=2;
          peer_timer[selected_source]<=selected_source==0 ? delay0 : delay1;
        end else begin child_busy[selected_source]<=0; peer_phase[selected_source]<=0; end
      end
      for(k=0;k<9;k=k+1) if(child_busy[k]) begin
        if(peer_phase[k]==1) begin
          if(peer_timer[k]!=0) peer_timer[k]<=peer_timer[k]-1;
          else if(!child_return_valid[k]) begin make_peer_message(k,0,0); peer_phase[k]<=3; end
        end
        if(peer_phase[k]==2 && no_terminal!=k) begin
          if(peer_timer[k]!=0) peer_timer[k]<=peer_timer[k]-1;
          else if(!child_return_valid[k] && (dependency==0 || k==0 || ever_called[0] || child_cancelled[k] || error_target==k)) begin
            make_peer_message(k,error_target==k || child_cancelled[k] ? 3 : 2,error_target==k ? 9 : child_cancelled[k] ? 11 : 0);
            peer_phase[k]<=4;
          end
        end
      end
      if(start_valid_i && start_ready_o) begin
        if(child_busy!=0 || child_return_valid!=0) $fatal(1,"new job before finite peers drained");
        ever_called<=0; hold_age<=0;
      end
      if(task_valid_o && task_packet_o[16+:8]==0 && task_target_o==hold_target[7:0]) hold_age<=hold_age+1;
      if(task_valid_o && task_ready_i) begin
        if(task_target_o>=9 || task_packet_o[24+:8]!=task_target_o || task_packet_o[0+:16]!=2 ||
           task_packet_o[160+:32]!=local_image_ids_i[32*task_target_o+:32] || task_packet_o[224+:32]!=start_generation_i) $fatal(1,"CALL route/image");
        if(task_packet_o[16+:8]==0) begin
          if(check_ptr!=0) assert(task_packet_o[256+:64]==ptr_start+64'(calls)*ptr_stride)
            else $fatal(1,"CALL pointer differs from fully unrolled oracle at %0d",calls);
          if(check_targets!=0) assert(task_target_o==oracle_targets[calls])
            else $fatal(1,"CALL target differs from fully unrolled oracle at %0d",calls);
          if(child_busy[task_target_o[3:0]] || !task_credit_o) $fatal(1,"CALL without finite target/terminal credit");
          child_busy[task_target_o[3:0]]<=1; child_call[task_target_o[3:0]]<=task_packet_o;
          child_cancelled[task_target_o[3:0]]<=0; ever_called[task_target_o[3:0]]<=1; calls<=calls+1;
          if(ready_mask[task_target_o[4:0]] && error_target!=int'(task_target_o)) begin peer_phase[task_target_o[3:0]]<=1; peer_timer[task_target_o[3:0]]<=ready_delay; end
          else begin peer_phase[task_target_o[3:0]]<=2; peer_timer[task_target_o[3:0]]<=task_target_o==0 ? delay0 : delay1; end
        end else begin
          if(!child_busy[task_target_o[3:0]] || task_credit_o ||
            task_packet_o[0+:16]!=child_call[task_target_o[3:0]][0+:16] ||
            task_packet_o[24+:232]!=child_call[task_target_o[3:0]][24+:232] || task_packet_o[256+:256]!=0)
              $fatal(1,"CANCEL identity or credit");
          cancels<=cancels+1; child_cancelled[task_target_o[3:0]]<=1;
          if(!child_return_valid[task_target_o[3:0]]) begin
            child_return_valid[task_target_o[3:0]]<=0; peer_phase[task_target_o[3:0]]<=2; peer_timer[task_target_o[3:0]]<=5;
          end
        end
      end
      active_count=$countones(trace_block_active_o);
      if(active_count>max_active) max_active=active_count;
      if(previous_result_stall) assert(result_valid_o && held_result=={230'b0,result_job_o,result_epoch_o,result_sequence_o,result_status_o,result_error_pc_o,result_source_o,result_child_error_pc_o,result_failed_task_sequence_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,result_counter_overflow_o,result_saturated_o}) else $fatal(1,"native mother result changed under backpressure");
      previous_result_stall<=result_valid_o&&!result_ready_i;
      held_result<={230'b0,result_job_o,result_epoch_o,result_sequence_o,result_status_o,result_error_pc_o,result_source_o,result_child_error_pc_o,result_failed_task_sequence_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,result_counter_overflow_o,result_saturated_o};
      if(previous_task_stall) assert(task_valid_o&&held_task==task_packet_o) else $fatal(1,"native mother task withdrew/changed");
      previous_task_stall<=task_valid_o&&!task_ready_i;held_task<=task_packet_o;
      if(result_valid_o && result_ready_i) begin
        if(prefix_max!=0 && (result_confirmed_read_bytes_o!=32'hffffffff || result_confirmed_write_bytes_o!=32'hffffffff || !result_counter_overflow_o))
          $fatal(1,"mother confirmed prefix saturation/overflow");
        if(child_busy!=0 || child_return_valid!=0 || trace_live_tokens_o!=0 || trace_block_active_o!=0)
          $fatal(1,"global result before peer/task drain");
        if(result_job_o!=start_job_i || result_epoch_o!=start_epoch_i || result_sequence_o!=start_sequence_i ||
           result_status_o!=(inject_mode==8 && ji==0 ? 16'd0 : recover_error!=0 && ji>0 ? 16'd0 : expect_status[15:0])) $fatal(1,"global result identity/status");
        returns<=returns+1;
      end
      if(life_o==6 && cfg_req_ready_o) $fatal(1,"mother runtime configuration admission");
      if(poison_o && expected_poison==0) $fatal(1,"unexpected mother poison");
    end
  end
  always @(negedge clk_i) begin
    task_ready_i=rst_ni && task_target_o<9 && local_enabled_i[task_target_o[3:0]] &&
      (task_packet_o[16+:8]==0 ? !child_busy[task_target_o[3:0]] &&
        !(task_target_o==hold_target[7:0] && hold_age<hold_cycles) : child_busy[task_target_o[3:0]] &&
        !(child_return_valid[task_target_o[3:0]] && child_return[task_target_o[3:0]][16+:8]<2)) && (stall==0 || cycle%7==0);
  end

  task config_command;
    input [2:0] op;
    input integer address;
    input [127:0] data;
    input integer expected;
    begin
      @(negedge clk_i); cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1;
      cfg_req_address_i=address[13:0]; cfg_req_data_i=data; cfg_req_proof_i=1;
      cfg_req_total_bytes_i=16'(words*16); cfg_req_image_id_i=expected_image; cfg_req_topology_id_i=expected_topology;
      cfg_req_abi_id_i=32'h02500002; cfg_req_capacity_id_i=32'h02590003;
      @(posedge clk_i); while(!cfg_req_ready_o) @(posedge clk_i);
      @(negedge clk_i); cfg_req_valid_i=0;
      while(!cfg_rsp_valid_o) @(negedge clk_i);
      repeat(stall) @(negedge clk_i);
      if(cfg_rsp_status_o!=expected[15:0]) $fatal(1,"mother config status");
      if(op==2 && cfg_rsp_data_o!==input_image[address>>4]) $fatal(1,"mother host actual readback");
      cfg_rsp_ready_i=1; @(negedge clk_i); cfg_rsp_ready_i=0;
    end
  endtask

  initial begin : scenario
`include "tb_native_init.svh"
    if(!$value$plusargs("IMAGE=%s",image_path) || !$value$plusargs("WORDS=%d",words)) $fatal(1,"missing mother image");
    n=$value$plusargs("STALL=%d",stall); n=$value$plusargs("MODE=%d",mode); n=$value$plusargs("RUNS=%d",runs);
    n=$value$plusargs("INJECT=%d",inject_mode);n=$value$plusargs("RECOVER_POISON=%d",recover_poison);n=$value$plusargs("READY1=%d",ready1);n=$value$plusargs("READY_MASK=%d",ready_mask);n=$value$plusargs("MIN_ACTIVE=%d",min_active); n=$value$plusargs("DEPENDENCY=%d",dependency);
    n=$value$plusargs("ERROR_TARGET=%d",error_target); n=$value$plusargs("NO_TERMINAL=%d",no_terminal);
    n=$value$plusargs("HOLD_TARGET=%d",hold_target); n=$value$plusargs("HOLD_CYCLES=%d",hold_cycles);
    n=$value$plusargs("DELAY0=%d",delay0); n=$value$plusargs("DELAY1=%d",delay1); n=$value$plusargs("SCALAR=%d",ready_scalar);
    n=$value$plusargs("TRAFFIC=%d",traffic); n=$value$plusargs("BAD_RETURN=%d",bad_return); n=$value$plusargs("PREFIX_MAX=%d",prefix_max);
    n=$value$plusargs("CALLS=%d",expected_calls); n=$value$plusargs("CANCELS=%d",expected_cancels);
    n=$value$plusargs("CHECK_PTR=%d",check_ptr);n=$value$plusargs("PTR_START=%d",ptr_start);
    n=$value$plusargs("PTR_STRIDE=%d",ptr_stride);n=$value$plusargs("EXPECT_READY=%d",expect_ready);
    if($value$plusargs("TIMING_TRACE=%s",timing_path)) begin
      timing_file=$fopen(timing_path,"w");assert(timing_file!=0);
      $fwrite(timing_file,"cycle,event,target,detail,value\n");
    end
    check_targets=$value$plusargs("TARGETS_FILE=%s",targets_path);
    if(check_targets!=0) $readmemh(targets_path,oracle_targets,0,expected_calls-1);
    n=$value$plusargs("EXPECTED=%d",expect_status); n=$value$plusargs("POISON=%d",expected_poison);
    n=$value$plusargs("RECOVER=%d",recover_error);
    n=$value$plusargs("FAULT_ADDR=%d",runtime_fault_addr); n=$value$plusargs("FAULT_XOR=%h",runtime_fault_xor);
    n=$value$plusargs("PM_ERROR=%d",pm_error);
    $readmemh(image_path,input_image,0,words-1);
    expected_image=input_image[3][96+:32]; expected_topology=input_image[4][0+:32];
    repeat(2) @(negedge clk_i); rst_ni=1;
    @(negedge clk_i); release_valid_i=1; release_sequence_i=1; release_epoch_i=1;
    @(negedge clk_i); release_valid_i=0;
    config_command(0,0,0,mode==6 ? 3 : 0);
    if(mode==6) begin
      assert(!image_valid_o&&!start_ready_o&&life_o==1);$display("PASS mother oversized PM metadata rejected");$finish;disable scenario;
    end
    if(mode==1) begin
      config_command(3,0,0,3);
      if(image_valid_o || start_ready_o || life_o!=1) $fatal(1,"mother partial load admitted");
      $display("PASS mother negative partial_load"); $finish; disable scenario;
    end
    for(n=0;n<words;n=n+1) config_command(1,n*16,input_image[n],0);
    for(n=0;n<words;n=n+1) config_command(2,n*16,0,0);
    config_command(3,0,0,mode==2 ? 3 : 0);
    if(mode==2) begin
      if(image_valid_o || start_ready_o || life_o!=1) $fatal(1,"mother invalid header admitted");
      $display("PASS mother negative invalid_header"); $finish; disable scenario;
    end
    config_command(4,0,0,0);
    for(n=0;n<9;n=n+1) local_image_ids_i[32*n+:32]=32'(100+n);local_enabled_i=9'h1ff;
    n=$value$plusargs("ENABLED=%d",local_enabled_i);
    if(image_valid_o || start_ready_o) $fatal(1,"mother local PREPARE bypass");
    deploy_valid_i=1; deploy_generation_i=2; start_credit_i=1;
    repeat(3) @(negedge clk_i);
    if(image_valid_o || start_ready_o) $fatal(1,"mother wrong generation admitted");
    deploy_generation_i=1;
    while(life_o!=5) @(negedge clk_i);
    runtime_active=1;
    for(ji=0;ji<runs;ji=ji+1) begin
      start_job_i=32'(7+ji); start_epoch_i=1; start_sequence_i=32'(ji+1); start_generation_i=1; start_args_i=0;
      if(recover_error!=0 && ji>0) error_target=-1;
      if(mode==3) start_generation_i=2;
      if(mode==4) start_args_i=1;
      start_valid_i=1;
      if(mode==3 || mode==4) begin
        repeat(5) @(negedge clk_i);
        if(start_ready_o || calls!=0 || result_valid_o) $fatal(1,"mother invalid START admitted");
        rst_ni=0; @(negedge clk_i); start_valid_i=0;
        $display("PASS mother negative invalid_START"); $finish; disable scenario;
      end
      @(posedge clk_i); while(!start_ready_o) @(posedge clk_i);
      @(negedge clk_i); start_valid_i=0;
      if(mode==5) begin
        while(!task_valid_o) @(negedge clk_i);
        @(posedge clk_i); @(negedge clk_i); deploy_valid_i=0;
      end
      if(inject_mode!=0 && (inject_mode!=8 || ji>0)) begin
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
      if(expected_poison!=0) begin
        while(!poison_o) @(negedge clk_i);
        repeat(10) @(negedge clk_i);
        if(result_valid_o || image_valid_o || start_ready_o || cfg_req_ready_o) $fatal(1,"mother poison fabricated result/admission");
        if(recover_poison!=0) begin
          assert(!recover_ready_o && trace_block_active_o!=0) else $fatal(1,"quarantine lost outstanding owner before late terminal");
          no_terminal=-1;
          while(!recover_ready_o) @(negedge clk_i);
          recover_valid_i=1;@(negedge clk_i);recover_valid_i=0;
          assert(!poison_o && life_o==1 && !start_ready_o && !image_valid_o && !result_valid_o && trace_block_active_o==0) else $fatal(1,"quarantine clear resumed stale PC/image");
        end
      end else begin
        while(!result_valid_o) @(negedge clk_i);
        repeat(5+stall*4) @(negedge clk_i);
        result_ready_i=1; @(negedge clk_i); result_ready_i=0;
        while(returns!=ji+1) @(negedge clk_i);
        if(life_o!=5 || !image_valid_o || trace_live_tokens_o!=0 || trace_block_active_o!=0 || trace_ireg_valid_o)
          $fatal(1,"mother not reusable after result");
      end
    end
    if(mode!=3 && mode!=4 && (calls!=expected_calls || cancels!=expected_cancels || returns!=(expected_poison!=0 ? 0 : runs)))
      $fatal(1,"mother transaction count calls=%0d cancel=%0d result=%0d",calls,cancels,returns);
    assert(max_active>=min_active) else $fatal(1,"native resident concurrency was not exercised");
    if(expect_ready>=0) assert(ready_count==expect_ready)else $fatal(1,"repeated READY count");
    $display("PASS mother calls=%0d cancels=%0d READY=%0d results=%0d poison=%0d",calls,cancels,ready_count,returns,poison_o);
    $display("PASS native residents=%0d protocol_faults=%0d runtime_cycles=%0d runtime_PM_reads=%0d",max_active,protocol_fault_count_o,runtime_cycles,runtime_PM_reads);
    $finish;
  end
`ifdef MC_TRANSPORT128
  wire timing_PM_req=dut.mother.pm_req_valid_o&&dut.mother.pm_req_ready_i&&!dut.mother.pm_req_write_o;
  wire timing_PM_rsp=dut.mother.pm_rsp_valid_i&&dut.mother.pm_rsp_ready_o;
  wire [13:0] timing_PM_address=dut.mother.pm_req_address_o;
`else
  wire timing_PM_req=dut.pm_req_valid_o&&dut.pm_req_ready_i&&!dut.pm_req_write_o;
  wire timing_PM_rsp=dut.pm_rsp_valid_i&&dut.pm_rsp_ready_o;
  wire [13:0] timing_PM_address=dut.pm_req_address_o;
`endif
  always @(posedge clk_i) if(runtime_active&&timing_file!=0) begin
    if(timing_PM_req)$fwrite(timing_file,"%0d,PMREQ,0,%0d,0\n",cycle,timing_PM_address);
    if(timing_PM_rsp)$fwrite(timing_file,"%0d,PMRSP,0,0,0\n",cycle);
    if(task_valid_o&&task_ready_i)$fwrite(timing_file,"%0d,TASK,%0d,%0d,%016x\n",cycle,task_target_o,task_packet_o[16+:8],task_packet_o[256+:64]);
    if(return_valid_i&&return_ready_o)$fwrite(timing_file,"%0d,RETURN,%0d,%0d,%0d\n",cycle,return_packet_i[24+:8],return_packet_i[16+:8],return_packet_i[96+:32]);
`ifdef MC_TRANSPORT128
    if(tx_valid&&tx_ready)$fwrite(timing_file,"%0d,TX,%0d,%0d,%0d\n",cycle,tx_target,tx_sop,tx_eop);
    if(rx_valid&&rx_ready)$fwrite(timing_file,"%0d,RX,%0d,%0d,%0d\n",cycle,rx_source,rx_sop,rx_eop);
`endif
  end
  initial begin #5000000; $fatal(1,"mother watchdog"); end
endmodule
