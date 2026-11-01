"""Generate a self-contained SV TB from frozen independent math vectors."""
import argparse
import json
from pathlib import Path


BODY = r'''
  reg clk=0; always #5 clk=~clk;
  reg reset=1,abort=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
  reg [127:0] in_data=0;
  wire in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,out_valid,out_last;
  wire [127:0] out_data; wire [9:0] out_index;
  block_w3_ffn8_top dut(.*);
  integer cycles=0,cases=0,v=0,ingress=0,sreq=0,sack=0,writes=0,reads=0;
  integer mcmd=0,mrsp=0,loads=0,ldone=0,abeats=0,bbeats=0,ecmd=0,ersp=0,gcmd=0,grsp=0;
  integer enative=0,gnative=0,gretired=0,tbegin=0,twrite=0,tcommit=0,ttake=0,trelease=0,starts=0,dtake=0;
  integer i0,q0,a0,w0,r0,mc0,mr0,l0,ld0,ab0,bb0,e0,er0,g0,gr0,en0,gn0,go0,tb0,tw0,tc0,tt0,tr0,st0;
  integer stage_acks[0:9]; integer frame_ingress_acks=0,frame_ingress_reqs=0,run_writes=0,run_reads=0;
  reg frame_open=0,job=0,pending=0,pending_write;reg [9:0] pending_addr;reg [127:0] pending_data;
  reg hold_out=0,hold_done=0,hold_s=0,hold_m=0,hold_e=0,hold_g=0,hold_in=0;
  reg [127:0] prev_out,prev_s,prev_m,prev_in;reg [9:0] prev_index;
  reg prev_last,prev_de,prev_ds,prev_ee,prev_es,prev_ge,prev_gs;
  reg load_completed=0; integer projection_execs=0;

  function automatic [127:0] raw_word;
    input integer vector_no,beat;reg [127:0] word;
    begin word=input_word(vector_no,beat);
      if(beat==0)word[127:64]=64'hbadc0ffee55aacc1;
      else if(beat<4)word=128'hfedcba98765432100123456789abcdef;
      raw_word=word;
    end
  endfunction
  function automatic signed [7:0] byte_at;
    input integer vector_no,base,offset;reg [127:0] word;
    begin word=input_word(vector_no,base+offset/16);byte_at=word[8*(offset%16)+:8];end
  endfunction
  function automatic signed [15:0] stage_lane;
    input integer vector_no,address,lane;reg [127:0] word;
    begin word=stage_word(vector_no,address);stage_lane=word[16*lane+:16];end
  endfunction
  function automatic signed [63:0] rne64;
    input signed [63:0] value;input integer shift;reg signed [63:0] q;reg [63:0] remn,half;
    begin if(shift==0)rne64=value;else begin q=value>>>shift;remn=$unsigned(value)&((64'd1<<shift)-1);half=64'd1<<(shift-1);rne64=q+((remn>half)||((remn==half)&&q[0]));end end
  endfunction
  function automatic signed [15:0] clip16;
    input signed [63:0] value;
    begin if(value>32767)clip16=32767;else if(value< -32768)clip16=-32768;else clip16=value[15:0];end
  endfunction
  task automatic crosscheck_frozen;
    input integer nvec;integer n,k;reg signed [63:0] sg,su,sd;reg signed [15:0] residual;
    begin for(n=0;n<8;n=n+1)begin sg=0;su=0;sd=0;
      for(k=0;k<8;k=k+1)begin
        sg=sg+byte_at(nvec,0,k)*byte_at(nvec,4,8*n+k);
        su=su+byte_at(nvec,0,k)*byte_at(nvec,8,8*n+k);
        sd=sd+stage_lane(nvec,468,k)*byte_at(nvec,12,8*n+k);
      end
      residual=$signed(byte_at(nvec,0,n))*8;
      if(clip16(rne64(sg,4))!==stage_lane(nvec,464,n)||clip16(rne64(su,4))!==stage_lane(nvec,465,n)||
         clip16(rne64(sd,7))!==stage_lane(nvec,472,n)||residual!==stage_lane(nvec,467,n)||
         clip16($signed(stage_lane(nvec,472,n))+$signed(residual))!==stage_lane(nvec,473,n))
        $fatal(1,"FAIL_W3 frozen independent M/residual formula mismatch");
    end end
  endtask
  function automatic [127:0] ram_word;
    input integer address;
    begin case(address%4)
      0:ram_word=dut.u_s.storage.bank0[address/4];1:ram_word=dut.u_s.storage.bank1[address/4];
      2:ram_word=dut.u_s.storage.bank2[address/4];3:ram_word=dut.u_s.storage.bank3[address/4];
    endcase end
  endfunction

  always @(posedge clk)begin
    cycles=cycles+1;if(cycles>300000)$fatal(1,"FAIL_W3 FFN watchdog");
    // DONE is a public transaction and survives leaf abort/internal reset.
    if(reset)hold_done=0;else begin
      if(hold_done&&(!done_valid||done_error!==prev_de||done_saturated!==prev_ds))$fatal(1,"FAIL_W3 DONE changed under stall/abort");
      hold_done=done_valid&&!done_ready;prev_de=done_error;prev_ds=done_saturated;
      if(done_valid&&done_ready)dtake=dtake+1;
    end
    if(reset||dut.leaf_reset)begin hold_out=0;hold_s=0;hold_m=0;hold_e=0;hold_g=0;hold_in=0;pending=0;end
    else begin
      if(hold_in&&(!in_valid||in_data!==prev_in))$fatal(1,"FAIL_W3 TB ingress changed while stalled");
      if(hold_out&&(!out_valid||out_data!==prev_out||out_index!==prev_index||out_last!==prev_last))$fatal(1,"FAIL_W3 output stall");
      if(hold_s&&(!dut.s_valid||dut.s_dout!==prev_s))$fatal(1,"FAIL_W3 S ACK stall");
      if(hold_m&&(!dut.m_rsp_valid||dut.m_rsp_data!==prev_m))$fatal(1,"FAIL_W3 M response stall");
      if(hold_e&&(!dut.e_rsp_valid||dut.e_rsp_error!==prev_ee||dut.e_rsp_saturated!==prev_es))$fatal(1,"FAIL_W3 E response stall");
      if(hold_g&&(!dut.g_rsp_valid||dut.g_rsp_error!==prev_ge||dut.g_rsp_saturated!==prev_gs))$fatal(1,"FAIL_W3 G response stall");
      hold_in=in_valid&&!in_ready;prev_in=in_data;
      hold_out=out_valid&&!out_ready;prev_out=out_data;prev_index=out_index;prev_last=out_last;
      hold_s=dut.s_valid&&!dut.s_take;prev_s=dut.s_dout;
      hold_m=dut.m_rsp_valid&&!dut.m_rsp_ready;prev_m=dut.m_rsp_data;
      hold_e=dut.e_rsp_valid&&!dut.e_rsp_ready;prev_ee=dut.e_rsp_error;prev_es=dut.e_rsp_saturated;
      hold_g=dut.g_rsp_valid&&!dut.g_rsp_ready;prev_ge=dut.g_rsp_error;prev_gs=dut.g_rsp_saturated;
      if(in_valid&&in_ready)begin if(!frame_open||job||ingress-i0>=16)$fatal(1,"FAIL_W3 ingress ownership");ingress=ingress+1;end
      if(dut.s_req&&dut.s_ready)begin
        if(pending)$fatal(1,"FAIL_W3 two ordinary S owners");pending=1;pending_addr=dut.s_addr;pending_write=dut.s_we;pending_data=dut.s_din;sreq=sreq+1;
        if(dut.s_we)begin writes=writes+1;
          if(dut.s_addr>=448&&dut.s_addr<=463)begin
            if(job||dut.s_addr!==448+frame_ingress_reqs||dut.s_din!==input_word(v,dut.s_addr-448))$fatal(1,"FAIL_W3 input order/canonical/literal clobber");frame_ingress_reqs=frame_ingress_reqs+1;
          end else if(dut.s_addr>=464&&dut.s_addr<=473)begin
            if(!job||dut.s_din!==stage_word(v,dut.s_addr))$fatal(1,"FAIL_W3 stage%0d data=%032h expected=%032h",dut.s_addr,dut.s_din,stage_word(v,dut.s_addr));run_writes=run_writes+1;
          end else $fatal(1,"FAIL_W3 unexpected S write");
        end else begin reads=reads+1;run_reads=run_reads+1;if(!job||dut.s_addr<464||dut.s_addr>473)$fatal(1,"FAIL_W3 unexpected S read");end
      end
      if(dut.s_valid&&dut.s_take)begin
        if(!pending)$fatal(1,"FAIL_W3 S ACK without owner");
        if(pending_write&&dut.s_dout!==pending_data)$fatal(1,"FAIL_W3 write echo ACK");
        if(!pending_write&&dut.s_dout!==stage_word(v,pending_addr))$fatal(1,"FAIL_W3 S stage read mismatch");
        if(pending_write&&pending_addr<464)frame_ingress_acks=frame_ingress_acks+1;
        if(pending_write&&pending_addr>=464)stage_acks[pending_addr-464]=stage_acks[pending_addr-464]+1;
        pending=0;sack=sack+1;
      end
      if(input_stored&&(ingress-i0!=16||frame_ingress_acks!=16||(!job&&pending)))$fatal(1,"FAIL_W3 marker before16 input/ACK");
      if(start_ready&&!input_stored)$fatal(1,"FAIL_W3 early ready");
      if(start_valid&&start_ready)begin if(job||!input_stored||frame_ingress_acks!=16)$fatal(1,"FAIL_W3 early/duplicate start");job=1;starts=starts+1;end
      if(dut.load_valid&&dut.load_ready)begin
        if(!job||loads-l0>2)$fatal(1,"FAIL_W3 loader lifecycle");
        if(dut.u_s.load_a_wide!==(loads-l0==2)||dut.u_s.load_b_wide||dut.u_s.load_rows!=1||dut.u_s.load_tiles!=1)$fatal(1,"FAIL_W3 loader format");
        load_completed=0;loads=loads+1;
      end
      if(dut.load_done_valid&&dut.load_done_take)begin ldone=ldone+1;load_completed=!dut.load_done_error;end
      if(dut.a_valid&&dut.a_ready)begin
        if(dut.a_data!==(loads-l0==3?stage_word(v,468):input_word(v,0)))$fatal(1,"FAIL_W3 loader A payload");abeats=abeats+1;
      end
      if(dut.b_valid&&dut.b_ready)bbeats=bbeats+1;
      if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
        if(!job)$fatal(1,"FAIL_W3 M before start");mcmd=mcmd+1;
        if(dut.m_cmd_op==10)begin if(!load_completed)$fatal(1,"FAIL_W3 EXEC before load done");projection_execs=projection_execs+1;end
      end
      if(dut.m_rsp_valid&&dut.m_rsp_ready)mrsp=mrsp+1;
      if(dut.e_req_valid&&dut.e_req_ready)ecmd=ecmd+1;
      if(dut.e_rsp_valid&&dut.e_rsp_ready)begin
        if(!dut.e_rsp_error&&stage_acks[dut.e_final?9:3]!=1)$fatal(1,"FAIL_W3 E completion before destination ACK");ersp=ersp+1;
      end
      if(dut.g_req_valid&&dut.g_req_ready)gcmd=gcmd+1;
      if(dut.g_rsp_valid&&dut.g_rsp_ready)begin if(!dut.g_rsp_error&&stage_acks[4]!=1)$fatal(1,"FAIL_W3 G completion before destination ACK");grsp=grsp+1;end
      if(dut.e_in_valid&&dut.e_in_ready)enative=enative+1;
      if(dut.g_in_valid&&dut.g_in_ready)gnative=gnative+1;
      if(dut.g_out_valid&&dut.g_out_ready)gretired=gretired+1;
      if(dut.u_t.begin_valid&&dut.u_t.begin_ready)tbegin=tbegin+1;
      if(dut.u_t.write_valid&&dut.u_t.write_ready)begin if(dut.u_t.write_index!=0||dut.u_t.write_data!==stage_word(v,473))$fatal(1,"FAIL_W3 T data/index");twrite=twrite+1;end
      if(dut.u_t.commit_valid&&dut.u_t.commit_ready)tcommit=tcommit+1;
      if(out_valid&&out_ready)begin if(ttake-tt0!=0||out_index!=0||!out_last||out_data!==stage_word(v,473))$fatal(1,"FAIL_W3 final oracle");ttake=ttake+1;end
      if(dut.u_t.release_valid&&dut.u_t.release_ready)trelease=trelease+1;
    end
  end
  task automatic mark;
    input [8*100-1:0] name;
    begin cases=cases+1;$display("CASE_PASS %0s",name);end
  endtask
  task automatic new_frame;
    input integer nv;integer k;
    begin @(negedge clk);if(busy||done_valid||input_stored||out_valid||!in_ready||start_ready)$fatal(1,"FAIL_W3 nonempty frame");
      v=nv;crosscheck_frozen(v);frame_open=1;job=0;load_completed=0;projection_execs=0;frame_ingress_acks=0;frame_ingress_reqs=0;run_writes=0;run_reads=0;
      for(k=0;k<10;k=k+1)stage_acks[k]=0;
      i0=ingress;q0=sreq;a0=sack;w0=writes;r0=reads;mc0=mcmd;mr0=mrsp;l0=loads;ld0=ldone;ab0=abeats;bb0=bbeats;e0=ecmd;er0=ersp;g0=gcmd;gr0=grsp;en0=enative;gn0=gnative;go0=gretired;tb0=tbegin;tw0=twrite;tc0=tcommit;tt0=ttake;tr0=trelease;st0=starts;
      in_valid=0;start_valid=0;out_ready=0;done_ready=0;
      // Dirty A padding and mid padding are overwritten, never supplied by reset.
      dut.u_s.storage.bank0[112]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank1[112]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank2[112]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank3[112]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank1[117]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank2[117]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank3[117]=128'hffffffffffffffffffffffffffffffff;
    end
  endtask
  task automatic send;
    input integer beat;
    begin @(negedge clk);in_valid=1;in_data=raw_word(v,beat);while(!in_ready)@(negedge clk);@(posedge clk);#1;if(!busy)$fatal(1,"FAIL_W3 accepted ingress not busy");@(negedge clk);in_valid=0;end
  endtask
  task automatic fill;
    integer beat;
    begin for(beat=0;beat<16;beat=beat+1)send(beat);while(!input_stored)@(negedge clk);if(frame_ingress_acks!=16||!busy||in_ready)$fatal(1,"FAIL_W3 incomplete stored frame");end
  endtask
  task automatic start_job;
    input hold_start;
    begin @(negedge clk);if(!start_ready)$fatal(1,"FAIL_W3 not start ready");start_valid=1;@(posedge clk);#1;@(negedge clk);if(starts-st0!=1||!busy||start_ready)$fatal(1,"FAIL_W3 start acceptance");if(!hold_start)start_valid=0;end
  endtask
  task automatic take_output;
    integer j;
    begin while(!out_valid)@(negedge clk);for(j=0;j<7;j=j+1)begin if(out_data!==stage_word(v,473)||out_index!=0||!out_last)$fatal(1,"FAIL_W3 held output");@(negedge clk);end
      out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;
    end
  endtask
  task automatic finish;
    input error_expected,abort_at_done;integer j,before_take;
    begin while(!done_valid)@(negedge clk);
      for(j=0;j<5;j=j+1)begin
        if(!done_valid||done_error!==error_expected||in_ready||start_ready||!busy)$fatal(1,"FAIL_W3 retained completion");
        if(!error_expected&&done_saturated!==expected_sat(v))$fatal(1,"FAIL_W3 accumulated saturation");@(negedge clk);
      end
      if(!error_expected&&(ttake-tt0!=1||trelease-tr0!=1||dut.t_busy))$fatal(1,"FAIL_W3 completion before T release");
      before_take=dtake;start_valid=0;done_ready=1;abort=abort_at_done;
      @(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;frame_open=0;job=0;repeat(3)@(negedge clk);
      if(dtake!=before_take+1||busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_W3 duplicate or stale completion");
    end
  endtask
  task automatic normal_counts;
    integer k;
    begin
      if(ingress-i0!=16||frame_ingress_acks!=16||sreq-q0!=32||sack-a0!=32||writes-w0!=26||reads-r0!=6||run_writes!=10||run_reads!=6||pending)$fatal(1,"FAIL_W3 32 S/26write/6read counts");
      if(mcmd-mc0!=15||mrsp-mr0!=15||projection_execs!=3||loads-l0!=3||ldone-ld0!=3||abeats-ab0!=3||bbeats-bb0!=3)$fatal(1,"FAIL_W3 projection counts");
      if(ecmd-e0!=2||ersp-er0!=2||gcmd-g0!=1||grsp-gr0!=1||enative-en0!=2||gnative-gn0!=4||gretired-go0!=4)$fatal(1,"FAIL_W3 native/adapter counts");
      if(tbegin-tb0!=1||twrite-tw0!=1||tcommit-tc0!=1||ttake-tt0!=1||trelease-tr0!=1||starts-st0!=1)$fatal(1,"FAIL_W3 T counts");
      for(k=0;k<10;k=k+1)if(stage_acks[k]!=1||ram_word(464+k)!==stage_word(v,464+k))$fatal(1,"FAIL_W3 final intermediate RAM%0d",464+k);
    end
  endtask
  task automatic run_normal;
    input integer nv;
    begin new_frame(nv);fill();start_job(0);take_output();finish(0,0);normal_counts();end
  endtask
  task automatic prestart_abort;
    begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;in_valid=0;start_valid=0;frame_open=0;job=0;repeat(3)@(negedge clk);
      if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_W3 prestart abort fabricated done");
    end
  endtask
  task automatic hard_reset;
    begin @(negedge clk);reset=1;in_valid=0;start_valid=0;out_ready=0;done_ready=0;repeat(3)@(negedge clk);reset=0;frame_open=0;job=0;repeat(3)@(negedge clk);
      if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_W3 hard reset stale lifecycle");end
  endtask
  integer beat,k;
  initial begin
    repeat(4)@(negedge clk);reset=0;@(negedge clk);
    new_frame(0);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);
    start_valid=1;repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0||mcmd!=mc0)$fatal(1,"FAIL_W3 early pending ACK start");end
    start_valid=0;release dut.permit_s_rsp;for(beat=1;beat<15;beat=beat+1)send(beat);
    while(frame_ingress_acks<15)@(negedge clk);force dut.permit_s_rsp=1'b0;send(15);while(!dut.s_valid)@(negedge clk);
    start_valid=1;repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0)$fatal(1,"FAIL_W3 last input accept before ACK");end
    start_valid=0;release dut.permit_s_rsp;while(!input_stored)@(negedge clk);repeat(3)@(negedge clk);
    if(starts!=st0)$fatal(1,"FAIL_W3 early start pulse queued");
    for(beat=0;beat<16;beat=beat+1)if(ram_word(448+beat)!==input_word(v,beat))$fatal(1,"FAIL_W3 canonical ingress RAM");
    mark("W3_INPUT16_STORED_AND_PADDING_ACK_GATE");
    start_job(1);take_output();finish(0,0);normal_counts();mark("W3_FFN8_NORMAL_STAGES_COUNTS_HELD_START");
    run_normal(1);mark("W3_FFN8_ZERO");run_normal(2);mark("W3_FFN8_POSITIVE_EXTREME_SATURATION");
    run_normal(3);mark("W3_FFN8_NEGATIVE_EXTREME_SATURATION");run_normal(4);mark("W3_FFN8_MIXED_WEIGHTS");run_normal(5);mark("W3_FFN8_SPARSE_DISTINCT_WEIGHTS");
    new_frame(4);for(beat=0;beat<15;beat=beat+1)send(beat);while(frame_ingress_acks<15)@(negedge clk);
    force dut.permit_s_rsp=1'b0;send(15);start_valid=1;repeat(4)@(negedge clk);
    if(starts!=st0||input_stored)$fatal(1,"FAIL_W3 held start early");release dut.permit_s_rsp;while(starts==st0)@(negedge clk);start_valid=0;
    take_output();finish(0,0);normal_counts();mark("W3_HELD_START_AFTER_FINAL_ACK_REPEAT");
    new_frame(0);force dut.permit_s_req=1'b0;send(0);repeat(4)@(negedge clk);prestart_abort();release dut.permit_s_req;run_normal(4);mark("W3_ABORT_CAPTURED_BEFORE_S_ACCEPT_RECOVER");
    new_frame(3);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);prestart_abort();release dut.permit_s_rsp;run_normal(0);mark("W3_ABORT_INPUT_PENDING_ACK_RECOVER");
    new_frame(2);fill();prestart_abort();run_normal(5);mark("W3_ABORT_COMPLETE_PRESTART_RECOVER");
    new_frame(4);fill();force dut.permit_s_rsp=1'b0;start_job(0);while(!dut.s_valid)@(negedge clk);
    @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;finish(1,0);run_normal(1);mark("W3_ABORT_RUN_S_ACK_RECOVER");
    new_frame(2);fill();start_job(0);take_output();abort=1;@(posedge clk);#1;@(negedge clk);abort=0;
    if(ttake-tt0!=1)$fatal(1,"FAIL_W3 consumed output retracted");finish(1,0);run_normal(4);mark("W3_ABORT_AFTER_CONSUMED_PREFIX_RECOVER");
    new_frame(2);fill();start_job(0);take_output();while(!done_valid)@(negedge clk);
    @(negedge clk);abort=1;repeat(3)begin @(negedge clk);if(!done_valid||done_error||!done_saturated)$fatal(1,"FAIL_W3 existing DONE flags changed");end
    abort=0;finish(0,1);normal_counts();mark("W3_DONE_ABORT_READY_EXACTLY_ONCE_SAT_HOLD");
    new_frame(4);send(0);send(1);hard_reset();run_normal(3);mark("W3_RESET_PARTIAL_INPUT_RECOVER");
    new_frame(4);fill();force dut.permit_g_rsp=1'b0;start_job(0);while(!dut.g_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();release dut.permit_g_rsp;run_normal(0);mark("W3_RESET_RETAINED_G_RESPONSE_RECOVER");
    new_frame(4);fill();start_job(0);while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();run_normal(5);mark("W3_RESET_COMMITTED_T_STALL_RECOVER");
    new_frame(4);fill();start_job(0);wait(dut.state==5&&dut.m_phase==2);
    @(negedge clk);force dut.m_cmd_data=64'h988c;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;
    finish(1,0);if(ttake!=tt0)$fatal(1,"FAIL_W3 error published output");run_normal(3);mark("W3_NATIVE_EXEC_ERROR_RECOVER");
    // Actual newly integrated native E error, not a fabricated adapter flag.
    new_frame(4);fill();start_job(0);wait(dut.e_in_valid&&dut.e_in_ready);
    @(negedge clk);force dut.e_in_op=4'd14;@(posedge clk);#1;@(negedge clk);release dut.e_in_op;
    finish(1,0);if(ttake!=tt0||twrite!=tw0||stage_acks[3]!=0)$fatal(1,"FAIL_W3 native E error wrote residual/output");
    run_normal(5);mark("W3_NATIVE_E_ERROR_NO_WRITE_RECOVER");
    // One invalid G beat among valid beats must error the whole service only
    // after every accepted pair is retired; no partial mid/T publication.
    new_frame(4);fill();start_job(0);wait(dut.g_in_valid&&dut.g_in_ready);
    @(negedge clk);force dut.g_in_fn=3'd4;@(posedge clk);#1;@(negedge clk);release dut.g_in_fn;
    finish(1,0);if(gnative-gn0!=4||gretired-go0!=4||stage_acks[4]!=0||ttake!=tt0||twrite!=tw0)$fatal(1,"FAIL_W3 native G error did not drain or wrote mid/output");
    run_normal(3);mark("W3_ONE_NATIVE_G_BEAT_ERROR_DRAIN_NO_WRITE_RECOVER");
    // E/G response stalls are real held service outputs after destination ACK.
    new_frame(4);fill();force dut.permit_e_rsp=1'b0;start_job(0);while(!dut.e_rsp_valid)@(negedge clk);repeat(6)@(negedge clk);release dut.permit_e_rsp;
    force dut.permit_g_rsp=1'b0;while(!dut.g_rsp_valid)@(negedge clk);repeat(6)@(negedge clk);release dut.permit_g_rsp;
    take_output();finish(0,0);normal_counts();mark("W3_E_G_RESPONSE_HOLD_AFTER_REAL_WRITE_ACK");
    $display("PASS_W3_FFN8 cases=%0d cycles=%0d input=%0d Sreq=%0d Sack=%0d Mcmd=%0d Mrsp=%0d Ttake=%0d",cases,cycles,ingress,sreq,sack,mcmd,mrsp,ttake);$finish;
  end
'''


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=ap.parse_args()
    d=json.loads((a.directory/'w3-contract-vectors.json').read_text(encoding='utf-8'))
    functions=[]
    for name,args,items,key in [
      ('input_word','input integer vector_no,beat;',[(v['index']*16+i,w) for v in d['vectors'] for i,w in enumerate(v['expected']['ingress_words_hex'])],'vector_no*16+beat'),
      ('stage_word','input integer vector_no,address;',[(v['index']*1024+int(addr),w) for v in d['vectors'] for addr,w in v['expected']['S_words_hex'].items()],'vector_no*1024+address')]:
        functions += ['  function automatic [127:0] '+name+';', '    '+args, '    begin case('+key+')']
        functions += ['      {}:{}=128\'h{};'.format(k,name,w) for k,w in items]
        functions += ['      default:'+name+'=128\'hbad;','    endcase end','  endfunction']
    functions += ['  function automatic expected_sat;input integer vector_no;begin case(vector_no)']
    functions += ['    {}:expected_sat=1\'b{};'.format(v['index'],int(v['expected']['done_saturated'])) for v in d['vectors']]
    functions += ['    default:expected_sat=1\'bx;endcase end endfunction']
    source='`timescale 1ns/1ps\n// Frozen expectations from independent math oracle, not DUT values.\nmodule block_w3_ffn8_tb;\n'+'\n'.join(functions)+'\n'+BODY+'\nendmodule\n'
    (a.directory/'block_w3_ffn8_tb.sv').write_bytes(source.encode('utf-8'))
    print('Prepared self-contained FFN8 TB with6 frozen independent stage/input vectors; not simulated')


if __name__=='__main__':main()
