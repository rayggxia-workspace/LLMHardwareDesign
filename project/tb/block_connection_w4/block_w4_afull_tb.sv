`timescale 1ns/1ps
// Independent file goldens: H1024/Sq2/Q16/KV8/D128 plus Wo and original-X residual.
// One native M/N/E/S/T set; all payload movement is observed on real handshakes.
module block_w4_afull_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,job_valid=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
 reg [31:0] job_generation=0,in_generation=0;reg [15:0] weights_version=16'h1234;
 reg [127:0] in_data=0;reg [8:0] in_index=0;reg in_last=0;
 wire job_ready,in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,done_partial;
 wire [8:0] done_words;wire [31:0] done_generation,out_generation;
 wire out_valid,out_last;wire [127:0] out_data;wire [9:0] out_index;
 wire wreq_valid;reg wreq_ready=1;wire [31:0] wreq_job;wire [15:0] wreq_seq,wreq_version;
 wire [1:0] wreq_matrix;wire [3:0] wreq_head;wire [6:0] wreq_group;wire [5:0] wreq_chunk;
 wire w_ready;wire w_valid;wire [31:0] w_job;wire [15:0] w_seq,w_version;
 wire [3:0] w_index;wire w_last,w_error;wire [127:0] w_data;
 block_w4_afull_top dut(.*);
 reg [127:0] gx[0:447],gw[0:393215],go[0:255],gn[0:255];
 reg [127:0] gkr[0:255],gv[0:255],gqr[0:511],gkn[0:255],gqn[0:511];
 reg [127:0] gkp[0:255],gqp[0:511],gkt[0:255],gqt[0:511];
 reg [127:0] gs[0:31],ge[0:31],gp[0:31],gc[0:511],gwo[0:255],base_actual[0:127],base_context[0:255];
 reg gsat=0;reg gold_sat_word[0:0];string vectors_dir,dump_dir,fixture_name;
 integer fd_x=0,fd_w=0,fd_o=0;reg dump_enabled=0;
 integer cycles=0,cases=0,next_generation=8192;reg [31:0] active_generation=0;reg [15:0] active_version=0;
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
 assign w_data=gw[int'(p_seq)*16+int'(p_index)];
 // NBA state updates keep payload stable across every accepting clock edge.
 always @(posedge clk)begin
  if(dut.leaf_reset)begin p_active<=0;p_index<=0;p_delay<=0;p_fault<=0;end
  else begin
   if(wreq_valid&&wreq_ready)begin
    if(p_active)$fatal(1,"FAIL_AFULL overlapping provider request");
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
 integer kv_writes_after_q=0;reg kv_frozen=0;integer frozen_kv=-1,context_acks=0,padding_acks=0,rawtakes=0,capture_acks=0,residual_acks=0;
 reg context_seen[0:511],padding_seen[0:3][0:1];
 integer begins=0,commits=0,twrites=0,ttakes=0,releases=0,tb0,tc0,tw0,tt0,tr0,raw_released=0,out_released=0;
 reg inject_meta=0;
 reg pending=0,pwrite=0;integer pstage=0,powner=0,ptag=0,pstate=0;reg [9:0] paddr=0;reg [127:0] pdata=0,ram[0:1023];reg written[0:1023];
 reg hold_done=0,hold_out=0,hold_wreq=0;reg [43:0] old_done;
 reg [170:0] old_out;reg [82:0] old_wreq;
 function automatic integer stream_seq;input integer matrix,kv,head,group_i,chunk;begin
  if(matrix==0)stream_seq=kv*2048+group_i*32+chunk;
  else if(matrix==1)stream_seq=kv*2048+512+group_i*32+chunk;
  else if(matrix==2)stream_seq=(head/2)*2048+1024+(head%2)*512+group_i*32+chunk;
  else stream_seq=16384+group_i*64+chunk;
 end endfunction
 function automatic bit is_padding;input integer addr;begin
  is_padding=addr>=320&&addr<336&&(addr%4==2||addr%4==3);
 end endfunction
 function automatic [127:0] score_replay;
  input integer token,head;begin score_replay=gs[token*16+head];if(token==0)score_replay[127:16]=0;end
 endfunction

 function automatic [127:0] aword;input integer st,row,tile;begin
  if(st==2)aword=gn[row*128+int'(dut.chunk_index)*4+tile];
  else if(st==5)aword=gqt[row*256+int'(dut.q_head)*16+int'(dut.chunk_index)*4+tile];
  else if(st==7)aword=gp[row*16+int'(dut.q_head)];
  else aword=gc[row*256+int'(dut.chunk_index)*4+tile];
 end endfunction
 function automatic [511:0] bword;input integer st,tile,half;
  integer j,col;reg [127:0] tmp;begin bword=0;
   for(j=0;j<4;j=j+1)begin
    if(st==2||st==8)tmp=gw[stream_seq(int'(dut.matrix),int'(dut.kv_head),int'(dut.q_head),int'(dut.group_index),int'(dut.chunk_index))*16+tile*4+j];
    else if(st==5)begin col=half*4+j;tmp=0;
     if(col<2)tmp=gkt[col*128+int'(dut.kv_head)*16+int'(dut.chunk_index)*4+tile];
    end else begin
     col=half*4+j;tmp=0;
     tmp[15:0]=gv[int'(dut.kv_head)*16+int'(dut.group_index)][16*col+:16];
     tmp[31:16]=gv[128+int'(dut.kv_head)*16+int'(dut.group_index)][16*col+:16];
    end
    bword[128*j+:128]=tmp;
   end
  end
 endfunction
 function automatic [127:0] result_word;input integer row;begin
  if(dut.stage==2)begin
   if(dut.matrix==0)result_word=gkr[row*128+int'(dut.kv_head)*16+int'(dut.group_index)];
   else if(dut.matrix==1)result_word=gv[row*128+int'(dut.kv_head)*16+int'(dut.group_index)];
   else result_word=gqr[row*256+int'(dut.q_head)*16+int'(dut.group_index)];
  end else if(dut.stage==5)result_word=gs[row*16+int'(dut.q_head)];
  else if(dut.stage==7)result_word=gc[row*256+int'(dut.q_head)*16+int'(dut.group_index)];
  else result_word=gwo[row*128+int'(dut.group_index)];
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
   if(off<0||off>=448||off!=input_acks)$fatal(1,"FAIL_AFULL ingress association addr=%0d index=%0d",addr,input_acks);
   expected_write=gx[off];
  end else if(dut.owner==3)begin
   if(dut.stage==0)begin off=addr-n_dst;expected_write=gn[int'(dut.token_index)*128+off];end
   else if(dut.stage==3)begin off=addr-n_dst;
    expected_write=dut.matrix==0 ? gkn[int'(dut.token_index)*128+int'(dut.kv_head)*16+off] : gqn[int'(dut.token_index)*256+int'(dut.q_head)*16+off];
   end else if(addr==n_exp)expected_write=ge[int'(dut.token_index)*16+int'(dut.q_head)];
   else if(addr==n_dst)expected_write=gp[int'(dut.token_index)*16+int'(dut.q_head)];
   else $fatal(1,"FAIL_AFULL unexpected N write addr=%0d",addr);
  end else if(dut.owner==1)begin
   if(addr!=int'(dut.e_dst))$fatal(1,"FAIL_AFULL E destination");
   if(dut.stage==4)expected_write=dut.matrix==0 ? gkt[int'(dut.token_index)*128+int'(dut.kv_head)*16+int'(dut.rope_group)] : gqt[int'(dut.token_index)*256+int'(dut.q_head)*16+int'(dut.rope_group)];
   else expected_write=go[int'(dut.row_index)*128+int'(dut.group_index)];
  end else if(addr==258&&dut.stage==9&&dut.owner==0)begin
   if(addr!=258||rawtakes!=capture_acks+1)$fatal(1,"FAIL_AFULL raw T capture association");
   expected_write=gx[(capture_acks%2)*128+capture_acks/2];
  end else case(dut.local_tag)
   1:begin if(addr!=128+int'(dut.copy_index))$fatal(1,"FAIL_AFULL parameter relocation");expected_write=gx[384+int'(dut.copy_index)];end
   3,5:begin off=addr-320;tile=off/4;slot=off%4;expected_write=aword(int'(dut.stage),slot,tile);end
   13:expected_write=0;
   8:begin if(addr!=336+int'(dut.weight_index))$fatal(1,"FAIL_AFULL weight placement");expected_write=gw[stream_seq(int'(dut.matrix),int'(dut.kv_head),int'(dut.q_head),int'(dut.group_index),int'(dut.chunk_index))*16+int'(dut.weight_index)];end
   10,12:begin off=addr-336;tile=off/8;col=off%8;expected_write=gkt[col*128+int'(dut.kv_head)*16+int'(dut.chunk_index)*4+tile];end
   16:begin col=addr-336;expected_write=0;expected_write[15:0]=gv[int'(dut.kv_head)*16+int'(dut.group_index)][16*col+:16];expected_write[31:16]=gv[128+int'(dut.kv_head)*16+int'(dut.group_index)][16*col+:16];end
   17:expected_write=result_word(int'(dut.read_slot[1]));
   20:expected_write=dut.matrix==0 ? gkp[int'(dut.token_index)*128+int'(dut.kv_head)*16+int'(dut.rope_group)] : gqp[int'(dut.token_index)*256+int'(dut.q_head)*16+int'(dut.rope_group)];
   22:begin if(!is_padding(addr)||padding_acks>=8)$fatal(1,"FAIL_AFULL padding write lifecycle");expected_write=0;end
   default:$fatal(1,"FAIL_AFULL unexpected local write tag=%0d addr=%0d",dut.local_tag,addr);
  endcase
 end endfunction
 task automatic bytes_out;input integer fd;input [127:0] data;begin
  for(integer j=0;j<16;j=j+1)$fwrite(fd,"%c",data[j*8+:8]);
 end endtask
 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>200000000)$fatal(1,"FAIL_AFULL watchdog state=%0d stage=%0d case=%0d",dut.state,dut.stage,cases);
  if(reset)begin pending=0;hold_done=0;hold_out=0;hold_wreq=0;obligation=0;end
  else begin
   if(hold_done&&(!done_valid||{done_error,done_saturated,done_partial,done_words,done_generation}!==old_done))$fatal(1,"FAIL_AFULL held DONE");
   hold_done=done_valid&&!done_ready;old_done={done_error,done_saturated,done_partial,done_words,done_generation};
   if(dut.leaf_reset)begin pending=0;hold_out=0;hold_wreq=0;end
   else begin
    if(hold_out&&!inject_meta&&(!out_valid||{out_data,out_index,out_last,out_generation}!==old_out))$fatal(1,"FAIL_AFULL output hold");
    if(hold_wreq&&(!wreq_valid||{wreq_job,wreq_seq,wreq_version,wreq_matrix,wreq_head,wreq_group,wreq_chunk}!==old_wreq))$fatal(1,"FAIL_AFULL request hold");
    hold_out=out_valid&&!out_ready&&!inject_meta;old_out={out_data,out_index,out_last,out_generation};
    hold_wreq=wreq_valid&&!wreq_ready;old_wreq={wreq_job,wreq_seq,wreq_version,wreq_matrix,wreq_head,wreq_group,wreq_chunk};
   end
   if(job_valid&&job_ready)begin
    if(obligation)$fatal(1,"FAIL_AFULL duplicate admitted job");obligation=1;active_generation=job_generation;active_version=weights_version;jobs=jobs+1;
   end
   if(done_valid&&done_ready)begin
    if(!obligation||done_generation!==active_generation)$fatal(1,"FAIL_AFULL wrong completion identity");dtakes=dtakes+1;obligation=0;
   end
   if(tracking&&!dut.leaf_reset)begin
    if(in_valid&&in_ready)begin
     inputs=inputs+1;
     if(in_generation==active_generation&&in_index==input_good&&in_last==(input_good==447))begin
      if(in_data!==gx[input_good])$fatal(1,"FAIL_AFULL actual input payload");input_good=input_good+1;
      if(dump_enabled)bytes_out(fd_x,in_data);
     end
    end
    if(start_valid&&start_ready)begin
     if(input_good!=448||input_acks!=448)$fatal(1,"FAIL_AFULL start before full stored ACK");starts=starts+1;launched=1;
    end
    if(dut.n_req_valid&&dut.n_req_ready)begin
     n_source=dut.n_src_hold;n_gamma=dut.n_gamma_hold;n_exp=dut.n_exp_hold;n_dst=dut.n_dst_hold;n_count=dut.n_count_hold;n_mode=dut.n_mode_hold;
     if(dut.owner!=3||((dut.stage==0)&&(n_count!=1024||n_mode!=1))||((dut.stage==3)&&(n_count!=128||n_mode!=1))||((dut.stage==6)&&(n_count!=int'(dut.token_index)+1||n_mode!=0)))$fatal(1,"FAIL_AFULL N phase/count");
     ns=ns+1;
    end
    if(dut.n_rsp_valid&&dut.n_rsp_ready)nr=nr+1;
    if(dut.n_cmd_valid&&dut.n_cmd_ready)begin
     if(strict_math&&!inject_n)begin
      if(dut.n_cmd_op==5)begin
       if(dut.n_cmd_data!==ram[n_source+int'(dut.u_n_ctrl.word_index)]||dut.n_cmd_aux!==ram[n_gamma+int'(dut.u_n_ctrl.word_index)])$fatal(1,"FAIL_AFULL N norm replay");
      end
      if(dut.n_cmd_op==3&&dut.n_cmd_data!==score_replay(int'(dut.token_index),int'(dut.q_head)))$fatal(1,"FAIL_AFULL raw score replay");
      if(dut.n_cmd_op==6&&dut.n_cmd_data!==ge[int'(dut.token_index)*16+int'(dut.q_head)])$fatal(1,"FAIL_AFULL exact U16 EXP replay");
     end
     nc=nc+1;
    end
    if(dut.n_native_rsp_valid&&dut.n_native_rsp_ready)nnr=nnr+1;
    if(dut.e_req_valid&&dut.e_req_ready)begin
     if(dut.owner!=1||dut.u_e_ctrl.req_count!=8)$fatal(1,"FAIL_AFULL E owner/count");
     if(dut.stage==4)begin
      if(dut.u_e_ctrl.req_op!=9||dut.u_e_ctrl.req_shift!=14||dut.u_e_ctrl.req_src_a!=374||dut.u_e_ctrl.req_src_b!=160+int'(dut.token_index)*16+int'(dut.rope_group))$fatal(1,"FAIL_AFULL actual split-half E route");
     end else begin
      if(dut.stage!=9||dut.u_e_ctrl.req_op!=0||dut.u_e_ctrl.req_shift!=0||dut.u_e_ctrl.req_src_a!=256+int'(dut.row_index)||dut.u_e_ctrl.req_src_b!=258||rawtakes!=capture_acks||rawtakes!=residual_acks+1)$fatal(1,"FAIL_AFULL residual E before capture ACK/route");
     end
     es=es+1;
    end
    if(dut.e_rsp_valid&&dut.e_rsp_ready)er=er+1;
    if(dut.e_in_valid&&dut.e_in_ready)begin
     if(strict_math&&!inject_e)begin
      if(dut.stage==4&&(dut.e_in_a!==ram[374]||dut.e_in_b!==ram[160+int'(dut.token_index)*16+int'(dut.rope_group)]))$fatal(1,"FAIL_AFULL RoPE E operands");
      if(dut.stage==9&&(dut.e_in_a!==gwo[int'(dut.row_index)*128+int'(dut.group_index)]||dut.e_in_b!==gx[int'(dut.row_index)*128+int'(dut.group_index)]))$fatal(1,"FAIL_AFULL residual original X/Wo operands");
     end
     ec=ec+1;
    end
    if(dut.e_out_valid&&dut.e_out_ready)eor=eor+1;
    if(wreq_valid&&wreq_ready)begin
     if(wreq_seq!=expected_request||wreq_seq!=stream_seq(int'(wreq_matrix),int'(dut.kv_head),int'(dut.q_head),int'(wreq_group),int'(wreq_chunk))||wreq_job!==active_generation||wreq_version!==active_version)$fatal(1,"FAIL_AFULL weight request order/version");
     if(wreq_head!==(wreq_matrix==3?4'd0:wreq_matrix==2?dut.q_head:{1'b0,dut.kv_head}))$fatal(1,"FAIL_AFULL request head identity");
     if(wreq_matrix==0&&wreq_group==0&&wreq_chunk==0)begin
      if(context_acks!=int'(dut.kv_head)*64)$fatal(1,"FAIL_AFULL overwrote KV before two Q contexts complete");kv_frozen=0;
     end
     if(wreq_matrix==2&&wreq_group==0&&wreq_chunk==0&&!dut.q_head[0])begin
      for(integer token=0;token<2;token=token+1)for(integer z=0;z<16;z=z+1)
       if(!written[192+token*16+z]||ram[192+token*16+z]!==gkt[token*128+int'(dut.kv_head)*16+z]||!written[224+token*16+z]||ram[224+token*16+z]!==gv[token*128+int'(dut.kv_head)*16+z])$fatal(1,"FAIL_AFULL shared KV incomplete");
      kv_frozen=1;frozen_kv=int'(dut.kv_head);
     end
     if(wreq_matrix==2&&(frozen_kv!=int'(dut.kv_head)||!kv_frozen||int'(dut.q_head)/2!=int'(dut.kv_head)))$fatal(1,"FAIL_AFULL GQA KV ownership");
     if(wreq_matrix==3)begin
      if(context_acks!=512||rawtakes!=2*int'(dut.group_index))$fatal(1,"FAIL_AFULL Wo context/preceding residual barrier");
      for(integer z=0;z<512;z=z+1)if(!context_seen[z])$fatal(1,"FAIL_AFULL Wo before complete context");
     end
     expected_request=expected_request+1;wrq=wrq+1;
    end
    if(w_valid&&w_ready)begin wb=wb+1;if(dump_enabled)bytes_out(fd_w,w_data);end
    if(dut.s_req&&dut.s_ready)begin
     if(pending)$fatal(1,"FAIL_AFULL two S owners outstanding");pending=1;pwrite=dut.s_we;paddr=dut.s_addr;pdata=dut.s_din;pstage=int'(dut.stage);powner=int'(dut.owner);ptag=int'(dut.local_tag);pstate=int'(dut.state);sreq=sreq+1;
     if(pwrite)begin
      if(strict_math&&pdata!==expected_write(int'(paddr)))$fatal(1,"FAIL_AFULL S write addr=%0d stage=%0d matrix=%0d tag=%0d got=%032h expected=%032h",paddr,dut.stage,dut.matrix,dut.local_tag,pdata,expected_write(int'(paddr)));
      if(kv_frozen&&dut.stage!=9&&paddr>=192&&paddr<256)$fatal(1,"FAIL_AFULL shared KV overwritten during Q pair");
      if(launched&&is_padding(int'(paddr))&&dut.stage!=11)$fatal(1,"FAIL_AFULL padding overwritten after initialization");
      swrites=swrites+1;
     end else sreads=sreads+1;
    end
    if(dut.s_valid&&dut.s_take)begin
     if(!pending)$fatal(1,"FAIL_AFULL ACK without S request");sack=sack+1;
     if(pwrite)begin
      ram[paddr]=pdata;written[paddr]=1;if(!launched)input_acks=input_acks+1;
      if(pstage==11&&ptag==22)begin
       if(padding_seen[(int'(paddr)-320)/4][int'(paddr)%4-2])$fatal(1,"FAIL_AFULL duplicate padding ACK");
       padding_seen[(int'(paddr)-320)/4][int'(paddr)%4-2]=1;padding_acks=padding_acks+1;
      end
      if(pstage==7&&powner==0&&ptag==17)begin
       if(paddr<512||context_seen[int'(paddr)-512])$fatal(1,"FAIL_AFULL context missing/duplicate address");
       context_seen[int'(paddr)-512]=1;context_acks=context_acks+1;
       if(paddr<768)begin
        if(fixture_name=="base")base_context[int'(paddr)-512]=pdata;
        if(fixture_name=="future_changed"&&pdata!==base_context[int'(paddr)-512])$fatal(1,"FAIL_AFULL future token changed token0 context any Q head");
       end
      end
      if(pstage==9&&powner==0&&paddr==258)capture_acks=capture_acks+1;
      if(pstage==9&&powner==1)residual_acks=residual_acks+1;
     end
     else if(!written[paddr]||dut.s_dout!==ram[paddr])$fatal(1,"FAIL_AFULL S read before write ACK/wrong version addr=%0d",paddr);
     pending=0;
    end
    if(dut.load_valid&&dut.load_ready)begin
     if(padding_acks!=8)$fatal(1,"FAIL_AFULL loader before all padding ACK");
     for(integer z=0;z<4;z=z+1)if(ram[322+4*z]!==0||ram[323+4*z]!==0)$fatal(1,"FAIL_AFULL padding not retained");
     loads=loads+1;
    end
    if(dut.load_done_valid&&dut.load_done_take)begin ldone=ldone+1;if(dut.load_done_error)loader_errors=loader_errors+1;end
    if(dut.u_s.feeder.mem_req&&dut.u_s.feeder.mem_ready)wide=wide+1;
    if(dut.a_valid&&dut.a_ready)begin
     if(strict_math&&(dut.a_bank!=0||!dut.a_wide||dut.a_row>1||dut.a_data!==aword(int'(dut.stage),int'(dut.a_row),int'(dut.a_tile))))$fatal(1,"FAIL_AFULL actual A128 loader layout");astream=astream+1;
    end
    if(dut.b_valid&&dut.b_ready)begin
     if(strict_math&&(dut.b_bank!=0||dut.b_wide!==(dut.stage!=2&&dut.stage!=8)||dut.b_data!==bword(int'(dut.stage),int'(dut.b_tile),int'(dut.b_half))))$fatal(1,"FAIL_AFULL actual B512 tile/half layout");bstream=bstream+1;
    end
    if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
     if(strict_math&&!inject_m)begin
      if(dut.m_cmd_op==4&&dut.m_cmd_data!==(dut.stage==5?64'd2896:64'd1))$fatal(1,"FAIL_AFULL M scale");
      if(dut.m_cmd_op==5&&dut.m_cmd_data!==((dut.stage==2||dut.stage==8)?64'h107:dut.stage==5?64'h119:64'h10e))$fatal(1,"FAIL_AFULL M READ units");
      if(dut.m_cmd_op==10&&dut.m_cmd_data!==((dut.stage==2||dut.stage==8)?(dut.chunk_index==0?64'h14885:64'h14881):dut.stage==5?(dut.chunk_index==0?64'h14287:64'h14283):64'h11827))$fatal(1,"FAIL_AFULL M fullK segment descriptor");
     end
     mc=mc+1;if(dut.m_cmd_op==10)mexec=mexec+1;if(dut.m_cmd_op==5)mread=mread+1;
    end
    if(dut.m_rsp_valid&&dut.m_rsp_ready)begin
     if(strict_math&&!inject_m&&!dut.m_rsp_error&&dut.m_phase==3&&dut.m_rsp_data!==read_container(int'(dut.read_slot[1]),int'(dut.read_slot[0])))$fatal(1,"FAIL_AFULL M S32 carrier/row READ");mr=mr+1;
    end
    if(dut.t_begin_valid&&dut.t_begin_ready)begin
     if(dut.u_t.begin_generation!==active_generation||dut.u_t.begin_words!=256)$fatal(1,"FAIL_AFULL T begin count/generation");
     if(dut.u_t.begin_owner==1)begin
      if(begins-tb0!=0||input_acks!=448||ns!=ns0)$fatal(1,"FAIL_AFULL raw spool before complete input/Norm");
     end else if(dut.u_t.begin_owner==2)begin
      if(raw_released!=1||residual_acks!=256||capture_acks!=256||context_acks!=512)$fatal(1,"FAIL_AFULL output T begins before source release/final ACK");
     end else $fatal(1,"FAIL_AFULL T begin owner");
     begins=begins+1;
    end
    if(dut.t_write_valid&&dut.t_write_ready)begin
     if(dut.t_write_index!=(twrites-tw0)%256)$fatal(1,"FAIL_AFULL T write ordering");
     if(dut.t_owner==1)begin
      if(dut.u_t.write_data!==gx[(int'(dut.t_write_index)%2)*128+int'(dut.t_write_index)/2])$fatal(1,"FAIL_AFULL real raw T payload/interleave");
     end else if(dut.t_owner==2)begin
      if(dut.u_t.write_data!==go[int'(dut.t_write_index)])$fatal(1,"FAIL_AFULL real output T payload");
     end else $fatal(1,"FAIL_AFULL T write owner");twrites=twrites+1;
    end
    if(dut.t_commit_valid&&dut.t_commit_ready)begin
     if(twrites-tw0!=(commits-tc0+1)*256)$fatal(1,"FAIL_AFULL T commit before all writes");commits=commits+1;
    end
    if(dut.t_read_valid&&!inject_meta)begin
     if(dut.t_generation!==active_generation||dut.t_word_count!=256||dut.t_read_last!==(dut.t_read_index==255))$fatal(1,"FAIL_AFULL T read metadata");
     if(dut.t_owner==1)begin
      if(dut.t_read_index!=rawtakes||dut.t_read_data!==gx[(rawtakes%2)*128+rawtakes/2])$fatal(1,"FAIL_AFULL preserved raw T changed during head/Wo");
      if(dut.t_read_take&&dut.stage!=9)$fatal(1,"FAIL_AFULL raw T take during head/Wo compute");
     end
    end
    if(dut.t_read_valid&&dut.t_read_take)begin
     if(inject_meta)$fatal(1,"FAIL_AFULL invalid T metadata accepted");
     if(dut.t_owner==1)rawtakes=rawtakes+1;
     else if(dut.t_owner!=2||!(out_valid&&out_ready))$fatal(1,"FAIL_AFULL output T take without host");ttakes=ttakes+1;
    end
    if(dut.t_release_valid&&dut.t_release_ready)begin
     if(dut.t_owner==1)begin
      if(rawtakes!=256||capture_acks!=256||residual_acks!=256||raw_released!=0)$fatal(1,"FAIL_AFULL raw release before residual write ACK");raw_released=1;
     end else if(dut.t_owner==2)begin
      if(out_count!=256||out_released!=0)$fatal(1,"FAIL_AFULL output release before final host take");out_released=1;
     end else $fatal(1,"FAIL_AFULL release owner");releases=releases+1;
    end
    if(out_valid&&out_ready)begin
     if(out_generation!==active_generation||out_index!=out_count||out_last!==(out_count==255)||out_data!==go[out_count])$fatal(1,"FAIL_AFULL context output count=%0d",out_count);
     if(fixture_name=="base"&&out_count<128)base_actual[out_count]=out_data;
     if(fixture_name=="future_changed"&&out_count<128&&out_data!==base_actual[out_count])$fatal(1,"FAIL_AFULL future token changed token0 both heads");
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
  $readmemh({vectors_dir,"/",name,"/stage/context.hex"},gc);$readmemh({vectors_dir,"/",name,"/stage/wo.hex"},gwo);$readmemh({vectors_dir,"/",name,"/expected-saturated.hex"},gold_sat_word);gsat=gold_sat_word[0];
 end endtask
 task automatic snapshot;begin
  q0=sreq;a0=sack;sw0=swrites;sr0=sreads;m0=mc;mr0=mr;me0=mexec;md0=mread;l0=loads;ld0=ldone;as0=astream;bs0=bstream;wd0=wide;
  ns0=ns;nr0=nr;nc0=nc;nn0=nnr;es0=es;er0=er;ec0=ec;eo0=eor;wq0=wrq;wb0=wb;ht0=host;tb0=begins;tc0=commits;tw0=twrites;tt0=ttakes;tr0=releases;
 end endtask
 task automatic admit;begin
  @(negedge clk);tracking=1;launched=0;input_good=0;input_acks=0;out_count=0;expected_request=0;kv_frozen=0;frozen_kv=-1;context_acks=0;padding_acks=0;rawtakes=0;capture_acks=0;residual_acks=0;raw_released=0;out_released=0;inject_meta=0;
  for(integer z=0;z<512;z=z+1)context_seen[z]=0;for(integer t=0;t<4;t=t+1)for(integer k=0;k<2;k=k+1)padding_seen[t][k]=0;
  for(integer z=0;z<1024;z=z+1)written[z]=0;
  snapshot();job_generation=next_generation;next_generation=next_generation+1;job_valid=1;
  do begin @(posedge clk);end while(!job_ready);@(negedge clk);job_valid=0;
  if(!busy)$fatal(1,"FAIL_AFULL accepted job not busy");
 end endtask
 task automatic send_word;input integer index;begin
  @(negedge clk);in_valid=1;in_data=gx[index];in_generation=active_generation;in_index=index[8:0];in_last=index==447;
  do begin @(posedge clk);end while(!in_ready);
  @(negedge clk);in_valid=0;
 end endtask
 task automatic frame;begin
  for(integer z=0;z<448;z=z+1)send_word(z);
  wait(input_stored);@(negedge clk);if(input_acks!=448||!start_ready)$fatal(1,"FAIL_AFULL complete input not stored");
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
  if(done_valid||busy||!job_ready)$fatal(1,"FAIL_AFULL hard reset lifecycle");
 end endtask
 task automatic finish;input bit err;input integer words;integer before_take;begin
  wait(done_valid);#1;
  if(done_error!==err||done_generation!==active_generation||done_words!=words||done_partial!==(err&&words!=0)||out_count!=words)$fatal(1,"FAIL_AFULL completion fields err=%0d words=%0d",done_error,done_words);
  if(!err&&(out_released!=1||raw_released!=1))$fatal(1,"FAIL_AFULL successful DONE before two actual releases");
  if(!err&&done_saturated!==gsat)$fatal(1,"FAIL_AFULL saturation expected=%0d got=%0d",gsat,done_saturated);
  before_take=dtakes;tick(4);if(dtakes!=before_take||!done_valid||job_ready)$fatal(1,"FAIL_AFULL retained completion");
  @(negedge clk);done_ready=1;tick(1);@(negedge clk);done_ready=0;tick(2);
  if(dtakes!=before_take+1||done_valid||busy||!job_ready)$fatal(1,"FAIL_AFULL exactly once completion/reuse");tracking=0;
 end endtask
 task automatic normal_counts;begin
  if(sreq-q0!=806408||sack-a0!=806408||swrites-sw0!=600424||sreads-sr0!=205984||mc-m0!=30336||mr-mr0!=30336||mexec-me0!=24896||mread-md0!=3616||loads-l0!=24896||ldone-ld0!=24896||astream-as0!=197632||bstream-bs0!=99328||wide-wd0!=198144||ns-ns0!=82||nr-nr0!=82||nc-nc0!=2340||nnr-nn0!=2340||es-es0!=1024||er-er0!=1024||ec-ec0!=1024||eor-eo0!=1024||wrq-wq0!=24576||wb-wb0!=393216||host-ht0!=256||padding_acks!=8||context_acks!=512||rawtakes!=256||capture_acks!=256||residual_acks!=256||begins-tb0!=2||commits-tc0!=2||twrites-tw0!=512||ttakes-tt0!=512||releases-tr0!=2||pending)$fatal(1,"FAIL_AFULL normal counts S=%0d/%0d W=%0d R=%0d M=%0d/%0d EX=%0d RD=%0d L=%0d A=%0d B=%0d wide=%0d N=%0d/%0d E=%0d WR=%0d WB=%0d H=%0d CTX=%0d CAP=%0d RES=%0d T=%0d/%0d/%0d/%0d/%0d",sreq-q0,sack-a0,swrites-sw0,sreads-sr0,mc-m0,mr-mr0,mexec-me0,mread-md0,loads-l0,astream-as0,bstream-bs0,wide-wd0,ns-ns0,nc-nc0,es-es0,wrq-wq0,wb-wb0,host-ht0,context_acks,capture_acks,residual_acks,begins-tb0,twrites-tw0,commits-tc0,ttakes-tt0,releases-tr0);
 end endtask
 task automatic open_dumps;input string name;begin
  fd_x=$fopen({dump_dir,"/",name,"-accepted-input.bin"},"wb");fd_w=$fopen({dump_dir,"/",name,"-accepted-weights.bin"},"wb");fd_o=$fopen({dump_dir,"/",name,"-output.bin"},"wb");
  if(!fd_x||!fd_w||!fd_o)$fatal(1,"FAIL_AFULL dump open");dump_enabled=1;
 end endtask
 task automatic close_dumps;begin dump_enabled=0;$fclose(fd_x);$fclose(fd_w);$fclose(fd_o);end endtask
 task automatic normal;input string name;begin
  load_fixture(name);open_dumps(name);admit();frame();
  if(name=="base")begin
   @(negedge clk);force dut.permit_n_req=0;force dut.permit_t_write=0;force dut.permit_t_commit=0;run_job();
   wait(dut.state==22);tick(3);if(twrites-tw0||dut.t_read_valid)$fatal(1,"FAIL_AFULL raw T write backpressure");
   @(negedge clk);release dut.permit_t_write;wait(dut.state==23);tick(3);if(commits-tc0||dut.t_read_valid)$fatal(1,"FAIL_AFULL raw T commit backpressure");
   @(negedge clk);release dut.permit_t_commit;wait(dut.t_read_valid&&dut.t_owner==1);tick(3);
   if(rawtakes||twrites-tw0!=256||begins-tb0!=1)$fatal(1,"FAIL_AFULL raw spool not sealed before head Norm");
   @(negedge clk);force dut.u_t.begin_valid=1'b1;
   tick(4);if(dut.t_begin_ready||rawtakes||dut.t_read_index!=0||dut.t_read_data!==gx[0])$fatal(1,"FAIL_AFULL raw lease rejected second BEGIN/preserved hold");
   @(negedge clk);release dut.u_t.begin_valid;release dut.permit_n_req;
  end else if(name=="boundary")begin
   @(negedge clk);force dut.permit_n_rsp=0;run_job();wait(dut.n_rsp_valid);tick(5);
   if(!dut.n_rsp_valid||dut.stage!=0||rawtakes)$fatal(1,"FAIL_AFULL N service response/T hold");
   @(negedge clk);release dut.permit_n_rsp;force dut.permit_m_rsp=0;
   wait(dut.m_rsp_valid);tick(5);if(!dut.m_rsp_valid||dut.m_phase!=0||rawtakes)$fatal(1,"FAIL_AFULL M response hold");
   @(negedge clk);release dut.permit_m_rsp;force dut.permit_e_rsp=0;
   wait(dut.e_rsp_valid);tick(5);if(!dut.e_rsp_valid||dut.stage!=4||rawtakes)$fatal(1,"FAIL_AFULL E service response hold");
   @(negedge clk);release dut.permit_e_rsp;force dut.permit_t_release=0;
   wait(dut.state==28);tick(4);if(done_valid||begins-tb0!=1||releases-tr0)$fatal(1,"FAIL_AFULL raw release backpressure");
   @(negedge clk);release dut.permit_t_release;
  end else run_job();
  wait(out_valid);tick(5);@(negedge clk);if(name=="boundary")force dut.permit_t_release=0;out_ready=1;
  if(name=="boundary")begin
   wait(out_count==256);tick(5);if(done_valid||out_released||releases-tr0!=1)$fatal(1,"FAIL_AFULL DONE before stalled output T release");
   @(negedge clk);release dut.permit_t_release;
  end
  wait(done_valid);#1;normal_counts();finish(0,256);@(negedge clk);out_ready=0;close_dumps();
 end endtask
 task automatic error_fixture;begin load_fixture("base");fault_mode=0;admit();frame();run_job();end endtask
 task automatic provider_error;input integer mode;integer reject_sreq,reject_swrites;begin
  @(negedge clk);force dut.permit_wrx=0;
  error_fixture(); // Install before the first weight request, while the bad beat is blocked.
  @(negedge clk);fault_mode=mode;
  do begin @(posedge clk);end while(!(wreq_valid&&wreq_ready));#1;
  reject_sreq=sreq;reject_swrites=swrites;
  @(negedge clk);release dut.permit_wrx;finish(1,0);fault_mode=0;
  if(sreq!=reject_sreq||swrites!=reject_swrites)$fatal(1,"FAIL_AFULL rejected weight caused S access mode=%0d",mode);
 end endtask
 // The following sequence is the predeclared finite fault/flow contract.
 initial begin
  if(!$value$plusargs("vectors=%s",vectors_dir)||!$value$plusargs("dump_dir=%s",dump_dir))$fatal(1,"FAIL_AFULL require +vectors and +dump_dir");
  hard_reset();load_fixture("base");
  @(negedge clk);abort=1;tick(1);@(negedge clk);abort=0;tick(2);if(done_valid||busy)$fatal(1,"FAIL_AFULL idle abort created job");mark("AFULL_IDLE_ABORT");
  admit();send_word(0);@(negedge clk);start_valid=1;tick(2);if(start_ready||launched)$fatal(1,"FAIL_AFULL early start accepted");@(negedge clk);start_valid=0;pulse_abort();finish(1,0);mark("AFULL_PARTIAL_INPUT_EARLY_START_ABORT");
  admit();for(integer z=0;z<447;z=z+1)send_word(z);wait(input_acks==447);
  @(negedge clk);force dut.permit_s_rsp=0;send_word(447);wait(dut.s_valid);tick(4);if(input_stored||start_ready||input_acks!=447)$fatal(1,"FAIL_AFULL final ACK storage gate");
  @(negedge clk);release dut.permit_s_rsp;wait(input_stored);pulse_abort();finish(1,0);mark("AFULL_FINAL_INPUT_ACK_PRESTART_TERMINAL");
  admit();@(negedge clk);in_valid=1;in_data=gx[0];in_generation=active_generation;in_index=1;in_last=0;tick(1);@(negedge clk);in_valid=0;finish(1,0);if(sreq!=q0)$fatal(1,"FAIL_AFULL bad X index wrote S");
  admit();@(negedge clk);in_valid=1;in_data=gx[0];in_generation=active_generation;in_index=0;in_last=1;tick(1);@(negedge clk);in_valid=0;finish(1,0);if(sreq!=q0)$fatal(1,"FAIL_AFULL bad X last wrote S");
  admit();pulse_abort();finish(1,0);admit();@(negedge clk);in_valid=1;in_data=gx[0];in_generation=active_generation-1;in_index=0;in_last=0;tick(1);@(negedge clk);in_valid=0;finish(1,0);if(sreq!=q0)$fatal(1,"FAIL_AFULL stale X wrote S");mark("AFULL_INPUT_BAD_META_AND_STALE_NEW_JOB");
  // Three complete full-dimension jobs each export input/6MiB weights/output actual bytes.
  normal("base");mark("AFULL_BASE_ALL_HEADS_WO_ORIGINAL_RESIDUAL");
  provider_gap=1;normal("future_changed");provider_gap=0;mark("AFULL_FUTURE_CHANGED_CAUSAL_ALL_HEADS");
  normal("boundary");mark("AFULL_BOUNDARY_SATURATION_AND_RESPONSE_HOLDS");
  load_fixture("base");@(negedge clk);weights_version=0;admit();frame();@(negedge clk);weights_version=16'h4321;run_job();wait(wreq_valid);if(wreq_version!=0)$fatal(1,"FAIL_AFULL version zero/admission binding");pulse_abort();finish(1,0);weights_version=16'h1234;mark("AFULL_ZERO_VERSION_CAPTURE_AT_ADMISSION");
  error_fixture();@(negedge clk);wreq_ready=0;wait(wreq_valid);tick(5);if(w_ready)$fatal(1,"FAIL_AFULL response ready before request accept");@(negedge clk);wreq_ready=1;wait(w_valid&&w_ready);pulse_abort();finish(1,0);mark("AFULL_PROVIDER_REQUEST_BACKPRESSURE");
  error_fixture();wait(dut.state==16);@(negedge clk);force dut.permit_wrx=0;tick(5);if(w_ready||!w_valid)$fatal(1,"FAIL_AFULL weight response hold");@(negedge clk);release dut.permit_wrx;pulse_abort();finish(1,0);mark("AFULL_PROVIDER_RESPONSE_BACKPRESSURE");
  provider_error(1);mark("AFULL_WEIGHT_BAD_INDEX");provider_error(2);mark("AFULL_WEIGHT_BAD_LAST");
  provider_error(3);provider_error(7);mark("AFULL_WEIGHT_OLD_AND_FUTURE_JOB_STRICT_REJECT");
  provider_error(4);mark("AFULL_WEIGHT_WRONG_SEQUENCE");provider_error(5);mark("AFULL_WEIGHT_WRONG_VERSION");provider_error(6);mark("AFULL_PROVIDER_ERROR_FLAG");
  error_fixture();wait(dut.local_tag==8&&dut.weight_index==15&&dut.state==6&&dut.s_valid);@(negedge clk);force dut.permit_s_rsp=0;tick(4);if(dut.load_valid||dut.weight_index!=15||dut.request_seq!=0)$fatal(1,"FAIL_AFULL loader before last weight write ACK");@(negedge clk);release dut.permit_s_rsp;pulse_abort();finish(1,0);mark("AFULL_LAST_WEIGHT_S_ACK_GATES_LOADER");
  error_fixture();wait(dut.load_valid);loader_errors_before=loader_errors;@(negedge clk);force dut.u_s.load_tiles=3'd0;
  do begin @(posedge clk);end while(!(dut.load_valid&&dut.load_ready));@(negedge clk);release dut.u_s.load_tiles;
  finish(1,0);if(loader_errors!=loader_errors_before+1)$fatal(1,"FAIL_AFULL missing native loader error response");mark("AFULL_NATIVE_LOADER_ILLEGAL_DESCRIPTOR_ERROR");
  error_fixture();wait(dut.m_cmd_valid&&dut.m_cmd_op==10);@(negedge clk);inject_m=1;force dut.m_cmd_data=64'h1488d;do begin @(posedge clk);end while(!(dut.m_cmd_valid&&dut.m_cmd_ready));@(negedge clk);release dut.m_cmd_data;inject_m=0;finish(1,0);mark("AFULL_NATIVE_M_RESERVED_DESCRIPTOR_ERROR");
  error_fixture();wait(dut.n_cmd_valid&&dut.n_cmd_op==1);@(negedge clk);inject_n=1;force dut.n_cmd_op=4'd15;do begin @(posedge clk);end while(!(dut.n_cmd_valid&&dut.n_cmd_ready));@(negedge clk);release dut.n_cmd_op;inject_n=0;finish(1,0);mark("AFULL_NATIVE_N_ERROR_COORDINATED_RESET");
  error_fixture();wait(dut.e_in_valid);@(negedge clk);inject_e=1;force dut.e_in_op=4'd14;do begin @(posedge clk);end while(!(dut.e_in_valid&&dut.e_in_ready));@(negedge clk);release dut.e_in_op;inject_e=0;finish(1,0);mark("AFULL_NATIVE_E_ROPE_ERROR");
  error_fixture();wait(dut.h_rsp_valid&&dut.owner==3);@(negedge clk);force dut.h_rsp_error=1'b1;do begin @(posedge clk);end while(!(dut.h_rsp_valid&&dut.h_rsp_ready));@(negedge clk);release dut.h_rsp_error;finish(1,0);mark("AFULL_S_HELPER_BOUNDARY_ERROR");
  error_fixture();wait(dut.stage==2&&wreq_valid);@(negedge clk);inject_meta=1;force dut.t_read_index=10'd1;tick(1);@(negedge clk);release dut.t_read_index;finish(1,0);if(rawtakes)$fatal(1,"FAIL_AFULL bad raw T metadata taken");mark("AFULL_RAW_T_BAD_METADATA_NO_TAKE");
  error_fixture();wait(out_valid);@(negedge clk);inject_meta=1;force dut.t_read_index=10'd1;out_ready=1;tick(1);@(negedge clk);out_ready=0;release dut.t_read_index;finish(1,0);if(ttakes-tt0!=256)$fatal(1,"FAIL_AFULL bad output T metadata taken");mark("AFULL_OUTPUT_T_BAD_METADATA_NO_HOST_TAKE");
  error_fixture();wait(dut.state==27&&dut.s_valid);@(negedge clk);force dut.permit_s_rsp=0;tick(5);
  if(rawtakes!=1||capture_acks||residual_acks||es-es0!=768||dut.e_req_valid)$fatal(1,"FAIL_AFULL raw capture S258 ACK did not gate E/next take");
  pulse_abort();@(negedge clk);release dut.permit_s_rsp;finish(1,0);mark("AFULL_RAW_CAPTURE_S_ACK_GATES_RESIDUAL_E");
  error_fixture();wait(dut.owner==1&&dut.stage==9&&dut.s_valid&&pending&&pwrite&&paddr==511);@(negedge clk);force dut.permit_s_rsp=0;tick(5);
  if(rawtakes!=256||capture_acks!=256||residual_acks!=255||raw_released||begins-tb0!=1)$fatal(1,"FAIL_AFULL last residual ACK did not gate raw release/output begin");
  @(negedge clk);release dut.permit_s_rsp;wait(begins-tb0==2);pulse_abort();finish(1,0);mark("AFULL_FINAL_RESIDUAL_ACK_RELEASE_REBEGIN_BARRIER");
  error_fixture();@(negedge clk);force dut.permit_n_rsp=0;wait(dut.n_rsp_valid);tick(5);
  if(dut.owner!=3||dut.token_index!=0||dut.stage!=0||ns-ns0!=1||!dut.n_rsp_valid||rawtakes)$fatal(1,"FAIL_AFULL held N lease/head T advanced");
  pulse_abort();@(negedge clk);release dut.permit_n_rsp;finish(1,0);mark("AFULL_HEAD_RUN_T_AND_N_LEASE_ABORT");
  load_fixture("base");admit();send_word(0);hard_reset();mark("AFULL_HARD_RESET_PARTIAL_INPUT_NO_DONE");
  error_fixture();wait(dut.state==16);hard_reset();mark("AFULL_HARD_RESET_WEIGHT_PENDING_NO_DONE");
  error_fixture();wait(out_valid);tick(4);hard_reset();mark("AFULL_HARD_RESET_HELD_OUTPUT");
  error_fixture();wait(out_valid);tick(5);@(negedge clk);out_ready=1;tick(1);@(negedge clk);out_ready=0;tick(2);pulse_abort();finish(1,1);mark("AFULL_OUTPUT_PREFIX_ABORT_PARTIAL");
  // Final no-reset complete recovery, true T RELEASE and completion exactly once.
  error_fixture();@(negedge clk);out_ready=1;wait(done_valid);#1;normal_counts();
  tick(4);@(negedge clk);abort=1;done_ready=1;tick(1);@(negedge clk);abort=0;done_ready=0;out_ready=0;tick(2);
  if(done_valid||busy||!job_ready||obligation)$fatal(1,"FAIL_AFULL DONE abort+ready duplicate/lost completion");tracking=0;mark("AFULL_FULL_RECOVERY_DONE_ABORT_READY");
  if(cases!=32)$fatal(1,"FAIL_AFULL declared case count got=%0d",cases);
  $display("AFULL_COUNTS cycles=%0d jobs=%0d X=%0d Sreq=%0d Sack=%0d M=%0d/%0d N=%0d/%0d E=%0d/%0d wreq=%0d W=%0d Ttake=%0d Trelease=%0d host=%0d done=%0d",cycles,jobs,inputs,sreq,sack,mc,mr,nc,nnr,ec,eor,wrq,wb,ttakes,releases,host,dtakes);
  $display("PASS_AFULL cases=%0d",cases);$finish;
 end
endmodule
