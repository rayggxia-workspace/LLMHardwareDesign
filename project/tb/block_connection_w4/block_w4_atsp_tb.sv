`timescale 1ns/1ps
// Real S/T/E residual-spool boundary. Wo is an external cut, not Attention.
module block_w4_atsp_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,job_valid=0,in_valid=0,start_valid=0,work_valid=0,work_rsp_ready=0;
 reg resume_valid=0,wo_valid=0,done_ready=0,out_ready=0;
 reg [31:0] job_generation=0,in_generation=0,wo_generation=0;
 reg [7:0] in_index=0,wo_index=0,work_addr=0;
 reg in_last=0,wo_last=0;
 reg [127:0] in_data=0,wo_data=0,work_data=0;
 wire job_ready,in_ready,input_stored,start_ready,busy,spool_saved,work_ready,work_rsp_valid,work_rsp_error;
 wire resume_ready,wo_ready,done_valid,done_error,done_saturated,done_partial,out_valid,out_last;
 wire [8:0] done_words;wire [31:0] done_generation,out_generation;
 wire [127:0] out_data;wire [9:0] out_index;
 block_w4_atsp_top dut(.*);
 reg [127:0] gold_x[0:2][0:255],gold_wo[0:2][0:255],gold_out[0:2][0:255];
 reg gold_sat[0:2];integer clip_elements[0:2];
 string vectors_dir,dump_dir,fixture_names[0:2];
 integer fd_x=0,fd_wo=0,fd_out=0;reg dump_enabled=0;
 integer cycles=0,cases=0,v=0,next_generation=4096;
 reg [31:0] active_generation=0;
 reg tracking=0,obligation=0,resumed=0,work_open=0,pending=0,pwrite;
 reg inject_meta=0,inject_e=0;
 reg [7:0] held_work_addr;reg [127:0] held_work_data;
 reg [9:0] paddr;reg [127:0] pdata,ram[0:1023];reg written[0:1023];
 integer jobs=0,starts=0,resumes=0,dtakes=0,ingress=0,wo_takes=0,sreq=0,sack=0,swrites=0,sreads=0;
 integer works=0,work_responses=0,ecommands=0,eresponses=0,enative=0,enative_rsp=0;
 integer begins=0,commits=0,twrites=0,ttakes=0,releases=0,hosttakes=0;
 integer j0,st0,res0,dt0,i0,wo0,q0,ack0,w0,r0,wk0,wr0,ec0,er0,en0,enr0,tb0,tc0,tw0,tt0,tr0,ht0;
 integer xgood=0,xacks=0,wogood=0,woacks=0,rawtakes=0,capacks=0,destacks=0;
 integer rawwrites=0,outwrites=0,rawreleased=0,outreleased=0,outcount=0,e_seq=-1;
 integer fault_sreq_before=0,fault_swrites_before=0;
 integer bad_x=0,bad_wo=0;reg work_error_expected=0;
 reg hold_done=0,hold_out=0,hold_work=0,hold_in=0,hold_wo=0,hold_raw=0;
 reg prev_de,prev_ds,prev_dp,prev_last,prev_work_error;
 reg [8:0] prev_words;reg [31:0] prev_dgen,prev_ogen;
 reg [9:0] prev_oi,prev_ri;reg [127:0] prev_out,prev_raw;
 reg [168:0] prev_in,prev_wo; // data128 + generation32 + index8 + last1

 function automatic integer tm;
  input integer interleaved;begin tm=(interleaved%2)*128+interleaved/2;end
 endfunction
 function automatic [127:0] add_word;
  input [127:0] a,b;integer lane;reg signed [16:0] sum;reg signed [15:0] aa,bb;begin
   add_word=0;
   for(lane=0;lane<8;lane=lane+1)begin
    aa=a[16*lane+:16];bb=b[16*lane+:16];sum={aa[15],aa}+{bb[15],bb};
    if(sum>32767)add_word[16*lane+:16]=16'h7fff;
    else if(sum< -32768)add_word[16*lane+:16]=16'h8000;
    else add_word[16*lane+:16]=sum[15:0];
   end
  end
 endfunction
 function automatic [127:0] expected_write;
  input integer addr;begin
   if(dut.owner==1)begin
    if(e_seq<0||addr!=(e_seq%2==0?e_seq/2:384+e_seq/2))$fatal(1,"FAIL_ATSP E destination association");
    expected_write=gold_out[v][tm(e_seq)];
   end else if(work_open)begin
    if(addr!=held_work_addr)$fatal(1,"FAIL_ATSP wrongworkaddress");expected_write=held_work_data;
   end else if(addr<256&&starts==st0)expected_write=gold_x[v][addr];
   else if(addr==256||addr==257)begin
    if(addr!=256+(woacks%2)||wogood!=woacks+1)$fatal(1,"FAIL_ATSP Wo capture/ACK association");
    expected_write=gold_wo[v][tm(woacks)];
   end else if(addr==258)begin
    if(rawtakes!=capacks+1)$fatal(1,"FAIL_ATSP raw holding capture association");expected_write=gold_x[v][tm(capacks)];
   end else begin $fatal(1,"FAIL_ATSP unexpectedSwrite addr=%0d",addr);expected_write=0;end
  end
 endfunction
 task automatic bytes_out;input integer fd;input [127:0] data;begin
  for(integer k=0;k<16;k=k+1)$fwrite(fd,"%c",data[8*k+:8]);
 end endtask

 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>1500000)$fatal(1,"FAIL_ATSP watchdog state=%0d",dut.state);
  if(reset)begin pending=0;hold_done=0;hold_out=0;hold_work=0;hold_in=0;hold_wo=0;hold_raw=0;end
  else begin
   if(hold_done&&(!done_valid||done_error!==prev_de||done_saturated!==prev_ds||done_partial!==prev_dp||done_words!==prev_words||done_generation!==prev_dgen))$fatal(1,"FAIL_ATSP heldDONE");
   hold_done=done_valid&&!done_ready;prev_de=done_error;prev_ds=done_saturated;prev_dp=done_partial;prev_words=done_words;prev_dgen=done_generation;
   if(!dut.leaf_reset)begin
    if(hold_out&&!inject_meta&&(!out_valid||out_data!==prev_out||out_index!==prev_oi||out_last!==prev_last||out_generation!==prev_ogen))$fatal(1,"FAIL_ATSP heldoutput");
    if(hold_work&&(!work_rsp_valid||work_rsp_error!==prev_work_error))$fatal(1,"FAIL_ATSP heldworkresponse");
    if(hold_in&&(!in_valid||{in_data,in_generation,in_index,in_last}!==prev_in))$fatal(1,"FAIL_ATSP heldXoffer");
    if(hold_wo&&(!wo_valid||{wo_data,wo_generation,wo_index,wo_last}!==prev_wo))$fatal(1,"FAIL_ATSP heldWooffer");
    if(hold_raw&&!inject_meta&&(dut.t_read_data!==prev_raw||dut.t_read_index!==prev_ri))$fatal(1,"FAIL_ATSP rawT holding changed withouttake");
    hold_out=out_valid&&!out_ready&&!inject_meta;prev_out=out_data;prev_oi=out_index;prev_last=out_last;prev_ogen=out_generation;
    hold_work=work_rsp_valid&&!work_rsp_ready;prev_work_error=work_rsp_error;
    hold_in=in_valid&&!in_ready;prev_in={in_data,in_generation,in_index,in_last};
    hold_wo=wo_valid&&!wo_ready;prev_wo={wo_data,wo_generation,wo_index,wo_last};
    hold_raw=tracking&&dut.t_owner==1&&dut.t_read_valid&&!dut.t_read_take&&!inject_meta;prev_raw=dut.t_read_data;prev_ri=dut.t_read_index;
   end else begin pending=0;hold_out=0;hold_work=0;hold_in=0;hold_wo=0;hold_raw=0;end
   if(job_valid&&job_ready)begin
    if(obligation)$fatal(1,"FAIL_ATSP acceptedsecondjob");active_generation=job_generation;obligation=1;jobs=jobs+1;
   end
   if(done_valid&&done_ready)begin
    if(!obligation||done_generation!==active_generation)$fatal(1,"FAIL_ATSP completionwithoutobligation");dtakes=dtakes+1;obligation=0;
   end
   if(tracking&&!dut.leaf_reset)begin
    if(in_valid&&in_ready)begin
     ingress=ingress+1;
     if(in_generation==active_generation&&in_index==xgood&&in_last==(xgood==255))begin
      if(in_data!==gold_x[v][xgood])$fatal(1,"FAIL_ATSP actualXpayload");xgood=xgood+1;
      if(dump_enabled)bytes_out(fd_x,in_data);
     end else bad_x=bad_x+1;
    end
    if(start_valid&&start_ready)begin if(xacks!=256||xgood!=256)$fatal(1,"FAIL_ATSP startbefore256ACK");starts=starts+1;end
    if(work_valid&&work_ready)begin
     if(!spool_saved||resumed||work_open)$fatal(1,"FAIL_ATSP work outsideheadhold");
     work_open=1;held_work_addr=work_addr;held_work_data=work_data;works=works+1;
    end
    if(work_rsp_valid&&work_rsp_ready)begin
     if(!work_open||work_rsp_error!==work_error_expected)$fatal(1,"FAIL_ATSP workcompletion");work_responses=work_responses+1;work_open=0;
    end
    if(resume_valid&&resume_ready)begin
     if(work_open||work_valid||!spool_saved)$fatal(1,"FAIL_ATSP resume cut pendingwork");resumed=1;resumes=resumes+1;
    end
    if(wo_valid&&wo_ready)begin
     wo_takes=wo_takes+1;
     if(wo_generation==active_generation&&wo_index==wogood&&wo_last==(wogood==255))begin
      if(wo_data!==gold_wo[v][tm(wogood)])$fatal(1,"FAIL_ATSP Wo cutpayload/interleaving");wogood=wogood+1;
      if(dump_enabled)bytes_out(fd_wo,wo_data);
     end else bad_wo=bad_wo+1;
    end
    if(dut.s_req&&dut.s_ready)begin
     if(pending)$fatal(1,"FAIL_ATSP sharedS overlappingtransaction");
     pending=1;pwrite=dut.s_we;paddr=dut.s_addr;pdata=dut.s_din;sreq=sreq+1;
     if(dut.s_we)begin
      if(dut.s_din!==expected_write(dut.s_addr))$fatal(1,"FAIL_ATSP Swrite addr=%0d data=%032h",dut.s_addr,dut.s_din);swrites=swrites+1;
     end else sreads=sreads+1;
    end
    if(dut.s_valid&&dut.s_take)begin
     if(!pending)$fatal(1,"FAIL_ATSP unexpectedSACK");sack=sack+1;
     if(pwrite)begin
      ram[paddr]=pdata;written[paddr]=1;
      if(dut.owner==1)destacks=destacks+1;
      else if(work_open)begin end
      else if(starts==st0&&paddr<256)xacks=xacks+1;
      else if(paddr==256||paddr==257)woacks=woacks+1;
      else if(paddr==258)capacks=capacks+1;
     end else if(!written[paddr]||dut.s_dout!==ram[paddr])$fatal(1,"FAIL_ATSP Sread beforeACK/wrongversion addr=%0d",paddr);
     pending=0;
    end
    if(dut.e_req_valid&&dut.e_req_ready)begin
     if(dut.owner!=1||rawtakes!=capacks||rawtakes!=ecommands-ec0+1||woacks<2*((rawtakes-1)/2+1))$fatal(1,"FAIL_ATSP E before rawcapture/pairACK");
     e_seq=rawtakes-1;
     if(dut.u_e_ctrl.req_src_a!=256+e_seq%2||dut.u_e_ctrl.req_src_b!=258||dut.u_e_ctrl.req_dst!=(e_seq%2==0?e_seq/2:384+e_seq/2))$fatal(1,"FAIL_ATSP E operand/destination routing");
     ecommands=ecommands+1;
    end
    if(dut.e_rsp_valid&&dut.e_rsp_ready)eresponses=eresponses+1;
    if(dut.e_in_valid&&dut.e_in_ready)begin
     if(dut.e_in_a!==gold_wo[v][tm(e_seq)]||dut.e_in_b!==gold_x[v][tm(e_seq)])$fatal(1,"FAIL_ATSP native E operands");
     if(!inject_e&&(dut.e_in_op!=0||dut.e_in_shift!=0))$fatal(1,"FAIL_ATSP native E operation");enative=enative+1;
    end
    if(dut.e_out_valid&&dut.e_out_ready)enative_rsp=enative_rsp+1;
    if(dut.t_begin_valid&&dut.t_begin_ready)begin
     if(dut.u_t.begin_generation!==active_generation||dut.u_t.begin_words!=256)$fatal(1,"FAIL_ATSP T begin identity/count");
     if(dut.u_t.begin_owner==1)begin if(begins-tb0!=0||xacks!=256)$fatal(1,"FAIL_ATSP raw begin order");end
     else if(dut.u_t.begin_owner==2)begin if(rawreleased!=1||destacks!=256||capacks!=256)$fatal(1,"FAIL_ATSP output begin before finalACK/release");end
     else $fatal(1,"FAIL_ATSP T lease owner");begins=begins+1;
    end
    if(dut.t_write_valid&&dut.t_write_ready)begin
     if(dut.t_owner==1)begin
      if(dut.t_write_index!=rawwrites||dut.held_data!==gold_x[v][tm(rawwrites)])$fatal(1,"FAIL_ATSP raw spool ordering/data");rawwrites=rawwrites+1;
     end else if(dut.t_owner==2)begin
      if(dut.t_write_index!=outwrites||dut.held_data!==gold_out[v][outwrites])$fatal(1,"FAIL_ATSP tokenmajor outputpack");outwrites=outwrites+1;
     end else $fatal(1,"FAIL_ATSP Twrite withoutlease");twrites=twrites+1;
    end
    if(dut.t_commit_valid&&dut.t_commit_ready)begin
     if(dut.t_owner==1&&rawwrites!=256)$fatal(1,"FAIL_ATSP raw commit short");
     if(dut.t_owner==2&&outwrites!=256)$fatal(1,"FAIL_ATSP output commit short");commits=commits+1;
    end
    if(dut.t_read_valid&&dut.t_read_take)begin
     if(dut.t_owner==1)begin
      if(!resumed||rawtakes>=256||dut.t_generation!==active_generation||dut.t_word_count!=256||dut.t_read_index!=rawtakes||dut.t_read_last!==(rawtakes==255)||dut.t_read_data!==gold_x[v][tm(rawtakes)]||destacks!=rawtakes||woacks<2*(rawtakes/2+1))$fatal(1,"FAIL_ATSP raw replay identity/data/lifetime");rawtakes=rawtakes+1;
     end else if(dut.t_owner!=2)$fatal(1,"FAIL_ATSP invalidTtakeowner");ttakes=ttakes+1;
    end
    if(out_valid&&out_ready)begin
     if(!resumed||rawreleased!=1||outcount>=256||out_index!=outcount||out_last!==(outcount==255)||out_generation!==active_generation||out_data!==gold_out[v][outcount])$fatal(1,"FAIL_ATSP host output order/value/gen");
     if(dump_enabled)bytes_out(fd_out,out_data);outcount=outcount+1;hosttakes=hosttakes+1;
    end
    if(dut.t_release_valid&&dut.t_release_ready)begin
     if(dut.t_owner==1)begin
      if(rawtakes!=256||capacks!=256||destacks!=256||eresponses-er0!=256)$fatal(1,"FAIL_ATSP rawrelease before allfinalACK");rawreleased=rawreleased+1;
     end else if(dut.t_owner==2)begin if(outcount!=256)$fatal(1,"FAIL_ATSP outputrelease beforehostdone");outreleased=outreleased+1;end
     else $fatal(1,"FAIL_ATSP releasewrongowner");releases=releases+1;
    end
    if(spool_saved&&!resumed&&dut.t_read_take)$fatal(1,"FAIL_ATSP rawtake duringheadhold");
    if(work_valid&&dut.state==11&&resume_ready)$fatal(1,"FAIL_ATSP work/resume priority");
   end
  end
 end

 task automatic mark;input integer n;begin cases=cases+1;$display("CASE_PASS %0s",case_name(n));end endtask
 function automatic [639:0] case_name;input integer n;begin case(n)
  0:case_name="ATSP_IDLE_ABORT_NO_OBLIGATION";
  1:case_name="ATSP_JOB_INPUT256_LASTACK_START_GATE";
  2:case_name="ATSP_PLAIN_FULL_S_OVERWRITE_T_PRESERVES_RAW";
  3:case_name="ATSP_DENSE_NORMAL_NO_RESET_REUSE";
  4:case_name="ATSP_SATURATION_OUTPUT_STALL_DONE_ABORT_READY";
  5:case_name="ATSP_HEAD_HOLD_NO_TAKE_DUPLICATE_BEGIN_BLOCKED";
  6:case_name="ATSP_WORK_REAL_ACK_RESPONSE_HOLD_RESUME_PRIORITY";
  7:case_name="ATSP_WO_CAPTURE_ACK_BACKPRESSURE";
  8:case_name="ATSP_E_RESPONSE_HOLD_AFTER_DESTINATION_ACK";
  9:case_name="ATSP_ABORT_ADMITTED_BEFORE_X";
  10:case_name="ATSP_ABORT_PARTIAL_INPUT_OBLIGATION";
  11:case_name="ATSP_ABORT_STORED_BEFORE_RUN";
  12:case_name="ATSP_ABORT_RAW_T_FILL";
  13:case_name="ATSP_ABORT_RAW_CAPTURE_ACK_PENDING";
  14:case_name="ATSP_ABORT_AFTER_HOST_OUTPUT_PREFIX";
  15:case_name="ATSP_RESET_PARTIAL_INPUT";
  16:case_name="ATSP_RESET_RAW_HEAD_HOLD";
  17:case_name="ATSP_RESET_COMMITTED_OUTPUT_STALL";
  18:case_name="ATSP_INPUT_S_HELPER_ERROR_TERMINAL";
  19:case_name="ATSP_WORK_ERROR_RESPONSE_HOLD_THEN_TERMINAL";
  20:case_name="ATSP_RAW_CAPTURE_S_ERROR_NO_E";
  21:case_name="ATSP_NATIVE_E_ERROR_NO_DESTINATION_WRITE";
  22:case_name="ATSP_WO_BAD_INDEX_NO_S_WRITE";
  23:case_name="ATSP_WO_BAD_LAST_NO_S_WRITE";
  24:case_name="ATSP_WO_BAD_GENERATION_NO_S_WRITE";
  25:case_name="ATSP_RAW_T_BAD_METADATA_NO_TAKE";
  26:case_name="ATSP_OUTPUT_T_BAD_METADATA_NO_PUBLICATION";
  27:case_name="ATSP_X_BAD_INDEX_AND_LAST_NO_S_WRITE";
  28:case_name="ATSP_STALE_X_AFTER_CANCEL_NEW_ADMISSION";
  29:case_name="ATSP_FINAL_NORMAL_RECOVERY_WITHOUT_RESET";
  default:case_name="INVALID";endcase end endfunction
 task automatic load_hex;input string path;input integer which,kind;integer fd,k,ret;reg [127:0] word;begin
  fd=$fopen(path,"r");if(fd==0)$fatal(1,"FAIL_ATSP missinggolden %s",path);
  for(k=0;k<256;k=k+1)begin ret=$fscanf(fd,"%h",word);if(ret!=1)$fatal(1,"FAIL_ATSP malformedgolden %s",path);
   if(kind==0)gold_x[which][k]=word;else if(kind==1)gold_wo[which][k]=word;else gold_out[which][k]=word;
  end
  ret=$fscanf(fd,"%h",word);if(ret!=-1)$fatal(1,"FAIL_ATSP goldentail %s",path);$fclose(fd);
 end endtask
 task automatic new_job;input integer which;input dumping;begin
  if(obligation||busy||done_valid||!job_ready)$fatal(1,"FAIL_ATSP newjob whenleased");v=which;tracking=1;resumed=0;work_open=0;pending=0;
  xgood=0;xacks=0;wogood=0;woacks=0;rawtakes=0;capacks=0;destacks=0;rawwrites=0;outwrites=0;rawreleased=0;outreleased=0;outcount=0;e_seq=-1;bad_x=0;bad_wo=0;work_error_expected=0;inject_meta=0;inject_e=0;
  for(integer k=0;k<1024;k=k+1)written[k]=0;
  j0=jobs;st0=starts;res0=resumes;dt0=dtakes;i0=ingress;wo0=wo_takes;q0=sreq;ack0=sack;w0=swrites;r0=sreads;wk0=works;wr0=work_responses;ec0=ecommands;er0=eresponses;en0=enative;enr0=enative_rsp;tb0=begins;tc0=commits;tw0=twrites;tt0=ttakes;tr0=releases;ht0=hosttakes;
  dump_enabled=dumping;
  if(dumping)begin
   fd_x=$fopen({dump_dir,"/",fixture_names[v],"-accepted-x.bin"},"wb");fd_wo=$fopen({dump_dir,"/",fixture_names[v],"-accepted-wo.bin"},"wb");fd_out=$fopen({dump_dir,"/",fixture_names[v],"-output.bin"},"wb");
   if(fd_x==0||fd_wo==0||fd_out==0)$fatal(1,"FAIL_ATSP actualdumpopen");
  end
  @(negedge clk);next_generation=next_generation+1;job_generation=next_generation;job_valid=1;
  while(!job_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);job_valid=0;
  if(jobs-j0!=1||!busy||!in_ready)$fatal(1,"FAIL_ATSP admission notcaptured");
 end endtask
 task automatic send_x;input integer index,fault;begin
  @(negedge clk);in_valid=1;in_data=gold_x[v][index];in_generation=fault==3?active_generation-32'd1:active_generation;
  in_index=fault==1?index+1:index;in_last=fault==2?1'b1:index==255;
  while(!in_ready)begin if(done_valid)$fatal(1,"FAIL_ATSP Xdriver afterterminal");@(negedge clk);end
  @(posedge clk);#1;@(negedge clk);in_valid=0;
 end endtask
 task automatic fill_x;begin for(integer k=0;k<256;k=k+1)send_x(k,0);while(!input_stored)@(negedge clk);if(xacks!=256||!start_ready)$fatal(1,"FAIL_ATSP storedwithoutallACK");end endtask
 task automatic start_spool;begin @(negedge clk);start_valid=1;while(!start_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);start_valid=0;end endtask
 task automatic wait_hold;begin while(!spool_saved||dut.state!=11)begin if(done_valid)$fatal(1,"FAIL_ATSP earlyterminal waitinghold");@(negedge clk);end if(rawwrites!=256||rawtakes!=0||!dut.t_read_valid||dut.t_begin_ready)$fatal(1,"FAIL_ATSP rawlease notheld");end endtask
 task automatic to_hold;begin fill_x();start_spool();wait_hold();end endtask
 task automatic resume_job;begin @(negedge clk);resume_valid=1;while(!resume_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);resume_valid=0;end endtask
 task automatic send_wo;input integer seq,fault;begin
  @(negedge clk);wo_valid=1;wo_data=gold_wo[v][tm(seq)];wo_generation=fault==3?active_generation-32'd1:active_generation;
  wo_index=fault==1?seq+1:seq;wo_last=fault==2?1'b1:seq==255;
  while(!wo_ready)begin if(done_valid)$fatal(1,"FAIL_ATSP Wodriver afterterminal");@(negedge clk);end
  @(posedge clk);#1;@(negedge clk);wo_valid=0;
 end endtask
 task automatic feed_all_wo;begin for(integer k=0;k<256;k=k+1)send_wo(k,0);end endtask
 task automatic write_work;input integer addr;begin
  @(negedge clk);work_valid=1;work_addr=addr;work_data=~gold_x[v][addr];while(!work_ready)@(negedge clk);
  @(posedge clk);#1;@(negedge clk);work_valid=0;work_rsp_ready=1;while(!work_rsp_valid)@(negedge clk);
  @(posedge clk);#1;@(negedge clk);work_rsp_ready=0;
 end endtask
 task automatic overwrite_all;begin
  for(integer k=0;k<256;k=k+1)write_work(k);
  for(integer k=0;k<256;k=k+1)if(ram[k]!==~gold_x[v][k])$fatal(1,"FAIL_ATSP realSoverwrite proof");
  if(rawtakes!=0||dut.t_read_data!==gold_x[v][0])$fatal(1,"FAIL_ATSP T didnotpreserveoverwrittenX");
 end endtask
 task automatic take_output;begin
  while(!out_valid)begin if(done_valid)$fatal(1,"FAIL_ATSP nooutputbeforeDONE");@(negedge clk);end
  repeat(7)@(negedge clk);out_ready=1;
  while(outcount<256)begin @(negedge clk);if(outcount==128)begin out_ready=0;repeat(7)@(negedge clk);out_ready=1;end end
  out_ready=0;
 end endtask
 task automatic finish;input expected_error,abort_ready;integer done_takes_before;begin
  while(!done_valid)@(negedge clk);
  if(done_error!==expected_error||done_words!==outcount||done_partial!==(expected_error&&outcount!=0)||done_generation!==active_generation)$fatal(1,"FAIL_ATSP terminalflags/words/generation");
  if(!expected_error&&(done_saturated!==gold_sat[v]||outcount!=256||rawreleased!=1||outreleased!=1))$fatal(1,"FAIL_ATSP successbeforeactualRELEASE");
  @(negedge clk);job_valid=1;job_generation=active_generation+32'd777;
  repeat(5)begin @(negedge clk);if(!done_valid||!busy||job_ready||in_ready||start_ready)$fatal(1,"FAIL_ATSP heldterminal admission");end
  job_valid=0;done_takes_before=dtakes;done_ready=1;abort=abort_ready;
  @(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;
  if(dtakes!=done_takes_before+1)$fatal(1,"FAIL_ATSP terminal notexactlyonce");
  tracking=0;work_open=0;resumed=0;
  if(dump_enabled)begin $fclose(fd_x);$fclose(fd_wo);$fclose(fd_out);fd_x=0;fd_wo=0;fd_out=0;dump_enabled=0;end
  repeat(3)@(negedge clk);if(obligation||busy||done_valid||!job_ready)$fatal(1,"FAIL_ATSP cleanreuse");
 end endtask
 task automatic counts;input integer work_count;begin
  if(jobs-j0!=1||starts-st0!=1||resumes-res0!=1||ingress-i0!=256||wo_takes-wo0!=256||works-wk0!=work_count||work_responses-wr0!=work_count)$fatal(1,"FAIL_ATSP publiccounts");
  if(sreq-q0!=2048+work_count||sack-ack0!=2048+work_count||swrites-w0!=1024+work_count||sreads-r0!=1024||pending)$fatal(1,"FAIL_ATSP SACKcounts");
  if(ecommands-ec0!=256||eresponses-er0!=256||enative-en0!=256||enative_rsp-enr0!=256||destacks!=256||capacks!=256||woacks!=256)$fatal(1,"FAIL_ATSP E/capturecounts");
  if(begins-tb0!=2||commits-tc0!=2||twrites-tw0!=512||ttakes-tt0!=512||releases-tr0!=2||hosttakes-ht0!=256||dtakes-dt0!=1)$fatal(1,"FAIL_ATSP Tleasecounts");
 end endtask
 task automatic normal;input integer which,work_count;input dumping,abort_ready;begin new_job(which,dumping);to_hold();if(work_count==256)overwrite_all();resume_job();feed_all_wo();take_output();finish(0,abort_ready);counts(work_count);end endtask
 task automatic pulse_abort;begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;job_valid=0;in_valid=0;start_valid=0;wo_valid=0;work_valid=0;work_rsp_ready=0;resume_valid=0;out_ready=0;end endtask
 task automatic hard_reset;begin
  @(negedge clk);reset=1;job_valid=0;in_valid=0;start_valid=0;wo_valid=0;work_valid=0;work_rsp_ready=0;resume_valid=0;out_ready=0;done_ready=0;
  repeat(3)@(negedge clk);reset=0;obligation=0;tracking=0;work_open=0;resumed=0;
  repeat(3)@(negedge clk);if(busy||done_valid||out_valid||!job_ready)$fatal(1,"FAIL_ATSP coordinatedreset");
 end endtask

 // Initial CASE sequence below. All source data comes from independent files.
 integer fd,ret,k,lane,fixture;reg signed [15:0] ax,bx;integer sum,clipcount;
 initial begin
  if(!$value$plusargs("vectors=%s",vectors_dir))$fatal(1,"FAIL_ATSP +vectors required");
  if(!$value$plusargs("dump_dir=%s",dump_dir))$fatal(1,"FAIL_ATSP +dump_dir required");
  fixture_names[0]="plain";fixture_names[1]="dense";fixture_names[2]="saturation";
  gold_sat[0]=0;gold_sat[1]=0;gold_sat[2]=1;
  for(fixture=0;fixture<3;fixture=fixture+1)begin
   load_hex({vectors_dir,"/",fixture_names[fixture],"/x.hex"},fixture,0);load_hex({vectors_dir,"/",fixture_names[fixture],"/wo.hex"},fixture,1);load_hex({vectors_dir,"/",fixture_names[fixture],"/expected-output.hex"},fixture,2);
   clipcount=0;
   for(k=0;k<256;k=k+1)begin
    if(add_word(gold_x[fixture][k],gold_wo[fixture][k])!==gold_out[fixture][k])$fatal(1,"FAIL_ATSP independent signedadd golden");
    for(lane=0;lane<8;lane=lane+1)begin ax=gold_x[fixture][k][16*lane+:16];bx=gold_wo[fixture][k][16*lane+:16];sum=ax+bx;if(sum>32767||sum< -32768)clipcount=clipcount+1;end
   end
   clip_elements[fixture]=clipcount;if((clipcount!=0)!==gold_sat[fixture])$fatal(1,"FAIL_ATSP golden saturationfact");
  end
  repeat(4)@(negedge clk);reset=0;repeat(3)@(negedge clk);
  pulse_abort();repeat(3)@(negedge clk);if(done_valid||busy||!job_ready)$fatal(1,"FAIL_ATSP idleabort createdobligation");mark(0);
  new_job(0,1);for(k=0;k<255;k=k+1)send_x(k,0);while(xacks<255)@(negedge clk);
  force dut.permit_s_rsp=1'b0;send_x(255,0);start_valid=1;repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0)$fatal(1,"FAIL_ATSP lastACKgate");end
  start_valid=0;release dut.permit_s_rsp;while(!input_stored)@(negedge clk);mark(1);
  start_spool();wait_hold();overwrite_all();resume_job();feed_all_wo();take_output();finish(0,0);counts(256);mark(2);
  normal(1,0,1,0);mark(3);normal(2,0,1,1);mark(4);
  new_job(0,0);to_hold();force dut.u_t.begin_valid=1'b1;repeat(6)begin @(negedge clk);if(dut.t_begin_ready||rawtakes||dut.t_read_data!==gold_x[v][0])$fatal(1,"FAIL_ATSP leasedT acceptedbegin/take");end
  release dut.u_t.begin_valid;pulse_abort();finish(1,0);mark(5);
  new_job(0,0);to_hold();force dut.permit_s_rsp=1'b0;
  @(negedge clk);resume_valid=1;work_valid=1;work_addr=0;work_data=~gold_x[v][0];
  #1;if(resume_ready||!work_ready)$fatal(1,"FAIL_ATSP workpriority");@(posedge clk);#1;@(negedge clk);work_valid=0;
  while(!dut.s_valid)@(negedge clk);repeat(5)begin @(negedge clk);if(work_rsp_valid||resume_ready||rawtakes)$fatal(1,"FAIL_ATSP workACKgate");end
  release dut.permit_s_rsp;while(!work_rsp_valid)@(negedge clk);repeat(5)begin @(negedge clk);if(resume_ready||rawtakes||work_rsp_error)$fatal(1,"FAIL_ATSP workresponsehold");end
  work_rsp_ready=1;@(posedge clk);#1;@(negedge clk);work_rsp_ready=0;resume_valid=0;pulse_abort();finish(1,0);mark(6);
  new_job(0,0);to_hold();resume_job();force dut.permit_s_rsp=1'b0;send_wo(0,0);
  while(!dut.s_valid)@(negedge clk);@(negedge clk);wo_valid=1;wo_generation=active_generation;wo_index=1;wo_last=0;wo_data=gold_wo[v][128];
  repeat(6)begin @(negedge clk);if(wo_ready||rawtakes||wogood!=1)$fatal(1,"FAIL_ATSP WoACKgate");end
  release dut.permit_s_rsp;while(!wo_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);wo_valid=0;pulse_abort();finish(1,0);mark(7);
  new_job(0,0);to_hold();resume_job();force dut.permit_e_rsp=1'b0;send_wo(0,0);send_wo(1,0);
  while(!dut.e_rsp_valid)@(negedge clk);repeat(7)begin @(negedge clk);if(rawtakes!=1||capacks!=1||destacks!=1||eresponses!=er0)$fatal(1,"FAIL_ATSP E responseACKhold");end
  pulse_abort();release dut.permit_e_rsp;finish(1,0);mark(8);
  new_job(0,0);pulse_abort();finish(1,0);mark(9);
  new_job(0,0);send_x(0,0);send_x(1,0);pulse_abort();finish(1,0);mark(10);
  new_job(0,0);fill_x();pulse_abort();finish(1,0);mark(11);
  new_job(0,0);fill_x();force dut.permit_t_write=1'b0;start_spool();while(dut.state!=8)@(negedge clk);pulse_abort();release dut.permit_t_write;finish(1,0);mark(12);
  new_job(0,0);to_hold();resume_job();send_wo(0,0);send_wo(1,0);while(dut.state!=19)@(negedge clk);force dut.permit_s_rsp=1'b0;
  while(!dut.s_valid)@(negedge clk);repeat(4)@(negedge clk);if(capacks!=0||rawtakes!=1||ecommands!=ec0)$fatal(1,"FAIL_ATSP captureACKgate");
  pulse_abort();release dut.permit_s_rsp;finish(1,0);mark(13);
  new_job(0,0);to_hold();resume_job();feed_all_wo();while(!out_valid)@(negedge clk);out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;
  pulse_abort();finish(1,0);if(outcount!=1||hosttakes-ht0!=1)$fatal(1,"FAIL_ATSP prefixrollback");mark(14);
  new_job(0,0);send_x(0,0);hard_reset();mark(15);
  new_job(0,0);to_hold();hard_reset();mark(16);
  new_job(0,0);to_hold();resume_job();feed_all_wo();while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();mark(17);
  new_job(0,0);send_x(0,0);@(negedge clk);while(!(dut.h_rsp_valid&&dut.h_rsp_ready))@(negedge clk);
  force dut.h_rsp_error=1'b1;@(posedge clk);#1;@(negedge clk);release dut.h_rsp_error;finish(1,0);mark(18);
  new_job(0,0);to_hold();work_error_expected=1;@(negedge clk);work_valid=1;work_addr=0;work_data=~gold_x[v][0];
  @(posedge clk);#1;@(negedge clk);work_valid=0;while(!(dut.h_rsp_valid&&dut.h_rsp_ready))@(negedge clk);
  force dut.h_rsp_error=1'b1;@(posedge clk);#1;@(negedge clk);release dut.h_rsp_error;
  while(!work_rsp_valid)@(negedge clk);repeat(5)begin @(negedge clk);if(!work_rsp_error||done_valid)$fatal(1,"FAIL_ATSP workerrorresponse disappeared");end
  work_rsp_ready=1;@(posedge clk);#1;@(negedge clk);work_rsp_ready=0;finish(1,0);mark(19);
  new_job(0,0);to_hold();resume_job();send_wo(0,0);send_wo(1,0);while(dut.state!=20)@(negedge clk);
  while(!(dut.h_rsp_valid&&dut.h_rsp_ready))@(negedge clk);force dut.h_rsp_error=1'b1;@(posedge clk);#1;@(negedge clk);release dut.h_rsp_error;
  finish(1,0);if(ecommands!=ec0)$fatal(1,"FAIL_ATSP captureerror issuedE");mark(20);
  new_job(0,0);to_hold();resume_job();send_wo(0,0);send_wo(1,0);@(negedge clk);while(!(dut.e_in_valid&&dut.e_in_ready))@(negedge clk);
  fault_swrites_before=swrites;inject_e=1;force dut.e_in_op=4'd14;@(posedge clk);#1;@(negedge clk);release dut.e_in_op;finish(1,0);
  if(destacks!=0||outcount!=0||swrites!=fault_swrites_before)$fatal(1,"FAIL_ATSP Eerror wrote result");mark(21);
  for(k=1;k<=3;k=k+1)begin
   new_job(0,0);to_hold();resume_job();fault_sreq_before=sreq;fault_swrites_before=swrites;send_wo(0,k);finish(1,0);
   if(woacks||rawtakes||bad_wo!=1||sreq!=fault_sreq_before||swrites!=fault_swrites_before)$fatal(1,"FAIL_ATSP rejectedWo sideeffect");mark(21+k);
  end
  new_job(0,0);to_hold();inject_meta=1;force dut.t_read_index=10'd1;
  @(posedge clk);#1;@(negedge clk);release dut.t_read_index;finish(1,0);if(rawtakes)$fatal(1,"FAIL_ATSP badrawmeta taken");mark(25);
  new_job(0,0);to_hold();resume_job();feed_all_wo();while(!out_valid)@(negedge clk);inject_meta=1;hold_out=0;force dut.t_read_index=10'd1;out_ready=1;
  @(posedge clk);#1;@(negedge clk);out_ready=0;release dut.t_read_index;finish(1,0);if(outcount)$fatal(1,"FAIL_ATSP badoutmeta published");mark(26);
  new_job(0,0);send_x(0,1);finish(1,0);if(xacks||bad_x!=1||sreq!=q0||swrites!=w0)$fatal(1,"FAIL_ATSP badXindex wroteS");
  new_job(0,0);send_x(0,2);finish(1,0);if(xacks||bad_x!=1||sreq!=q0||swrites!=w0)$fatal(1,"FAIL_ATSP badXlast wroteS");mark(27);
  new_job(0,0);send_x(0,0);pulse_abort();finish(1,0);
  new_job(0,0);send_x(0,3);finish(1,0);if(xacks||bad_x!=1||sreq!=q0||swrites!=w0)$fatal(1,"FAIL_ATSP staleX contaminatednewjob");mark(28);
  normal(1,0,0,0);mark(29);
  if(cases!=30)$fatal(1,"FAIL_ATSP CASEcount");
  $display("ATSP_STATS cycles=%0d jobs=%0d X=%0d Wo=%0d Sreq=%0d Sack=%0d E=%0d Ttake=%0d Trelease=%0d host=%0d done=%0d",cycles,jobs,ingress,wo_takes,sreq,sack,ecommands,ttakes,releases,hosttakes,dtakes);
  $display("PASS_ATSP cases=%0d",cases);$finish;
 end
endmodule
