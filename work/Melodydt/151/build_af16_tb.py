"""Generate a self-contained AF16 SV TB from independent frozen expectations."""
import argparse
import hashlib
import json
from pathlib import Path

CASE_IDS=['AF16_INPUT40_A_REAL_ACK_STORED_GATE','AF16_NORMAL_COMPOSE_STAGES_COUNTS',
 'AF16_CAUSAL_FUTURE_TOKEN_CHANGED','AF16_ZERO_F_GAMMA_EXACT_A_HIDDEN',
 'AF16_SIGNED_GAMMAS','AF16_ZERO_ROWS','AF16_POSITIVE_SATURATION',
 'AF16_NEGATIVE_SATURATION','AF16_QUARTER_TURN_LAYOUT','AF16_RANDOM_0','AF16_RANDOM_1',
 'AF16_PARAMETER_REUSE_AND_REPEAT','AF16_A_CAPTURE_F_FEED_F_START_BACKPRESSURE',
 'AF16_ABORT_PARTIAL_PRESTART','AF16_ABORT_COMPLETE_PRESTART',
 'AF16_ABORT_PARENT_RUN_BEFORE_A_START','AF16_ABORT_PARENT_RUN_PARTIAL_F_FEED',
 'AF16_ABORT_AFTER_HOST_PREFIX','AF16_DONE_ABORT_READY_EXACTLY_ONCE',
 'AF16_RESET_PARTIAL_INPUT','AF16_RESET_F_OUTPUT_STALL',
 'AF16_A_NATIVE_N_ERROR_RECOVER','AF16_A_NATIVE_M_ERROR_RECOVER',
 'AF16_F_NATIVE_N_ERROR_RECOVER','AF16_F_NATIVE_M_ERROR_RECOVER',
 'AF16_F_NATIVE_E_ERROR_RECOVER','AF16_F_NATIVE_G_ERROR_RECOVER',
 'AF16_F_PARTIAL_FRAME_S_ERROR_PARENT_TERMINAL',
 'AF16_A_PRESTART_FRAME_S_ERROR_NO_TERMINAL',
 'AF16_SECOND_F_NATIVE_ERROR_PRESERVES_HOST_PREFIX',
 'AF16_BAD_A_FIRST_METADATA_NO_CAPTURE',
 'AF16_BAD_F_METADATA_NO_HOST_PUBLICATION',
 'AF16_UNUSED_AND_CLOSED_CHILD_SATURATION_IGNORED']

