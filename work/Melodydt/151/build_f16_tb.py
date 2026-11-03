"""Generate a self-contained SV TB from frozen independent math vectors."""
import argparse
import json
import hashlib
from pathlib import Path


CASE_IDS=['F16_INPUT17_STORED_AND_PADDING_ACK_GATE', 'F16_H8I8_NORMAL_STAGES_COUNTS_HELD_START', 'F16_ZERO_X_VARIABLE_GAMMA', 'F16_POSITIVE_EXTREME_SATURATION', 'F16_NEGATIVE_EXTREME_SATURATION', 'F16_SIGNED_NONUNITY_GAMMA', 'F16_ZERO_GAMMA_PRESERVES_FULL_S16_X', 'F16_SPARSE_LAYOUT', 'F16_SEEDED_RANDOM_0', 'F16_SEEDED_RANDOM_1', 'F16_ZERO_GAMMA_NON8_RESIDUAL', 'F16_HELD_START_AFTER_FINAL_ACK_REPEAT', 'F16_ABORT_CAPTURED_BEFORE_S_ACCEPT_RECOVER', 'F16_ABORT_INPUT_PENDING_ACK_RECOVER', 'F16_ABORT_COMPLETE_PRESTART_RECOVER', 'F16_ABORT_RUN_S_ACK_RECOVER', 'F16_ABORT_AFTER_CONSUMED_PREFIX_RECOVER', 'F16_DONE_ABORT_READY_EXACTLY_ONCE_SAT_HOLD', 'F16_RESET_PARTIAL_INPUT_RECOVER', 'F16_RESET_RETAINED_G_RESPONSE_RECOVER', 'F16_RESET_COMMITTED_T_STALL_RECOVER', 'F16_NATIVE_EXEC_ERROR_RECOVER', 'F16_NATIVE_E_ERROR_NO_WRITE_RECOVER', 'F16_ONE_NATIVE_G_BEAT_ERROR_DRAIN_NO_WRITE_RECOVER', 'F16_E_G_RESPONSE_HOLD_AFTER_REAL_WRITE_ACK', 'F16_N_SERVICE_RESPONSE_HOLD_AFTER474ACK', 'F16_NATIVE_N_ERROR_NO_PROJECTION_COORDINATED_RECOVER', 'F16_RESET_HELD_N_SERVICE_RESPONSE_RECOVER', 'F16_ABORT_N_DESTINATION_ACK_COORDINATED_RECOVER', 'F16_S_SERVICE_ERROR_NO_OUTPUT_RECOVER']

