"""Generate self-contained A16 TB and independently declared CASE contract."""
import argparse,json,hashlib
from pathlib import Path

CASE_IDS=['A16_INPUT27_ACK_PADDING_GATE','A16_NORMAL_REAL_ROPE_STAGES_COUNTS','A16_CAUSAL_FUTURE_TOKEN_CHANGED','A16_ZERO_GAMMA_EXACT_RESIDUAL','A16_SIGNED_NONUNITY_GAMMA','A16_ZERO_ROWS_VARIABLE_GAMMA','A16_POSITIVE_SATURATION','A16_NEGATIVE_SATURATION','A16_QUARTER_TURN_SPARSE_LAYOUT','A16_RANDOM_0','A16_RANDOM_1','A16_HELD_START_FINAL_ACK_REPEAT','A16_N_M_LOADER_E_RESPONSE_BACKPRESSURE','A16_ABORT_CAPTURED_BEFORE_S','A16_ABORT_INPUT_ACK','A16_ABORT_PRESTART_COMPLETE','A16_ABORT_RUN_PAD_ACK','A16_ABORT_BETWEEN_TWO_OUTPUT_WORDS','A16_DONE_ABORT_READY_EXACTLY_ONCE','A16_RESET_PARTIAL_INPUT','A16_RESET_HELD_N_SERVICE','A16_RESET_COMMITTED_T_STALL','A16_NATIVE_N_ERROR_RECOVER','A16_NATIVE_QK_EXEC_ERROR_RECOVER','A16_NATIVE_WO_EXEC_ERROR_RECOVER','A16_NATIVE_ROPE_ERROR_RECOVER','A16_NATIVE_RESIDUAL_E_ERROR_RECOVER','A16_S_HELPER_ERROR_RECOVER','A16_ABORT_SECOND_PROBABILITY_ACK','A16_RESET_HELD_M_RESPONSE']

