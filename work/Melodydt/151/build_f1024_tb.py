"""Generate full-size deterministic provider + literal integer stage oracle TB."""
import argparse,json,hashlib
from pathlib import Path

CASE_IDS=['F1024_INPUT256_REAL_ACK_GATE','F1024_DENSE_FULL_DIMENSION_ALL_CHUNKS',
 'F1024_PROVIDER_BAD_INDEX','F1024_PROVIDER_BAD_LAST','F1024_PROVIDER_FUTURE_JOB',
 'F1024_PROVIDER_FUTURE_SEQ','F1024_PROVIDER_BAD_VERSION','F1024_PROVIDER_MATCHING_ERROR',
 'F1024_OLD_JOB_DRAIN_NO_WRITE','F1024_OLD_SEQ_DRAIN_NO_WRITE',
 'F1024_WEIGHT_WRITE_ACK_BACKPRESSURE','F1024_REQUEST_HOLD_VERSION_BINDING',
 'F1024_CANCEL_LATE_OLD_JOB_NEW_JOB_ISOLATION','F1024_PRESTART_PARTIAL_ABORT',
 'F1024_PRESTART_STORED_ABORT','F1024_RESET_PARTIAL_INPUT','F1024_RESET_PENDING_PROVIDER',
 'F1024_NATIVE_N_ERROR','F1024_NATIVE_M_EXEC_ERROR','F1024_NATIVE_G_ERROR_DRAIN',
 'F1024_S_HELPER_ERROR','F1024_ZERO_VERSION_REJECTED','F1024_JOB_EXHAUSTION_NO_WRAP',
 'F1024_GAMMA0_FULL_DIMENSION_DONE_ABORT_READY','F1024_FULL_OUTPUT_PREFIX_ABORT',
 'F1024_RESET_HELD_M_RESPONSE']

