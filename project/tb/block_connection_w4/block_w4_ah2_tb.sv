`timescale 1ns/1ps
// Independent file goldens; this slice ends at two-head context, without Wo/TSP.
module block_w4_ah2_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,job_valid=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
 reg [31:0] job_generation=0,in_generation=0;reg [15:0] weights_version=16'h1234;
 reg [127:0] in_data=0;reg [8:0] in_index=0;reg in_last=0;
 wire job_ready,in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,done_partial;
 wire [8:0] done_words;wire [31:0] done_generation,out_generation;
 wire out_valid,out_last;wire [127:0] out_data;wire [9:0] out_index;
 wire wreq_valid;reg wreq_ready=1;wire [31:0] wreq_job;wire [15:0] wreq_seq,wreq_version;
 wire [1:0] wreq_matrix;wire [3:0] wreq_group;wire [4:0] wreq_chunk;
 wire w_ready;wire w_valid;wire [31:0] w_job;wire [15:0] w_seq,w_version;
 wire [3:0] w_index;wire w_last,w_error;wire [127:0] w_data;
 block_w4_ah2_top dut(.*);
 reg [127:0] gx[0:447],gw[0:32767],go[0:63],gn[0:255];
 reg [127:0] gkr[0:31],gv[0:31],gqr[0:63],gkn[0:31],gqn[0:63];
 reg [127:0] gkp[0:31],gqp[0:63],gkt[0:31],gqt[0:63];
 reg [127:0] gs[0:3],ge[0:3],gp[0:3],gc[0:63],base_actual[0:31];
 reg gsat=0;string vectors_dir,dump_dir,fixture_name;
 integer fd_x=0,fd_w=0,fd_o=0;reg dump_enabled=0;
 integer cycles=0,cases=0,next_generation=8192;reg [31:0] active_generation=0;
 reg obligation=0,tracking=0,launched=0,strict_math=1,inject_m=0,inject_n=0,inject_e=0;
 integer fault_mode=0;reg provider_enable=1,provider_gap=0;
 reg p_active=0;reg [31:0] p_job=0;reg [15:0] p_seq=0,p_version=0;
 reg [3:0] p_index=0;integer p_fault=0,p_delay=0;
 assign w_valid=p_active&&p_delay==0;
 assign w_job=p_job+(p_fault==3 ? 32'd1 : p_fault==7 ? -32'd1 : 32'd0);
 assign w_seq=p_seq+(p_fault==4 ? 16'd1 : 16'd0);
 assign w_version=p_version^(p_fault==5 ? 16'd1 : 16'd0);
 assign w_index=p_index^(p_fault==1 ? 4'd1 : 4'd0);
 assign w_last=p_fault==2 ? !(p_index==15) : p_index==15;
 assign w_error=p_fault==6;
 assign w_data=gw[{p_seq[10:0],4'd0}+{11'd0,p_index}];
 // NBA state updates keep payload stable across every accepting clock edge.
 always @(posedge clk)begin
  if(dut.leaf_reset)begin p_active<=0;p_index<=0;p_delay<=0;p_fault<=0;end
  else begin
   if(wreq_valid&&wreq_ready)begin
    if(p_active)$fatal(1,"FAIL_AH2 overlapping provider request");
    p_active<=provider_enable;p_job<=wreq_job;p_seq<=wreq_seq;p_version<=wreq_version;p_index<=0;
    p_fault<=fault_mode;p_delay<=provider_gap ? 3 : 0;
   end else if(p_delay!=0)p_delay<=p_delay-1;
   if(w_valid&&w_ready)begin
    if(p_index==15||p_fault!=0)p_active<=0;
    else begin p_index<=p_index+1'b1;p_delay<=provider_gap ? (int'(p_index)%3) : 0;end
   end
  end
 end
 integer jobs=0,dtakes=0,inputs=0,starts=0,sreq=0,sack=0,swrites=0,sreads=0;
 integer mc=0,mr=0,mexec=0,mread=0,loads=0,ldone=0,astream=0,bstream=0,wide=0;
 integer loader_errors=0,loader_errors_before=0;
 integer ns=0,nr=0,nc=0,nnr=0,es=0,er=0,ec=0,eor=0,wrq=0,wb=0,host=0;
 integer q0,a0,sw0,sr0,m0,mr0,me0,md0,l0,ld0,as0,bs0,wd0,ns0,nr0,nc0,nn0,es0,er0,ec0,eo0,wq0,wb0,ht0;
 integer input_good=0,input_acks=0,out_count=0,expected_request=0,n_source=0,n_gamma=0,n_exp=0,n_dst=0,n_count=0,n_mode=0;
 integer kv_writes_after_q=0;reg kv_frozen=0;
 reg pending=0,pwrite=0;reg [9:0] paddr=0;reg [127:0] pdata=0,ram[0:1023];reg written[0:1023];
 reg hold_done=0,hold_out=0,hold_wreq=0;reg [44:0] old_done;
 reg [170:0] old_out;reg [74:0] old_wreq;
 function automatic [127:0] score_replay;
  input integer token,head;begin score_replay=gs[token*2+head];if(token==0)score_replay[127:16]=0;end
 endfunction

 function automatic [127:0] aword;input integer st,row,tile;begin
  if(st==2)aword=gn[row*128+int'(dut.chunk_index)*4+tile];
  else if(st==5)aword=gqt[row*32+int'(dut.qhead)*16+int'(dut.chunk_index)*4+tile];
  else aword=gp[row*2+int'(dut.qhead)];
 end endfunction
 function automatic [511:0] bword;input integer st,tile,half;
  integer j,k,col,word_i;reg [127:0] tmp;begin bword=0;
   for(j=0;j<4;j=j+1)begin
    if(st==2)tmp=gw[(int'(dut.matrix)*512+int'(dut.group_index)*32+int'(dut.chunk_index))*16+tile*4+j];
    else if(st==5)begin col=half*4+j;tmp=0;
     if(col<2)tmp=gkt[col*16+int'(dut.chunk_index)*4+tile];
    end else begin
     col=half*4+j;tmp=0;
     tmp[15:0]=gv[int'(dut.group_index)][16*col+:16];
     tmp[31:16]=gv[16+int'(dut.group_index)][16*col+:16];
    end
    bword[128*j+:128]=tmp;
   end
  end
 endfunction
 function automatic [127:0] result_word;input integer row;begin
  if(dut.stage==2)begin
   if(dut.matrix==0)result_word=gkr[row*16+int'(dut.group_index)];
   else if(dut.matrix==1)result_word=gv[row*16+int'(dut.group_index)];
   else result_word=gqr[row*32+int'(dut.qhead)*16+int'(dut.group_index)];
  end else if(dut.stage==5)result_word=gs[row*2+int'(dut.qhead)];
  else result_word=gc[row*32+int'(dut.qhead)*16+int'(dut.group_index)];
 end endfunction
 function automatic [127:0] read_container;
  input integer row,half;integer j;reg [127:0] compact;reg signed [15:0] lane;begin
   compact=result_word(row);read_container=0;
   for(j=0;j<4;j=j+1)begin lane=compact[(half*4+j)*16+:16];read_container[32*j+:32]={{16{lane[15]}},lane};end
  end
 endfunction
 function automatic [127:0] expected_write;input integer addr;integer off,tile,slot,col;begin
  expected_write=0;
  if(!launched)begin
   off=addr<384 ? addr : addr-512+384;
   if(off<0||off>=448||off!=input_acks)$fatal(1,"FAIL_AH2 ingress association addr=%0d index=%0d",addr,input_acks);
   expected_write=gx[off];
  end else if(dut.owner==3)begin
   if(dut.stage==0)begin off=addr-n_dst;expected_write=gn[int'(dut.token_index)*128+off];end
   else if(dut.stage==3)begin off=addr-n_dst;
    expected_write=dut.matrix==0 ? gkn[int'(dut.token_index)*16+off] : gqn[int'(dut.token_index)*32+int'(dut.qhead)*16+off];
   end else if(addr==n_exp)expected_write=ge[int'(dut.token_index)*2+int'(dut.qhead)];
   else if(addr==n_dst)expected_write=gp[int'(dut.token_index)*2+int'(dut.qhead)];
   else $fatal(1,"FAIL_AH2 unexpected N write addr=%0d",addr);
  end else if(dut.owner==1)begin
   if(addr!=int'(dut.e_dst))$fatal(1,"FAIL_AH2 E destination");
   expected_write=dut.matrix==0 ? gkt[int'(dut.token_index)*16+int'(dut.rope_group)] : gqt[int'(dut.token_index)*32+int'(dut.qhead)*16+int'(dut.rope_group)];
  end else case(dut.local_tag)
   1:begin if(addr!=128+int'(dut.copy_index))$fatal(1,"FAIL_AH2 parameter relocation");expected_write=gx[384+int'(dut.copy_index)];end
   3,5:begin off=addr-320;tile=off/4;slot=off%4;expected_write=aword(int'(dut.stage),slot,tile);end
   6,7,13:expected_write=0;
   8:begin if(addr!=336+int'(dut.weight_index))$fatal(1,"FAIL_AH2 weight placement");expected_write=gw[(int'(dut.matrix)*512+int'(dut.group_index)*32+int'(dut.chunk_index))*16+int'(dut.weight_index)];end
   10,12:begin off=addr-336;tile=off/8;col=off%8;expected_write=gkt[col*16+int'(dut.chunk_index)*4+tile];end
   16:begin col=addr-336;expected_write=0;expected_write[15:0]=gv[int'(dut.group_index)][16*col+:16];expected_write[31:16]=gv[16+int'(dut.group_index)][16*col+:16];end
   17:expected_write=result_word(int'(dut.read_slot[1]));
   20:expected_write=dut.matrix==0 ? gkp[int'(dut.token_index)*16+int'(dut.rope_group)] : gqp[int'(dut.token_index)*32+int'(dut.qhead)*16+int'(dut.rope_group)];
   default:$fatal(1,"FAIL_AH2 unexpected local write tag=%0d addr=%0d",dut.local_tag,addr);
  endcase
 end endfunction
 task automatic bytes_out;input integer fd;input [127:0] data;begin
  for(integer j=0;j<16;j=j+1)$fwrite(fd,"%c",data[j*8+:8]);
 end endtask
 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>30000000)$fatal(1,"FAIL_AH2 watchdog state=%0d stage=%0d case=%0d",dut.state,dut.stage,cases);
  if(reset)begin pending=0;hold_done=0;hold_out=0;hold_wreq=0;obligation=0;end
  else begin
   if(hold_done&&(!done_valid||{done_error,done_saturated,done_partial,done_words,done_generation}!==old_done))$fatal(1,"FAIL_AH2 held DONE");
   hold_done=done_valid&&!done_ready;old_done={done_error,done_saturated,done_partial,done_words,done_generation};
   if(dut.leaf_reset)begin pending=0;hold_out=0;hold_wreq=0;end
   else begin
    if(hold_out&&(!out_valid||{out_data,out_index,out_last,out_generation}!==old_out))$fatal(1,"FAIL_AH2 output hold");
    if(hold_wreq&&(!wreq_valid||{wreq_job,wreq_seq,wreq_version,wreq_matrix,wreq_group,wreq_chunk}!==old_wreq))$fatal(1,"FAIL_AH2 request hold");
    hold_out=out_valid&&!out_ready;old_out={out_data,out_index,out_last,out_generation};
    hold_wreq=wreq_valid&&!wreq_ready;old_wreq={wreq_job,wreq_seq,wreq_version,wreq_matrix,wreq_group,wreq_chunk};
   end
   if(job_valid&&job_ready)begin
    if(obligation)$fatal(1,"FAIL_AH2 duplicate admitted job");obligation=1;active_generation=job_generation;jobs=jobs+1;
   end
   if(done_valid&&done_ready)begin
    if(!obligation||done_generation!==active_generation)$fatal(1,"FAIL_AH2 wrong completion identity");dtakes=dtakes+1;obligation=0;
   end
   if(tracking&&!dut.leaf_reset)begin
    if(in_valid&&in_ready)begin
     inputs=inputs+1;
     if(in_generation==active_generation&&in_index==input_good&&in_last==(input_good==447))begin
      if(in_data!==gx[input_good])$fatal(1,"FAIL_AH2 actual input payload");input_good=input_good+1;
      if(dump_enabled)bytes_out(fd_x,in_data);
     end
    end
    if(start_valid&&start_ready)begin
     if(input_good!=448||input_acks!=448)$fatal(1,"FAIL_AH2 start before full stored ACK");starts=starts+1;launched=1;
    end
    if(dut.n_req_valid&&dut.n_req_ready)begin
     n_source=dut.n_src_hold;n_gamma=dut.n_gamma_hold;n_exp=dut.n_exp_hold;n_dst=dut.n_dst_hold;n_count=dut.n_count_hold;n_mode=dut.n_mode_hold;
     if(dut.owner!=3||((dut.stage==0)&&(n_count!=1024||n_mode!=1))||((dut.stage==3)&&(n_count!=128||n_mode!=1))||((dut.stage==6)&&(n_count!=int'(dut.token_index)+1||n_mode!=0)))$fatal(1,"FAIL_AH2 N phase/count");
     ns=ns+1;
    end
    if(dut.n_rsp_valid&&dut.n_rsp_ready)nr=nr+1;
    if(dut.n_cmd_valid&&dut.n_cmd_ready)begin
     if(strict_math&&!inject_n)begin
      if(dut.n_cmd_op==5)begin
       if(dut.n_cmd_data!==ram[n_source+int'(dut.u_n_ctrl.word_index)]||dut.n_cmd_aux!==ram[n_gamma+int'(dut.u_n_ctrl.word_index)])$fatal(1,"FAIL_AH2 N norm replay");
      end
      if(dut.n_cmd_op==3&&dut.n_cmd_data!==score_replay(int'(dut.token_index),int'(dut.qhead)))$fatal(1,"FAIL_AH2 raw score replay");
      if(dut.n_cmd_op==6&&dut.n_cmd_data!==ge[int'(dut.token_index)*2+int'(dut.qhead)])$fatal(1,"FAIL_AH2 exact U16 EXP replay");
     end
     nc=nc+1;
    end
    if(dut.n_native_rsp_valid&&dut.n_native_rsp_ready)nnr=nnr+1;
    if(dut.e_req_valid&&dut.e_req_ready)begin
     if(dut.owner!=1||dut.u_e_ctrl.req_op!=9||dut.u_e_ctrl.req_shift!=14||dut.u_e_ctrl.req_count!=8||dut.u_e_ctrl.req_src_a!=374||dut.u_e_ctrl.req_src_b!=160+int'(dut.token_index)*16+int'(dut.rope_group))$fatal(1,"FAIL_AH2 actual split-half E route");es=es+1;
    end
    if(dut.e_rsp_valid&&dut.e_rsp_ready)er=er+1;
    if(dut.e_in_valid&&dut.e_in_ready)begin
     if(strict_math&&!inject_e&&(dut.e_in_a!==ram[374]||dut.e_in_b!==ram[160+int'(dut.token_index)*16+int'(dut.rope_group)]))$fatal(1,"FAIL_AH2 E operands");ec=ec+1;
    end
    if(dut.e_out_valid&&dut.e_out_ready)eor=eor+1;
    if(wreq_valid&&wreq_ready)begin
     if(wreq_seq!=expected_request||wreq_seq!=int'(wreq_matrix)*512+int'(wreq_group)*32+int'(wreq_chunk)||wreq_job!==active_generation||wreq_version!=16'h1234)$fatal(1,"FAIL_AH2 weight request order/version");
     if(wreq_matrix==2&&!kv_frozen)begin
      for(integer z=0;z<32;z=z+1)if(!written[192+z]||ram[192+z]!==gkt[z]||!written[224+z]||ram[224+z]!==gv[z])$fatal(1,"FAIL_AH2 shared KV incomplete");kv_frozen=1;
     end
     expected_request=expected_request+1;wrq=wrq+1;
    end
    if(w_valid&&w_ready)begin wb=wb+1;if(dump_enabled)bytes_out(fd_w,w_data);end
    if(dut.s_req&&dut.s_ready)begin
     if(pending)$fatal(1,"FAIL_AH2 two S owners outstanding");pending=1;pwrite=dut.s_we;paddr=dut.s_addr;pdata=dut.s_din;sreq=sreq+1;
     if(pwrite)begin
      if(strict_math&&pdata!==expected_write(int'(paddr)))$fatal(1,"FAIL_AH2 S write addr=%0d stage=%0d matrix=%0d tag=%0d got=%032h expected=%032h",paddr,dut.stage,dut.matrix,dut.local_tag,pdata,expected_write(int'(paddr)));
      if(kv_frozen&&paddr>=192&&paddr<256)$fatal(1,"FAIL_AH2 shared KV overwritten after Q starts");swrites=swrites+1;
     end else sreads=sreads+1;
    end
    if(dut.s_valid&&dut.s_take)begin
     if(!pending)$fatal(1,"FAIL_AH2 ACK without S request");sack=sack+1;
     if(pwrite)begin ram[paddr]=pdata;written[paddr]=1;if(!launched)input_acks=input_acks+1;end
     else if(!written[paddr]||dut.s_dout!==ram[paddr])$fatal(1,"FAIL_AH2 S read before write ACK/wrong version addr=%0d",paddr);
     pending=0;
    end
    if(dut.load_valid&&dut.load_ready)loads=loads+1;
    if(dut.load_done_valid&&dut.load_done_take)begin ldone=ldone+1;if(dut.load_done_error)loader_errors=loader_errors+1;end
    if(dut.u_s.feeder.mem_req&&dut.u_s.feeder.mem_ready)wide=wide+1;
    if(dut.a_valid&&dut.a_ready)begin
     if(strict_math&&(dut.a_bank!=0||!dut.a_wide||dut.a_row>1||dut.a_data!==aword(int'(dut.stage),int'(dut.a_row),int'(dut.a_tile))))$fatal(1,"FAIL_AH2 actual A128 loader layout");astream=astream+1;
    end
    if(dut.b_valid&&dut.b_ready)begin
     if(strict_math&&(dut.b_bank!=0||dut.b_wide!==(dut.stage!=2)||dut.b_data!==bword(int'(dut.stage),int'(dut.b_tile),int'(dut.b_half))))$fatal(1,"FAIL_AH2 actual B512 tile/half layout");bstream=bstream+1;
    end
    if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
     if(strict_math&&!inject_m)begin
      if(dut.m_cmd_op==4&&dut.m_cmd_data!==(dut.stage==5?64'd2896:64'd1))$fatal(1,"FAIL_AH2 M scale");
      if(dut.m_cmd_op==5&&dut.m_cmd_data!==(dut.stage==2?64'h107:dut.stage==5?64'h119:64'h10e))$fatal(1,"FAIL_AH2 M READ units");
      if(dut.m_cmd_op==10&&dut.m_cmd_data!==(dut.stage==2?(dut.chunk_index==0?64'h14885:64'h14881):dut.stage==5?(dut.chunk_index==0?64'h14287:64'h14283):64'h11827))$fatal(1,"FAIL_AH2 M fullK segment descriptor");
     end
     mc=mc+1;if(dut.m_cmd_op==10)mexec=mexec+1;if(dut.m_cmd_op==5)mread=mread+1;
    end
    if(dut.m_rsp_valid&&dut.m_rsp_ready)begin
     if(strict_math&&!inject_m&&!dut.m_rsp_error&&dut.m_phase==3&&dut.m_rsp_data!==read_container(int'(dut.read_slot[1]),int'(dut.read_slot[0])))$fatal(1,"FAIL_AH2 M S32 carrier/row READ");mr=mr+1;
    end
    if(out_valid&&out_ready)begin
     if(out_generation!==active_generation||out_index!=out_count||out_last!==(out_count==63)||out_data!==go[out_count])$fatal(1,"FAIL_AH2 context output count=%0d",out_count);
     if(fixture_name=="base"&&out_count<32)base_actual[out_count]=out_data;
     if(fixture_name=="future_changed"&&out_count<32&&out_data!==base_actual[out_count])$fatal(1,"FAIL_AH2 future token changed token0 both heads");
     if(dump_enabled)bytes_out(fd_o,out_data);out_count=out_count+1;host=host+1;
    end
   end
  end
 end

 task automatic tick;input integer count;begin repeat(count)begin @(posedge clk);#1;end end endtask
 task automatic mark;input string id;begin cases=cases+1;$display("CASE_PASS %s",id);end endtask
 task automatic load_fixture;input string name;begin
  fixture_name=name;
  $readmemh({vectors_dir,"/",name,"/input.hex"},gx);$readmemh({vectors_dir,"/",name,"/weights.hex"},gw);
  $readmemh({vectors_dir,"/",name,"/expected-output.hex"},go);
  $readmemh({vectors_dir,"/",name,"/stage/norm.hex"},gn);
  $readmemh({vectors_dir,"/",name,"/stage/kraw.hex"},gkr);$readmemh({vectors_dir,"/",name,"/stage/v.hex"},gv);$readmemh({vectors_dir,"/",name,"/stage/qraw.hex"},gqr);
  $readmemh({vectors_dir,"/",name,"/stage/k-rms.hex"},gkn);$readmemh({vectors_dir,"/",name,"/stage/q-rms.hex"},gqn);
  $readmemh({vectors_dir,"/",name,"/stage/k-pair.hex"},gkp);$readmemh({vectors_dir,"/",name,"/stage/q-pair.hex"},gqp);
  $readmemh({vectors_dir,"/",name,"/stage/k-rope.hex"},gkt);$readmemh({vectors_dir,"/",name,"/stage/q-rope.hex"},gqt);
  $readmemh({vectors_dir,"/",name,"/stage/scores.hex"},gs);$readmemh({vectors_dir,"/",name,"/stage/exp.hex"},ge);$readmemh({vectors_dir,"/",name,"/stage/p.hex"},gp);
  $readmemh({vectors_dir,"/",name,"/stage/context.hex"},gc);gsat=name=="boundary";
 end endtask
 task automatic snapshot;begin
  q0=sreq;a0=sack;sw0=swrites;sr0=sreads;m0=mc;mr0=mr;me0=mexec;md0=mread;l0=loads;ld0=ldone;as0=astream;bs0=bstream;wd0=wide;
  ns0=ns;nr0=nr;nc0=nc;nn0=nnr;es0=es;er0=er;ec0=ec;eo0=eor;wq0=wrq;wb0=wb;ht0=host;
 end endtask
 task automatic admit;begin
  @(negedge clk);tracking=1;launched=0;input_good=0;input_acks=0;out_count=0;expected_request=0;kv_frozen=0;
  for(integer z=0;z<1024;z=z+1)written[z]=0;
  snapshot();job_generation=next_generation;next_generation=next_generation+1;job_valid=1;
  do begin @(posedge clk);end while(!job_ready);@(negedge clk);job_valid=0;
  if(!busy)$fatal(1,"FAIL_AH2 accepted job not busy");
 end endtask
 task automatic send_word;input integer index;begin
  @(negedge clk);in_valid=1;in_data=gx[index];in_generation=active_generation;in_index=index[8:0];in_last=index==447;
  do begin @(posedge clk);end while(!in_ready);
  @(negedge clk);in_valid=0;
 end endtask
 task automatic frame;begin
  for(integer z=0;z<448;z=z+1)send_word(z);
  wait(input_stored);@(negedge clk);if(input_acks!=448||!start_ready)$fatal(1,"FAIL_AH2 complete input not stored");
 end endtask
 task automatic run_job;begin
  @(negedge clk);start_valid=1;do begin @(posedge clk);end while(!start_ready);@(negedge clk);start_valid=0;
 end endtask
 task automatic pulse_abort;begin
  @(negedge clk);abort=1;tick(1);@(negedge clk);abort=0;in_valid=0;start_valid=0;
 end endtask
 task automatic hard_reset;begin
  @(negedge clk);reset=1;in_valid=0;start_valid=0;job_valid=0;out_ready=0;done_ready=0;abort=0;
  tick(3);@(negedge clk);reset=0;tracking=0;fault_mode=0;provider_enable=1;provider_gap=0;strict_math=1;inject_m=0;inject_n=0;inject_e=0;tick(2);
  if(done_valid||busy||!job_ready)$fatal(1,"FAIL_AH2 hard reset lifecycle");
 end endtask
 task automatic finish;input bit err;input integer words;integer before_take;begin
  wait(done_valid);#1;
  if(done_error!==err||done_generation!==active_generation||done_words!=words||done_partial!==(err&&words!=0)||out_count!=words)$fatal(1,"FAIL_AH2 completion fields err=%0d words=%0d",done_error,done_words);
  if(!err&&done_saturated!==gsat)$fatal(1,"FAIL_AH2 saturation expected=%0d got=%0d",gsat,done_saturated);
  before_take=dtakes;tick(4);if(dtakes!=before_take||!done_valid||job_ready)$fatal(1,"FAIL_AH2 retained completion");
  @(negedge clk);done_ready=1;tick(1);@(negedge clk);done_ready=0;tick(2);
  if(dtakes!=before_take+1||done_valid||busy||!job_ready)$fatal(1,"FAIL_AH2 exactly once completion/reuse");tracking=0;
 end endtask
 task automatic normal_counts;begin
  if(sreq-q0!=85784||sack-a0!=85784||swrites-sw0!=67564||sreads-sr0!=18220||mc-m0!=2672||mr-mr0!=2672||mexec-me0!=2088||mread-md0!=388||loads-l0!=2088||ldone-ld0!=2088||astream-as0!=16512||bstream-bs0!=8320||wide-wd0!=16576||ns-ns0!=12||nr-nr0!=12||nc-nc0!=744||nnr-nn0!=744||es-es0!=96||er-er0!=96||ec-ec0!=96||eor-eo0!=96||wrq-wq0!=2048||wb-wb0!=32768||host-ht0!=64||pending)$fatal(1,"FAIL_AH2 normal counts S=%0d/%0d W=%0d R=%0d M=%0d/%0d EX=%0d RD=%0d L=%0d A=%0d B=%0d wide=%0d N=%0d/%0d E=%0d WR=%0d WB=%0d H=%0d",sreq-q0,sack-a0,swrites-sw0,sreads-sr0,mc-m0,mr-mr0,mexec-me0,mread-md0,loads-l0,astream-as0,bstream-bs0,wide-wd0,ns-ns0,nc-nc0,es-es0,wrq-wq0,wb-wb0,host-ht0);
 end endtask
 task automatic open_dumps;input string name;begin
  fd_x=$fopen({dump_dir,"/",name,"-accepted-input.bin"},"wb");fd_w=$fopen({dump_dir,"/",name,"-accepted-weights.bin"},"wb");fd_o=$fopen({dump_dir,"/",name,"-output.bin"},"wb");
  if(!fd_x||!fd_w||!fd_o)$fatal(1,"FAIL_AH2 dump open");dump_enabled=1;
 end endtask
 task automatic close_dumps;begin dump_enabled=0;$fclose(fd_x);$fclose(fd_w);$fclose(fd_o);end endtask
 task automatic normal;input string name;begin
  load_fixture(name);open_dumps(name);admit();frame();
  if(name=="boundary")begin
   @(negedge clk);force dut.permit_n_rsp=0;run_job();wait(dut.n_rsp_valid);tick(5);
   if(!dut.n_rsp_valid||dut.stage!=0)$fatal(1,"FAIL_AH2 N service response hold");
   @(negedge clk);release dut.permit_n_rsp;force dut.permit_m_rsp=0;
   wait(dut.m_rsp_valid);tick(5);if(!dut.m_rsp_valid||dut.m_phase!=0)$fatal(1,"FAIL_AH2 M response hold");
   @(negedge clk);release dut.permit_m_rsp;force dut.permit_e_rsp=0;
   wait(dut.e_rsp_valid);tick(5);if(!dut.e_rsp_valid||dut.stage!=4)$fatal(1,"FAIL_AH2 E service response hold");
   @(negedge clk);release dut.permit_e_rsp;
  end else run_job();
  wait(out_valid);tick(5);@(negedge clk);out_ready=1;wait(done_valid);#1;normal_counts();finish(0,64);@(negedge clk);out_ready=0;close_dumps();
 end endtask
 task automatic error_fixture;begin load_fixture("base");fault_mode=0;admit();frame();run_job();end endtask
 task automatic provider_error;input integer mode;integer reject_sreq,reject_swrites;begin
  @(negedge clk);force dut.permit_wrx=0;
  error_fixture(); // Install before the first weight request, while the bad beat is blocked.
  @(negedge clk);fault_mode=mode;
  do begin @(posedge clk);end while(!(wreq_valid&&wreq_ready));#1;
  reject_sreq=sreq;reject_swrites=swrites;
  @(negedge clk);release dut.permit_wrx;finish(1,0);fault_mode=0;
  if(sreq!=reject_sreq||swrites!=reject_swrites)$fatal(1,"FAIL_AH2 rejected weight caused S access mode=%0d",mode);
 end endtask
 task automatic inject_native_m;begin
  wait(dut.m_cmd_valid&&dut.m_cmd_ready&&dut.m_cmd_op==10);@(negedge clk);inject_m=1;force dut.m_cmd_data=64'h1488d;
  do begin @(posedge clk);end while(!(dut.m_cmd_valid&&dut.m_cmd_ready));@(negedge clk);release dut.m_cmd_data;inject_m=0;
 end endtask
 initial begin
  if(!$value$plusargs("vectors=%s",vectors_dir)||!$value$plusargs("dump_dir=%s",dump_dir))$fatal(1,"FAIL_AH2 require +vectors and +dump_dir");
  hard_reset();load_fixture("base");
  @(negedge clk);abort=1;tick(1);@(negedge clk);abort=0;tick(2);if(done_valid||busy)$fatal(1,"FAIL_AH2 idle abort created job");mark("AH2_IDLE_ABORT");
  admit();send_word(0);@(negedge clk);start_valid=1;tick(2);if(start_ready||launched)$fatal(1,"FAIL_AH2 early start accepted");@(negedge clk);start_valid=0;pulse_abort();finish(1,0);mark("AH2_PARTIAL_INPUT_EARLY_START_ABORT");
  admit();for(integer z=0;z<447;z=z+1)send_word(z);wait(input_acks==447);
  @(negedge clk);force dut.permit_s_rsp=0;send_word(447);wait(dut.s_valid);tick(4);if(input_stored||start_ready||input_acks!=447)$fatal(1,"FAIL_AH2 final ACK storage gate");
  @(negedge clk);release dut.permit_s_rsp;wait(input_stored);pulse_abort();finish(1,0);mark("AH2_FINAL_INPUT_ACK_GATE_PRESTART_TERMINAL");
  admit();@(negedge clk);in_valid=1;in_data=gx[0];in_generation=active_generation;in_index=1;in_last=0;tick(1);@(negedge clk);in_valid=0;finish(1,0);if(sreq!=q0)$fatal(1,"FAIL_AH2 bad X wrote S");mark("AH2_INPUT_BAD_INDEX");
  admit();@(negedge clk);in_valid=1;in_data=gx[0];in_generation=active_generation;in_index=0;in_last=1;tick(1);@(negedge clk);in_valid=0;finish(1,0);if(sreq!=q0)$fatal(1,"FAIL_AH2 bad last wrote S");mark("AH2_INPUT_BAD_LAST");
  admit();pulse_abort();finish(1,0);admit();@(negedge clk);in_valid=1;in_data=gx[0];in_generation=active_generation-1;in_index=0;in_last=0;tick(1);@(negedge clk);in_valid=0;finish(1,0);if(sreq!=q0)$fatal(1,"FAIL_AH2 stale X wrote S");mark("AH2_STALE_X_AFTER_NEW_ADMISSION");
  // Full normal jobs exercise no-reset reuse, fullK, all goldens, and raw dump SHA.
  normal("base");mark("AH2_BASE_FULL_H1024_TWO_HEADS");
  provider_gap=1;normal("future_changed");provider_gap=0;mark("AH2_FUTURE_CHANGED_CAUSAL_TOKEN0_BOTH_HEADS");
  normal("boundary");mark("AH2_BOUNDARY_SATURATION_FULL_H1024");
  load_fixture("base");admit();frame();@(negedge clk);weights_version=16'h4321;run_job();wait(wreq_valid);if(wreq_version!=16'h1234)$fatal(1,"FAIL_AH2 version not bound at admission");pulse_abort();finish(1,0);weights_version=16'h1234;mark("AH2_VERSION_CAPTURE_AT_JOB_ADMISSION");
  error_fixture();@(negedge clk);wreq_ready=0;wait(wreq_valid);tick(5);if(w_ready)$fatal(1,"FAIL_AH2 response ready before request accept");@(negedge clk);wreq_ready=1;wait(w_valid&&w_ready);pulse_abort();finish(1,0);mark("AH2_PROVIDER_REQUEST_BACKPRESSURE");
  error_fixture();wait(dut.state==16);@(negedge clk);force dut.permit_wrx=0;tick(5);if(w_ready||!w_valid)$fatal(1,"FAIL_AH2 weight response hold");@(negedge clk);release dut.permit_wrx;pulse_abort();finish(1,0);mark("AH2_PROVIDER_RESPONSE_BACKPRESSURE");
  provider_error(1);mark("AH2_WEIGHT_BAD_INDEX");provider_error(2);mark("AH2_WEIGHT_BAD_LAST");provider_error(3);mark("AH2_WEIGHT_FUTURE_JOB");provider_error(4);mark("AH2_WEIGHT_WRONG_SEQUENCE");provider_error(5);mark("AH2_WEIGHT_WRONG_VERSION");provider_error(6);mark("AH2_PROVIDER_ERROR_FLAG");provider_error(7);mark("AH2_WEIGHT_OLD_JOB_STRICT_REJECT");
  error_fixture();wait(dut.local_tag==8&&dut.weight_index==15&&dut.state==6&&dut.s_valid);@(negedge clk);force dut.permit_s_rsp=0;tick(4);if(dut.load_valid||dut.weight_index!=15||dut.request_seq!=0)$fatal(1,"FAIL_AH2 loader before last weight write ACK");@(negedge clk);release dut.permit_s_rsp;pulse_abort();finish(1,0);mark("AH2_WEIGHT_S_ACK_GATE");
  error_fixture();wait(dut.state==13);@(negedge clk);force dut.permit_load=0;tick(4);if(dut.load_valid)$fatal(1,"FAIL_AH2 loader permit");@(negedge clk);release dut.permit_load;wait(dut.load_valid&&dut.load_ready);pulse_abort();finish(1,0);mark("AH2_LOADER_STALL_ABORT");
  error_fixture();wait(dut.load_valid);loader_errors_before=loader_errors;@(negedge clk);force dut.u_s.load_tiles=3'd0;
  do begin @(posedge clk);end while(!(dut.load_valid&&dut.load_ready));@(negedge clk);release dut.u_s.load_tiles;
  finish(1,0);if(loader_errors!=loader_errors_before+1)$fatal(1,"FAIL_AH2 missing real loader error response");mark("AH2_NATIVE_LOADER_ILLEGAL_DESCRIPTOR_ERROR");
  error_fixture();@(negedge clk);force dut.permit_n_rsp=0;wait(dut.n_rsp_valid);tick(5);
  if(dut.owner!=3||dut.token_index!=0||dut.stage!=0||ns-ns0!=1||!dut.n_rsp_valid)$fatal(1,"FAIL_AH2 held N lease advanced");
  pulse_abort();@(negedge clk);release dut.permit_n_rsp;finish(1,0);mark("AH2_N_RESPONSE_HELD_LEASE_ABORT");
  error_fixture();wait(dut.m_cmd_valid&&dut.m_cmd_op==10);@(negedge clk);inject_m=1;force dut.m_cmd_data=64'h1488d;do begin @(posedge clk);end while(!(dut.m_cmd_valid&&dut.m_cmd_ready));@(negedge clk);release dut.m_cmd_data;inject_m=0;finish(1,0);mark("AH2_NATIVE_M_RESERVED_DESCRIPTOR_ERROR");
  error_fixture(); // Native N first BEGIN of a fresh input RMS group.
  wait(dut.n_cmd_valid&&dut.n_cmd_op==1);@(negedge clk);inject_n=1;force dut.n_cmd_op=4'd15;do begin @(posedge clk);end while(!(dut.n_cmd_valid&&dut.n_cmd_ready));@(negedge clk);release dut.n_cmd_op;inject_n=0;finish(1,0);mark("AH2_NATIVE_N_ERROR_COORDINATED_RESET");
  error_fixture();wait(dut.e_in_valid);@(negedge clk);inject_e=1;force dut.e_in_op=4'd14;do begin @(posedge clk);end while(!(dut.e_in_valid&&dut.e_in_ready));@(negedge clk);release dut.e_in_op;inject_e=0;finish(1,0);mark("AH2_NATIVE_E_ROPE_ERROR");
  error_fixture();wait(dut.h_rsp_valid&&dut.owner==3);@(negedge clk);force dut.h_rsp_error=1'b1;do begin @(posedge clk);end while(!(dut.h_rsp_valid&&dut.h_rsp_ready));@(negedge clk);release dut.h_rsp_error;finish(1,0);mark("AH2_S_HELPER_BOUNDARY_ERROR");
  load_fixture("base");admit();send_word(0);hard_reset();mark("AH2_HARD_RESET_PARTIAL_INPUT_NO_DONE");
  error_fixture();wait(dut.state==16);hard_reset();mark("AH2_HARD_RESET_WEIGHT_PENDING_NO_DONE");
  // Output stall/prefix error: observed prefix remains visible, no global rollback.
  error_fixture();wait(out_valid);tick(5);@(negedge clk);out_ready=1;tick(1);@(negedge clk);out_ready=0;tick(2);pulse_abort();finish(1,1);mark("AH2_OUTPUT_PREFIX_ABORT_PARTIAL");
  error_fixture();wait(out_valid);tick(4);hard_reset();mark("AH2_HARD_RESET_HELD_OUTPUT");
  // Recovery completes all stages after native errors/reset; completion survives abort.
  error_fixture();@(negedge clk);out_ready=1;wait(done_valid);#1;normal_counts();
  tick(4);@(negedge clk);abort=1;done_ready=1;tick(1);@(negedge clk);abort=0;done_ready=0;out_ready=0;tick(2);
  if(done_valid||busy||!job_ready||obligation)$fatal(1,"FAIL_AH2 DONE abort+ready duplicate/lost completion");tracking=0;mark("AH2_FULL_RECOVERY_DONE_ABORT_READY");
  if(cases!=32)$fatal(1,"FAIL_AH2 declared case count got=%0d",cases);
  $display("AH2_COUNTS cycles=%0d jobs=%0d X=%0d Sreq=%0d Sack=%0d M=%0d/%0d N=%0d/%0d E=%0d/%0d wreq=%0d W=%0d host=%0d done=%0d",cycles,jobs,inputs,sreq,sack,mc,mr,nc,nnr,ec,eor,wrq,wb,host,dtakes);
  $display("PASS_AH2 cases=%0d",cases);$finish;
 end
endmodule
