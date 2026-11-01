`timescale 1ns/1ps
// Issue151 W1 fixed-DOT8 integration test. Integer expectations are computed
// only from these TB-owned A/B arrays, then cross-checked against literal W0
// vectors. No DUT register, RAM result, or internal arithmetic supplies oracle.
module block_w1_mst_tb;
  reg clk=0;
  always #5 clk=~clk;
  reg reset=1,abort=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
  reg [127:0] in_data=0;
  wire in_ready,input_stored,start_ready,busy,done_valid,done_error,out_valid,out_last;
  wire [127:0] out_data;
  wire [9:0] out_index;
  block_w1_mst_top dut(.*);

  integer cycles=0,cases=0,vector_id=0;
  integer avec[0:7],bvec[0:7][0:7];
  reg signed [63:0] oracle[0:7];
  integer in_accepts=0,ingress_req=0,ingress_ack=0,result_req=0,result_ack=0;
  integer read_req=0,read_ack=0,s_requests=0,s_responses=0;
  integer m_commands=0,m_responses=0,load_commands=0,load_completions=0;
  integer a_beats=0,b_beats=0,t_begins=0,t_writes=0,t_commits=0,t_reads=0,t_releases=0;
  integer start_accepts=0,done_takes=0,job_output_count=0,job_execs=0;
  integer i0,iq0,ia0,wq0,wa0,rq0,ra0,sq0,sa0,mc0,mr0,lc0,ld0,ab0,bb0;
  integer tb0,tw0,tc0,tr0,tl0,st0;
  reg frame_open=0,job_started=0,loader_complete=0,s_pending=0,s_pending_write;
  reg [9:0] s_pending_addr;
  reg [127:0] s_pending_data;
  reg previous_out_hold=0,previous_s_hold=0,previous_m_hold=0,previous_done_hold=0,previous_in_hold=0;
  reg [127:0] previous_out_data,previous_s_data,previous_m_data,previous_in_data;
  reg [9:0] previous_out_index;
  reg previous_out_last,previous_m_error,previous_m_sat,previous_done_error;

  function automatic signed [63:0] literal_dot;
    input integer v,n;
    begin
      case(v)
        0:literal_dot=-4*(n+1);
        1:literal_dot=0;
        2:literal_dot=131072;
        3:literal_dot=-130048;
        4:case(n)
          0:literal_dot=3391;1:literal_dot=3414;2:literal_dot=3437;3:literal_dot=3460;
          4:literal_dot=3483;5:literal_dot=3506;6:literal_dot=3017;7:literal_dot=-13344;
          default:literal_dot=64'hbad;
        endcase
        default:literal_dot=64'hbad;
      endcase
    end
  endfunction
  function automatic [127:0] expected_word;
    input integer index;
    begin
      if(index<0||index>3)expected_word=128'hbad;
      else expected_word={oracle[2*index+1],oracle[2*index]};
    end
  endfunction
  function automatic [127:0] canonical_word;
    input integer beat;
    integer k,n,lane;
    reg [127:0] value;
    begin
      value=0;
      if(beat==0)for(k=0;k<8;k=k+1)value[8*k+:8]=avec[k];
      if(beat>=4&&beat<8)for(lane=0;lane<16;lane=lane+1)begin
        n=(beat-4)*2+lane/8;k=lane%8;value[8*lane+:8]=bvec[n][k];
      end
      canonical_word=value;
    end
  endfunction
  function automatic [127:0] raw_word;
    input integer beat;
    reg [127:0] value;
    begin
      // Intentionally nonzero user padding must be ignored AND overwritten.
      value=canonical_word(beat);
      if(beat==0)raw_word={64'hd15ea5ed55aa33cc,value[63:0]};
      else if(beat<4)raw_word=128'hfeedfacecafebabe0123456789abcdef;
      else raw_word=canonical_word(beat);
    end
  endfunction
  function automatic [127:0] ram_word;
    input integer address;
    begin case(address%4)
      0:ram_word=dut.u_s.storage.bank0[address/4];
      1:ram_word=dut.u_s.storage.bank1[address/4];
      2:ram_word=dut.u_s.storage.bank2[address/4];
      3:ram_word=dut.u_s.storage.bank3[address/4];
    endcase end
  endfunction

  always @(posedge clk) begin
    cycles=cycles+1;
    if(cycles>150000)$fatal(1,"FAIL_W1 watchdog");
    // Public DONE survives a coordinated leaf abort. Count its handshake even
    // on abort+ready; only hard reset invalidates an existing completion.
    if(reset)previous_done_hold=0;
    else begin
      if(previous_done_hold&&(!done_valid||done_error!==previous_done_error))$fatal(1,"FAIL_W1 DONE changed while stalled or aborted");
      previous_done_hold=done_valid&&!done_ready;previous_done_error=done_error;
      if(done_valid&&done_ready)done_takes=done_takes+1;
    end
    if(reset||dut.leaf_reset)begin
      previous_out_hold=0;previous_s_hold=0;previous_m_hold=0;previous_in_hold=0;s_pending=0;
    end else begin
      if(previous_in_hold&&(!in_valid||in_data!==previous_in_data))$fatal(1,"FAIL_W1 TB ingress changed while stalled");
      if(previous_out_hold&&(!out_valid||out_data!==previous_out_data||out_index!==previous_out_index||out_last!==previous_out_last))$fatal(1,"FAIL_W1 output changed while stalled");
      if(previous_s_hold&&(!dut.s_valid||dut.s_dout!==previous_s_data))$fatal(1,"FAIL_W1 native S ACK changed while stalled");
      if(previous_m_hold&&(!dut.m_rsp_valid||dut.m_rsp_data!==previous_m_data||dut.m_rsp_error!==previous_m_error||dut.m_rsp_saturated!==previous_m_sat))$fatal(1,"FAIL_W1 native M response changed while stalled");
      previous_in_hold=in_valid&&!in_ready;previous_in_data=in_data;
      previous_out_hold=out_valid&&!out_ready;previous_out_data=out_data;previous_out_index=out_index;previous_out_last=out_last;
      previous_s_hold=dut.s_valid&&!dut.s_take;previous_s_data=dut.s_dout;
      previous_m_hold=dut.m_rsp_valid&&!dut.m_rsp_ready;previous_m_data=dut.m_rsp_data;previous_m_error=dut.m_rsp_error;previous_m_sat=dut.m_rsp_saturated;
      if(in_valid&&in_ready)begin
        if(!frame_open||job_started||in_accepts-i0>=8)$fatal(1,"FAIL_W1 input accepted without fresh frame ownership");
        in_accepts=in_accepts+1;
      end
      if(dut.s_req&&dut.s_ready)begin
        if(s_pending)$fatal(1,"FAIL_W1 two ordinary S requests outstanding");
        s_pending=1;s_pending_write=dut.s_we;s_pending_addr=dut.s_addr;s_pending_data=dut.s_din;s_requests=s_requests+1;
        if(dut.s_we&&dut.s_addr>=448&&dut.s_addr<=455)begin
          if(job_started||dut.s_addr!==448+(ingress_req-iq0)||dut.s_din!==canonical_word(dut.s_addr-448))$fatal(1,"FAIL_W1 ingress address/order/canonical payload or S_INIT clobber");
          ingress_req=ingress_req+1;
        end else if(dut.s_we&&dut.s_addr>=456&&dut.s_addr<=459)begin
          if(!job_started||dut.s_addr!==456+(result_req-wq0)||dut.s_din!==expected_word(dut.s_addr-456))$fatal(1,"FAIL_W1 result write/order mismatch");
          result_req=result_req+1;
        end else if(!dut.s_we&&dut.s_addr>=456&&dut.s_addr<=459)begin
          if(!job_started||dut.s_addr!==456+(read_req-rq0))$fatal(1,"FAIL_W1 result read/order mismatch");
          read_req=read_req+1;
        end else $fatal(1,"FAIL_W1 unexpected ordinary S transaction");
      end
      if(dut.s_valid&&dut.s_take)begin
        if(!s_pending)$fatal(1,"FAIL_W1 S ACK without owner");
        if(s_pending_write&&dut.s_dout!==s_pending_data)$fatal(1,"FAIL_W1 S write ACK lost/corrupted");
        if(!s_pending_write&&dut.s_dout!==expected_word(s_pending_addr-456))$fatal(1,"FAIL_W1 S read result mismatch");
        if(s_pending_write&&s_pending_addr<456)ingress_ack=ingress_ack+1;
        else if(s_pending_write)result_ack=result_ack+1;
        else read_ack=read_ack+1;
        s_pending=0;s_responses=s_responses+1;
      end
      if(input_stored&&(in_accepts-i0!=8||ingress_ack-ia0!=8||(!job_started&&s_pending)))$fatal(1,"FAIL_W1 input_stored before 8 accepts and actual ACKs");
      if(start_ready&&!input_stored)$fatal(1,"FAIL_W1 start_ready without stored frame");
      if(start_valid&&start_ready)begin
        if(job_started||!input_stored||in_accepts-i0!=8||ingress_ack-ia0!=8)$fatal(1,"FAIL_W1 illegal/duplicate start");
        start_accepts=start_accepts+1;job_started=1;
      end
      if(dut.load_valid&&dut.load_ready)begin
        if(!job_started)$fatal(1,"FAIL_W1 loader before start");
        load_commands=load_commands+1;
      end
      if(dut.load_done_valid&&dut.load_done_take)begin
        if(job_execs!=0)$fatal(1,"FAIL_W1 loader completion confused with EXEC");
        load_completions=load_completions+1;loader_complete=!dut.load_done_error;
      end
      if(dut.a_valid&&dut.a_ready)a_beats=a_beats+1;
      if(dut.b_valid&&dut.b_ready)b_beats=b_beats+1;
      if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
        if(!job_started)$fatal(1,"FAIL_W1 M command before accepted start");
        m_commands=m_commands+1;
        if(dut.m_cmd_op==10)begin
          if(!loader_complete)$fatal(1,"FAIL_W1 EXEC before loader done");
          job_execs=job_execs+1;
        end
      end
      if(dut.m_rsp_valid&&dut.m_rsp_ready)m_responses=m_responses+1;
      if(dut.u_t.begin_valid&&dut.u_t.begin_ready)t_begins=t_begins+1;
      if(dut.u_t.write_valid&&dut.u_t.write_ready)begin
        if(dut.u_t.write_index!==t_writes-tw0||dut.u_t.write_index>3||dut.u_t.write_data!==expected_word(dut.u_t.write_index))$fatal(1,"FAIL_W1 T fill/order mismatch");
        t_writes=t_writes+1;
      end
      if(dut.u_t.commit_valid&&dut.u_t.commit_ready)t_commits=t_commits+1;
      if(out_valid&&out_ready)begin
        if(job_output_count>3||out_index!==job_output_count||out_data!==expected_word(job_output_count)||out_last!==(job_output_count==3))$fatal(1,"FAIL_W1 output oracle/order/last index=%0d data=%032h expected=%032h",out_index,out_data,expected_word(job_output_count));
        job_output_count=job_output_count+1;t_reads=t_reads+1;
      end
      if(dut.u_t.release_valid&&dut.u_t.release_ready)t_releases=t_releases+1;
    end
  end

  task automatic make_vector;
    input integer v;
    integer k,n,value;
    reg signed [63:0] sum;
    begin
      vector_id=v;
      for(k=0;k<8;k=k+1)begin
        case(v)
          0:avec[k]=(k%2==0)?k+1:-(k+1);
          1:avec[k]=0;
          2,3:avec[k]=-128;
          4:case(k)0:avec[k]=-128;1:avec[k]=127;2:avec[k]=-1;3:avec[k]=0;4:avec[k]=1;5:avec[k]=-64;6:avec[k]=64;7:avec[k]=2;endcase
        endcase
      end
      for(n=0;n<8;n=n+1)begin
        sum=0;
        for(k=0;k<8;k=k+1)begin
          case(v)
            0:bvec[n][k]=n+1;
            1,3:bvec[n][k]=127;
            2:bvec[n][k]=-128;
            4:begin value=(23*n+17*k)%256;bvec[n][k]=value-128;end
          endcase
          sum=sum+avec[k]*bvec[n][k];
        end
        oracle[n]=sum;
        if(sum!==literal_dot(v,n))$fatal(1,"FAIL_W1 independent TB oracle differs from W0 literal v=%0d n=%0d",v,n);
      end
    end
  endtask
  task automatic new_frame;
    input integer v;
    begin
      @(negedge clk);
      if(busy||done_valid||input_stored||out_valid||!in_ready||start_ready)$fatal(1,"FAIL_W1 new frame not empty");
      make_vector(v);frame_open=1;job_started=0;job_output_count=0;job_execs=0;loader_complete=0;
      i0=in_accepts;iq0=ingress_req;ia0=ingress_ack;wq0=result_req;wa0=result_ack;rq0=read_req;ra0=read_ack;
      sq0=s_requests;sa0=s_responses;mc0=m_commands;mr0=m_responses;lc0=load_commands;ld0=load_completions;
      ab0=a_beats;bb0=b_beats;tb0=t_begins;tw0=t_writes;tc0=t_commits;tr0=t_reads;tl0=t_releases;st0=start_accepts;
      out_ready=0;done_ready=0;start_valid=0;in_valid=0;
    end
  endtask
  task automatic send_beat;
    input integer beat;
    begin
      @(negedge clk);in_data=raw_word(beat);in_valid=1;
      while(!in_ready)@(negedge clk);
      @(posedge clk);#1;if(!busy)$fatal(1,"FAIL_W1 accepted input does not retain frame ownership");
      @(negedge clk);in_valid=0;
    end
  endtask
  task automatic fill_frame;
    integer beat;
    begin
      for(beat=0;beat<8;beat=beat+1)send_beat(beat);
      while(!input_stored)@(negedge clk);
      if(ingress_req-iq0!=8||ingress_ack-ia0!=8||in_accepts-i0!=8)$fatal(1,"FAIL_W1 ingress phase accounting");
      if(!busy||in_ready)$fatal(1,"FAIL_W1 complete frame does not retain ownership");
    end
  endtask
  task automatic start_job;
    input keep_valid;
    begin
      @(negedge clk);if(!start_ready||!input_stored)$fatal(1,"FAIL_W1 not start-ready");start_valid=1;
      @(posedge clk);#1;@(negedge clk);
      if(!busy||start_ready||start_accepts-st0!=1)$fatal(1,"FAIL_W1 start not accepted once");
      if(!keep_valid)start_valid=0;
    end
  endtask
  task automatic drain_words;
    input integer count;
    integer index,j;
    begin
      for(index=0;index<count;index=index+1)begin
        while(!out_valid)@(negedge clk);
        for(j=0;j<index+3;j=j+1)begin
          if(!out_valid||out_data!==expected_word(job_output_count)||out_index!==job_output_count||out_last!==(job_output_count==3))$fatal(1,"FAIL_W1 stalled output mismatch");
          @(negedge clk);
        end
        out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;
      end
    end
  endtask
  task automatic finish_job;
    input expect_error,abort_on_done;
    integer j,old_takes;
    begin
      while(!done_valid)@(negedge clk);
      for(j=0;j<5;j=j+1)begin
        if(!done_valid||done_error!==expect_error||start_ready||!busy||in_ready)$fatal(1,"FAIL_W1 retained DONE incorrect");
        @(negedge clk);
      end
      if(!expect_error&&(job_output_count!=4||dut.t_busy||t_releases-tl0!=1))$fatal(1,"FAIL_W1 success before complete drain and RELEASE");
      if(expect_error&&out_valid)$fatal(1,"FAIL_W1 abort output not invalidated");
      old_takes=done_takes;start_valid=0;done_ready=1;abort=abort_on_done;
      #1;if(in_ready)$fatal(1,"FAIL_W1 DONE take edge also admitted next-frame input");
      if(abort_on_done)begin #1;if(!done_valid||done_error!==expect_error)$fatal(1,"FAIL_W1 abort revoked existing DONE");end
      @(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;frame_open=0;job_started=0;
      repeat(3)@(negedge clk);
      if(done_valid||busy||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_W1 completion/frame not retired");
      if(done_takes!=old_takes+1)$fatal(1,"FAIL_W1 completion must be consumed exactly once including abort+ready");
    end
  endtask
  task automatic nominal_counts;
    begin
      if(in_accepts-i0!=8||ingress_req-iq0!=8||ingress_ack-ia0!=8)$fatal(1,"FAIL_W1 ingress must be eight distinct writes/ACKs");
      if(result_req-wq0!=4||result_ack-wa0!=4||read_req-rq0!=4||read_ack-ra0!=4)$fatal(1,"FAIL_W1 RUN S phase must be four result writes plus four reads/ACKs");
      if(s_requests-sq0!=16||s_responses-sa0!=16||s_pending)$fatal(1,"FAIL_W1 full frame S accounting");
      if(m_commands-mc0!=7||m_responses-mr0!=7||job_execs!=1)$fatal(1,"FAIL_W1 M seven commands/responses");
      if(load_commands-lc0!=1||load_completions-ld0!=1||a_beats-ab0!=1||b_beats-bb0!=1)$fatal(1,"FAIL_W1 loader phase counts");
      if(t_begins-tb0!=1||t_writes-tw0!=4||t_commits-tc0!=1||t_reads-tr0!=4||t_releases-tl0!=1||start_accepts-st0!=1)$fatal(1,"FAIL_W1 T/start counts");
    end
  endtask
  task automatic pass_case;
    input [8*96-1:0] name;
    begin cases=cases+1;$display("CASE_PASS %0s",name);end
  endtask
  task automatic recover;
    input integer v;
    begin new_frame(v);fill_frame();start_job(0);drain_words(4);finish_job(0,0);nominal_counts();end
  endtask
  task automatic no_job_abort;
    begin
      @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;in_valid=0;start_valid=0;frame_open=0;job_started=0;
      repeat(3)@(negedge clk);
      if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_W1 pre-start abort fabricated completion or retained input");
    end
  endtask
  task automatic hard_reset;
    begin
      @(negedge clk);reset=1;in_valid=0;start_valid=0;out_ready=0;done_ready=0;
      repeat(3)@(negedge clk);
      if(busy||done_valid||out_valid||input_stored||in_ready||start_ready)$fatal(1,"FAIL_W1 reset did not suppress lifecycle");
      reset=0;frame_open=0;job_started=0;repeat(3)@(negedge clk);
      if(busy||done_valid||out_valid||input_stored||start_ready||!in_ready)$fatal(1,"FAIL_W1 reset retained old frame/job");
    end
  endtask

  integer beat,j,old_start;
  initial begin
    repeat(4)@(negedge clk);reset=0;@(negedge clk);
    new_frame(0);
    // RAM reset does not clear payload: deliberately dirty all four A words.
    dut.u_s.storage.bank0[112]=128'hffffffffffffffffffffffffffffffff;
    dut.u_s.storage.bank1[112]=128'hffffffffffffffffffffffffffffffff;
    dut.u_s.storage.bank2[112]=128'hffffffffffffffffffffffffffffffff;
    dut.u_s.storage.bank3[112]=128'hffffffffffffffffffffffffffffffff;
    force dut.permit_s_rsp=1'b0;
    send_beat(0);while(!dut.s_valid)@(negedge clk);
    if(!busy)$fatal(1,"FAIL_W1 first accepted input does not retain frame ownership");
    // Hold the next public beat through real native ACK backpressure.
    @(negedge clk);in_valid=1;in_data=raw_word(1);start_valid=1;
    repeat(6)begin @(negedge clk);if(in_ready||input_stored||start_ready||m_commands!=mc0)$fatal(1,"FAIL_W1 partial input or pending ACK admitted start");end
    start_valid=0;release dut.permit_s_rsp;
    while(!in_ready)@(negedge clk);
    @(posedge clk);#1;@(negedge clk);in_valid=0;
    for(beat=2;beat<7;beat=beat+1)send_beat(beat);
    while(ingress_ack-ia0<7)@(negedge clk);
    // The eighth input handshake is insufficient until its actual ACK retires.
    force dut.permit_s_rsp=1'b0;
    send_beat(7);while(!dut.s_valid)@(negedge clk);
    start_valid=1;
    repeat(6)begin @(negedge clk);if(input_stored||start_ready||start_accepts!=st0||ingress_ack-ia0!=7)$fatal(1,"FAIL_W1 last accept confused with stored ACK");end
    start_valid=0;release dut.permit_s_rsp;
    while(!input_stored)@(negedge clk);
    repeat(5)@(negedge clk);
    if(start_accepts!=st0||m_commands!=mc0||load_commands!=lc0)$fatal(1,"FAIL_W1 early start pulse queued");
    for(beat=0;beat<8;beat=beat+1)if(ram_word(448+beat)!==canonical_word(beat))$fatal(1,"FAIL_W1 dirty RAM or ignored-padding bytes not actually overwritten");
    pass_case("W1_INPUT8_STORED_BEFORE_START");
    pass_case("W1_EARLY_START_PULSE_NOT_QUEUED");
    pass_case("W1_CANONICAL_PADDING_AND_STALE_RAM");
    pass_case("W1_PUBLIC_INGRESS_NATIVE_ACK_BACKPRESSURE");
    // Hold start valid throughout RUN: no second start may be enqueued.
    start_job(1);drain_words(4);finish_job(0,0);nominal_counts();
    pass_case("W1_DOT8_LITERAL_P2");pass_case("W1_INPUT_OUTPUT_DONE_BACKPRESSURE");
    pass_case("W1_PHASED_S_M_T_COUNTS_AND_HELD_START_ONCE");
    pass_case("W1_DONE_RETIRES_BEFORE_NEXT_FRAME_READY");
    recover(1);pass_case("W1_DOT8_ZERO");
    recover(2);pass_case("W1_DOT8_MAX_POSITIVE");
    recover(3);pass_case("W1_DOT8_MIN_NEGATIVE");
    recover(4);pass_case("W1_DOT8_DISTINCT_COLUMNS");
    pass_case("W1_TWO_DIFFERENT_FRAMES_NO_STALE_COMPLETE");

    // Held start asserted before final ACK: accepts exactly once after ready.
    new_frame(4);for(beat=0;beat<7;beat=beat+1)send_beat(beat);
    while(ingress_ack-ia0<7)@(negedge clk);
    force dut.permit_s_rsp=1'b0;send_beat(7);while(!dut.s_valid)@(negedge clk);
    start_valid=1;repeat(4)@(negedge clk);
    if(start_accepts!=st0||input_stored||start_ready)$fatal(1,"FAIL_W1 held early start accepted prematurely");
    release dut.permit_s_rsp;
    while(start_accepts==st0)@(negedge clk);
    repeat(3)@(negedge clk);start_valid=0;
    drain_words(4);finish_job(0,0);nominal_counts();pass_case("W1_HELD_START_ACCEPTS_ONCE_AFTER_READY");

    // Abort before start: partial, native-accepted/pending-ACK, complete frame.
    new_frame(4);for(beat=0;beat<3;beat=beat+1)send_beat(beat);
    while(ingress_ack-ia0<3)@(negedge clk);no_job_abort();recover(0);pass_case("W1_ABORT_PARTIAL_INPUT_RECOVER");
    new_frame(3);force dut.permit_s_rsp=1'b0;send_beat(0);while(!dut.s_valid)@(negedge clk);
    if(ingress_req-iq0!=1||ingress_ack-ia0!=0)$fatal(1,"FAIL_W1 missing accepted input pending ACK setup");
    no_job_abort();release dut.permit_s_rsp;recover(4);pass_case("W1_ABORT_INPUT_NATIVE_ACCEPT_PENDING_ACK_RECOVER");
    new_frame(1);fill_frame();no_job_abort();recover(2);pass_case("W1_ABORT_COMPLETE_NOT_STARTED_RECOVER");

    // RUN abort flushes native ACK; one error completion, no implicit replay.
    new_frame(4);fill_frame();force dut.permit_s_rsp=1'b0;start_job(0);
    while(!dut.s_valid)@(negedge clk);
    if(s_pending_addr<456||!s_pending_write)$fatal(1,"FAIL_W1 RUN pending-result ACK setup");
    @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;
    finish_job(1,0);recover(3);pass_case("W1_ABORT_RUN_PENDING_RESULT_ACK_RECOVER");
    new_frame(4);fill_frame();start_job(0);drain_words(2);
    @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;
    if(job_output_count!=2)$fatal(1,"FAIL_W1 consumed prefix retracted or advanced");
    finish_job(1,0);recover(0);pass_case("W1_ABORT_AFTER_CONSUMED_OUTPUT_PREFIX_RECOVER");

    // Existing DONE is retained under abort, including ready on the same edge.
    new_frame(4);fill_frame();start_job(0);drain_words(4);while(!done_valid)@(negedge clk);
    @(negedge clk);abort=1;repeat(3)begin @(negedge clk);if(!done_valid||done_error)$fatal(1,"FAIL_W1 abort mutated existing success DONE");end
    abort=0;finish_job(0,1);nominal_counts();recover(1);pass_case("W1_ABORT_EXISTING_DONE_AND_SAME_EDGE_READY_RECOVER");

    // Reset invalidates control ownership, not physical RAM payload.
    new_frame(4);send_beat(0);send_beat(1);while(ingress_ack-ia0<2)@(negedge clk);
    hard_reset();recover(3);pass_case("W1_RESET_PARTIAL_INPUT_RECOVER");
    new_frame(4);force dut.permit_s_rsp=1'b0;send_beat(0);while(!dut.s_valid)@(negedge clk);
    hard_reset();release dut.permit_s_rsp;recover(2);pass_case("W1_RESET_INPUT_NATIVE_ACCEPT_PENDING_ACK_RECOVER");
    new_frame(4);fill_frame();hard_reset();recover(1);pass_case("W1_RESET_COMPLETE_NOT_STARTED_RECOVER");
    new_frame(4);fill_frame();force dut.permit_m_rsp=1'b0;start_job(0);while(!dut.m_rsp_valid)@(negedge clk);
    hard_reset();release dut.permit_m_rsp;recover(0);pass_case("W1_RESET_RUN_RECOVER");
    new_frame(4);fill_frame();start_job(0);drain_words(2);hard_reset();recover(3);pass_case("W1_RESET_AFTER_CONSUMED_OUTPUT_PREFIX_RECOVER");
    new_frame(4);fill_frame();start_job(0);drain_words(4);while(!done_valid)@(negedge clk);
    hard_reset();recover(2);pass_case("W1_RESET_EXISTING_DONE_RECOVER");

    // Block helper request after public input capture, then cancel pre-native.
    new_frame(4);force dut.permit_s_req=1'b0;send_beat(0);repeat(5)@(negedge clk);
    if(in_accepts-i0!=1||ingress_req-iq0!=0||input_stored||start_ready)$fatal(1,"FAIL_W1 request-stall acceptance/setup");
    no_job_abort();release dut.permit_s_req;recover(1);pass_case("W1_ABORT_CAPTURED_BEFORE_NATIVE_REQUEST_RECOVER");
    // TB-only fault at one real EXEC handshake; no new runtime DUT field.
    new_frame(4);fill_frame();start_job(0);wait(dut.operation==4&&dut.state==1);
    @(negedge clk);force dut.m_cmd_data=64'h988c;
    @(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;
    finish_job(1,0);
    if(job_output_count!=0||job_execs!=1)$fatal(1,"FAIL_W1 native EXEC error published data or skipped EXEC");
    recover(4);pass_case("W1_NATIVE_EXEC_DESCRIPTOR_ERROR_RECOVER");
    $display("PASS_W1_MST cases=%0d cycles=%0d inputAccept=%0d ingressReq=%0d ingressACK=%0d resultReq=%0d resultACK=%0d readReq=%0d readACK=%0d Mcmd=%0d Mrsp=%0d Ttake=%0d",cases,cycles,in_accepts,ingress_req,ingress_ack,result_req,result_ack,read_req,read_ack,m_commands,m_responses,t_reads);
    $finish;
  end
endmodule