BODY=r'''
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;reg [127:0] in_data=0;
 wire in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,out_valid,out_last;wire [127:0] out_data;wire [9:0] out_index;
 block_w4_a16_top dut(.*);
 integer cycles=0,cases=0,v=0,ingress=0,sreq=0,sack=0,writes=0,reads=0,mcmd=0,mrsp=0,loads=0,ldone=0,wide=0,abeats=0,bbeats=0,nsvc=0,nsvc_rsp=0,ncmd=0,nrsp=0,esvc=0,esvc_rsp=0,ttake=0,tbegin=0,twrite=0,tcommit=0,trelease=0,starts=0,dtake=0;
 integer i0,q0,a0,w0,r0,mc0,mr0,l0,ld0,wd0,ab0,bb0,ns0,nsr0,nc0,nr0,e0,er0,tt0,tb0,tw0,tc0,tr0,st0,frameacks=0,framereqs=0,nstep=0;
 integer written[0:1023];reg job=0,frame_open=0,pending=0,pending_write,strict_native=1,load_completed=0;
 reg [9:0] pending_addr;reg [127:0] pending_data;reg ho=0,hd=0,hs=0,hm=0,hn=0,he=0,hi=0;
 reg [127:0] po,ps,pm,pi;reg [9:0] pidx;reg plast,pde,pds,pne,pns,pee,pes;
 function automatic [127:0] ram;input integer a;begin case(a%4)0:ram=dut.u_s.storage.bank0[a/4];1:ram=dut.u_s.storage.bank1[a/4];2:ram=dut.u_s.storage.bank2[a/4];3:ram=dut.u_s.storage.bank3[a/4];endcase end endfunction
 function automatic [127:0] current_word;input integer a;begin current_word=write_word(v,a,written[a]-1);end endfunction
 function automatic [127:0] mask_word;input [127:0] data;input integer count;begin mask_word=0;for(integer k=0;k<8;k=k+1)if(k<count)mask_word[16*k+:16]=data[16*k+:16];end endfunction
 function automatic [127:0] raw_input;input integer vec,beat;begin raw_input=input_word(vec,beat);if((beat>=1&&beat<=3)||(beat>=5&&beat<=7))raw_input=128'hfedcba98765432100123456789abcdef;end endfunction
 function automatic integer abase;input integer p;begin case(p)0,1,2:abase=480;3:abase=488;4:abase=516;5:abase=520;default:abase=0;endcase end endfunction
 function automatic integer bbase;input integer p;begin case(p)0:bbase=456;1:bbase=460;2:bbase=464;3:bbase=496;4:bbase=504;5:bbase=468;default:bbase=0;endcase end endfunction
 function automatic integer dst_n;input integer n;begin case(n)0:dst_n=480;1:dst_n=481;2:dst_n=516;3:dst_n=517;endcase end endfunction
 function automatic integer src_n;input integer n;begin case(n)0:src_n=448;1:src_n=452;2:src_n=512;3:src_n=513;endcase end endfunction
 function automatic integer nop;input integer stage,step;begin if(stage<2)case(step)0:nop=0;1:nop=1;2:nop=2;3:nop=5;default:nop=-1;endcase else case(step)0:nop=0;1:nop=1;2:nop=2;3:nop=3;4:nop=4;5:nop=6;default:nop=-1;endcase end endfunction
 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>1000000)$fatal(1,"FAIL_A16 watchdog");
  if(reset)hd=0;else begin if(hd&&(!done_valid||done_error!==pde||done_saturated!==pds))$fatal(1,"FAIL_A16 heldDONE");hd=done_valid&&!done_ready;pde=done_error;pds=done_saturated;if(done_valid&&done_ready)dtake=dtake+1;end
  if(reset||dut.leaf_reset)begin ho=0;hs=0;hm=0;hn=0;he=0;hi=0;pending=0;end else begin
   if(hi&&(!in_valid||in_data!==pi))$fatal(1,"FAIL_A16 inputhold");hi=in_valid&&!in_ready;pi=in_data;
   if(ho&&(!out_valid||out_data!==po||out_index!==pidx||out_last!==plast))$fatal(1,"FAIL_A16 outputhold");ho=out_valid&&!out_ready;po=out_data;pidx=out_index;plast=out_last;
   if(hs&&(!dut.s_valid||dut.s_dout!==ps))$fatal(1,"FAIL_A16 Sresponsehold");hs=dut.s_valid&&!dut.s_take;ps=dut.s_dout;
   if(hm&&(!dut.m_rsp_valid||dut.m_rsp_data!==pm))$fatal(1,"FAIL_A16 Mresponsehold");hm=dut.m_rsp_valid&&!dut.m_rsp_ready;pm=dut.m_rsp_data;
   if(hn&&(!dut.n_rsp_valid||dut.n_rsp_error!==pne||dut.n_rsp_saturated!==pns))$fatal(1,"FAIL_A16 Nservicehold");hn=dut.n_rsp_valid&&!dut.n_rsp_ready;pne=dut.n_rsp_error;pns=dut.n_rsp_saturated;
   if(he&&(!dut.e_rsp_valid||dut.e_rsp_error!==pee||dut.e_rsp_saturated!==pes))$fatal(1,"FAIL_A16 Eservicehold");he=dut.e_rsp_valid&&!dut.e_rsp_ready;pee=dut.e_rsp_error;pes=dut.e_rsp_saturated;
   if(in_valid&&in_ready)begin if(!frame_open||job||ingress-i0>=27)$fatal(1,"FAIL_A16 inputownership");ingress=ingress+1;end
   if(dut.s_req&&dut.s_ready)begin
    if(pending)$fatal(1,"FAIL_A16 multipleSowner");pending=1;pending_write=dut.s_we;pending_addr=dut.s_addr;pending_data=dut.s_din;sreq=sreq+1;
    if(dut.s_we)begin
     if(dut.s_din!==write_word(v,dut.s_addr,written[dut.s_addr])||written[dut.s_addr]>=expected_writes(v,dut.s_addr))$fatal(1,"FAIL_A16 goldenwrite vec%0d addr%0d nth%0d got%032h",v,dut.s_addr,written[dut.s_addr],dut.s_din);
     if(dut.s_addr>=448&&dut.s_addr<=474)begin if(job||dut.s_addr!=448+framereqs)$fatal(1,"FAIL_A16 inputorder");framereqs=framereqs+1;end else if(!job)$fatal(1,"FAIL_A16 compute beforeRUN");
     written[dut.s_addr]=written[dut.s_addr]+1;writes=writes+1;
    end else begin if(!job||written[dut.s_addr]<1)$fatal(1,"FAIL_A16 uninitializedread");reads=reads+1;end
   end
   if(dut.s_valid&&dut.s_take)begin
    if(!pending)$fatal(1,"FAIL_A16 unownedACK");if(dut.s_dout!==(pending_write?pending_data:current_word(pending_addr)))$fatal(1,"FAIL_A16 read/writeACKgolden");
    if(pending_write&&pending_addr>=448&&pending_addr<=474)frameacks=frameacks+1;pending=0;sack=sack+1;
   end
   if(input_stored&&(ingress-i0!=27||frameacks!=27||(!job&&pending)))$fatal(1,"FAIL_A16 storedmarker");if(start_ready&&!input_stored)$fatal(1,"FAIL_A16 earlyready");
   if(start_valid&&start_ready)begin if(job||frameacks!=27)$fatal(1,"FAIL_A16 earlyRUN");job=1;starts=starts+1;end
   if(dut.load_valid&&dut.load_ready)begin if(pending||dut.u_s.load_rows!=2||dut.u_s.load_tiles!=1||!dut.u_s.load_a_wide||dut.u_s.load_b_wide!==(dut.projection==3||dut.projection==4))$fatal(1,"FAIL_A16 loadergeometry");loads=loads+1;load_completed=0;end
   if(dut.u_s.mem_req&&dut.u_s.mem_ready)wide=wide+1;
   if(dut.load_done_valid&&dut.load_done_take)begin ldone=ldone+1;load_completed=!dut.load_done_error;end
   if(dut.a_valid&&dut.a_ready)begin if(dut.a_row>1||dut.a_data!==current_word(abase(dut.projection)+dut.a_row))$fatal(1,"FAIL_A16 loaderArows");abeats=abeats+1;end
   if(dut.b_valid&&dut.b_ready)begin if(dut.b_data!=={current_word(bbase(dut.projection)+4*dut.b_half+3),current_word(bbase(dut.projection)+4*dut.b_half+2),current_word(bbase(dut.projection)+4*dut.b_half+1),current_word(bbase(dut.projection)+4*dut.b_half)})$fatal(1,"FAIL_A16 Bcolumnpacking");bbeats=bbeats+1;end
   if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
    if(strict_native)case(dut.m_phase)
     0:if(dut.m_cmd_op!=6)$fatal(1,"FAIL_A16 CLEARopcode");
     1:if(dut.m_cmd_op!=4||dut.m_cmd_data!=(dut.projection==3?11585:1))$fatal(1,"FAIL_A16 Mscale");
     2:if(dut.m_cmd_op!=10||dut.m_cmd_data!=((dut.projection==3||dut.projection==4)?64'h11887:64'h11885))$fatal(1,"FAIL_A16 EXECformat");
     3,4,5,6:if(dut.m_cmd_op!=5||dut.m_cmd_index!=((dut.m_phase>=5?8:0)+(dut.m_phase==4||dut.m_phase==6))||dut.m_cmd_data!=(dut.projection==3?64'h119:dut.projection==4?64'h10e:64'h107))$fatal(1,"FAIL_A16 Mreadindexshift");
    endcase
    if(dut.m_cmd_op==10&&!load_completed)$fatal(1,"FAIL_A16 EXECbeforeload");mcmd=mcmd+1;
   end
   if(dut.m_rsp_valid&&dut.m_rsp_ready)begin if(!dut.m_rsp_error&&dut.m_phase>=3&&dut.m_rsp_data!==m_carrier(v,dut.projection,dut.m_phase-3))$fatal(1,"FAIL_A16 Mcarrier");mrsp=mrsp+1;end
   if(dut.n_req_valid&&dut.n_req_ready)begin nsvc=nsvc+1;nstep=0;end
   if(dut.n_cmd_valid&&dut.n_cmd_ready)begin
    if(strict_native)begin
     if(dut.n_cmd_op!=nop(dut.n_stage,nstep))$fatal(1,"FAIL_A16 Nphase");
     if(dut.n_cmd_op==0&&(dut.n_cmd_param!=(dut.n_stage<2?1:0)||dut.n_cmd_data[31:0]!=1))$fatal(1,"FAIL_A16 Nmodeepsilon");
     if(dut.n_cmd_op==1||dut.n_cmd_op==3||dut.n_cmd_op==5||dut.n_cmd_op==6)begin
      if(dut.n_cmd_count!=(dut.n_stage<2?8:dut.n_stage-1)||dut.n_cmd_data!==mask_word(current_word(dut.n_cmd_op==6?514+dut.n_stage-2:src_n(dut.n_stage)),dut.n_stage<2?8:dut.n_stage-1))$fatal(1,"FAIL_A16 causalprefixrawEXP");
      if(dut.n_cmd_op==5&&dut.n_cmd_aux!==input_word(v,24))$fatal(1,"FAIL_A16 gamma");
     end
    end
    nstep=nstep+1;ncmd=ncmd+1;
   end
   if(dut.n_native_rsp_valid&&dut.n_native_rsp_ready)nrsp=nrsp+1;
   if(dut.n_rsp_valid&&dut.n_rsp_ready)begin if(!dut.n_rsp_error&&(written[dst_n(dut.n_stage)]!=1||pending))$fatal(1,"FAIL_A16 Nearlydone");nsvc_rsp=nsvc_rsp+1;end
   if(dut.e_req_valid&&dut.e_req_ready)esvc=esvc+1;
   if(dut.e_in_valid&&dut.e_in_ready&&strict_native)begin if(dut.e_in_op!=(dut.e_stage<4?9:0)||dut.e_in_shift!=(dut.e_stage<4?14:0))$fatal(1,"FAIL_A16 Eropeadd");end
   if(dut.e_rsp_valid&&dut.e_rsp_ready)esvc_rsp=esvc_rsp+1;
   if(dut.u_t.begin_valid&&dut.u_t.begin_ready)begin if(dut.u_t.begin_words!=2)$fatal(1,"FAIL_A16 Twordcount");tbegin=tbegin+1;end
   if(dut.u_t.write_valid&&dut.u_t.write_ready)begin if(dut.u_t.write_index>1||dut.u_t.write_data!==final_word(v,dut.u_t.write_index))$fatal(1,"FAIL_A16 Tfill");twrite=twrite+1;end
   if(dut.u_t.commit_valid&&dut.u_t.commit_ready)tcommit=tcommit+1;
   if(out_valid&&out_ready)begin if(out_index!=ttake-tt0||out_last!==(ttake-tt0==1)||out_data!==final_word(v,ttake-tt0))$fatal(1,"FAIL_A16 outputroworder");ttake=ttake+1;end
   if(dut.u_t.release_valid&&dut.u_t.release_ready)trelease=trelease+1;
  end
 end
 task automatic mark;input integer idx;begin cases=cases+1;$display("CASE_PASS %0s",case_name(idx));end endtask
 task automatic new_frame;input integer vec;integer k;
  begin @(negedge clk);if(busy||done_valid||input_stored||out_valid||!in_ready)$fatal(1,"FAIL_A16 staleframe");v=vec;frame_open=1;job=0;strict_native=1;frameacks=0;framereqs=0;load_completed=0;
   for(k=0;k<1024;k=k+1)written[k]=0;
   i0=ingress;q0=sreq;a0=sack;w0=writes;r0=reads;mc0=mcmd;mr0=mrsp;l0=loads;ld0=ldone;wd0=wide;ab0=abeats;bb0=bbeats;ns0=nsvc;nsr0=nsvc_rsp;nc0=ncmd;nr0=nrsp;e0=esvc;er0=esvc_rsp;tt0=ttake;tb0=tbegin;tw0=twrite;tc0=tcommit;tr0=trelease;st0=starts;
   in_valid=0;start_valid=0;out_ready=0;done_ready=0;
  end
 endtask
 task automatic send;input integer beat;begin @(negedge clk);in_valid=1;in_data=raw_input(v,beat);while(!in_ready)@(negedge clk);@(posedge clk);#1;if(!busy)$fatal(1,"FAIL_A16 notbusy");@(negedge clk);in_valid=0;end endtask
 task automatic fill;begin for(integer k=0;k<27;k=k+1)send(k);while(!input_stored)@(negedge clk);if(frameacks!=27)$fatal(1,"FAIL_A16 inputACK27");end endtask
 task automatic start_job;input held;begin @(negedge clk);if(!start_ready)$fatal(1,"FAIL_A16 notstartready");start_valid=1;@(posedge clk);#1;@(negedge clk);if(starts-st0!=1||start_ready)$fatal(1,"FAIL_A16 duplicateRUN");if(!held)start_valid=0;end endtask
 task automatic take_one;begin while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;end endtask
 task automatic take_all;begin take_one();take_one();end endtask
 task automatic finish;input error_expected,doneabort;integer beforetake;
  begin while(!done_valid)@(negedge clk);repeat(5)begin if(!done_valid||done_error!==error_expected||in_ready||start_ready||!busy)$fatal(1,"FAIL_A16 heldterminal");if(!error_expected&&done_saturated!==expected_sat(v))$fatal(1,"FAIL_A16 saturationOR");@(negedge clk);end
   if(!error_expected&&(ttake-tt0!=2||trelease-tr0!=1||dut.t_busy))$fatal(1,"FAIL_A16 DONEbeforeTreleased");
   beforetake=dtake;start_valid=0;done_ready=1;abort=doneabort;@(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;frame_open=0;job=0;repeat(3)@(negedge clk);
   if(dtake!=beforetake+1||busy||done_valid||input_stored||out_valid||!in_ready)$fatal(1,"FAIL_A16 terminalreuse");
  end
 endtask
 task automatic normal_counts;
  begin if(ingress-i0!=27||frameacks!=27||sreq-q0!=103||sack-a0!=103||writes-w0!=73||reads-r0!=30||pending)$fatal(1,"FAIL_A16 103S73W30R");
   if(mcmd-mc0!=42||mrsp-mr0!=42||loads-l0!=6||ldone-ld0!=6||wide-wd0!=14||abeats-ab0!=12||bbeats-bb0!=8)$fatal(1,"FAIL_A16 Mloadercounts");
   if(nsvc-ns0!=4||nsvc_rsp-nsr0!=4||ncmd-nc0!=20||nrsp-nr0!=20||esvc-e0!=6||esvc_rsp-er0!=6)$fatal(1,"FAIL_A16 NEcounts");
   if(tbegin-tb0!=1||twrite-tw0!=2||tcommit-tc0!=1||ttake-tt0!=2||trelease-tr0!=1)$fatal(1,"FAIL_A16 Tlifecycle");
   for(integer k=0;k<1024;k=k+1)if(written[k]!=expected_writes(v,k))$fatal(1,"FAIL_A16 writehistorycount%0d",k);
  end
 endtask
 task automatic run_normal;input integer vec;begin new_frame(vec);fill();start_job(0);take_all();finish(0,0);normal_counts();end endtask
 task automatic preabort;begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;in_valid=0;start_valid=0;frame_open=0;job=0;repeat(3)@(negedge clk);if(busy||done_valid||input_stored||!in_ready)$fatal(1,"FAIL_A16 preabortmadeDONE");end endtask
 task automatic hard_reset;begin @(negedge clk);reset=1;in_valid=0;start_valid=0;out_ready=0;done_ready=0;repeat(3)@(negedge clk);reset=0;frame_open=0;job=0;repeat(3)@(negedge clk);if(busy||done_valid||out_valid||input_stored||!in_ready)$fatal(1,"FAIL_A16 hardresetstale");end endtask
 integer k;
 initial begin
  repeat(4)@(negedge clk);reset=0;@(negedge clk);new_frame(0);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);start_valid=1;repeat(4)begin @(negedge clk);if(start_ready||input_stored||starts!=st0)$fatal(1,"FAIL_A16 earlyACKstart");end start_valid=0;release dut.permit_s_rsp;
  for(k=1;k<26;k=k+1)send(k);while(frameacks<26)@(negedge clk);force dut.permit_s_rsp=1'b0;send(26);start_valid=1;repeat(4)begin @(negedge clk);if(start_ready||input_stored||starts!=st0)$fatal(1,"FAIL_A16 lastcoefficientACKstart");end start_valid=0;release dut.permit_s_rsp;while(!input_stored)@(negedge clk);repeat(3)@(negedge clk);if(starts!=st0)$fatal(1,"FAIL_A16 earlypulsequeued");mark(0);
  start_job(1);take_all();finish(0,0);normal_counts();mark(1);for(k=1;k<10;k=k+1)begin run_normal(k);mark(k+1);end
  new_frame(0);for(k=0;k<26;k=k+1)send(k);while(frameacks<26)@(negedge clk);force dut.permit_s_rsp=1'b0;send(26);start_valid=1;repeat(4)@(negedge clk);release dut.permit_s_rsp;while(starts==st0)@(negedge clk);start_valid=0;take_all();finish(0,0);normal_counts();mark(11);
  new_frame(0);fill();force dut.permit_n_rsp=1'b0;start_job(0);while(!dut.n_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);force dut.permit_m_rsp=1'b0;release dut.permit_n_rsp;while(!dut.m_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);force dut.permit_load=1'b0;release dut.permit_m_rsp;wait(dut.state==7);repeat(5)@(negedge clk);force dut.permit_e_rsp=1'b0;release dut.permit_load;while(!dut.e_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);release dut.permit_e_rsp;take_all();finish(0,0);normal_counts();mark(12);
  new_frame(0);force dut.permit_s_req=1'b0;send(0);repeat(4)@(negedge clk);preabort();release dut.permit_s_req;run_normal(3);mark(13);
  new_frame(0);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);preabort();release dut.permit_s_rsp;run_normal(0);mark(14);
  new_frame(0);fill();preabort();run_normal(2);mark(15);
  new_frame(0);fill();force dut.permit_s_rsp=1'b0;start_job(0);while(!dut.s_valid)@(negedge clk);@(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;finish(1,0);run_normal(4);mark(16);
  new_frame(0);fill();start_job(0);take_one();@(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;if(ttake-tt0!=1)$fatal(1,"FAIL_A16 prefixrollback");finish(1,0);run_normal(0);mark(17);
  new_frame(5);fill();start_job(0);take_all();while(!done_valid)@(negedge clk);abort=1;repeat(3)begin @(negedge clk);if(!done_valid||done_error||!done_saturated)$fatal(1,"FAIL_A16 DONEabortflags");end abort=0;finish(0,1);normal_counts();mark(18);
  new_frame(0);send(0);send(1);hard_reset();run_normal(2);mark(19);
  new_frame(0);fill();force dut.permit_n_rsp=1'b0;start_job(0);while(!dut.n_rsp_valid)@(negedge clk);repeat(4)@(negedge clk);hard_reset();release dut.permit_n_rsp;run_normal(0);mark(20);
  new_frame(0);fill();start_job(0);while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();run_normal(7);mark(21);
  new_frame(0);fill();strict_native=0;start_job(0);wait(dut.n_cmd_valid&&dut.n_cmd_ready&&dut.n_cmd_op==1);@(negedge clk);force dut.n_cmd_op=4'd15;@(posedge clk);#1;@(negedge clk);release dut.n_cmd_op;finish(1,0);if(twrite!=tw0||loads!=l0)$fatal(1,"FAIL_A16 Nerrorescaped");run_normal(0);mark(22);
  new_frame(0);fill();strict_native=0;start_job(0);wait(dut.state==5&&dut.projection==3&&dut.m_phase==2);@(negedge clk);force dut.m_cmd_data=64'h1188f;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;finish(1,0);if(written[512]!=0||twrite!=tw0)$fatal(1,"FAIL_A16 QKerrorescaped");run_normal(3);mark(23);
  new_frame(0);fill();strict_native=0;start_job(0);wait(dut.state==5&&dut.projection==5&&dut.m_phase==2);@(negedge clk);force dut.m_cmd_data=64'h1188d;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;finish(1,0);if(written[528]!=0||twrite!=tw0)$fatal(1,"FAIL_A16 Woerrorescaped");run_normal(0);mark(24);
  new_frame(0);fill();strict_native=0;start_job(0);wait(dut.e_in_valid&&dut.e_in_ready&&dut.e_stage==0);@(negedge clk);force dut.e_in_op=4'd14;@(posedge clk);#1;@(negedge clk);release dut.e_in_op;finish(1,0);if(written[488]!=1||twrite!=tw0)$fatal(1,"FAIL_A16 RoPEerrorwrote");run_normal(7);mark(25);
  new_frame(0);fill();strict_native=0;start_job(0);wait(dut.e_in_valid&&dut.e_in_ready&&dut.e_stage==4);@(negedge clk);force dut.e_in_op=4'd14;@(posedge clk);#1;@(negedge clk);release dut.e_in_op;finish(1,0);if(written[528]!=0||twrite!=tw0)$fatal(1,"FAIL_A16 residualerrorwrote");run_normal(2);mark(26);
  new_frame(0);fill();start_job(0);wait(dut.h_rsp_valid&&dut.h_rsp_ready&&dut.owner==0);@(negedge clk);force dut.h_rsp_error=1'b1;@(posedge clk);#1;@(negedge clk);release dut.h_rsp_error;finish(1,0);if(twrite!=tw0)$fatal(1,"FAIL_A16 Serrorpublished");run_normal(0);mark(27);
  new_frame(0);fill();start_job(0);wait(dut.n_mem_req_valid&&dut.n_mem_req_write&&dut.n_mem_req_addr==517);force dut.permit_s_rsp=1'b0;while(!dut.s_valid)@(negedge clk);repeat(4)@(negedge clk);@(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;finish(1,0);run_normal(3);mark(28);
  new_frame(0);fill();force dut.permit_m_rsp=1'b0;start_job(0);while(!dut.m_rsp_valid)@(negedge clk);repeat(4)@(negedge clk);hard_reset();release dut.permit_m_rsp;run_normal(0);mark(29);
  $display("A16_STATS cycles=%0d input=%0d Sreq=%0d Sack=%0d Mcmd=%0d Mrsp=%0d Ncmd=%0d Nrsp=%0d Ttake=%0d",cycles,ingress,sreq,sack,mcmd,mrsp,ncmd,nrsp,ttake);$display("PASS_W4_A16 cases=%0d",cases);$finish;
 end
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();d=json.loads((a.directory/'a16-contract-vectors.json').read_text(encoding='utf-8'));vectors=d['vectors'];f=[]
    sets=[('input_word','input integer vec,beat;','vec*32+beat',[(v['index']*32+i,w) for v in vectors for i,w in enumerate(v['expected']['ingress_words_hex'])]),('write_word','input integer vec,address,occurrence;','vec*4096+address*2+occurrence',[(v['index']*4096+int(addr)*2+j,w) for v in vectors for addr,words in v['expected']['S_write_history_hex'].items() for j,w in enumerate(words)]),('final_word','input integer vec,row;','vec*2+row',[(v['index']*2+i,v['expected']['S_final_hex'][str(528+i)]) for v in vectors for i in range(2)])]
    from a16_integer_reference import pack
    sets.append(('m_carrier','input integer vec,projection,readindex;','vec*32+projection*4+readindex',[(v['index']*32+pr*4+rd,'%032x'%pack(v['expected']['M_outputs'][pr][rd//2][4*(rd%2):4*(rd%2)+4],32)) for v in vectors for pr in range(6) for rd in range(4)]))
    for name,args,index,items in sets:
        f+=['function automatic [127:0] '+name+';',args,'begin case('+index+')'];f+=[' {}:{}=128\'h{};'.format(k,name,w) for k,w in items];f+=[' default:'+name+"=128'hbad;endcase end endfunction"]
    f+=['function automatic integer expected_writes;input integer vec,address;begin case(vec*1024+address)'];f+=[' {}:expected_writes={};'.format(v['index']*1024+int(addr),len(ws)) for v in vectors for addr,ws in v['expected']['S_write_history_hex'].items()];f+=[' default:expected_writes=0;endcase end endfunction']
    f+=['function automatic expected_sat;input integer vec;begin case(vec)'];f+=[' {}:expected_sat={};'.format(v['index'],int(v['expected']['done_saturated'])) for v in vectors];f+=[' default:expected_sat=0;endcase end endfunction']
    f+=['function automatic [8*100-1:0] case_name;input integer index;begin case(index)'];f+=[' {}:case_name="{}";'.format(i,c) for i,c in enumerate(CASE_IDS)];f+=[' default:case_name="unknown";endcase end endfunction']
    tb='`timescale 1ns/1ps\n// Self-contained pure-math expected constants, not DUT outputs.\nmodule block_w4_a16_tb;\n'+'\n'.join(f)+'\n'+BODY+'\nendmodule\n';path=a.directory/'block_w4_a16_tb.sv';path.write_bytes(tb.encode('utf-8'))
    sources=['project/rtl/block_v2/'+n for n in ['block_v2_e.sv','block_v2_m.sv','block_v2_n.sv','block_v2_n_group.sv']]+['project/rtl/block_feed_v1/'+n for n in ['block_feed_loader.sv','block_feed_s16k.sv','block_feed_s_macro.sv']]+['project/rtl/block_v1/transaction6k.sv','project/rtl/block_connection_p2/block_p2_s_ctrl.sv','project/rtl/block_connection_w3/block_w3_e_ctrl.sv','project/rtl/block_connection_w4/block_w4_n_ctrl.sv','project/rtl/block_connection_w4/block_w4_a16_top.sv','project/tb/block_connection_w4/block_w4_a16_tb.sv']
    contract={'schema_version':1,'status':'FROZEN_BOUNDED_MATH_CASE_REQUIREMENTS_NOT_RTL_EXECUTION','top_module':'block_w4_a16_tb','pass_marker':'PASS_W4_A16','pass_line_regex':'^PASS_W4_A16 cases=30$','expected_case_ids':CASE_IDS,'expected_unique_case_count':30,'compile_sources':sources,'include_dirs':['project/rtl/block_v2','work/Melodydt/151'],'TB_includes':[],'tb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'vectors_path':'work/Melodydt/151/a16-contract-vectors.json','reference_dependencies':['work/Melodydt/151/a16_integer_reference.py'],'normal_counts':d['normal_counts'],'execution_policy':'rootserverVerilatoronly;no localRTLrun','scope':'H8,2tokencausal,head1,explicitadjacentpairRoPE;notmodelqualityorPPA'}
    (a.directory/'a16-tb-contract.json').write_bytes((json.dumps(contract,indent=2)+'\n').encode('utf-8'));print('Prepared A16 self-containedTB10vectors/30CASE;noRTLrun')

if __name__=='__main__':main()
