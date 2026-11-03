"""Self-contained A8 SV TB and independently declared bounded CASE contract.

No simulator is invoked. RTL runs are server Verilator only.
"""
import argparse
import hashlib
import json
from pathlib import Path

CASE_IDS=[
 'A8_INPUT12_STORED_PADDING_ACK_GATE',
 'A8_NONCONSTANT_STAGES_COUNTS_HELD_START',
 'A8_EQUAL_SCORES_UNIFORM_PROB',
 'A8_ZERO_QUERY_NONZERO_VALUES',
 'A8_LAST_KEY_NEWMAX_EXTREME',
 'A8_ALTERNATING_SIGNED_EXTREME',
 'A8_SPARSE_IDENTITY_LAYOUT',
 'A8_NEGATIVE_QUERY_MIXED_KEYS',
 'A8_CONSTANT_VALUE_CHANNELS',
 'A8_HELD_START_AFTER_LAST_ACK_REPEAT',
 'A8_M_CMD_RSP_LOADER_N_COMPLETION_BACKPRESSURE',
 'A8_ABORT_CAPTURED_BEFORE_S_ACCEPT_RECOVER',
 'A8_ABORT_INPUT_PENDING_ACK_RECOVER',
 'A8_ABORT_COMPLETE_PRESTART_RECOVER',
 'A8_ABORT_RUN_SCORE_ACK_RECOVER',
 'A8_ABORT_AFTER_CONSUMED_PREFIX_RECOVER',
 'A8_DONE_ABORT_READY_EXACTLY_ONCE',
 'A8_RESET_PARTIAL_INPUT_RECOVER',
 'A8_RESET_HELD_N_SERVICE_RECOVER',
 'A8_RESET_COMMITTED_T_STALL_RECOVER',
 'A8_NATIVE_N_ERROR_NO_PV_COORDINATED_RECOVER',
 'A8_NATIVE_QK_EXEC_ERROR_RECOVER',
 'A8_NATIVE_PV_EXEC_ERROR_RECOVER',
 'A8_ABORT_EXP_WRITE_ACK_COORDINATED_RECOVER',
 'A8_RESET_HELD_M_RESPONSE_RECOVER',
 'A8_PROBABILITY_DESTINATION_ACK_GATES_PV'
]