BODY = r'''
  reg clk=0; always #5 clk=~clk;
  reg reset=1,abort=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
  reg [127:0] in_data=0;
  wire in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,out_valid,out_last;
  wire [127:0] out_data; wire [9:0] out_index;
  block_w4_f16_top dut(.*);
  integer cycles=0,cases=0,v=0,ingress=0,sreq=0,sack=0,writes=0,reads=0;
  integer mcmd=0,mrsp=0,loads=0,ldone=0,abeats=0,bbeats=0,ecmd=0,ersp=0,gcmd=0,grsp=0;
  integer enative=0,gnative=0,gretired=0,tbegin=0,twrite=0,tcommit=0,ttake=0,trelease=0,starts=0,dtake=0;
  integer i0,q0,a0,w0,r0,mc0,mr0,l0,ld0,ab0,bb0,e0,er0,g0,gr0,en0,gn0,go0,tb0,tw0,tc0,tt0,tr0,st0;
  integer nservice=0,nservice_rsp=0,ncommands=0,nresponses=0,ns0,nr0,nc0,np0,norm_acks=0;
  integer stage_acks[0:11]; integer frame_ingress_acks=0,frame_ingress_reqs=0,run_writes=0,run_reads=0;
  reg frame_open=0,job=0,pending=0,pending_write;reg [9:0] pending_addr;reg [127:0] pending_data;
  reg hold_out=0,hold_done=0,hold_s=0,hold_m=0,hold_e=0,hold_g=0,hold_in=0;
  reg [127:0] prev_out,prev_s,prev_m,prev_in;reg [9:0] prev_index;
  reg prev_last,prev_de,prev_ds,prev_ee,prev_es,prev_ge,prev_gs;
  reg load_completed=0; integer projection_execs=0;

  function automatic [127:0] raw_word;
    input integer vector_no,beat;reg [127:0] word;
    begin word=input_word(vector_no,beat);
      if(beat>=1&&beat<4)word=128'hfedcba98765432100123456789abcdef;
      raw_word=word;
    end
  endfunction
  function automatic signed [7:0] byte_at;
    input integer vector_no,base,offset;reg [127:0] word;
    begin word=input_word(vector_no,base+offset/16);byte_at=word[8*(offset%16)+:8];end
  endfunction
  function automatic signed [15:0] projection_byte;
    input integer vector_no,lane;reg [127:0] word;
    begin word=norm_word(vector_no);projection_byte=$signed(word[16*lane+:16]);end
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
        sg=sg+projection_byte(nvec,k)*byte_at(nvec,4,8*n+k);
        su=su+projection_byte(nvec,k)*byte_at(nvec,8,8*n+k);
        sd=sd+stage_lane(nvec,468,k)*byte_at(nvec,12,8*n+k);
      end
      residual=stage_lane(nvec,466,n);
      if(clip16(rne64(sg,7))!==stage_lane(nvec,464,n)||clip16(rne64(su,7))!==stage_lane(nvec,465,n)||
         clip16(rne64(sd,7))!==stage_lane(nvec,472,n)||residual!==stage_lane(nvec,467,n)||
         clip16($signed(stage_lane(nvec,472,n))+$signed(residual))!==stage_lane(nvec,473,n))
        $fatal(1,"FAIL_F16 independent S16M/RNE7/original residual formula mismatch");
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
    cycles=cycles+1;if(cycles>300000)$fatal(1,"FAIL_F16 FFN watchdog");
    // DONE is a public transaction and survives leaf abort/internal reset.
    if(reset)hold_done=0;else begin
      if(hold_done&&(!done_valid||done_error!==prev_de||done_saturated!==prev_ds))$fatal(1,"FAIL_F16 DONE changed under stall/abort");
      hold_done=done_valid&&!done_ready;prev_de=done_error;prev_ds=done_saturated;
      if(done_valid&&done_ready)dtake=dtake+1;
    end
    if(reset||dut.leaf_reset)begin hold_out=0;hold_s=0;hold_m=0;hold_e=0;hold_g=0;hold_in=0;pending=0;end
    else begin
      if(hold_in&&(!in_valid||in_data!==prev_in))$fatal(1,"FAIL_F16 TB ingress changed while stalled");
      if(hold_out&&(!out_valid||out_data!==prev_out||out_index!==prev_index||out_last!==prev_last))$fatal(1,"FAIL_F16 output stall");
      if(hold_s&&(!dut.s_valid||dut.s_dout!==prev_s))$fatal(1,"FAIL_F16 S ACK stall");
      if(hold_m&&(!dut.m_rsp_valid||dut.m_rsp_data!==prev_m))$fatal(1,"FAIL_F16 M response stall");
      if(hold_e&&(!dut.e_rsp_valid||dut.e_rsp_error!==prev_ee||dut.e_rsp_saturated!==prev_es))$fatal(1,"FAIL_F16 E response stall");
      if(hold_g&&(!dut.g_rsp_valid||dut.g_rsp_error!==prev_ge||dut.g_rsp_saturated!==prev_gs))$fatal(1,"FAIL_F16 G response stall");
      hold_in=in_valid&&!in_ready;prev_in=in_data;
      hold_out=out_valid&&!out_ready;prev_out=out_data;prev_index=out_index;prev_last=out_last;
      hold_s=dut.s_valid&&!dut.s_take;prev_s=dut.s_dout;
      hold_m=dut.m_rsp_valid&&!dut.m_rsp_ready;prev_m=dut.m_rsp_data;
      hold_e=dut.e_rsp_valid&&!dut.e_rsp_ready;prev_ee=dut.e_rsp_error;prev_es=dut.e_rsp_saturated;
      hold_g=dut.g_rsp_valid&&!dut.g_rsp_ready;prev_ge=dut.g_rsp_error;prev_gs=dut.g_rsp_saturated;
      if(in_valid&&in_ready)begin if(!frame_open||job||ingress-i0>=17)$fatal(1,"FAIL_F16 ingress ownership");ingress=ingress+1;end
      if(dut.s_req&&dut.s_ready)begin
        if(pending)$fatal(1,"FAIL_F16 two ordinary S owners");pending=1;pending_addr=dut.s_addr;pending_write=dut.s_we;pending_data=dut.s_din;sreq=sreq+1;
        if(dut.s_we)begin writes=writes+1;
          if(dut.s_addr==448&&job)begin
            if(dut.s_din!==norm_word(v))$fatal(1,"FAIL_F16 complete S16 norm overwrite originalA");run_writes=run_writes+1;
          end else if((dut.s_addr>=448&&dut.s_addr<=463)||(dut.s_addr==475&&!job))begin
            if(job||dut.s_addr!==(frame_ingress_reqs<16?448+frame_ingress_reqs:475)||dut.s_din!==input_word(v,frame_ingress_reqs))$fatal(1,"FAIL_F16 input order/canonical/literal clobber");frame_ingress_reqs=frame_ingress_reqs+1;
          end else if(dut.s_addr>=464&&dut.s_addr<=475)begin
            if(!job||dut.s_din!==stage_word(v,dut.s_addr))$fatal(1,"FAIL_F16 stage%0d data=%032h expected=%032h",dut.s_addr,dut.s_din,stage_word(v,dut.s_addr));run_writes=run_writes+1;
          end else $fatal(1,"FAIL_F16 unexpected S write");
        end else begin reads=reads+1;run_reads=run_reads+1;if(!job||dut.s_addr<464||dut.s_addr>475)$fatal(1,"FAIL_F16 unexpected S read");end
      end
      if(dut.s_valid&&dut.s_take)begin
        if(!pending)$fatal(1,"FAIL_F16 S ACK without owner");
        if(pending_write&&dut.s_dout!==pending_data)$fatal(1,"FAIL_F16 write echo ACK");
        if(!pending_write&&dut.s_dout!==stage_word(v,pending_addr))$fatal(1,"FAIL_F16 S stage read mismatch");
        if(pending_write&&(pending_addr<464||pending_addr==475)&&!job)frame_ingress_acks=frame_ingress_acks+1;
        if(pending_write&&pending_addr==448&&job)norm_acks=norm_acks+1;
        if(pending_write&&pending_addr>=464)stage_acks[pending_addr-464]=stage_acks[pending_addr-464]+1;
        pending=0;sack=sack+1;
      end
      if(input_stored&&(ingress-i0!=17||frame_ingress_acks!=17||(!job&&pending)))$fatal(1,"FAIL_F16 marker before17 input/ACK");
      if(start_ready&&!input_stored)$fatal(1,"FAIL_F16 early ready");
      if(start_valid&&start_ready)begin if(job||!input_stored||frame_ingress_acks!=17)$fatal(1,"FAIL_F16 early/duplicate start");job=1;starts=starts+1;end
      if(dut.load_valid&&dut.load_ready)begin
        if(!job||loads-l0>2)$fatal(1,"FAIL_F16 loader lifecycle");
        if(dut.u_s.load_a_wide!==1'b1||dut.u_s.load_b_wide||dut.u_s.load_rows!=1||dut.u_s.load_tiles!=1)$fatal(1,"FAIL_F16 loader format");
        load_completed=0;loads=loads+1;
      end
      if(dut.load_done_valid&&dut.load_done_take)begin ldone=ldone+1;load_completed=!dut.load_done_error;end
      if(dut.a_valid&&dut.a_ready)begin
        if(dut.a_data!==(loads-l0==3?stage_word(v,468):norm_word(v)))$fatal(1,"FAIL_F16 loader A payload");abeats=abeats+1;
      end
      if(dut.b_valid&&dut.b_ready)bbeats=bbeats+1;
      if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
        if(!job)$fatal(1,"FAIL_F16 M before start");mcmd=mcmd+1;
        if(dut.m_cmd_op==10)begin if(!load_completed)$fatal(1,"FAIL_F16 EXEC before load done");projection_execs=projection_execs+1;end
      end
      if(dut.m_rsp_valid&&dut.m_rsp_ready)mrsp=mrsp+1;
      if(dut.n_req_valid&&dut.n_req_ready)nservice=nservice+1;
      if(dut.n_rsp_valid&&dut.n_rsp_ready)begin
        if(!dut.n_rsp_error&&stage_acks[10]!=1)$fatal(1,"FAIL_F16 N completion before474ACK");nservice_rsp=nservice_rsp+1;
      end
      if(dut.n_cmd_valid&&dut.n_cmd_ready)begin
        if(dut.owner!=3)$fatal(1,"FAIL_F16 N service lost S owner");
        if(dut.n_cmd_op==1||dut.n_cmd_op==5)begin
          if(dut.n_cmd_count!=8||dut.n_cmd_data!==stage_word(v,466))$fatal(1,"FAIL_F16 raw originalX replay");
          if(dut.n_cmd_op==5&&dut.n_cmd_aux!==stage_word(v,475))$fatal(1,"FAIL_F16 gamma");
        end
        ncommands=ncommands+1;
      end
      if(dut.n_native_rsp_valid&&dut.n_native_rsp_ready)nresponses=nresponses+1;
      if(dut.e_req_valid&&dut.e_req_ready)ecmd=ecmd+1;
      if(dut.e_rsp_valid&&dut.e_rsp_ready)begin
        if(!dut.e_rsp_error&&stage_acks[dut.e_final?9:3]!=1)$fatal(1,"FAIL_F16 E completion before destination ACK");ersp=ersp+1;
      end
      if(dut.g_req_valid&&dut.g_req_ready)gcmd=gcmd+1;
      if(dut.g_rsp_valid&&dut.g_rsp_ready)begin if(!dut.g_rsp_error&&stage_acks[4]!=1)$fatal(1,"FAIL_F16 G completion before destination ACK");grsp=grsp+1;end
      if(dut.e_in_valid&&dut.e_in_ready)enative=enative+1;
      if(dut.g_in_valid&&dut.g_in_ready)gnative=gnative+1;
      if(dut.g_out_valid&&dut.g_out_ready)gretired=gretired+1;
      if(dut.u_t.begin_valid&&dut.u_t.begin_ready)tbegin=tbegin+1;
      if(dut.u_t.write_valid&&dut.u_t.write_ready)begin if(dut.u_t.write_index!=0||dut.u_t.write_data!==stage_word(v,473))$fatal(1,"FAIL_F16 T data/index");twrite=twrite+1;end
      if(dut.u_t.commit_valid&&dut.u_t.commit_ready)tcommit=tcommit+1;
      if(out_valid&&out_ready)begin if(ttake-tt0!=0||out_index!=0||!out_last||out_data!==stage_word(v,473))$fatal(1,"FAIL_F16 final oracle");ttake=ttake+1;end
      if(dut.u_t.release_valid&&dut.u_t.release_ready)trelease=trelease+1;
    end
  end
  task automatic mark;
    input [8*100-1:0] name;
    begin cases=cases+1;$display("CASE_PASS %0s",name);end
  endtask
  task automatic new_frame;
    input integer nv;integer k;
    begin @(negedge clk);if(busy||done_valid||input_stored||out_valid||!in_ready||start_ready)$fatal(1,"FAIL_F16 nonempty frame");
      v=nv;crosscheck_frozen(v);frame_open=1;job=0;load_completed=0;projection_execs=0;frame_ingress_acks=0;frame_ingress_reqs=0;run_writes=0;run_reads=0;
      for(k=0;k<12;k=k+1)stage_acks[k]=0;norm_acks=0;ns0=nservice;nr0=nservice_rsp;nc0=ncommands;np0=nresponses;
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
    begin @(negedge clk);in_valid=1;in_data=raw_word(v,beat);while(!in_ready)@(negedge clk);@(posedge clk);#1;if(!busy)$fatal(1,"FAIL_F16 accepted ingress not busy");@(negedge clk);in_valid=0;end
  endtask
  task automatic fill;
    integer beat;
    begin for(beat=0;beat<17;beat=beat+1)send(beat);while(!input_stored)@(negedge clk);if(frame_ingress_acks!=17||!busy||in_ready)$fatal(1,"FAIL_F16 incomplete stored frame");end
  endtask
  task automatic start_job;
    input hold_start;
    begin @(negedge clk);if(!start_ready)$fatal(1,"FAIL_F16 not start ready");start_valid=1;@(posedge clk);#1;@(negedge clk);if(starts-st0!=1||!busy||start_ready)$fatal(1,"FAIL_F16 start acceptance");if(!hold_start)start_valid=0;end
  endtask
  task automatic take_output;
    integer j;
    begin while(!out_valid)@(negedge clk);for(j=0;j<7;j=j+1)begin if(out_data!==stage_word(v,473)||out_index!=0||!out_last)$fatal(1,"FAIL_F16 held output");@(negedge clk);end
      out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;
    end
  endtask
  task automatic finish;
    input error_expected,abort_at_done;integer j,before_take;
    begin while(!done_valid)@(negedge clk);
      for(j=0;j<5;j=j+1)begin
        if(!done_valid||done_error!==error_expected||in_ready||start_ready||!busy)$fatal(1,"FAIL_F16 retained completion");
        if(!error_expected&&done_saturated!==expected_sat(v))$fatal(1,"FAIL_F16 accumulated saturation");@(negedge clk);
      end
      if(!error_expected&&(ttake-tt0!=1||trelease-tr0!=1||dut.t_busy))$fatal(1,"FAIL_F16 completion before T release");
      before_take=dtake;start_valid=0;done_ready=1;abort=abort_at_done;
      @(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;frame_open=0;job=0;repeat(3)@(negedge clk);
      if(dtake!=before_take+1||busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_F16 duplicate or stale completion");
    end
  endtask
  task automatic normal_counts;
    integer k;
    begin
      if(ingress-i0!=17||frame_ingress_acks!=17||sreq-q0!=39||sack-a0!=39||writes-w0!=29||reads-r0!=10||run_writes!=12||run_reads!=10||pending)$fatal(1,"FAIL_F16 39 S/29write/10read counts");
      if(mcmd-mc0!=15||mrsp-mr0!=15||projection_execs!=3||loads-l0!=3||ldone-ld0!=3||abeats-ab0!=3||bbeats-bb0!=3)$fatal(1,"FAIL_F16 projection counts");
      if(ecmd-e0!=2||ersp-er0!=2||gcmd-g0!=1||grsp-gr0!=1||enative-en0!=2||gnative-gn0!=4||gretired-go0!=4)$fatal(1,"FAIL_F16 native/adapter counts");
      if(tbegin-tb0!=1||twrite-tw0!=1||tcommit-tc0!=1||ttake-tt0!=1||trelease-tr0!=1||starts-st0!=1)$fatal(1,"FAIL_F16 T counts");
      if(nservice-ns0!=1||nservice_rsp-nr0!=1||ncommands-nc0!=4||nresponses-np0!=4||norm_acks!=1||ram_word(448)!==norm_word(v))$fatal(1,"FAIL_F16 N/narrow counts");
      for(k=0;k<12;k=k+1)if(stage_acks[k]!=1||ram_word(464+k)!==stage_word(v,464+k))$fatal(1,"FAIL_F16 final intermediate RAM%0d",464+k);
    end
  endtask
  task automatic run_normal;
    input integer nv;
    begin new_frame(nv);fill();start_job(0);take_output();finish(0,0);normal_counts();end
  endtask
  task automatic prestart_abort;
    begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;in_valid=0;start_valid=0;frame_open=0;job=0;repeat(3)@(negedge clk);
      if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_F16 prestart abort fabricated done");
    end
  endtask
  task automatic hard_reset;
    begin @(negedge clk);reset=1;in_valid=0;start_valid=0;out_ready=0;done_ready=0;repeat(3)@(negedge clk);reset=0;frame_open=0;job=0;repeat(3)@(negedge clk);
      if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_F16 hard reset stale lifecycle");end
  endtask
  integer beat,k;
  initial begin
    repeat(4)@(negedge clk);reset=0;@(negedge clk);
    new_frame(0);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);
    start_valid=1;repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0||mcmd!=mc0)$fatal(1,"FAIL_F16 early pending ACK start");end
    start_valid=0;release dut.permit_s_rsp;for(beat=1;beat<16;beat=beat+1)send(beat);
    while(frame_ingress_acks<16)@(negedge clk);force dut.permit_s_rsp=1'b0;send(16);while(!dut.s_valid)@(negedge clk);
    start_valid=1;repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0)$fatal(1,"FAIL_F16 last input accept before ACK");end
    start_valid=0;release dut.permit_s_rsp;while(!input_stored)@(negedge clk);repeat(3)@(negedge clk);
    if(starts!=st0)$fatal(1,"FAIL_F16 early start pulse queued");
    for(beat=0;beat<17;beat=beat+1)if(ram_word(beat<16?448+beat:475)!==input_word(v,beat))$fatal(1,"FAIL_F16 canonical ingress RAM");
    mark("F16_INPUT17_STORED_AND_PADDING_ACK_GATE");
    start_job(1);take_output();finish(0,0);normal_counts();mark("F16_H8I8_NORMAL_STAGES_COUNTS_HELD_START");
    run_normal(1);mark("F16_ZERO_X_VARIABLE_GAMMA");run_normal(2);mark("F16_POSITIVE_EXTREME_SATURATION");
    run_normal(3);mark("F16_NEGATIVE_EXTREME_SATURATION");run_normal(4);mark("F16_SIGNED_NONUNITY_GAMMA");run_normal(5);mark("F16_ZERO_GAMMA_PRESERVES_FULL_S16_X");
    run_normal(6);mark("F16_SPARSE_LAYOUT");run_normal(7);mark("F16_SEEDED_RANDOM_0");
    run_normal(8);mark("F16_SEEDED_RANDOM_1");run_normal(9);mark("F16_ZERO_GAMMA_NON8_RESIDUAL");
    new_frame(4);for(beat=0;beat<16;beat=beat+1)send(beat);while(frame_ingress_acks<16)@(negedge clk);
    force dut.permit_s_rsp=1'b0;send(16);start_valid=1;repeat(4)@(negedge clk);
    if(starts!=st0||input_stored)$fatal(1,"FAIL_F16 held start early");release dut.permit_s_rsp;while(starts==st0)@(negedge clk);start_valid=0;
    take_output();finish(0,0);normal_counts();mark("F16_HELD_START_AFTER_FINAL_ACK_REPEAT");
    new_frame(0);force dut.permit_s_req=1'b0;send(0);repeat(4)@(negedge clk);prestart_abort();release dut.permit_s_req;run_normal(4);mark("F16_ABORT_CAPTURED_BEFORE_S_ACCEPT_RECOVER");
    new_frame(3);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);prestart_abort();release dut.permit_s_rsp;run_normal(0);mark("F16_ABORT_INPUT_PENDING_ACK_RECOVER");
    new_frame(2);fill();prestart_abort();run_normal(5);mark("F16_ABORT_COMPLETE_PRESTART_RECOVER");
    new_frame(4);fill();force dut.permit_s_rsp=1'b0;start_job(0);while(!dut.s_valid)@(negedge clk);
    @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;finish(1,0);run_normal(1);mark("F16_ABORT_RUN_S_ACK_RECOVER");
    new_frame(2);fill();start_job(0);take_output();abort=1;@(posedge clk);#1;@(negedge clk);abort=0;
    if(ttake-tt0!=1)$fatal(1,"FAIL_F16 consumed output retracted");finish(1,0);run_normal(4);mark("F16_ABORT_AFTER_CONSUMED_PREFIX_RECOVER");
    new_frame(2);fill();start_job(0);take_output();while(!done_valid)@(negedge clk);
    @(negedge clk);abort=1;repeat(3)begin @(negedge clk);if(!done_valid||done_error||!done_saturated)$fatal(1,"FAIL_F16 existing DONE flags changed");end
    abort=0;finish(0,1);normal_counts();mark("F16_DONE_ABORT_READY_EXACTLY_ONCE_SAT_HOLD");
    new_frame(4);send(0);send(1);hard_reset();run_normal(3);mark("F16_RESET_PARTIAL_INPUT_RECOVER");
    new_frame(4);fill();force dut.permit_g_rsp=1'b0;start_job(0);while(!dut.g_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();release dut.permit_g_rsp;run_normal(0);mark("F16_RESET_RETAINED_G_RESPONSE_RECOVER");
    new_frame(4);fill();start_job(0);while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();run_normal(5);mark("F16_RESET_COMMITTED_T_STALL_RECOVER");
    new_frame(4);fill();start_job(0);wait(dut.state==5&&dut.m_phase==2);
    @(negedge clk);force dut.m_cmd_data=64'h988c;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;
    finish(1,0);if(ttake!=tt0)$fatal(1,"FAIL_F16 error published output");run_normal(3);mark("F16_NATIVE_EXEC_ERROR_RECOVER");
    // Actual newly integrated native E error, not a fabricated adapter flag.
    new_frame(4);fill();start_job(0);wait(dut.e_in_valid&&dut.e_in_ready);
    @(negedge clk);force dut.e_in_op=4'd14;@(posedge clk);#1;@(negedge clk);release dut.e_in_op;
    finish(1,0);if(ttake!=tt0||twrite!=tw0||stage_acks[3]!=0)$fatal(1,"FAIL_F16 native E error wrote residual/output");
    run_normal(5);mark("F16_NATIVE_E_ERROR_NO_WRITE_RECOVER");
    // One invalid G beat among valid beats must error the whole service only
    // after every accepted pair is retired; no partial mid/T publication.
    new_frame(4);fill();start_job(0);wait(dut.g_in_valid&&dut.g_in_ready);
    @(negedge clk);force dut.g_in_fn=3'd4;@(posedge clk);#1;@(negedge clk);release dut.g_in_fn;
    finish(1,0);if(gnative-gn0!=4||gretired-go0!=4||stage_acks[4]!=0||ttake!=tt0||twrite!=tw0)$fatal(1,"FAIL_F16 native G error did not drain or wrote mid/output");
    run_normal(3);mark("F16_ONE_NATIVE_G_BEAT_ERROR_DRAIN_NO_WRITE_RECOVER");
    // E/G response stalls are real held service outputs after destination ACK.
    new_frame(4);fill();force dut.permit_e_rsp=1'b0;start_job(0);while(!dut.e_rsp_valid)@(negedge clk);repeat(6)@(negedge clk);release dut.permit_e_rsp;
    force dut.permit_g_rsp=1'b0;while(!dut.g_rsp_valid)@(negedge clk);repeat(6)@(negedge clk);release dut.permit_g_rsp;
    take_output();finish(0,0);normal_counts();mark("F16_E_G_RESPONSE_HOLD_AFTER_REAL_WRITE_ACK");
    new_frame(4);fill();force dut.permit_n_rsp=1'b0;start_job(0);while(!dut.n_rsp_valid)@(negedge clk);repeat(6)@(negedge clk);
    if(stage_acks[10]!=1||norm_acks!=0||mcmd!=mc0)$fatal(1,"FAIL_F16 N completed but top consumed early");release dut.permit_n_rsp;
    take_output();finish(0,0);normal_counts();mark("F16_N_SERVICE_RESPONSE_HOLD_AFTER474ACK");
    new_frame(4);fill();start_job(0);wait(dut.n_cmd_valid&&dut.n_cmd_ready&&dut.n_cmd_op==1);
    @(negedge clk);force dut.n_cmd_op=4'd15;@(posedge clk);#1;@(negedge clk);release dut.n_cmd_op;
    finish(1,0);if(stage_acks[10]!=0||norm_acks!=0||mcmd!=mc0||twrite!=tw0)$fatal(1,"FAIL_F16 native N error escaped preNorm");
    run_normal(5);mark("F16_NATIVE_N_ERROR_NO_PROJECTION_COORDINATED_RECOVER");
    new_frame(4);fill();force dut.permit_n_rsp=1'b0;start_job(0);while(!dut.n_rsp_valid)@(negedge clk);repeat(4)@(negedge clk);hard_reset();release dut.permit_n_rsp;
    run_normal(0);mark("F16_RESET_HELD_N_SERVICE_RESPONSE_RECOVER");
    new_frame(4);fill();start_job(0);wait(dut.n_mem_req_valid&&dut.n_mem_req_write&&dut.n_mem_req_addr==474);
    force dut.permit_s_rsp=1'b0;while(!dut.s_valid)@(negedge clk);repeat(4)@(negedge clk);
    if(stage_acks[10]!=0||norm_acks!=0||mcmd!=mc0)$fatal(1,"FAIL_F16 N finalwrite missingACK early projection");
    @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;
    finish(1,0);run_normal(1);mark("F16_ABORT_N_DESTINATION_ACK_COORDINATED_RECOVER");
    // Helper has no native S error output. Inject its defined service-error
    // boundary, after a real accepted write, to check partial/no-output recovery.
    new_frame(4);fill();start_job(0);wait(dut.h_rsp_valid&&dut.h_rsp_ready&&dut.owner==0);
    @(negedge clk);force dut.h_rsp_error=1'b1;@(posedge clk);#1;@(negedge clk);release dut.h_rsp_error;
    finish(1,0);if(twrite!=tw0||ttake!=tt0)$fatal(1,"FAIL_F16 S helper response error published output");
    run_normal(9);mark("F16_S_SERVICE_ERROR_NO_OUTPUT_RECOVER");
    $display("F16_STATS cycles=%0d input=%0d Sreq=%0d Sack=%0d Mcmd=%0d Mrsp=%0d Ncmd=%0d Nrsp=%0d Ttake=%0d",cycles,ingress,sreq,sack,mcmd,mrsp,ncommands,nresponses,ttake);
    $display("PASS_W4_F16 cases=%0d",cases);$finish;
  end
'''


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=ap.parse_args()
    d=json.loads((a.directory/'f16-contract-vectors.json').read_text(encoding='utf-8'))
    functions=[]
    for name,args,items,key in [
      ('input_word','input integer vector_no,beat;',[(v['index']*17+i,w) for v in d['vectors'] for i,w in enumerate(v['expected']['ingress_words_hex'])],'vector_no*17+beat'),
      ('stage_word','input integer vector_no,address;',[(v['index']*1024+int(addr),w) for v in d['vectors'] for addr,w in v['expected']['S_words_hex'].items()],'vector_no*1024+address')]:
        functions += ['  function automatic [127:0] '+name+';', '    '+args, '    begin case('+key+')']
        functions += ['      {}:{}=128\'h{};'.format(k,name,w) for k,w in items]
        functions += ['      default:'+name+'=128\'hbad;','    endcase end','  endfunction']
    functions += ['  function automatic [127:0] norm_word;input integer vector_no;begin case(vector_no)']
    functions += ['    {}:norm_word=128\'h{};'.format(v['index'],v['expected']['normalized_input_word_hex']) for v in d['vectors']]
    functions += ['    default:norm_word=0;endcase end endfunction']
    functions += ['  function automatic expected_sat;input integer vector_no;begin case(vector_no)']
    functions += ['    {}:expected_sat=1\'b{};'.format(v['index'],int(v['expected']['done_saturated'])) for v in d['vectors']]
    functions += ['    default:expected_sat=1\'bx;endcase end endfunction']
    source='`timescale 1ns/1ps\n// Frozen expectations from independent math oracle, not DUT values.\nmodule block_w4_f16_tb;\n'+'\n'.join(functions)+'\n'+BODY+'\nendmodule\n'
    (a.directory/'block_w4_f16_tb.sv').write_bytes(source.encode('utf-8'))
    contract={'schema_version':1,'status':'FROZEN_EXPECTATIONS_NOT_RTL_EXECUTION','top_module':'block_w4_f16_tb','tb_path':'project/tb/block_connection_w4/block_w4_f16_tb.sv','pass_marker':'PASS_W4_F16','pass_line_regex':'^PASS_W4_F16 cases='+str(len(CASE_IDS))+'$','expected_case_ids':CASE_IDS,'expected_unique_case_count':len(CASE_IDS),'compile_sources':['project/rtl/block_v2/block_v2_e.sv','project/rtl/block_v2/block_v2_g.sv','project/rtl/block_v2/block_v2_m.sv','project/rtl/block_v2/block_v2_n.sv','project/rtl/block_v2/block_v2_n_group.sv','project/rtl/block_feed_v1/block_feed_loader.sv','project/rtl/block_feed_v1/block_feed_s16k.sv','project/rtl/block_feed_v1/block_feed_s_macro.sv','project/rtl/block_v1/transaction6k.sv','project/rtl/block_connection_p2/block_p2_s_ctrl.sv','project/rtl/block_connection_w3/block_w3_e_ctrl.sv','project/rtl/block_connection_w3/block_w3_g_ctrl.sv','project/rtl/block_connection_w4/block_w4_n_ctrl.sv','project/rtl/block_connection_w4/block_w4_f16_top.sv','project/tb/block_connection_w4/block_w4_f16_tb.sv'],'include_dirs':['project/rtl/block_v2','work/Melodydt/151'],'TB_includes':[],'vectors_path':'work/Melodydt/151/f16-contract-vectors.json','reference_path':'work/Melodydt/151/f16_integer_reference.py','tb_sha256':hashlib.sha256((a.directory/'block_w4_f16_tb.sv').read_bytes()).hexdigest(),'normal_counts':{'S':39,'S_write':29,'S_read':10,'M':15,'loader':3,'N':4,'E':2,'G':4,'T':1},'scope':'F16 explicitH8I8 integer profile,not fullmodel quality,not L5 orphysical','execution_policy':'serverVerilator only;root performs simulation;thisgenerator does not'}
    (a.directory/'f16-tb-contract.json').write_bytes((json.dumps(contract,indent=2)+'\n').encode('utf-8'))
    print('Prepared self-contained F16 TB10vectors/30case contract; noRTLrun')


if __name__=='__main__':main()
