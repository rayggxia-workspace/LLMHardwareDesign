`timescale 1ns/1ps
module phase2_mst_tb;
  reg clk=0;
  always #5 clk=~clk;
  reg reset=1,abort=0,start_valid=0,done_ready=0,out_ready=0;
  wire start_ready,busy,done_valid,done_error,out_valid,out_last;
  wire [127:0] out_data;
  wire [9:0] out_index;
  block_p2_mst_top dut(.*);
  integer cycles=0,job_output_count=0;
  integer s_requests=0,s_responses=0,s_writes=0,s_reads=0,m_commands=0,m_responses=0;
  integer load_commands=0,load_completions=0,a_beats=0,b_beats=0;
  integer t_begins=0,t_writes=0,t_commits=0,t_reads=0,t_releases=0,done_takes=0;
  integer job_execs=0;
  reg loader_complete=0,s_pending=0,s_pending_write=0;
  reg [9:0] s_pending_addr;
  reg [127:0] s_pending_data;
  reg previous_out_hold=0,previous_m_hold=0,previous_done_hold=0;
  reg [127:0] previous_out_data,previous_m_data;
  reg [9:0] previous_out_index;
  reg previous_out_last,previous_m_error,previous_m_sat,previous_done_error;
  integer s0,sr0,sw0,rd0,mc0,mr0,lc0,ld0,ab0,bb0,tb0,tw0,tc0,tr0,tl0;

  function automatic [127:0] expected_word;
    input integer index;
    begin case(index)
      0:expected_word=128'hfffffffffffffff8fffffffffffffffc;
      1:expected_word=128'hfffffffffffffff0fffffffffffffff4;
      2:expected_word=128'hffffffffffffffe8ffffffffffffffec;
      3:expected_word=128'hffffffffffffffe0ffffffffffffffe4;
      default:expected_word=128'hbad;
    endcase end
  endfunction

  always @(posedge clk) begin
    cycles=cycles+1;
    if(cycles>50000) $fatal(1,"FAIL_P2 MST watchdog");
    if(reset||dut.leaf_reset) begin
      previous_out_hold=0;previous_m_hold=0;previous_done_hold=0;s_pending=0;
    end else begin
      if(previous_out_hold && (!out_valid||out_data!==previous_out_data||out_index!==previous_out_index||out_last!==previous_out_last))
        $fatal(1,"FAIL_P2 T output changed while stalled");
      if(previous_m_hold && (!dut.m_rsp_valid||dut.m_rsp_data!==previous_m_data||dut.m_rsp_error!==previous_m_error||dut.m_rsp_saturated!==previous_m_sat))
        $fatal(1,"FAIL_P2 M response changed while stalled");
      if(previous_done_hold && (!done_valid||done_error!==previous_done_error))
        $fatal(1,"FAIL_P2 completion changed while stalled");
      previous_out_hold=out_valid&&!out_ready;previous_out_data=out_data;
      previous_out_index=out_index;previous_out_last=out_last;
      previous_m_hold=dut.m_rsp_valid&&!dut.m_rsp_ready;previous_m_data=dut.m_rsp_data;
      previous_m_error=dut.m_rsp_error;previous_m_sat=dut.m_rsp_saturated;
      previous_done_hold=done_valid&&!done_ready;previous_done_error=done_error;
      if(dut.s_req&&dut.s_ready) begin
        if(s_pending) $fatal(1,"FAIL_P2 more than one ordinary S request outstanding");
        s_pending=1;s_pending_write=dut.s_we;s_pending_data=dut.s_din;s_pending_addr=dut.s_addr;
        s_requests=s_requests+1;
        if(dut.s_we) s_writes=s_writes+1;else s_reads=s_reads+1;
      end
      if(dut.s_valid&&dut.s_take) begin
        if(!s_pending) $fatal(1,"FAIL_P2 S ACK without matching request");
        if(s_pending_write && dut.s_dout!==s_pending_data) $fatal(1,"FAIL_P2 S write ACK not equal din");
        if(!s_pending_write && (s_pending_addr<456||s_pending_addr>459||dut.s_dout!==expected_word(s_pending_addr-456)))
          $fatal(1,"FAIL_P2 result S readback mismatch");
        s_pending=0;s_responses=s_responses+1;
      end
      if(dut.load_valid&&dut.load_ready) load_commands=load_commands+1;
      if(dut.load_done_valid&&dut.load_done_take) begin
        load_completions=load_completions+1;
        if(job_execs!=0) $fatal(1,"FAIL_P2 loader done incorrectly treated as M compute completion");
        loader_complete=!dut.load_done_error;
      end
      if(dut.a_valid&&dut.a_ready) a_beats=a_beats+1;
      if(dut.b_valid&&dut.b_ready) b_beats=b_beats+1;
      if(dut.m_cmd_valid&&dut.m_cmd_ready) begin
        m_commands=m_commands+1;
        if(dut.m_cmd_op==10) begin
          if(!loader_complete) $fatal(1,"FAIL_P2 EXEC before successful loader done");
          job_execs=job_execs+1;
        end
      end
      if(dut.m_rsp_valid&&dut.m_rsp_ready) m_responses=m_responses+1;
      if(dut.u_t.begin_valid&&dut.u_t.begin_ready) t_begins=t_begins+1;
      if(dut.u_t.write_valid&&dut.u_t.write_ready) begin
        if(dut.u_t.write_index>3||dut.u_t.write_data!==expected_word(dut.u_t.write_index))
          $fatal(1,"FAIL_P2 T fill word/index mismatch");
        t_writes=t_writes+1;
      end
      if(dut.u_t.commit_valid&&dut.u_t.commit_ready) t_commits=t_commits+1;
      if(out_valid&&out_ready) begin
        if(job_output_count>3||out_index!==job_output_count||out_data!==expected_word(job_output_count)||out_last!==(job_output_count==3))
          $fatal(1,"FAIL_P2 output literal/order/last mismatch index=%0d expected=%0d data=%032h",out_index,job_output_count,out_data);
        job_output_count=job_output_count+1;t_reads=t_reads+1;
      end
      if(dut.u_t.release_valid&&dut.u_t.release_ready) t_releases=t_releases+1;
      if(done_valid&&done_ready) done_takes=done_takes+1;
    end
  end

  task automatic begin_job;
    begin
      @(negedge clk);
      if(!start_ready||busy||done_valid) $fatal(1,"FAIL_P2 not idle at new job");
      job_output_count=0;job_execs=0;loader_complete=0;
      s0=s_requests;sr0=s_responses;sw0=s_writes;rd0=s_reads;mc0=m_commands;mr0=m_responses;
      lc0=load_commands;ld0=load_completions;ab0=a_beats;bb0=b_beats;
      tb0=t_begins;tw0=t_writes;tc0=t_commits;tr0=t_reads;tl0=t_releases;
      out_ready=0;done_ready=0;start_valid=1;
      @(posedge clk);#1;
      @(negedge clk);start_valid=0;
      if(!busy||start_ready) $fatal(1,"FAIL_P2 start not accepted exactly once");
    end
  endtask

  task automatic drain_output;
    integer index,j;
    begin
      for(index=0;index<4;index=index+1) begin
        while(!out_valid) @(negedge clk);
        for(j=0;j<index+3;j=j+1) begin
          if(!out_valid||out_data!==expected_word(index)||out_index!==index||out_last!==(index==3))
            $fatal(1,"FAIL_P2 output hold mismatch");
          @(negedge clk);
        end
        out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;
      end
    end
  endtask

  task automatic completion;
    input expect_error;
    input abort_on_done;
    integer j,old_takes;
    begin
      while(!done_valid) @(negedge clk);
      for(j=0;j<6;j=j+1) begin
        if(!done_valid||done_error!==expect_error||start_ready||!busy)
          $fatal(1,"FAIL_P2 retained completion incorrect");
        @(negedge clk);
      end
      if(!expect_error && (job_output_count!=4||dut.t_busy))
        $fatal(1,"FAIL_P2 successful done before full drain/release");
      if(expect_error && (job_output_count!=0||out_valid))
        $fatal(1,"FAIL_P2 aborted/error run published unexpected output");
      old_takes=done_takes;
      done_ready=1;abort=abort_on_done;
      // DONE already existed: abort cannot cancel or duplicate that completion.
      if(abort_on_done) begin #1;if(!done_valid) $fatal(1,"FAIL_P2 abort masked existing completion");end
      @(posedge clk);#1;
      @(negedge clk);done_ready=0;abort=0;
      repeat(3) @(negedge clk);
      if(done_valid||busy||!start_ready) $fatal(1,"FAIL_P2 completion not retired exactly once");
      // Top leaf reset on abort deliberately masks native monitors, so explicit
      // pin state above is authoritative for the abort+DONE take combination.
      if(!abort_on_done && done_takes!=old_takes+1) $fatal(1,"FAIL_P2 completion accounting");
    end
  endtask

  task automatic check_nominal_counts;
    begin
      if(s_requests-s0!=16||s_responses-sr0!=16||s_writes-sw0!=12||s_reads-rd0!=4||s_pending)
        $fatal(1,"FAIL_P2 S ordinary accounting requests=%0d rsp=%0d writes=%0d reads=%0d",s_requests-s0,s_responses-sr0,s_writes-sw0,s_reads-rd0);
      if(m_commands-mc0!=7||m_responses-mr0!=7||job_execs!=1)
        $fatal(1,"FAIL_P2 M command/response accounting");
      if(load_commands-lc0!=1||load_completions-ld0!=1||a_beats-ab0!=1||b_beats-bb0!=1)
        $fatal(1,"FAIL_P2 loader accounting");
      if(t_begins-tb0!=1||t_writes-tw0!=4||t_commits-tc0!=1||t_reads-tr0!=4||t_releases-tl0!=1)
        $fatal(1,"FAIL_P2 T lifecycle accounting");
    end
  endtask

  initial begin
    repeat(4) @(negedge clk);reset=0;@(negedge clk);
    // Real leaf response backpressure, plus blocked launch points before accept.
    force dut.permit_m_cmd=1'b0;
    force dut.permit_load=1'b0;
    force dut.permit_s_rsp=1'b0;
    begin_job();
    wait(dut.state==1&&dut.operation==0);
    repeat(5) @(negedge clk);
    if(dut.m_cmd_op!==6||dut.m_cmd_data!==0||dut.m_cmd_index!==0||dut.m_cmd_valid)
      $fatal(1,"FAIL_P2 blocked M launch fields");
    release dut.permit_m_cmd;
    wait(dut.s_valid);repeat(7) @(negedge clk);
    if(!dut.s_valid||dut.s_dout!==128'h0000000000000000f807fa05fc03fe01||s_responses!=sr0)
      $fatal(1,"FAIL_P2 S ACK was not held under masked take");
    release dut.permit_s_rsp;
    wait(dut.state==5);repeat(6) @(negedge clk);
    if(dut.load_valid||job_execs!=0) $fatal(1,"FAIL_P2 blocked loader launch");
    release dut.permit_load;
    wait(dut.operation==4&&dut.state==1);
    force dut.permit_m_rsp=1'b0;
    wait(dut.m_rsp_valid);repeat(8) @(negedge clk);
    if(!dut.m_rsp_valid||dut.m_rsp_error||dut.m_rsp_data!==0||load_completions-ld0!=1)
      $fatal(1,"FAIL_P2 EXEC response hold");
    release dut.permit_m_rsp;
    // A busy start pulse must not queue a second run.
    @(negedge clk);start_valid=1;repeat(2) @(negedge clk);start_valid=0;
    drain_output();completion(0,0);check_nominal_counts();
    $display("CASE_PASS M01_LITERAL_S8_DOT8_END_TO_END");
    $display("CASE_PASS M02_ACK_OWNER_AND_LOAD_VS_EXEC_DONE");
    $display("CASE_PASS M03_NATIVE_RESPONSE_AND_OUTPUT_STALL_HOLD");
    $display("CASE_PASS M04_BUSY_START_REJECTED_AND_DONE_HOLD");
    begin_job();drain_output();completion(0,1);check_nominal_counts();
    $display("CASE_PASS M05_REPEAT_RUN_SAME_LITERAL");
    $display("CASE_PASS M06_ABORT_WITH_EXISTING_DONE_TAKE_NO_DUPLICATE");
    // Coordinated abort while a real S ACK is outstanding.
    force dut.permit_s_rsp=1'b0;
    begin_job();wait(dut.s_valid);@(negedge clk);abort=1;
    @(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;
    completion(1,0);
    $display("CASE_PASS M07_RUN_ABORT_FLUSHES_PENDING_ACK");
    begin_job();drain_output();completion(0,0);check_nominal_counts();
    $display("CASE_PASS M08_RECOVER_AFTER_ABORT");
    // Hard reset while T's first committed output is stalled: no completion.
    begin_job();wait(out_valid);@(negedge clk);reset=1;
    repeat(3) @(negedge clk);
    if(out_valid||done_valid||busy) $fatal(1,"FAIL_P2 coordinated hard reset did not suppress lifecycle");
    reset=0;repeat(3) @(negedge clk);
    if(!start_ready||done_valid||out_valid) $fatal(1,"FAIL_P2 reset left a stale output/completion");
    $display("CASE_PASS M09_HARD_RESET_AT_T_STALL");
    begin_job();drain_output();completion(0,0);check_nominal_counts();
    $display("CASE_PASS M10_RECOVER_AFTER_HARD_RESET");
    // Force a native reserved bit for one EXEC accept, not a changed fixture.
    begin_job();wait(dut.operation==4&&dut.state==1);
    @(negedge clk);force dut.m_cmd_data=64'h988c;
    @(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;
    completion(1,0);
    $display("CASE_PASS M11_NATIVE_EXEC_DESCRIPTOR_ERROR_PROPAGATION");
    begin_job();wait(dut.state==5);
    @(negedge clk);force dut.u_s.feeder.load_a_base=10'd449;
    @(posedge clk);#1;@(negedge clk);release dut.u_s.feeder.load_a_base;
    completion(1,0);
    if(job_execs!=0) $fatal(1,"FAIL_P2 bad loader descriptor still executed M");
    $display("CASE_PASS M12_NATIVE_LOADER_ALIGNMENT_ERROR_PROPAGATION");
    begin_job();drain_output();completion(0,0);check_nominal_counts();
    $display("CASE_PASS M13_RECOVER_AFTER_NATIVE_ERROR");
    $display("PASS_P2_MST real leaf composition cycles=%0d Sreq=%0d Sack=%0d Mcmd=%0d Mrsp=%0d Tread=%0d",
      cycles,s_requests,s_responses,m_commands,m_responses,t_reads);
    $finish;
  end
endmodule