BODY=r'''
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
 reg [127:0] in_data=0;
 wire in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,out_valid,out_last;
 wire [127:0] out_data;wire [9:0] out_index;
 block_w4_a8_top dut(.*);
 integer cycles=0,cases=0,v=0,ingress=0,sreq=0,sack=0,writes=0,reads=0;
 integer mcmd=0,mrsp=0,loads=0,ldone=0,abeats=0,bbeats=0,ncmd=0,nrsp=0,nservice=0,nservice_rsp=0;
 integer tbegin=0,twrite=0,tcommit=0,ttake=0,trelease=0,starts=0,dtake=0;
 integer i0,q0,a0,w0,r0,mc0,mr0,l0,ld0,ab0,bb0,nc0,nr0,ns0,nsr0,tb0,tw0,tc0,tt0,tr0,st0;
 integer stage_acks[0:6],input_acks=0,input_reqs=0,run_writes=0,run_reads=0;
 reg frame_open=0,job=0,pending=0,pending_write,strict_native=1,load_completed=0;
 reg [9:0] pending_addr;reg [127:0] pending_data;
 reg hold_out=0,hold_done=0,hold_s=0,hold_m=0,hold_n=0,hold_in=0;
 reg [127:0] old_out,old_s,old_m,old_in;reg [9:0] old_index;reg old_last,old_de,old_ds,old_ne,old_ns;
 integer projection_execs=0;
 function automatic integer stage_index;input integer address;
  begin case(address)460:stage_index=0;461:stage_index=1;464:stage_index=2;465:stage_index=3;466:stage_index=4;467:stage_index=5;468:stage_index=6;default:stage_index=-1;endcase end
 endfunction
 function automatic [127:0] ram;input integer address;
  begin case(address%4)0:ram=dut.u_s.storage.bank0[address/4];1:ram=dut.u_s.storage.bank1[address/4];2:ram=dut.u_s.storage.bank2[address/4];3:ram=dut.u_s.storage.bank3[address/4];endcase end
 endfunction
 function automatic [127:0] dirty_input;input integer vec,beat;reg [127:0] data;
  begin data=a8_input_word(vec,beat);if(beat==0)data[127:64]=64'hbadc0ffee55aacc1;else if(beat<4)data=128'hfedcba98765432100123456789abcdef;dirty_input=data;end
 endfunction
 function automatic signed [7:0] byte_at;input integer vec,base,offset;reg [127:0] data;
  begin data=a8_input_word(vec,base+offset/16);byte_at=data[8*(offset%16)+:8];end
 endfunction
 function automatic signed [15:0] lane;input integer vec,address,index;reg [127:0] data;
  begin data=a8_stage_word(vec,address);lane=$signed(data[16*index+:16]);end
 endfunction
 function automatic signed [63:0] round_even;input signed [63:0] value;input integer shift;reg signed [63:0] q;reg [63:0] r,h;
  begin q=value>>>shift;r=$unsigned(value)&((64'd1<<shift)-1);h=64'd1<<(shift-1);round_even=q+((r>h)||((r==h)&&q[0]));end
 endfunction
 task automatic crosscheck;input integer vec;integer t,d,c;reg signed [63:0] raw;
  begin for(t=0;t<8;t=t+1)begin raw=0;for(d=0;d<8;d=d+1)raw=raw+byte_at(vec,0,d)*byte_at(vec,4,8*t+d);
   if(round_even(raw*64'sd11585,19)!=={{48{lane(vec,460,t)[15]}},lane(vec,460,t)})$fatal(1,"FAIL_A8 independent QK formula");
  end
  for(c=0;c<8;c=c+1)begin raw=0;for(t=0;t<8;t=t+1)raw=raw+lane(vec,464,t)*byte_at(vec,8,8*c+t);
   if(round_even(raw,11)!==$signed(lane(vec,468,c)))$fatal(1,"FAIL_A8 independent PV/layout formula");
  end end
 endtask
 function automatic integer native_n_op;input integer index;
  begin case(index)0:native_n_op=0;1:native_n_op=1;2:native_n_op=2;3:native_n_op=3;4:native_n_op=4;5:native_n_op=6;default:native_n_op=-1;endcase end
 endfunction
 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>400000)$fatal(1,"FAIL_A8 watchdog");
  // Public DONE survives abort/internal leaf reset; only hard reset cancels it.
  if(reset)hold_done=0;else begin
   if(hold_done&&(!done_valid||done_error!==old_de||done_saturated!==old_ds))$fatal(1,"FAIL_A8 held DONE changed");
   hold_done=done_valid&&!done_ready;old_de=done_error;old_ds=done_saturated;
   if(done_valid&&done_ready)dtake=dtake+1;
  end
  if(reset||dut.leaf_reset)begin hold_out=0;hold_s=0;hold_m=0;hold_n=0;hold_in=0;pending=0;end
  else begin
   if(hold_in&&(!in_valid||in_data!==old_in))$fatal(1,"FAIL_A8 TB ingress unstable");
   if(hold_out&&(!out_valid||out_data!==old_out||out_index!==old_index||out_last!==old_last))$fatal(1,"FAIL_A8 output hold");
   if(hold_s&&(!dut.s_valid||dut.s_dout!==old_s))$fatal(1,"FAIL_A8 S ACK hold");
   if(hold_m&&(!dut.m_rsp_valid||dut.m_rsp_data!==old_m))$fatal(1,"FAIL_A8 M response hold");
   if(hold_n&&(!dut.n_rsp_valid||dut.n_rsp_error!==old_ne||dut.n_rsp_saturated!==old_ns))$fatal(1,"FAIL_A8 N service hold");
   hold_in=in_valid&&!in_ready;old_in=in_data;hold_out=out_valid&&!out_ready;old_out=out_data;old_index=out_index;old_last=out_last;
   hold_s=dut.s_valid&&!dut.s_take;old_s=dut.s_dout;hold_m=dut.m_rsp_valid&&!dut.m_rsp_ready;old_m=dut.m_rsp_data;
   hold_n=dut.n_rsp_valid&&!dut.n_rsp_ready;old_ne=dut.n_rsp_error;old_ns=dut.n_rsp_saturated;
   if(in_valid&&in_ready)begin if(!frame_open||job||ingress-i0>=12)$fatal(1,"FAIL_A8 ingress ownership");ingress=ingress+1;end
   if(dut.s_req&&dut.s_ready)begin
    if(pending)$fatal(1,"FAIL_A8 multiple ordinary S owners");pending=1;pending_write=dut.s_we;pending_addr=dut.s_addr;pending_data=dut.s_din;sreq=sreq+1;
    if(dut.s_we)begin writes=writes+1;
     if(dut.s_addr>=448&&dut.s_addr<=459)begin
      if(job||dut.s_addr!=448+input_reqs||dut.s_din!==a8_input_word(v,dut.s_addr-448))$fatal(1,"FAIL_A8 ingress canonicalization/order");input_reqs=input_reqs+1;
     end else if(stage_index(dut.s_addr)>=0)begin
      if(!job||dut.s_din!==a8_stage_word(v,dut.s_addr))$fatal(1,"FAIL_A8 math S write addr%0d got%032h expected%032h",dut.s_addr,dut.s_din,a8_stage_word(v,dut.s_addr));run_writes=run_writes+1;
     end else $fatal(1,"FAIL_A8 forbidden S write/unused462..463");
    end else begin
     reads=reads+1;run_reads=run_reads+1;
     if(!job||!(dut.s_addr==460||dut.s_addr==461||dut.s_addr==468))$fatal(1,"FAIL_A8 forbidden S read");
    end
   end
   if(dut.s_valid&&dut.s_take)begin
    if(!pending)$fatal(1,"FAIL_A8 ACK without ownership");
    if(pending_write&&dut.s_dout!==pending_data)$fatal(1,"FAIL_A8 ACK echo");
    if(!pending_write&&dut.s_dout!==a8_stage_word(v,pending_addr))$fatal(1,"FAIL_A8 stage read lineage");
    if(pending_write&&pending_addr<460)input_acks=input_acks+1;
    if(pending_write&&stage_index(pending_addr)>=0)stage_acks[stage_index(pending_addr)]=stage_acks[stage_index(pending_addr)]+1;
    pending=0;sack=sack+1;
   end
   if(input_stored&&(ingress-i0!=12||input_acks!=12||(!job&&pending)))$fatal(1,"FAIL_A8 stored before12ACK");
   if(start_ready&&!input_stored)$fatal(1,"FAIL_A8 early start ready");
   if(start_valid&&start_ready)begin if(job||input_acks!=12||!input_stored)$fatal(1,"FAIL_A8 duplicate/early start");job=1;starts=starts+1;end
   if(dut.load_valid&&dut.load_ready)begin
    if(!job||loads-l0>1||pending||dut.u_s.load_a_wide!==(loads-l0==1)||dut.u_s.load_b_wide||dut.u_s.load_rows!=1||dut.u_s.load_tiles!=1)$fatal(1,"FAIL_A8 loader geometry/ownership");
    if(loads-l0==1&&(stage_acks[2]!=1||stage_acks[3]!=1||stage_acks[4]!=1||stage_acks[5]!=1))$fatal(1,"FAIL_A8 PV before prob/padding ACK");
    loads=loads+1;load_completed=0;
   end
   if(dut.load_done_valid&&dut.load_done_take)begin ldone=ldone+1;load_completed=!dut.load_done_error;end
   if(dut.a_valid&&dut.a_ready)begin if(dut.a_data!==(loads-l0==1?a8_input_word(v,0):a8_stage_word(v,464)))$fatal(1,"FAIL_A8 A payload/narrow-v-wide format");abeats=abeats+1;end
   if(dut.b_valid&&dut.b_ready)begin
    if(dut.b_data!=={a8_input_word(v,loads-l0==1?7:11),a8_input_word(v,loads-l0==1?6:10),a8_input_word(v,loads-l0==1?5:9),a8_input_word(v,loads-l0==1?4:8)})$fatal(1,"FAIL_A8 full512 B K/V layout");bbeats=bbeats+1;
   end
   if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
    if(!job)$fatal(1,"FAIL_A8 M beforeRUN");
    if(strict_native)case(dut.m_phase)
     0:if(dut.m_cmd_op!=6||dut.m_cmd_data!=0)$fatal(1,"FAIL_A8 CLEAR is opcode6");
     1:if(dut.m_cmd_op!=4||dut.m_cmd_data!=(dut.projection==0?11585:1))$fatal(1,"FAIL_A8 factor signedS16/left0");
     2:if(dut.m_cmd_op!=10||dut.m_cmd_index!=0||dut.m_cmd_data!=(dut.projection==0?64'h9884:64'h9885))$fatal(1,"FAIL_A8 EXEC layout");
     3,4:if(dut.m_cmd_op!=5||dut.m_cmd_index!=(dut.m_phase==4)||dut.m_cmd_data!=(dut.projection==0?64'h113:64'h10b))$fatal(1,"FAIL_A8 quantization/read half");
    endcase
    if(dut.m_cmd_op==10)begin if(!load_completed)$fatal(1,"FAIL_A8 EXEC before load complete");projection_execs=projection_execs+1;end
    mcmd=mcmd+1;
   end
   if(dut.m_rsp_valid&&dut.m_rsp_ready)begin
    if(!dut.m_rsp_error&&(dut.m_phase==3||dut.m_phase==4)&&dut.m_rsp_data!==(dut.projection==0?a8_qk_carrier(v,dut.m_phase==4):a8_pv_carrier(v,dut.m_phase==4)))$fatal(1,"FAIL_A8 M fourS32 carriers");mrsp=mrsp+1;
   end
   if(dut.n_req_valid&&dut.n_req_ready)begin if(stage_acks[0]!=1||dut.owner!=3)$fatal(1,"FAIL_A8 N before scoreACK/owner");nservice=nservice+1;end
   if(dut.n_rsp_valid&&dut.n_rsp_ready)begin if(!dut.n_rsp_error&&(stage_acks[1]!=1||stage_acks[2]!=1))$fatal(1,"FAIL_A8 N completion before EXP/probACK");nservice_rsp=nservice_rsp+1;end
   if(dut.n_cmd_valid&&dut.n_cmd_ready)begin
    if(strict_native)begin
     if(dut.n_cmd_op!=native_n_op(ncmd-nc0))$fatal(1,"FAIL_A8 N phase order");
     if(dut.n_cmd_op==1||dut.n_cmd_op==3||dut.n_cmd_op==6)begin
      if(dut.n_cmd_count!=8||dut.n_cmd_data!==(dut.n_cmd_op==6?a8_stage_word(v,461):a8_stage_word(v,460)))$fatal(1,"FAIL_A8 N raw/EXP lineage and count");
     end
    end
    ncmd=ncmd+1;
   end
   if(dut.n_native_rsp_valid&&dut.n_native_rsp_ready)nrsp=nrsp+1;
   if(dut.u_t.begin_valid&&dut.u_t.begin_ready)tbegin=tbegin+1;
   if(dut.u_t.write_valid&&dut.u_t.write_ready)begin if(dut.u_t.write_index!=0||dut.u_t.write_data!==a8_stage_word(v,468))$fatal(1,"FAIL_A8 T word");twrite=twrite+1;end
   if(dut.u_t.commit_valid&&dut.u_t.commit_ready)tcommit=tcommit+1;
   if(out_valid&&out_ready)begin if(ttake-tt0!=0||out_index!=0||!out_last||out_data!==a8_stage_word(v,468))$fatal(1,"FAIL_A8 final math");ttake=ttake+1;end
   if(dut.u_t.release_valid&&dut.u_t.release_ready)trelease=trelease+1;
  end
 end
 task automatic mark;input integer which;begin cases=cases+1;$display("CASE_PASS %0s",case_name(which));end endtask
 task automatic new_frame;input integer vec;integer k;
  begin @(negedge clk);if(busy||done_valid||input_stored||out_valid||!in_ready||start_ready)$fatal(1,"FAIL_A8 stale lifecycle");
   v=vec;crosscheck(v);frame_open=1;job=0;strict_native=1;input_acks=0;input_reqs=0;run_writes=0;run_reads=0;load_completed=0;projection_execs=0;
   for(k=0;k<7;k=k+1)stage_acks[k]=0;
   i0=ingress;q0=sreq;a0=sack;w0=writes;r0=reads;mc0=mcmd;mr0=mrsp;l0=loads;ld0=ldone;ab0=abeats;bb0=bbeats;nc0=ncmd;nr0=nrsp;ns0=nservice;nsr0=nservice_rsp;tb0=tbegin;tw0=twrite;tc0=tcommit;tt0=ttake;tr0=trelease;st0=starts;
   in_valid=0;start_valid=0;out_ready=0;done_ready=0;
   dut.u_s.storage.bank0[112]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank1[112]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank2[112]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank3[112]=128'hffffffffffffffffffffffffffffffff;
   dut.u_s.storage.bank1[116]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank2[116]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank3[116]=128'hffffffffffffffffffffffffffffffff;
  end
 endtask
 task automatic send;input integer beat;
  begin @(negedge clk);in_valid=1;in_data=dirty_input(v,beat);while(!in_ready)@(negedge clk);@(posedge clk);#1;if(!busy)$fatal(1,"FAIL_A8 accepted data notbusy");@(negedge clk);in_valid=0;end
 endtask
 task automatic fill;integer k;
  begin for(k=0;k<12;k=k+1)send(k);while(!input_stored)@(negedge clk);if(input_acks!=12||!busy||in_ready)$fatal(1,"FAIL_A8 frame notstored");end
 endtask
 task automatic start_job;input hold_start;
  begin @(negedge clk);if(!start_ready)$fatal(1,"FAIL_A8 notstartready");start_valid=1;@(posedge clk);#1;@(negedge clk);if(starts-st0!=1||!busy||start_ready)$fatal(1,"FAIL_A8 start");if(!hold_start)start_valid=0;end
 endtask
 task automatic take_output;integer k;
  begin while(!out_valid)@(negedge clk);repeat(7)begin if(out_data!==a8_stage_word(v,468)||out_index!=0||!out_last)$fatal(1,"FAIL_A8 held output data");@(negedge clk);end
   out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;
  end
 endtask
 task automatic finish;input error_expected,abort_at_done;integer before_take;
  begin while(!done_valid)@(negedge clk);repeat(5)begin if(!done_valid||done_error!==error_expected||in_ready||start_ready||!busy||done_saturated!==a8_expected_saturated(v))$fatal(1,"FAIL_A8 completion hold/status");@(negedge clk);end
   if(!error_expected&&(ttake-tt0!=1||trelease-tr0!=1||dut.t_busy))$fatal(1,"FAIL_A8 done before RELEASE");
   before_take=dtake;start_valid=0;done_ready=1;abort=abort_at_done;@(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;frame_open=0;job=0;repeat(3)@(negedge clk);
   if(dtake!=before_take+1||busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_A8 done duplicate/stale");
  end
 endtask
 task automatic normal_counts;integer k;
  begin if(ingress-i0!=12||input_acks!=12||sreq-q0!=23||sack-a0!=23||writes-w0!=19||reads-r0!=4||run_writes!=7||run_reads!=4||pending)$fatal(1,"FAIL_A8 23S/19W4R");
   if(mcmd-mc0!=10||mrsp-mr0!=10||projection_execs!=2||loads-l0!=2||ldone-ld0!=2||abeats-ab0!=2||bbeats-bb0!=2)$fatal(1,"FAIL_A8 M10/load2");
   if(nservice-ns0!=1||nservice_rsp-nsr0!=1||ncmd-nc0!=6||nrsp-nr0!=6)$fatal(1,"FAIL_A8 N service/native6");
   if(tbegin-tb0!=1||twrite-tw0!=1||tcommit-tc0!=1||ttake-tt0!=1||trelease-tr0!=1||starts-st0!=1)$fatal(1,"FAIL_A8 T lifecycle");
   for(k=0;k<7;k=k+1)if(stage_acks[k]!=1)$fatal(1,"FAIL_A8 stageACK count");
   if(ram(460)!==a8_stage_word(v,460)||ram(461)!==a8_stage_word(v,461)||ram(464)!==a8_stage_word(v,464)||ram(465)!=0||ram(466)!=0||ram(467)!=0||ram(468)!==a8_stage_word(v,468))$fatal(1,"FAIL_A8 finalRAM");
  end
 endtask
 task automatic run_normal;input integer vec;begin new_frame(vec);fill();start_job(0);take_output();finish(0,0);normal_counts();end endtask
 task automatic prestart_abort;
  begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;in_valid=0;start_valid=0;frame_open=0;job=0;repeat(3)@(negedge clk);
   if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_A8 prestartabort fabricated DONE");
  end
 endtask
 task automatic hard_reset;
  begin @(negedge clk);reset=1;in_valid=0;start_valid=0;out_ready=0;done_ready=0;repeat(3)@(negedge clk);reset=0;frame_open=0;job=0;repeat(3)@(negedge clk);
   if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_A8 reset lifecycle");
  end
 endtask
 integer k;
 initial begin
  repeat(4)@(negedge clk);reset=0;@(negedge clk);
  new_frame(0);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);start_valid=1;
  repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0||mcmd!=mc0)$fatal(1,"FAIL_A8 pendingACK start");end
  start_valid=0;release dut.permit_s_rsp;for(k=1;k<11;k=k+1)send(k);while(input_acks<11)@(negedge clk);
  force dut.permit_s_rsp=1'b0;send(11);while(!dut.s_valid)@(negedge clk);start_valid=1;
  repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0)$fatal(1,"FAIL_A8 lastunACKed start");end
  start_valid=0;release dut.permit_s_rsp;while(!input_stored)@(negedge clk);repeat(3)@(negedge clk);
  if(starts!=st0)$fatal(1,"FAIL_A8 earlypulse queued");for(k=0;k<12;k=k+1)if(ram(448+k)!==a8_input_word(v,k))$fatal(1,"FAIL_A8 stored input");mark(0);
  start_job(1);take_output();finish(0,0);normal_counts();mark(1);
  for(k=1;k<8;k=k+1)begin run_normal(k);mark(k+1);end
  new_frame(5);for(k=0;k<11;k=k+1)send(k);while(input_acks<11)@(negedge clk);force dut.permit_s_rsp=1'b0;send(11);start_valid=1;
  repeat(4)@(negedge clk);if(starts!=st0||input_stored)$fatal(1,"FAIL_A8 heldstart early");release dut.permit_s_rsp;while(starts==st0)@(negedge clk);start_valid=0;
  take_output();finish(0,0);normal_counts();mark(9);
  new_frame(3);fill();force dut.permit_m_cmd=1'b0;start_job(0);repeat(5)@(negedge clk);if(mcmd!=mc0)$fatal(1,"FAIL_A8 command backpressure");
  force dut.permit_m_rsp=1'b0;release dut.permit_m_cmd;while(!dut.m_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);force dut.permit_load=1'b0;release dut.permit_m_rsp;
  wait(dut.state==7);repeat(5)@(negedge clk);if(loads!=l0)$fatal(1,"FAIL_A8 loader backpressure");force dut.permit_n_rsp=1'b0;release dut.permit_load;
  while(!dut.n_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);if(stage_acks[2]!=1||stage_acks[3]!=0||loads-l0!=1)$fatal(1,"FAIL_A8 servicecompleted yet PV early");release dut.permit_n_rsp;
  take_output();finish(0,0);normal_counts();mark(10);
  new_frame(0);force dut.permit_s_req=1'b0;send(0);repeat(4)@(negedge clk);prestart_abort();release dut.permit_s_req;run_normal(6);mark(11);
  new_frame(3);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);prestart_abort();release dut.permit_s_rsp;run_normal(0);mark(12);
  new_frame(2);fill();prestart_abort();run_normal(5);mark(13);
  new_frame(4);fill();force dut.permit_s_rsp=1'b0;start_job(0);while(!dut.s_valid)@(negedge clk);
  @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;finish(1,0);run_normal(1);mark(14);
  new_frame(3);fill();start_job(0);take_output();abort=1;@(posedge clk);#1;@(negedge clk);abort=0;
  if(ttake-tt0!=1)$fatal(1,"FAIL_A8 consumedprefix retracted");finish(1,0);run_normal(4);mark(15);
  new_frame(0);fill();start_job(0);take_output();while(!done_valid)@(negedge clk);@(negedge clk);abort=1;
  repeat(3)begin @(negedge clk);if(!done_valid||done_error||done_saturated)$fatal(1,"FAIL_A8 existingDONE changed underabort");end
  abort=0;finish(0,1);normal_counts();mark(16);
  new_frame(4);send(0);send(1);hard_reset();run_normal(3);mark(17);
  new_frame(4);fill();force dut.permit_n_rsp=1'b0;start_job(0);while(!dut.n_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();release dut.permit_n_rsp;run_normal(0);mark(18);
  new_frame(4);fill();start_job(0);while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();run_normal(5);mark(19);
  new_frame(4);fill();strict_native=0;start_job(0);wait(dut.n_cmd_valid&&dut.n_cmd_ready&&dut.n_cmd_op==1);
  @(negedge clk);force dut.n_cmd_op=4'd15;@(posedge clk);#1;@(negedge clk);release dut.n_cmd_op;
  finish(1,0);if(stage_acks[1]!=0||stage_acks[2]!=0||loads-l0!=1||twrite!=tw0)$fatal(1,"FAIL_A8 nativeN error published/PV");run_normal(6);mark(20);
  new_frame(4);fill();strict_native=0;start_job(0);wait(dut.state==5&&dut.projection==0&&dut.m_phase==2);
  @(negedge clk);force dut.m_cmd_data=64'h988c;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;
  finish(1,0);if(stage_acks[0]!=0||nservice!=ns0||twrite!=tw0)$fatal(1,"FAIL_A8 QKerror escaped");run_normal(3);mark(21);
  new_frame(5);fill();strict_native=0;start_job(0);wait(dut.state==5&&dut.projection==1&&dut.m_phase==2);
  @(negedge clk);force dut.m_cmd_data=64'h988d;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;
  finish(1,0);if(stage_acks[6]!=0||twrite!=tw0)$fatal(1,"FAIL_A8 PVerror output");run_normal(2);mark(22);
  new_frame(3);fill();start_job(0);wait(dut.n_mem_req_valid&&dut.n_mem_req_write&&dut.n_mem_req_addr==461);force dut.permit_s_rsp=1'b0;while(!dut.s_valid)@(negedge clk);repeat(4)@(negedge clk);
  @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;finish(1,0);run_normal(1);mark(23);
  new_frame(5);fill();force dut.permit_m_rsp=1'b0;start_job(0);while(!dut.m_rsp_valid)@(negedge clk);repeat(4)@(negedge clk);hard_reset();release dut.permit_m_rsp;run_normal(7);mark(24);
  new_frame(3);fill();start_job(0);wait(dut.n_mem_req_valid&&dut.n_mem_req_write&&dut.n_mem_req_addr==464);force dut.permit_s_rsp=1'b0;while(!dut.s_valid)@(negedge clk);
  repeat(5)begin @(negedge clk);if(stage_acks[2]!=0||loads-l0!=1||mcmd-mc0!=5)$fatal(1,"FAIL_A8 PV beforeprobACK");end release dut.permit_s_rsp;
  take_output();finish(0,0);normal_counts();mark(25);
  $display("PASS_W4_A8 cases=%0d cycles=%0d input=%0d Sreq=%0d Sack=%0d Mcmd=%0d Mrsp=%0d Ncmd=%0d Nrsp=%0d Ttake=%0d",cases,cycles,ingress,sreq,sack,mcmd,mrsp,ncmd,nrsp,ttake);$finish;
 end
'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();out=a.directory
    literals=(out/'a8_expected_vectors.svh').read_text(encoding='utf-8')
    fn=['function automatic [8*100-1:0] case_name;input integer index;begin case(index)']
    fn+=[' {}:case_name="{}";'.format(i,c) for i,c in enumerate(CASE_IDS)];fn+=[' default:case_name="invalid";endcase end endfunction']
    # Explicit signed cast avoids tool-specific indexing on function returns.
    body=BODY.replace('{{48{lane(vec,460,t)[15]}},lane(vec,460,t)}','$signed(lane(vec,460,t))')
    text='`timescale 1ns/1ps\n// Independent mathematical literals; no DUT-derived expected values.\nmodule block_w4_a8_tb;\n'+literals+'\n'+'\n'.join(fn)+'\n'+body+'\nendmodule\n'
    tb=out/'block_w4_a8_tb.sv';tb.write_bytes(text.encode('utf-8'))
    contract={'schema_version':1,'status':'FROZEN_CASE_REQUIREMENTS_NOT_RTL_EXECUTION','top_module':'block_w4_a8_tb','dut_module':'block_w4_a8_top','tb_path':'project/tb/block_connection_w4/block_w4_a8_tb.sv','extra_rtl_paths':['project/rtl/block_connection_p2/block_p2_s_ctrl.sv','project/rtl/block_connection_w4/block_w4_n_ctrl.sv','project/rtl/block_connection_w4/block_w4_a8_top.sv'],'data_input_paths':['work/Melodydt/151/a8-contract-vectors.json','work/Melodydt/151/a8_integer_reference.py','work/Melodydt/151/a8_expected_vectors.svh'],'native_sources_required':['project/rtl/block_v2/block_v2_m.sv','project/rtl/block_v2/block_v2_n.sv','project/rtl/block_v2/block_v2_n_group.sv','project/rtl/block_v2/block_v2_n_exp.svh','project/rtl/block_feed_v1/block_feed_loader.sv','project/rtl/block_feed_v1/block_feed_s16k.sv','project/rtl/block_feed_v1/block_feed_s_macro.sv','project/rtl/block_v1/transaction6k.sv'],'expected_case_ids':CASE_IDS,'pass_marker':'PASS_W4_A8','expected_unique_case_count':len(CASE_IDS),'tb_sha256':hashlib.sha256(tb.read_bytes()).hexdigest(),'numeric_vectors':8,'normal_counts':{'S_requests_ACKs':23,'S_write':19,'S_read':4,'M_commands_responses':10,'loader_accept_done':2,'N_services':1,'N_commands_responses':6,'T_words':1},'independent_expectations':'Case requirements are declared in this generator, not dynamically extracted from the DUT/TB log to define the expected set. Literal expectations are frozen mathematical JSON/include.','run_policy':'server Verilator only; no local RTL execution; task prefix zenanyan; working tree/log/results below /public/home/yuzelu/Melodydt/','limits':'bounded QK/Softmax/PV; not full A, L4 whole, MEM, model quality or physical acceptance'}
    (out/'a8-tb-contract.json').write_bytes((json.dumps(contract,indent=2)+'\n').encode('utf-8'))
    print('Prepared block_w4_a8_tb and independent26CASE contract; no RTL execution')


if __name__=='__main__':main()
