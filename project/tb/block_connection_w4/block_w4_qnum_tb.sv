`timescale 1ns/1ps
// File-driven real trained-data integer check; expected stages generated independently.
// A fixed elaborated binding; no runtime op/address/shape/shift and no force/release.
module block_w4_qnum_tb #(
 parameter [31:0] N_EPSILON=32'd1,
 parameter [5:0] M_GATE_SHIFT=6'd7,
 parameter [5:0] M_UP_SHIFT=6'd7,
 parameter [5:0] M_DOWN_SHIFT=6'd7
);
 reg [127:0] gold_X[0:1][0:127],gold_gamma[0:1][0:127],gold_norm[0:1][0:127];
 reg [127:0] gold_gate[0:1][0:383],gold_up[0:1][0:383],gold_mid[0:1][0:383];
 reg [127:0] gold_down[0:1][0:127],gold_output[0:1][0:127];
 reg gold_sat[0:1];
 reg [7:0] weight_bytes[0:9437183];
 string fixture_dir,input_path,gamma_path,norm_path,gate_path,up_path,mid_path,down_path,output_path,weights_path,dump_path,sat_path;
 integer expected_sat=-1,unused_arg=0;
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
 wire [127:0] w_data=file_word(p_seq,p_index);
 block_w4_qnum_top #(.N_EPSILON(N_EPSILON),.M_GATE_SHIFT(M_GATE_SHIFT),.M_UP_SHIFT(M_UP_SHIFT),.M_DOWN_SHIFT(M_DOWN_SHIFT)) dut(.*);
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

 function automatic [127:0] file_word;
  input integer sequence_no,beat_no;integer offset,k;begin
   file_word=0;offset=sequence_no*256+beat_no*16;
   if(sequence_no<0||sequence_no>=36864||beat_no<0||beat_no>=16)$fatal(1,"FAIL_QNUM fileword bounds");
   for(k=0;k<16;k=k+1)file_word[8*k+:8]=weight_bytes[offset+k];
  end
 endfunction
 function automatic [5:0] expected_shift;
  input [1:0] matrix_no;begin expected_shift=matrix_no==0?M_GATE_SHIFT:matrix_no==1?M_UP_SHIFT:M_DOWN_SHIFT;end
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
   end else if(addr<928)expected_write=file_word(dut.request_seq,addr-912);
   else if(addr==928)expected_write=gold_gate[v][dut.group_index];
   else if(addr==929)expected_write=gold_up[v][dut.group_index];
   else if(addr==931)expected_write=gold_down[v][dut.group_index];
   else begin $fatal(1,"FAIL_QNUM unexpectedSaddr=%0d",addr);expected_write=0;end
  end
 endfunction

 // Independent ordered file provider; no DUT arithmetic output creates data.
 always @(posedge clk)begin
  if(reset)begin p_active<=0;p_delay<=0;p_index<=0;expected_job=0;end
  else begin
   if(start_valid&&start_ready)begin expected_job=expected_job+1;expected_version=weights_version;req_in_job=0;end
   if(p_delay>0)p_delay<=p_delay-1;
   if(w_valid&&w_ready)begin
    if(accepted!=weight_acks)$fatal(1,"FAIL_QNUM data before previous actualSwriteACK");
    accepted=accepted+1;
    for(integer byte_no=0;byte_no<16;byte_no=byte_no+1)$fwrite(weight_file,"%c",w_data[8*byte_no+:8]);
    dump_bytes=dump_bytes+16;
    if(p_index==15)p_active<=0;else p_index<=p_index+1;
    p_delay<=1;
   end
   if(wreq_valid&&wreq_ready)begin
    if(wreq_job!==expected_job[15:0]||wreq_seq!==req_in_job[15:0]||wreq_version!==16'h1234)$fatal(1,"FAIL_QNUM request identity/version");
    if(req_in_job<24576)begin
     if(wreq_matrix!==(req_in_job%64)/32||wreq_group!==req_in_job/64||wreq_chunk!==req_in_job%32)$fatal(1,"FAIL_QNUM gate/up request sequence");
    end else if(wreq_matrix!==2||wreq_group!==(req_in_job-24576)/96||wreq_chunk!==(req_in_job-24576)%96)$fatal(1,"FAIL_QNUM down request sequence");
    if(weight_acks!=req_in_job*16)$fatal(1,"FAIL_QNUM request before previous16writeACKs");
    p_job<=wreq_job;p_seq<=wreq_seq;p_version<=wreq_version;p_matrix<=wreq_matrix;p_group<=wreq_group;p_chunk<=wreq_chunk;
    p_index<=0;p_delay<=2;p_active<=1;requests=requests+1;req_in_job=req_in_job+1;
   end
  end
 end

 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>150000000)$fatal(1,"FAIL_QNUM watchdog state=%0d seq=%0d",dut.state,dut.request_seq);
  if(reset)begin hold_out=0;hold_done=0;hold_req=0;hold_weight=0;pending=0;end
  else begin
   if(hold_done&&(!done_valid||done_error!==prev_error||done_saturated!==prev_sat))$fatal(1,"FAIL_QNUM heldDONE");
   hold_done=done_valid&&!done_ready;prev_error=done_error;prev_sat=done_saturated;
   if(!dut.leaf_reset)begin
    if(hold_out&&(!out_valid||out_data!==prev_out||out_index!==prev_index||out_last!==prev_last))$fatal(1,"FAIL_QNUM heldoutput");
    if(hold_req&&(!wreq_valid||{wreq_job,wreq_seq,wreq_version,wreq_matrix,wreq_group,wreq_chunk}!==prev_req))$fatal(1,"FAIL_QNUM heldrequest");
    if(hold_weight&&(!w_valid||{w_job,w_seq,w_version,w_index,w_last,w_error,w_data}!==prev_weight))$fatal(1,"FAIL_QNUM provider heldresponse");
    hold_out=out_valid&&!out_ready;prev_out=out_data;prev_index=out_index;prev_last=out_last;
    hold_req=wreq_valid&&!wreq_ready;prev_req={wreq_job,wreq_seq,wreq_version,wreq_matrix,wreq_group,wreq_chunk};
    hold_weight=w_valid&&!w_ready;prev_weight={w_job,w_seq,w_version,w_index,w_last,w_error,w_data};
   end else begin hold_out=0;hold_req=0;hold_weight=0;pending=0;end
   if(in_valid&&in_ready)ingress=ingress+1;
   if(start_valid&&start_ready)begin starts=starts+1;running=1;if(frame_acks!=256)$fatal(1,"FAIL_QNUM startbeforeACK256");end
   if(done_valid&&done_ready)dtake=dtake+1;
   if(out_valid&&out_ready)begin
    if(!running||frame_output>=128||out_index!==frame_output||out_last!==(frame_output==127)||out_data!==gold_output[v][frame_output])$fatal(1,"FAIL_QNUM output idx=%0d got=%032h",frame_output,out_data);
    frame_output=frame_output+1;ttake=ttake+1;
   end
   if(tracking&&!dut.leaf_reset)begin
    if(dut.s_req&&dut.s_ready)begin
     if(pending)$fatal(1,"FAIL_QNUM overlapS");pending=1;pwrite=dut.s_we;paddr=dut.s_addr;pdata=dut.s_din;sreq=sreq+1;
     if(dut.s_we)begin
      if(dut.s_din!==expected_write(dut.s_addr))$fatal(1,"FAIL_QNUM Sstage addr=%0d got=%032h expected=%032h",dut.s_addr,dut.s_din,expected_write(dut.s_addr));writes=writes+1;
     end else reads=reads+1;
    end
    if(dut.s_valid&&dut.s_take)begin
     if(!pending)$fatal(1,"FAIL_QNUM unexpectedACK");sack=sack+1;
     if(pwrite)begin
      ram[paddr]=pdata;written[paddr]=1;
      if(paddr<256)frame_acks=frame_acks+1;
      if(paddr>=912&&paddr<928)weight_acks=weight_acks+1;
     end else if(!written[paddr]||dut.s_dout!==ram[paddr])$fatal(1,"FAIL_QNUM wrongread/readbeforeACK addr=%0d",paddr);
     pending=0;
    end
    if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
     mcmd=mcmd+1;
     if(dut.m_cmd_op==10)begin
      execs=execs+1;
      if(!fault_native&&dut.m_cmd_data!==(dut.chunk_index==0?64'hc885:64'hc881))$fatal(1,"FAIL_QNUM raw fullK accumulation descriptor");
     end
     if(dut.m_cmd_op==5&&(dut.chunk_index!=(dut.matrix==2?95:31)||dut.m_cmd_data!=(64'h100|{58'd0,expected_shift(dut.matrix)})))$fatal(1,"FAIL_QNUM intermediate quantization/read");
    end
    if(dut.m_rsp_valid&&dut.m_rsp_ready)mrsp=mrsp+1;
    if(dut.n_cmd_valid&&dut.n_cmd_ready)begin
     ncmd=ncmd+1;
     if(dut.n_cmd_op==0&&(dut.n_cmd_param!=1||dut.n_cmd_data[31:0]!==N_EPSILON))$fatal(1,"FAIL_QNUM boundN mode/epsilon");
    end
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


 task automatic mark;input string label;begin cases=cases+1;$display("CASE_PASS %s",label);end endtask
 task automatic load_hex;input string path;input integer stage_no,count;
  integer fd,k,code;reg [127:0] word;begin
   fd=$fopen(path,"r");if(fd==0)$fatal(1,"FAIL_QNUM missingstagefile %s",path);
   for(k=0;k<count;k=k+1)begin
    code=$fscanf(fd,"%h",word);if(code!=1)$fatal(1,"FAIL_QNUM short/malformedstage %s word%0d",path,k);
    case(stage_no)
     0:gold_X[0][k]=word;1:gold_gamma[0][k]=word;2:gold_norm[0][k]=word;3:gold_gate[0][k]=word;
     4:gold_up[0][k]=word;5:gold_mid[0][k]=word;6:gold_down[0][k]=word;7:gold_output[0][k]=word;
     default:$fatal(1,"FAIL_QNUM badloaderstage");
    endcase
   end
   code=$fscanf(fd,"%h",word);if(code!=-1)$fatal(1,"FAIL_QNUM extra/malformedstagetail %s",path);$fclose(fd);
  end
 endtask
 task automatic send_input;input integer beat;begin
  @(negedge clk);in_valid=1;in_data=beat<128?gold_X[0][beat]:gold_gamma[0][beat-128];
  while(!in_ready)@(negedge clk);@(posedge clk);#1;if(!busy)$fatal(1,"FAIL_QNUM accepted input notbusy");
  @(negedge clk);in_valid=0;
 end endtask
 task automatic check_counts;begin
  if(ingress!=256||sreq!=888076||sack!=888076||writes!=739084||reads!=148992||frame_acks!=256)$fatal(1,"FAIL_QNUM ordinaryS counts");
  if(mcmd!=40448||mrsp!=40448||execs!=36864||ncmd!=258||nrsp!=258||gsvc!=384||grsp!=384||gissued!=1536||gretired!=1536||esvc!=128||ersp!=128)$fatal(1,"FAIL_QNUM compute counts");
  if(loads!=36864||ldone!=36864||wide!=294912||abeats!=147456||bbeats!=147456||requests!=36864||accepted!=589824||weight_acks!=589824||ttake!=128||trelease!=1||starts!=1||pending||p_active)$fatal(1,"FAIL_QNUM provider/loader/T counts");
 end endtask
 integer fd,count,extra,i;
 initial begin
  fixture_dir="";unused_arg=$value$plusargs("fixture_dir=%s",fixture_dir);
  input_path={fixture_dir,"/input.hex"};gamma_path={fixture_dir,"/gamma.hex"};norm_path={fixture_dir,"/norm.hex"};
  gate_path={fixture_dir,"/gate.hex"};up_path={fixture_dir,"/up.hex"};mid_path={fixture_dir,"/mid.hex"};
  down_path={fixture_dir,"/down.hex"};output_path={fixture_dir,"/output.hex"};weights_path={fixture_dir,"/../weights-stream.bin"};sat_path={fixture_dir,"/expected-saturated.hex"};
  unused_arg=$value$plusargs("input=%s",input_path);unused_arg=$value$plusargs("gamma=%s",gamma_path);unused_arg=$value$plusargs("norm=%s",norm_path);
  unused_arg=$value$plusargs("gate=%s",gate_path);unused_arg=$value$plusargs("up=%s",up_path);unused_arg=$value$plusargs("mid=%s",mid_path);
  unused_arg=$value$plusargs("down=%s",down_path);unused_arg=$value$plusargs("output=%s",output_path);unused_arg=$value$plusargs("weights=%s",weights_path);
  if(!$value$plusargs("dump=%s",dump_path))$fatal(1,"FAIL_QNUM +dump=new-file required");
  if(!$value$plusargs("expected_sat=%d",expected_sat))begin
   fd=$fopen(sat_path,"r");if(fd==0)$fatal(1,"FAIL_QNUM expectedsatfile missing");
   count=$fscanf(fd,"%h",expected_sat);if(count!=1)$fatal(1,"FAIL_QNUM expectedsat parse");extra=$fscanf(fd,"%d",i);if(extra!=-1)$fatal(1,"FAIL_QNUM expectedsat tail");$fclose(fd);
  end
  if(expected_sat<0||expected_sat>1)$fatal(1,"FAIL_QNUM expectedsat notbit");gold_sat[0]=expected_sat[0];
  load_hex(input_path,0,128);load_hex(gamma_path,1,128);load_hex(norm_path,2,128);
  load_hex(gate_path,3,384);load_hex(up_path,4,384);load_hex(mid_path,5,384);load_hex(down_path,6,128);load_hex(output_path,7,128);
  fd=$fopen(weights_path,"rb");if(fd==0)$fatal(1,"FAIL_QNUM weights file missing");
  count=$fread(weight_bytes,fd);extra=$fgetc(fd);$fclose(fd);
  if(count!=9437184||extra!=-1)$fatal(1,"FAIL_QNUM weights bytecount/trailingdata %0d",count);
  fd=$fopen(dump_path,"rb");if(fd!=0)begin $fclose(fd);$fatal(1,"FAIL_QNUM refuse existing accepted dump");end
  weight_file=$fopen(dump_path,"wb");if(weight_file==0)$fatal(1,"FAIL_QNUM accepted dump open");dump_enabled=1;dump_bytes=0;
  repeat(4)@(negedge clk);reset=0;repeat(3)@(negedge clk);
  v=0;tracking=1;running=0;frame_acks=0;frame_output=0;fault=0;fault_native=0;weights_version=16'h1234;
  for(i=0;i<1024;i=i+1)written[i]=0;
  for(i=0;i<256;i=i+1)send_input(i);
  if(input_stored||start_ready||frame_acks==256)$fatal(1,"FAIL_QNUM lastinput accepted incorrectly alreadyACKed");
  start_valid=1;@(posedge clk);#1;@(negedge clk);start_valid=0;if(starts!=0)$fatal(1,"FAIL_QNUM early start queued/accepted");
  while(!input_stored)@(negedge clk);
  if(frame_acks!=256||!start_ready||!busy||in_ready)$fatal(1,"FAIL_QNUM last actualinputACK gate");mark("QNUM_INPUT256_REAL_ACK_GATE");
  allow_request=0;start_valid=1;@(posedge clk);#1;@(negedge clk);start_valid=0;
  while(!wreq_valid)@(negedge clk);repeat(8)@(negedge clk);
  if(requests!=0)$fatal(1,"FAIL_QNUM heldrequest accepted");allow_request=1;mark("QNUM_REQUEST_HOLD_STATIC_BINDING");
  while(!out_valid)@(negedge clk);repeat(8)@(negedge clk);out_ready=1;
  while(frame_output<128)begin
   @(negedge clk);
   if(frame_output==64)begin out_ready=0;repeat(7)@(negedge clk);out_ready=1;end
  end
  out_ready=0;mark("QNUM_OUTPUT_STALL_ORDER_VALUES");
  while(!done_valid)@(negedge clk);
  if(done_error||done_saturated!==gold_sat[0]||trelease!=1)$fatal(1,"FAIL_QNUM success/clip/release mismatch");
  mark("QNUM_ALL_INTEGER_STAGE_VALUES");check_counts();mark("QNUM_FULL_OPERATION_COUNTS");
  if(dump_bytes!=9437184)$fatal(1,"FAIL_QNUM acceptedstream incomplete");$fclose(weight_file);weight_file=0;dump_enabled=0;mark("QNUM_ACCEPTED_WEIGHT_STREAM");
  repeat(6)begin @(negedge clk);if(!done_valid||!busy||in_ready||start_ready||done_error||done_saturated!==gold_sat[0])$fatal(1,"FAIL_QNUM heldDONE");end
  oldtake=dtake;done_ready=1;abort=1;@(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;
  if(dtake!=oldtake+1)$fatal(1,"FAIL_QNUM DONE not exactlyonce withabortready");
  tracking=0;running=0;repeat(4)@(negedge clk);
  if(busy||done_valid||input_stored||!in_ready||dtake!=oldtake+1)$fatal(1,"FAIL_QNUM no cleanreusable afterDONE");mark("QNUM_DONE_HOLD_ABORT_READY_ONCE");
  $display("QNUM_STATS cycles=%0d input=%0d Sreq=%0d Sack=%0d Mcmd=%0d Ncmd=%0d requests=%0d bytes=%0d Ttake=%0d",cycles,ingress,sreq,sack,mcmd,ncmd,requests,dump_bytes,ttake);
  $display("PASS_QNUM cases=%0d",cases);$finish;
 end
endmodule