BODY=r'''
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
 reg [127:0] in_data=0;
 wire in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated;
 wire out_valid,out_last;wire [127:0] out_data;wire [9:0] out_index;
 block_w4_af16_top dut(.*);
 integer cycles=0,cases=0,v=0,ingress=0,sreq=0,sack=0,writes=0,reads=0;
 integer mcmd=0,mrsp=0,ncmd=0,nrsp=0,ecmd=0,ersp=0,gcmd=0,grsp=0;
 integer loads=0,ldone=0,wide=0,abeats=0,bbeats=0,gissued=0,gretired=0;
 integer childtakes=0,releases=0,hosttakes=0,starts=0,dtakes=0,adone=0,fdone=0;
 integer a_inputs=0,f_inputs=0,a_frame_acks=0,host_frame_inputs=0,frow=0,frame_outputs=0;
 integer a_seen[0:1023];integer f_seen[0:1][0:1023];
 reg [127:0] a_ram[0:1023];reg [127:0] f_ram[0:1023];
 reg a_written[0:1023];reg f_written[0:1023];
 reg a_pending=0,f_pending=0,a_pwrite,f_pwrite;reg [9:0] a_paddr,f_paddr;
 reg [127:0] a_pdata,f_pdata;
 reg tracking=0,running=0,hold_out=0,hold_done=0;
 reg [127:0] prev_out;reg [9:0] prev_index;reg prev_last,prev_de,prev_ds;
 integer i0,q0,ack0,w0,r0,m0,mr0,n0,nr0,e0,er0,g0,gr0,l0,ld0,wd0,ab0,bb0,gi0,go0,ct0,rel0,ht0,st0,ad0,fd0;

 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>500000)$fatal(1,"FAIL_AF16 watchdog state=%0d",dut.state);
  if(reset)begin hold_out=0;hold_done=0;a_pending=0;f_pending=0;end
  else begin
   if(hold_done&&(!done_valid||done_error!==prev_de||done_saturated!==prev_ds))$fatal(1,"FAIL_AF16 heldDONE");
   if(!abort&&hold_out&&(!out_valid||out_data!==prev_out||out_index!==prev_index||out_last!==prev_last))$fatal(1,"FAIL_AF16 heldoutput");
   hold_out=!abort&&out_valid&&!out_ready;prev_out=out_data;prev_index=out_index;prev_last=out_last;
   hold_done=done_valid&&!done_ready;prev_de=done_error;prev_ds=done_saturated;
   if(in_valid&&in_ready)begin
    ingress=ingress+1;host_frame_inputs=host_frame_inputs+1;
    if(tracking&&host_frame_inputs>40)$fatal(1,"FAIL_AF16 inputoverwrite");
   end
   if(start_valid&&start_ready)begin starts=starts+1;running=1;end
   if(done_valid&&done_ready)dtakes=dtakes+1;
   if(out_valid&&out_ready)begin
    if(!tracking||!running||frame_outputs>=2||out_index!==frame_outputs||out_last!==(frame_outputs==1)||out_data!==final_word(v,frame_outputs))$fatal(1,"FAIL_AF16 hostoutput row=%0d got=%032h",frame_outputs,out_data);
    frame_outputs=frame_outputs+1;hosttakes=hosttakes+1;
   end
   if(dut.a_done_valid&&dut.a_done_ready)adone=adone+1;
   if(dut.f_done_valid&&dut.f_done_ready)fdone=fdone+1;
   if(dut.u_a.in_valid&&dut.u_a.in_ready)begin
    if(a_inputs>=27||dut.u_a.in_data!==input_word(v,a_inputs))$fatal(1,"FAIL_AF16 A ingress order");
    a_inputs=a_inputs+1;
   end
   if(dut.u_f.in_valid&&dut.u_f.in_ready)begin
    if(f_inputs>=34||dut.u_f.in_data!==f_input_word(v,f_inputs/17,f_inputs%17))$fatal(1,"FAIL_AF16 bitexact hidden/parameter reuse beat=%0d",f_inputs);
    if(f_inputs%17==0)begin
     frow=f_inputs/17;
     for(integer j=0;j<1024;j=j+1)f_written[j]=0;
    end
    f_inputs=f_inputs+1;
   end
   if(dut.a_start_valid&&dut.a_start_ready)begin
    if(host_frame_inputs!=40||!dut.u_a.input_stored||a_frame_acks!=27)$fatal(1,"FAIL_AF16 childA earlyRUN");
   end
   if(dut.f_start_valid&&dut.f_start_ready)begin
    if(!dut.u_f.input_stored||f_inputs!=(frow+1)*17||adone-ad0!=1)$fatal(1,"FAIL_AF16 childF earlyRUN");
   end
  end
 end

__MONITORS__

 task automatic mark;input integer idx;begin cases=cases+1;$display("CASE_PASS %0s",case_name(idx));end endtask
 task automatic new_frame;input integer vec;integer k;begin
  if(busy||done_valid||input_stored)$fatal(1,"FAIL_AF16 stale at newframe");
  v=vec;tracking=1;running=0;host_frame_inputs=0;a_inputs=0;f_inputs=0;a_frame_acks=0;frow=0;frame_outputs=0;
  a_pending=0;f_pending=0;
  for(k=0;k<1024;k=k+1)begin a_seen[k]=0;f_seen[0][k]=0;f_seen[1][k]=0;a_written[k]=0;f_written[k]=0;end
  i0=ingress;q0=sreq;ack0=sack;w0=writes;r0=reads;m0=mcmd;mr0=mrsp;n0=ncmd;nr0=nrsp;e0=ecmd;er0=ersp;g0=gcmd;gr0=grsp;l0=loads;ld0=ldone;wd0=wide;ab0=abeats;bb0=bbeats;gi0=gissued;go0=gretired;ct0=childtakes;rel0=releases;ht0=hosttakes;st0=starts;ad0=adone;fd0=fdone;
 end endtask
 task automatic send;input integer beat;begin
  @(negedge clk);in_valid=1;in_data=input_word(v,beat);
  while(!in_ready)@(negedge clk);@(posedge clk);#1;
  if(!busy)$fatal(1,"FAIL_AF16 input capture notbusy");
  @(negedge clk);in_valid=0;
 end endtask
 task automatic fill;begin
  for(integer k=0;k<40;k=k+1)send(k);
  while(!input_stored)@(negedge clk);
  if(a_frame_acks!=27||!start_ready||!busy||in_ready)$fatal(1,"FAIL_AF16 stored gate");
 end endtask
 task automatic start_job;input held;begin
  @(negedge clk);if(!start_ready)$fatal(1,"FAIL_AF16 notready");start_valid=1;
  @(posedge clk);#1;@(negedge clk);if(!held)start_valid=0;
 end endtask
 task automatic take_one;begin
  while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);
  out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;
 end endtask
 task automatic finish;input expected_error,abort_at_take;integer oldtake;begin
  while(!done_valid)@(negedge clk);
  if(done_error!==expected_error)$fatal(1,"FAIL_AF16 errorflag expected=%0d got=%0d",expected_error,done_error);
  if(!expected_error&&(done_saturated!==sat_word(v)||frame_outputs!=2||releases-rel0!=3||adone-ad0!=1||fdone-fd0!=2))$fatal(1,"FAIL_AF16 earlyDONE/saturation");
  repeat(5)begin @(negedge clk);if(!done_valid||!busy||in_ready||start_ready)$fatal(1,"FAIL_AF16 DONEhold");end
  oldtake=dtakes;done_ready=1;abort=abort_at_take;@(posedge clk);#1;
  @(negedge clk);done_ready=0;abort=0;start_valid=0;
  if(dtakes!=oldtake+1)$fatal(1,"FAIL_AF16 DONE duplicate/suppressed");
  tracking=0;running=0;repeat(3)@(negedge clk);
  if(done_valid||busy||input_stored||!in_ready)$fatal(1,"FAIL_AF16 DONEreuse");
 end endtask
 task automatic normal_counts;begin
  if(ingress-i0!=40||sreq-q0!=181||sack-ack0!=181||writes-w0!=131||reads-r0!=50)$fatal(1,"FAIL_AF16 S/counts input=%0d req=%0d ack=%0d W%0d R%0d",ingress-i0,sreq-q0,sack-ack0,writes-w0,reads-r0);
  if(mcmd-m0!=72||mrsp-mr0!=72||ncmd-n0!=28||nrsp-nr0!=28||ecmd-e0!=10||ersp-er0!=10||gcmd-g0!=2||grsp-gr0!=2||gissued-gi0!=8||gretired-go0!=8)$fatal(1,"FAIL_AF16 compute counts");
  if(loads-l0!=12||ldone-ld0!=12||wide-wd0!=26||abeats-ab0!=18||bbeats-bb0!=14||childtakes-ct0!=4||releases-rel0!=3||hosttakes-ht0!=2||starts-st0!=1||a_inputs!=27||f_inputs!=34)$fatal(1,"FAIL_AF16 lifecycle counts");
 end endtask
 task automatic run_normal;input integer vec;begin new_frame(vec);fill();start_job(0);take_one();take_one();finish(0,0);normal_counts();end endtask
 task automatic pulse_abort;begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;start_valid=0;in_valid=0;out_ready=0;end endtask
 task automatic preabort;begin pulse_abort();tracking=0;running=0;repeat(4)@(negedge clk);if(done_valid||busy||input_stored||!in_ready)$fatal(1,"FAIL_AF16 preabort createdDONE");end endtask
 task automatic hard_reset;begin
  @(negedge clk);reset=1;in_valid=0;start_valid=0;out_ready=0;done_ready=0;
  repeat(3)@(negedge clk);reset=0;tracking=0;running=0;
  repeat(4)@(negedge clk);if(done_valid||busy||out_valid||input_stored||!in_ready)$fatal(1,"FAIL_AF16 reset stale");
 end endtask

 initial begin
  repeat(4)@(negedge clk);reset=0;repeat(3)@(negedge clk);
  // A27 real ACK is required even if every F parameter has already arrived.
  new_frame(0);for(integer k=0;k<26;k=k+1)send(k);
  while(a_frame_acks<26)@(negedge clk);force dut.u_a.permit_s_rsp=1'b0;
  send(26);for(integer k=27;k<40;k=k+1)send(k);
  start_valid=1;repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0||in_ready)$fatal(1,"FAIL_AF16 unACKedAacceptedRUN");end
  start_valid=0;release dut.u_a.permit_s_rsp;
  while(!input_stored)@(negedge clk);mark(0);
  start_job(1);take_one();take_one();finish(0,0);normal_counts();mark(1);
  for(integer k=1;k<10;k=k+1)begin run_normal(k);mark(k+1);end
  run_normal(0);run_normal(3);mark(11);
  new_frame(0);fill();force dut.permit_capture=1'b0;force dut.permit_f_feed=1'b0;force dut.permit_f_start=1'b0;
  start_job(0);while(!dut.a_out_valid)@(negedge clk);repeat(6)@(negedge clk);
  if(childtakes!=ct0)$fatal(1,"FAIL_AF16 capture ignoredstall");release dut.permit_capture;
  while(dut.state!=4)@(negedge clk);repeat(5)@(negedge clk);if(f_inputs!=0)$fatal(1,"FAIL_AF16 feedstall");release dut.permit_f_feed;
  while(!dut.f_input_stored)@(negedge clk);repeat(5)@(negedge clk);if(!dut.u_f.input_stored||dut.f_start_valid)$fatal(1,"FAIL_AF16 Fstored/startgate");release dut.permit_f_start;
  take_one();take_one();finish(0,0);normal_counts();mark(12);
  new_frame(0);send(0);send(1);preabort();run_normal(0);mark(13);
  new_frame(0);fill();preabort();run_normal(2);mark(14);
  new_frame(0);fill();force dut.permit_a_start=1'b0;start_job(0);repeat(5)@(negedge clk);
  if(dut.u_a.running)$fatal(1,"FAIL_AF16 Astarted despitegate");pulse_abort();release dut.permit_a_start;finish(1,0);run_normal(0);mark(15);
  new_frame(0);fill();start_job(0);while(f_inputs<2)@(negedge clk);force dut.permit_f_feed=1'b0;
  pulse_abort();release dut.permit_f_feed;finish(1,0);run_normal(0);mark(16);
  new_frame(0);fill();start_job(0);take_one();pulse_abort();if(frame_outputs!=1)$fatal(1,"FAIL_AF16 prefixrollback");finish(1,0);run_normal(0);mark(17);
  new_frame(5);fill();start_job(0);take_one();take_one();while(!done_valid)@(negedge clk);
  abort=1;repeat(3)begin @(negedge clk);if(!done_valid||done_error||!done_saturated)$fatal(1,"FAIL_AF16 DONEabort flags");end abort=0;
  finish(0,1);normal_counts();mark(18);
  new_frame(0);send(0);hard_reset();run_normal(0);mark(19);
  new_frame(0);fill();start_job(0);while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();run_normal(0);mark(20);
  new_frame(0);fill();start_job(0);@(negedge clk);while(!(dut.u_a.n_cmd_valid&&dut.u_a.n_cmd_ready))@(negedge clk);
  force dut.u_a.n_cmd_op=4'd15;@(posedge clk);#1;@(negedge clk);release dut.u_a.n_cmd_op;finish(1,0);if(frame_outputs!=0||f_inputs!=0)$fatal(1,"FAIL_AF16 A Nerror escaped");run_normal(0);mark(21);
  new_frame(0);fill();start_job(0);wait(dut.u_a.state==5&&dut.u_a.projection==3&&dut.u_a.m_phase==2);@(negedge clk);
  force dut.u_a.m_cmd_data=64'h1188f;@(posedge clk);#1;@(negedge clk);release dut.u_a.m_cmd_data;finish(1,0);if(frame_outputs!=0||f_inputs!=0)$fatal(1,"FAIL_AF16 A Merror escaped");run_normal(0);mark(22);
  new_frame(0);fill();start_job(0);@(negedge clk);while(!(dut.u_f.n_cmd_valid&&dut.u_f.n_cmd_ready))@(negedge clk);
  force dut.u_f.n_cmd_op=4'd15;@(posedge clk);#1;@(negedge clk);release dut.u_f.n_cmd_op;finish(1,0);if(frame_outputs!=0)$fatal(1,"FAIL_AF16 F Nerror escaped");run_normal(0);mark(23);
  new_frame(0);fill();start_job(0);wait(dut.u_f.state==5&&dut.u_f.m_phase==2);@(negedge clk);
  force dut.u_f.m_cmd_data=64'h988d;@(posedge clk);#1;@(negedge clk);release dut.u_f.m_cmd_data;finish(1,0);if(frame_outputs!=0)$fatal(1,"FAIL_AF16 F Merror escaped");run_normal(0);mark(24);
  new_frame(0);fill();start_job(0);@(negedge clk);while(!(dut.u_f.e_in_valid&&dut.u_f.e_in_ready))@(negedge clk);
  force dut.u_f.e_in_op=4'd14;@(posedge clk);#1;@(negedge clk);release dut.u_f.e_in_op;finish(1,0);if(frame_outputs!=0)$fatal(1,"FAIL_AF16 F Eerror escaped");run_normal(0);mark(25);
  new_frame(0);fill();start_job(0);@(negedge clk);while(!(dut.u_f.g_in_valid&&dut.u_f.g_in_ready))@(negedge clk);
  force dut.u_f.g_in_fn=3'd4;@(posedge clk);#1;@(negedge clk);release dut.u_f.g_in_fn;finish(1,0);if(frame_outputs!=0)$fatal(1,"FAIL_AF16 F Gerror escaped");run_normal(0);mark(26);
  new_frame(0);fill();start_job(0);wait(dut.state==4&&f_inputs>=1);@(negedge clk);
  while(!(dut.u_f.h_rsp_valid&&dut.u_f.h_rsp_ready))@(negedge clk);
  force dut.u_f.h_rsp_error=1'b1;@(posedge clk);#1;@(negedge clk);release dut.u_f.h_rsp_error;finish(1,0);if(frame_outputs!=0)$fatal(1,"FAIL_AF16 Fframeerror escaped");run_normal(0);mark(27);
  new_frame(0);send(0);@(negedge clk);while(!(dut.u_a.h_rsp_valid&&dut.u_a.h_rsp_ready))@(negedge clk);
  force dut.u_a.h_rsp_error=1'b1;@(posedge clk);#1;@(negedge clk);release dut.u_a.h_rsp_error;
  repeat(8)@(negedge clk);if(done_valid||busy||input_stored||!in_ready)$fatal(1,"FAIL_AF16 prestartframefailure terminal/stuck");tracking=0;run_normal(0);mark(28);
  new_frame(0);fill();start_job(0);take_one();@(negedge clk);
  while(!(dut.u_f.n_cmd_valid&&dut.u_f.n_cmd_ready&&f_inputs>=34))@(negedge clk);
  force dut.u_f.n_cmd_op=4'd15;@(posedge clk);#1;@(negedge clk);release dut.u_f.n_cmd_op;finish(1,0);
  if(frame_outputs!=1||hosttakes-ht0!=1)$fatal(1,"FAIL_AF16 secondrowerror prefixrollback");run_normal(0);mark(29);
  new_frame(0);fill();force dut.permit_capture=1'b0;start_job(0);
  while(!dut.a_out_valid)@(negedge clk);force dut.a_out_last=1'b1;
  @(posedge clk);#1;@(negedge clk);release dut.a_out_last;release dut.permit_capture;
  finish(1,0);if(childtakes-ct0!=0||f_inputs!=0||frame_outputs!=0)$fatal(1,"FAIL_AF16 badAmetadata escaped");run_normal(0);mark(30);
  new_frame(0);fill();start_job(0);while(!dut.f_out_valid)@(negedge clk);
  hold_out=0;force dut.f_out_index=10'd1;out_ready=1;
  @(posedge clk);#1;@(negedge clk);out_ready=0;release dut.f_out_index;
  finish(1,0);if(frame_outputs!=0||hosttakes-ht0!=0)$fatal(1,"FAIL_AF16 badFmetadata published");run_normal(0);mark(31);
  new_frame(0);fill();force dut.permit_a_start=1'b0;start_job(0);
  force dut.f_done_saturated=1'b1;repeat(5)@(negedge clk);
  release dut.f_done_saturated;release dut.permit_a_start;
  while(dut.state!=4)@(negedge clk);force dut.a_done_saturated=1'b1;
  take_one();take_one();release dut.a_done_saturated;
  finish(0,0);normal_counts();mark(32);
  if(cases!=33)$fatal(1,"FAIL_AF16 CASEcount");
  $display("AF16_STATS cycles=%0d input=%0d Sreq=%0d Sack=%0d Mcmd=%0d Mrsp=%0d Ncmd=%0d Nrsp=%0d childTtake=%0d release=%0d host=%0d",cycles,ingress,sreq,sack,mcmd,mrsp,ncmd,nrsp,childtakes,releases,hosttakes);
  $display("PASS_W4_AF16 cases=%0d",cases);$finish;
 end
'''