BODY=r'''
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
 reg [127:0] in_data=0;reg [15:0] weights_version=16'h1234;
 wire in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,out_valid,out_last;
 wire [127:0] out_data;wire [9:0] out_index;
 wire wreq_valid,w_ready;wire [15:0] wreq_job,wreq_seq,wreq_version;
 wire [1:0] wreq_matrix;wire [8:0] wreq_group;wire [6:0] wreq_chunk;
 reg allow_request=1,allow_data=1;
 reg p_active=0;reg [15:0] p_job=0,p_seq=0,p_version=0;
 integer p_matrix=0,p_group=0,p_chunk=0,p_index=0,p_delay=0;
 integer fault=0;integer v=0,seed=37,expected_job=0,expected_version=0,req_in_job=0;
 wire wreq_ready=allow_request&&!p_active;
 wire w_valid=p_active&&allow_data&&p_delay==0;
 wire stale_seq_fault=fault==8&&p_seq>0;
 wire [15:0] w_job=fault==3 ? p_job+16'd1 : fault==7 ? p_job-16'd1 : p_job;
 wire [15:0] w_seq=fault==4 ? p_seq+16'd1 : stale_seq_fault ? p_seq-16'd1 : p_seq;
 wire [15:0] w_version=fault==5 ? p_version^16'd1 : p_version;
 wire [4:0] w_index=fault==1 ? 5'd1 : p_index[4:0];
 wire w_last=fault==2 ? 1'b1 : p_index==15;
 wire w_error=fault==6;
 wire [127:0] w_data=recipe_word(p_matrix,p_group,p_chunk,p_index,seed);
 block_w4_f1024_top dut(.*);
 integer cycles=0,cases=0,ingress=0,sreq=0,sack=0,writes=0,reads=0;
 integer mcmd=0,mrsp=0,execs=0,ncmd=0,nrsp=0,gsvc=0,grsp=0,gissued=0,gretired=0,esvc=0,ersp=0;
 integer loads=0,ldone=0,wide=0,abeats=0,bbeats=0,ttake=0,trelease=0,starts=0,dtake=0;
 integer requests=0,accepted=0,stales=0,weight_acks=0,frame_acks=0,frame_output=0;
 integer i0,q0,ak0,w0,r0,m0,mr0,x0,n0,nr0,g0,gr0,gi0,go0,e0,er0,l0,ld0,wd0,ab0,bb0,tt0,tr0,st0,rq0,ac0,wa0;
 integer scratch0,oldtake,weight_file=0,dump_bytes=0;reg dump_enabled=0;
 reg tracking=0,running=0,pending=0,pwrite,hold_out=0,hold_done=0,hold_req=0,hold_weight=0,fault_native=0;
 reg [9:0] paddr,prev_index;reg [127:0] pdata,ram[0:1023],prev_out;
 reg written[0:1023];reg prev_last,prev_error,prev_sat;reg [65:0] prev_req;reg [182:0] prev_weight;
 string out_dir;

 function automatic [127:0] recipe_word;
  input integer matrix_no,group_no,chunk_no,beat_no,recipe_seed;
  integer i,n,k,value;begin
   recipe_word=0;
   for(i=0;i<16;i=i+1)begin
    n=group_no*8+2*(beat_no%4)+i/8;k=chunk_no*32+8*(beat_no/4)+i%8;
    value=((13*n+7*k+recipe_seed+41*matrix_no)%251)-125;
    recipe_word[8*i+:8]=value[7:0];
   end
  end
 endfunction
 function automatic [127:0] expected_write;
  input integer addr;integer tile;begin
   if(addr<128)expected_write=gold_X[v][addr];
   else if(addr<256)expected_write=gold_gamma[v][addr-128];
   else if(addr<384)expected_write=gold_norm[v][addr-256];
   else if(addr<768)expected_write=gold_mid[v][addr-384];
   else if(addr<896)expected_write=gold_output[v][addr-768];
   else if(addr<912)begin
    tile=(addr-896)/4;
    if((addr-896)%4!=0)expected_write=0;
    else if(dut.matrix==2)expected_write=gold_mid[v][dut.chunk_index*4+tile];
    else expected_write=gold_norm[v][dut.chunk_index*4+tile];
   end else if(addr<928)expected_write=recipe_word(dut.matrix,dut.group_index,dut.chunk_index,addr-912,seed);
   else if(addr==928)expected_write=gold_gate[v][dut.group_index];
   else if(addr==929)expected_write=gold_up[v][dut.group_index];
   else if(addr==931)expected_write=gold_down[v][dut.group_index];
   else begin $fatal(1,"FAIL_F1024 unexpectedSaddr=%0d",addr);expected_write=0;end
  end
 endfunction

 // Independent ordered provider: no ready from DUT is used to calculate data.
 always @(posedge clk)begin
  if(reset)begin p_active<=0;p_delay<=0;p_index<=0;expected_job=0;end
  else begin
   if(start_valid&&start_ready)begin expected_job=expected_job+1;expected_version=weights_version;req_in_job=0;end
   if(p_delay>0)p_delay<=p_delay-1;
   if(w_valid&&w_ready)begin
    if(fault==7||stale_seq_fault)begin stales=stales+1;fault<=0;end
    else if(fault>=1&&fault<=6)begin p_active<=0;fault<=0;end
    else begin
     accepted=accepted+1;
     if(dump_enabled)begin
      for(integer byte_no=0;byte_no<16;byte_no=byte_no+1)$fwrite(weight_file,"%c",w_data[8*byte_no+:8]);
      dump_bytes=dump_bytes+16;
     end
     if(p_index==15)p_active<=0;else p_index<=p_index+1;
     p_delay<=1;
    end
   end
   if(wreq_valid&&wreq_ready)begin
    if(wreq_job!==expected_job[15:0]||wreq_seq!==req_in_job[15:0]||wreq_version!==expected_version[15:0])$fatal(1,"FAIL_F1024 request identity");
    if(req_in_job<24576)begin
     if(wreq_matrix!==(req_in_job%64)/32||wreq_group!==req_in_job/64||wreq_chunk!==req_in_job%32)$fatal(1,"FAIL_F1024 gate/up request order");
    end else if(wreq_matrix!==2||wreq_group!==(req_in_job-24576)/96||wreq_chunk!==(req_in_job-24576)%96)$fatal(1,"FAIL_F1024 down request order");
    if(weight_acks-wa0!=req_in_job*16)$fatal(1,"FAIL_F1024 nextrequest before16SACK");
    p_job<=wreq_job;p_seq<=wreq_seq;p_version<=wreq_version;p_matrix<=wreq_matrix;p_group<=wreq_group;p_chunk<=wreq_chunk;p_index<=0;p_delay<=2;p_active<=1;
    requests=requests+1;req_in_job=req_in_job+1;
   end
  end
 end

 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>150000000)$fatal(1,"FAIL_F1024 watchdog state=%0d seq=%0d",dut.state,dut.request_seq);
  if(reset)begin hold_out=0;hold_done=0;hold_req=0;hold_weight=0;pending=0;end
  else begin
   if(hold_done&&(!done_valid||done_error!==prev_error||done_saturated!==prev_sat))$fatal(1,"FAIL_F1024 heldDONE");
   hold_done=done_valid&&!done_ready;prev_error=done_error;prev_sat=done_saturated;
   if(!dut.leaf_reset)begin
    if(hold_out&&(!out_valid||out_data!==prev_out||out_index!==prev_index||out_last!==prev_last))$fatal(1,"FAIL_F1024 heldoutput");
    if(hold_req&&(!wreq_valid||{wreq_job,wreq_seq,wreq_version,wreq_matrix,wreq_group,wreq_chunk}!==prev_req))$fatal(1,"FAIL_F1024 heldrequest");
    if(hold_weight&&(!w_valid||{w_job,w_seq,w_version,w_index,w_last,w_error,w_data}!==prev_weight))$fatal(1,"FAIL_F1024 provider heldresponse");
    hold_out=out_valid&&!out_ready;prev_out=out_data;prev_index=out_index;prev_last=out_last;
    hold_req=wreq_valid&&!wreq_ready;prev_req={wreq_job,wreq_seq,wreq_version,wreq_matrix,wreq_group,wreq_chunk};
    hold_weight=w_valid&&!w_ready;prev_weight={w_job,w_seq,w_version,w_index,w_last,w_error,w_data};
   end else begin hold_out=0;hold_req=0;hold_weight=0;pending=0;end
   if(in_valid&&in_ready)ingress=ingress+1;
   if(start_valid&&start_ready)begin starts=starts+1;running=1;if(frame_acks!=256)$fatal(1,"FAIL_F1024 startbeforeACK256");end
   if(done_valid&&done_ready)dtake=dtake+1;
   if(out_valid&&out_ready)begin
    if(!running||frame_output>=128||out_index!==frame_output||out_last!==(frame_output==127)||out_data!==gold_output[v][frame_output])$fatal(1,"FAIL_F1024 output idx=%0d got=%032h",frame_output,out_data);
    frame_output=frame_output+1;ttake=ttake+1;
   end
   if(tracking&&!dut.leaf_reset)begin
    if(dut.s_req&&dut.s_ready)begin
     if(pending)$fatal(1,"FAIL_F1024 overlapS");pending=1;pwrite=dut.s_we;paddr=dut.s_addr;pdata=dut.s_din;sreq=sreq+1;
     if(dut.s_we)begin
      if(dut.s_din!==expected_write(dut.s_addr))$fatal(1,"FAIL_F1024 Sstage addr=%0d got=%032h expected=%032h",dut.s_addr,dut.s_din,expected_write(dut.s_addr));writes=writes+1;
     end else reads=reads+1;
    end
    if(dut.s_valid&&dut.s_take)begin
     if(!pending)$fatal(1,"FAIL_F1024 unexpectedACK");sack=sack+1;
     if(pwrite)begin
      ram[paddr]=pdata;written[paddr]=1;
      if(paddr<256)frame_acks=frame_acks+1;
      if(paddr>=912&&paddr<928)weight_acks=weight_acks+1;
     end else if(!written[paddr]||dut.s_dout!==ram[paddr])$fatal(1,"FAIL_F1024 wrongread/readbeforeACK addr=%0d",paddr);
     pending=0;
    end
    if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
     mcmd=mcmd+1;
     if(dut.m_cmd_op==10)begin
      execs=execs+1;
      if(!fault_native&&dut.m_cmd_data!==(dut.chunk_index==0?64'hc885:64'hc881))$fatal(1,"FAIL_F1024 raw fullK accumulation descriptor");
     end
     if(dut.m_cmd_op==5&&(dut.chunk_index!=(dut.matrix==2?95:31)||dut.m_cmd_data!=64'h107))$fatal(1,"FAIL_F1024 intermediate quantization/read");
    end
    if(dut.m_rsp_valid&&dut.m_rsp_ready)mrsp=mrsp+1;
    if(dut.n_cmd_valid&&dut.n_cmd_ready)ncmd=ncmd+1;
    if(dut.n_native_rsp_valid&&dut.n_native_rsp_ready)nrsp=nrsp+1;
    if(dut.g_req_valid&&dut.g_req_ready)gsvc=gsvc+1;
    if(dut.g_rsp_valid&&dut.g_rsp_ready)grsp=grsp+1;
    if(dut.g_in_valid&&dut.g_in_ready)gissued=gissued+1;
    if(dut.g_out_valid&&dut.g_out_ready)gretired=gretired+1;
    if(dut.e_req_valid&&dut.e_req_ready)esvc=esvc+1;
    if(dut.e_rsp_valid&&dut.e_rsp_ready)ersp=ersp+1;
    if(dut.load_valid&&dut.load_ready)loads=loads+1;
    if(dut.load_done_valid&&dut.load_done_take)ldone=ldone+1;
    if(dut.u_s.mem_req&&dut.u_s.mem_ready)wide=wide+1;
    if(dut.a_valid&&dut.a_ready)abeats=abeats+1;
    if(dut.b_valid&&dut.b_ready)bbeats=bbeats+1;
    if(dut.state==17&&dut.t_release_ready)trelease=trelease+1;
   end
  end
 end

 task automatic mark;input integer n;begin cases=cases+1;$display("CASE_PASS %0s",case_name(n));end endtask
 task automatic new_frame;input integer which;input dumping;begin
  if(busy||done_valid||input_stored||p_active)$fatal(1,"FAIL_F1024 newframe stale");
  v=which;seed=which==0?37:91;weights_version=which==0?16'h1234:16'h4321;
  tracking=1;running=0;frame_acks=0;frame_output=0;pending=0;fault=0;fault_native=0;allow_request=1;allow_data=1;
  for(integer k=0;k<1024;k=k+1)written[k]=0;
  i0=ingress;q0=sreq;ak0=sack;w0=writes;r0=reads;m0=mcmd;mr0=mrsp;x0=execs;n0=ncmd;nr0=nrsp;g0=gsvc;gr0=grsp;gi0=gissued;go0=gretired;e0=esvc;er0=ersp;l0=loads;ld0=ldone;wd0=wide;ab0=abeats;bb0=bbeats;tt0=ttake;tr0=trelease;st0=starts;rq0=requests;ac0=accepted;wa0=weight_acks;
  dump_enabled=dumping;dump_bytes=0;
  if(dumping)begin
   weight_file=$fopen({out_dir,which==0?"/weights-dense.bin":"/weights-gamma0.bin"},"wb");
   if(weight_file==0)$fatal(1,"FAIL_F1024 openbinarydump");
  end
 end endtask
 task automatic send;input integer beat;begin
  @(negedge clk);in_valid=1;in_data=beat<128?gold_X[v][beat]:gold_gamma[v][beat-128];
  while(!in_ready)@(negedge clk);@(posedge clk);#1;if(!busy)$fatal(1,"FAIL_F1024 capturednotbusy");
  @(negedge clk);in_valid=0;
 end endtask
 task automatic fill;begin for(integer k=0;k<256;k=k+1)send(k);while(!input_stored)@(negedge clk);if(frame_acks!=256||!start_ready||!busy||in_ready)$fatal(1,"FAIL_F1024 storedACK256");end endtask
 task automatic start_job;begin @(negedge clk);start_valid=1;@(posedge clk);#1;@(negedge clk);start_valid=0;end endtask
 task automatic finish;input error_expected,abort_take;begin
  while(!done_valid)@(negedge clk);if(done_error!==error_expected)$fatal(1,"FAIL_F1024 errorflag");
  if(!error_expected&&(frame_output!=128||done_saturated!==gold_sat[v]||trelease-tr0!=1))$fatal(1,"FAIL_F1024 earlyDONE/saturation");
  repeat(5)begin @(negedge clk);if(!done_valid||!busy||in_ready||start_ready)$fatal(1,"FAIL_F1024 DONEhold");end
  oldtake=dtake;done_ready=1;abort=abort_take;@(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;
  if(dtake!=oldtake+1)$fatal(1,"FAIL_F1024 DONEduplicate");
  tracking=0;running=0;p_active=0;fault=0;
  if(dump_enabled)begin $fclose(weight_file);weight_file=0;dump_enabled=0;if(dump_bytes!=9437184)$fatal(1,"FAIL_F1024 binarybytes=%0d",dump_bytes);end
  repeat(3)@(negedge clk);if(busy||done_valid||input_stored||!in_ready)$fatal(1,"FAIL_F1024 reuse");
 end endtask
 task automatic normal_counts;begin
  if(ingress-i0!=256||sreq-q0!=888076||sack-ak0!=888076||writes-w0!=739084||reads-r0!=148992)$fatal(1,"FAIL_F1024 ordinaryS counts");
  if(mcmd-m0!=40448||mrsp-mr0!=40448||execs-x0!=36864||ncmd-n0!=258||nrsp-nr0!=258||gsvc-g0!=384||grsp-gr0!=384||gissued-gi0!=1536||gretired-go0!=1536||esvc-e0!=128||ersp-er0!=128)$fatal(1,"FAIL_F1024 compute counts");
  if(loads-l0!=36864||ldone-ld0!=36864||wide-wd0!=294912||abeats-ab0!=147456||bbeats-bb0!=147456||requests-rq0!=36864||accepted-ac0!=589824||weight_acks-wa0!=589824||ttake-tt0!=128||trelease-tr0!=1||starts-st0!=1)$fatal(1,"FAIL_F1024 provider/loader/T counts");
 end endtask
 task automatic drain_output;begin
  while(!out_valid)@(negedge clk);repeat(8)@(negedge clk);out_ready=1;
  while(frame_output<128)@(negedge clk);out_ready=0;
 end endtask
 task automatic pulse_abort;begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;start_valid=0;in_valid=0;out_ready=0;p_active=0;end endtask
 task automatic preabort;begin pulse_abort();tracking=0;running=0;repeat(3)@(negedge clk);if(busy||done_valid||input_stored||!in_ready)$fatal(1,"FAIL_F1024 preabortDONE");end endtask
 task automatic hard_reset;begin
  @(negedge clk);reset=1;in_valid=0;start_valid=0;out_ready=0;done_ready=0;p_active=0;
  repeat(3)@(negedge clk);reset=0;tracking=0;running=0;
  repeat(3)@(negedge clk);if(busy||done_valid||out_valid||input_stored||!in_ready)$fatal(1,"FAIL_F1024 resetstale");
 end endtask
 task automatic fail_provider;input integer kind,case_no;begin
  new_frame(0,0);fill();fault=kind;start_job();finish(1,0);
  if(frame_output!=0||weight_acks-wa0!=0)$fatal(1,"FAIL_F1024 badproviderwrote");mark(case_no);
 end endtask

 initial begin
  if(!$value$plusargs("out_dir=%s",out_dir))out_dir=".";
  __INIT__
  repeat(4)@(negedge clk);reset=0;repeat(3)@(negedge clk);
  new_frame(0,1);for(integer k=0;k<255;k=k+1)send(k);
  while(frame_acks<255)@(negedge clk);force dut.permit_s_rsp=1'b0;send(255);start_valid=1;
  repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0)$fatal(1,"FAIL_F1024 finalACKgate");end
  start_valid=0;release dut.permit_s_rsp;while(!input_stored)@(negedge clk);mark(0);
  start_job();weights_version=16'h7777;drain_output();finish(0,0);normal_counts();mark(1);
  fail_provider(1,2);fail_provider(2,3);fail_provider(3,4);fail_provider(4,5);fail_provider(5,6);fail_provider(6,7);
  new_frame(0,0);fill();fault=7;start_job();while(stales==0)@(negedge clk);while(weight_acks-wa0<1)@(negedge clk);
  if(done_valid)$fatal(1,"FAIL_F1024 oldjobnotdrained");pulse_abort();finish(1,0);mark(8);
  new_frame(0,0);fill();scratch0=stales;fault=8;start_job();while(stales==scratch0)@(negedge clk);
  while(weight_acks-wa0<17)@(negedge clk);if(done_valid)$fatal(1,"FAIL_F1024 oldseqnotdrained");pulse_abort();finish(1,0);mark(9);
  new_frame(0,0);fill();start_job();while(accepted-ac0<1)@(negedge clk);force dut.permit_s_rsp=1'b0;
  while(!dut.s_valid)@(negedge clk);scratch0=accepted;repeat(8)@(negedge clk);
  if(accepted!=scratch0||w_ready)$fatal(1,"FAIL_F1024 currentbeatbeforewriteACK");release dut.permit_s_rsp;
  while(weight_acks-wa0<1)@(negedge clk);pulse_abort();finish(1,0);mark(10);
  new_frame(0,0);fill();allow_request=0;start_job();while(!wreq_valid)@(negedge clk);
  weights_version=16'h9999;repeat(8)@(negedge clk);allow_request=1;
  while(weight_acks-wa0<1)@(negedge clk);pulse_abort();finish(1,0);mark(11);
  new_frame(0,0);fill();allow_data=0;start_job();while(!p_active)@(negedge clk);pulse_abort();finish(1,0);
  new_frame(0,0);fill();scratch0=stales;fault=7;start_job();while(stales==scratch0)@(negedge clk);
  while(weight_acks-wa0<1)@(negedge clk);pulse_abort();finish(1,0);mark(12);
  new_frame(0,0);send(0);send(1);preabort();mark(13);
  new_frame(0,0);fill();preabort();mark(14);
  new_frame(0,0);send(0);hard_reset();mark(15);
  new_frame(0,0);fill();allow_data=0;start_job();while(!p_active)@(negedge clk);hard_reset();mark(16);
  new_frame(0,0);fill();start_job();@(negedge clk);while(!(dut.n_cmd_valid&&dut.n_cmd_ready))@(negedge clk);
  force dut.n_cmd_op=4'd15;@(posedge clk);#1;@(negedge clk);release dut.n_cmd_op;finish(1,0);if(requests!=rq0)$fatal(1,"FAIL_F1024 Nerrorloaded");mark(17);
  new_frame(0,0);fill();fault_native=1;start_job();wait(dut.state==5&&dut.m_phase==2);@(negedge clk);
  force dut.m_cmd_data=64'hc88d;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;finish(1,0);mark(18);
  new_frame(0,0);fill();start_job();@(negedge clk);while(!(dut.g_in_valid&&dut.g_in_ready))@(negedge clk);
  force dut.g_in_fn=3'd4;@(posedge clk);#1;@(negedge clk);release dut.g_in_fn;finish(1,0);if(written[384]||frame_output!=0)$fatal(1,"FAIL_F1024 Gerrorwrote");mark(19);
  new_frame(0,0);fill();start_job();@(negedge clk);while(!(dut.h_rsp_valid&&dut.h_rsp_ready))@(negedge clk);
  force dut.h_rsp_error=1'b1;@(posedge clk);#1;@(negedge clk);release dut.h_rsp_error;finish(1,0);mark(20);
  new_frame(0,0);fill();weights_version=0;start_valid=1;repeat(5)begin @(negedge clk);if(start_ready||starts!=st0)$fatal(1,"FAIL_F1024 zeroVersionaccepted");end start_valid=0;preabort();mark(21);
  new_frame(0,0);fill();force dut.job_counter=16'hffff;start_valid=1;repeat(5)begin @(negedge clk);if(start_ready||starts!=st0)$fatal(1,"FAIL_F1024 jobwrap");end start_valid=0;preabort();release dut.job_counter;hard_reset();mark(22);
  new_frame(1,1);fill();start_job();drain_output();finish(0,1);normal_counts();mark(23);
  new_frame(1,0);fill();start_job();while(!out_valid)@(negedge clk);out_ready=1;
  @(posedge clk);#1;@(negedge clk);out_ready=0;pulse_abort();finish(1,0);
  if(frame_output!=1||ttake-tt0!=1)$fatal(1,"FAIL_F1024 prefixrollback");mark(24);
  new_frame(0,0);fill();force dut.permit_m_rsp=1'b0;start_job();while(!dut.m_rsp_valid)@(negedge clk);
  hard_reset();release dut.permit_m_rsp;new_frame(0,0);send(0);preabort();mark(25);
  if(cases!=26)$fatal(1,"FAIL_F1024 CASEcount");
  $display("F1024_STATS cycles=%0d input=%0d Sreq=%0d Sack=%0d Mcmd=%0d Mrsp=%0d Ncmd=%0d Nrsp=%0d req=%0d beats=%0d stale=%0d Ttake=%0d",cycles,ingress,sreq,sack,mcmd,mrsp,ncmd,nrsp,requests,accepted,stales,ttake);
  $display("PASS_W4_F1024 cases=%0d",cases);$finish;
 end
'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();d=a.directory
    data=json.loads((d/'f1024-contract-vectors.json').read_text(encoding='utf-8'))
    sv='`timescale 1ns/1ps\nmodule block_w4_f1024_tb;\n'
    for stage,count in [('X',128),('gamma',128),('norm',128),('gate',384),('up',384),('mid',384),('down',128),('output',128)]:sv+=' reg [127:0] gold_'+stage+'[0:1][0:'+str(count-1)+'];\n'
    sv+=' reg gold_sat[0:1];\n function automatic [639:0] case_name;input integer i;begin case(i)\n'
    sv+='\n'.join(' '+str(i)+':case_name="'+name+'";' for i,name in enumerate(CASE_IDS))+'\n default:case_name="INVALID";endcase end endfunction\n'
    initial=[]
    for v in data['vectors']:
        i=v['index'];e=v['expected'];initial.append('gold_sat['+str(i)+"]=1'b"+str(int(e['done_saturated']))+';')
        for stage,words in e['words'].items():
            initial.extend('gold_'+stage+'['+str(i)+']['+str(j)+"]=128'h"+word+';' for j,word in enumerate(words))
    sv+=BODY.replace('__INIT__','\n  '.join(initial))+'\nendmodule\n';tb=d/'block_w4_f1024_tb.sv';tb.write_bytes(sv.encode('utf-8'))
    sources=['project/rtl/block_v2/block_v2_'+s+'.sv' for s in ['e','g','m','n','n_group']]
    sources+=['project/rtl/block_feed_v1/'+s+'.sv' for s in ['block_feed_loader','block_feed_s16k','block_feed_s_macro']]
    sources+=['project/rtl/block_v1/transaction6k.sv','project/rtl/block_connection_p2/block_p2_s_ctrl.sv','project/rtl/block_connection_w3/block_w3_e_ctrl.sv','project/rtl/block_connection_w3/block_w3_g_ctrl.sv','project/rtl/block_connection_w4/block_w4_n_long_ctrl.sv','project/rtl/block_connection_w4/block_w4_f1024_top.sv','project/tb/block_connection_w4/block_w4_f1024_tb.sv']
    contract={'schema_version':1,'status':'FROZEN_FULL_DIMENSION_SELECTED_INTEGER_CASES_NOT_RTL_EXECUTION',
      'top_module':'block_w4_f1024_tb','pass_marker':'PASS_W4_F1024','pass_line_regex':'^PASS_W4_F1024 cases=26$',
      'expected_case_ids':CASE_IDS,'expected_unique_case_count':26,'compile_sources':sources,
      'include_dirs':['project/rtl/block_v2','work/Melodydt/151'],'TB_includes':[],
      'reference_dependencies':['work/Melodydt/151/f1024_integer_reference.py','work/Melodydt/151/f16_integer_reference.py'],
      'input_paths':['work/Melodydt/151/f1024-contract-vectors.json','work/Melodydt/151/f1024-weight-stream-index.json'],
      'tb_sha256':hashlib.sha256(tb.read_bytes()).hexdigest(),'vectors_path':'work/Melodydt/151/f1024-contract-vectors.json',
      'normal_counts':data['normal_counts'],'execution_policy':'root server Verilator only;no local RTL',
      'runtime_plusargs':['+out_dir=<existing result directory>'],
      'binary_dumps':[dict(v['canonical_weight_stream'],fixture=v['id'],filename='weights-'+v['id']+'.bin') for v in data['vectors']],
      'scope':'2complete fullsizefixtures+1fullcompute prefixabort;negativecases mostlyearly;not trained model/PPA'}
    (d/'f1024-tb-contract.json').write_bytes((json.dumps(contract,indent=2)+'\n').encode('utf-8'))
    print('PASS_F1024_TB_GENERATED cases=26 SHA256='+contract['tb_sha256'])


if __name__=='__main__':main()