def function(name, records, args):
    decl=' function automatic [127:0] '+name+';\n'
    decl+=''.join('  input integer '+a+';\n' for a in args)
    # Explicit tuple-comparison branches avoid hidden arithmetic-key collisions.
    decl+='  integer matched;begin matched=0;'+name+"=0;\n"
    for keys,value in records:
        decl+='   if('+ '&&'.join(a+'=='+str(k) for a,k in zip(args,keys))+') begin matched=1;'+name+"=128'h%032x;end\n"%value
    return decl+'   if(!matched)$fatal(1,"FAIL_AF16 unknown '+name+' lookup");\n  end\n endfunction\n'


def monitor(prefix, path, history):
    # Both native ordinary S ports are individually serialized by their helpers.
    own='a' if prefix=='a' else 'f'
    stage='a_stage_word(v,'+path+'.s_addr,a_seen['+path+'.s_addr])' if prefix=='a' else 'f_stage_word(v,frow,'+path+'.s_addr,f_seen[frow]['+path+'.s_addr])'
    inc='a_seen['+path+'.s_addr]=a_seen['+path+'.s_addr]+1;' if prefix=='a' else 'f_seen[frow]['+path+'.s_addr]=f_seen[frow]['+path+'.s_addr]+1;'
    ackextra='if(a_pwrite&&a_paddr>=448&&a_paddr<=474&&a_inputs<=27&&!dut.u_a.running)a_frame_acks=a_frame_acks+1;' if prefix=='a' else ''
    return '''
 always @(posedge clk)begin
  if(PATH.leaf_reset)P_pending=0;
  else if(tracking)begin
   if(PATH.s_req&&PATH.s_ready)begin
    if(P_pending)$fatal(1,"FAIL_AF16 P overlapping S");
    P_pending=1;P_pwrite=PATH.s_we;P_paddr=PATH.s_addr;P_pdata=PATH.s_din;sreq=sreq+1;
    if(PATH.s_we)begin
     if(PATH.s_din!==STAGE)$fatal(1,"FAIL_AF16 P Sstage addr=%0d data=%032h",PATH.s_addr,PATH.s_din);
     INC writes=writes+1;
    end else reads=reads+1;
   end
   if(PATH.s_valid&&PATH.s_take)begin
    if(!P_pending)$fatal(1,"FAIL_AF16 P unexpectedSACK");sack=sack+1;
    if(P_pwrite)begin P_ram[P_paddr]=P_pdata;P_written[P_paddr]=1;end
    else if(!P_written[P_paddr]||PATH.s_dout!==P_ram[P_paddr])$fatal(1,"FAIL_AF16 P readbeforeACK/wrongversion addr=%0d",P_paddr);
    ACKEXTRA P_pending=0;
   end
   if(PATH.m_cmd_valid&&PATH.m_cmd_ready)mcmd=mcmd+1;
   if(PATH.m_rsp_valid&&PATH.m_rsp_ready)mrsp=mrsp+1;
   if(PATH.n_cmd_valid&&PATH.n_cmd_ready)ncmd=ncmd+1;
   if(PATH.n_native_rsp_valid&&PATH.n_native_rsp_ready)nrsp=nrsp+1;
   if(PATH.e_req_valid&&PATH.e_req_ready)ecmd=ecmd+1;
   if(PATH.e_rsp_valid&&PATH.e_rsp_ready)ersp=ersp+1;
   if(PATH.load_valid&&PATH.load_ready)loads=loads+1;
   if(PATH.load_done_valid&&PATH.load_done_take)ldone=ldone+1;
   if(PATH.u_s.mem_req&&PATH.u_s.mem_ready)wide=wide+1;
   if(PATH.a_valid&&PATH.a_ready)abeats=abeats+1;
   if(PATH.b_valid&&PATH.b_ready)bbeats=bbeats+1;
   if(PATH.t_read_valid&&PATH.t_read_take)childtakes=childtakes+1;
   if(PATH.state==17&&PATH.t_release_ready)releases=releases+1;
  end
 end
'''.replace('ACKEXTRA',ackextra).replace('STAGE',stage).replace('INC',inc).replace('PATH',path).replace('P_',own+'_').replace(' P ', ' '+own+' ')


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
    args=p.parse_args();d=args.directory;data=json.loads((d/'af16-contract-vectors.json').read_text(encoding='utf-8'))
    inputs=[];hidden=[];final=[];fi=[];ah=[];fh=[];sats=[]
    for v in data['vectors']:
        n=v['index'];r=v['expected']
        inputs += [((n,i),w) for i,w in enumerate(r['ingress_words'])]
        hidden += [((n,i),w) for i,w in enumerate(r['A_hidden_words'])]
        final += [((n,i),w) for i,w in enumerate(r['final_words'])]
        sats.append('  '+str(n)+':sat_word=1\'b'+str(int(r['done_saturated']))+';')
        for a,ws in r['A']['S_write_history'].items():ah += [((n,int(a),j),w) for j,w in enumerate(ws)]
        for row in range(2):
            fi += [((n,row,j),w) for j,w in enumerate(r['F'][row]['ingress_words'])]
            for a,ws in r['F_S_write_history'][row].items():fh += [((n,row,int(a),j),w) for j,w in enumerate(ws)]
    sv='`timescale 1ns/1ps\nmodule block_w4_af16_tb;\n'
    for name,records,params in [('input_word',inputs,['v','i']),('hidden_word',hidden,['v','i']),('final_word',final,['v','i']),('f_input_word',fi,['v','row','i']),('a_stage_word',ah,['v','addr','version']),('f_stage_word',fh,['v','row','addr','version'])]:sv+=function(name,records,params)
    sv+=" function automatic sat_word;input integer v;begin sat_word=0;case(v)\n"+'\n'.join(sats)+'\n endcase end endfunction\n'
    sv+=' function automatic [639:0] case_name;input integer i;begin case(i)\n'
    sv+='\n'.join('  '+str(i)+':case_name="'+name+'";' for i,name in enumerate(CASE_IDS))
    sv+='\n default:case_name="INVALID";endcase end endfunction\n'
    mon=monitor('a','dut.u_a','a')+monitor('f','dut.u_f','f')
    mon+='''
 always @(posedge clk)if(!reset&&!dut.u_f.leaf_reset&&tracking)begin
  if(dut.u_f.g_req_valid&&dut.u_f.g_req_ready)gcmd=gcmd+1;
  if(dut.u_f.g_rsp_valid&&dut.u_f.g_rsp_ready)grsp=grsp+1;
  if(dut.u_f.g_in_valid&&dut.u_f.g_in_ready)gissued=gissued+1;
  if(dut.u_f.g_out_valid&&dut.u_f.g_out_ready)gretired=gretired+1;
 end
'''
    sv+=BODY.replace('__MONITORS__',mon)+'\nendmodule\n'
    tb=d/'block_w4_af16_tb.sv';tb.write_bytes(sv.encode('utf-8'))
    sources=['project/rtl/block_v2/block_v2_'+s+'.sv' for s in ['e','g','m','n','n_group']]
    sources += ['project/rtl/block_feed_v1/'+s+'.sv' for s in ['block_feed_loader','block_feed_s16k','block_feed_s_macro']]
    sources += ['project/rtl/block_v1/transaction6k.sv','project/rtl/block_connection_p2/block_p2_s_ctrl.sv','project/rtl/block_connection_w3/block_w3_e_ctrl.sv','project/rtl/block_connection_w3/block_w3_g_ctrl.sv','project/rtl/block_connection_w4/block_w4_n_ctrl.sv','project/rtl/block_connection_w4/block_w4_a16_top.sv','project/rtl/block_connection_w4/block_w4_f16_top.sv','project/rtl/block_connection_w4/block_w4_af16_top.sv','project/tb/block_connection_w4/block_w4_af16_tb.sv']
    contract={'schema_version':1,'status':'FROZEN_BOUNDED_CASE_CONTRACT_NOT_RTL_EXECUTION',
     'top_module':'block_w4_af16_tb','pass_marker':'PASS_W4_AF16',
     'pass_line_regex':'^PASS_W4_AF16 cases=33$','expected_case_ids':CASE_IDS,'expected_unique_case_count':33,
     'compile_sources':sources,'include_dirs':['project/rtl/block_v2','work/Melodydt/151'],
     'TB_includes':[],'tb_sha256':hashlib.sha256(tb.read_bytes()).hexdigest(),
     'vectors_path':'work/Melodydt/151/af16-contract-vectors.json',
     'reference_dependencies':['work/Melodydt/151/af16_integer_reference.py']+[x['path'] for x in data['reference_dependencies']],
     'reference_dependency_sha256':data['reference_dependencies'],'normal_counts':data['normal_counts'],
     'execution_policy':'root server Verilator only; no local RTL run',
     'scope':'fixed A16 two-token output into shared F16 twice; no L5 network/MEM/full model/physical proof'}
    (d/'af16-tb-contract.json').write_bytes((json.dumps(contract,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS_AF16_TB_GENERATED cases=33 SHA256='+contract['tb_sha256'])


if __name__=='__main__':main()
