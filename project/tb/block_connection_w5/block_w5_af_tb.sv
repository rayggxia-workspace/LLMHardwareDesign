`timescale 1ns/1ps
// Complete G1: real A/F, edge S and an external real S destination for ACK.
// File goldens are inherited independent AF1024 mathematics, never DUT output.
module block_w5_af_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,job_valid=0,start_valid=0,in_valid=0,done_ready=0;
 reg [31:0] job_generation=0,in_generation=0;
 reg [15:0] weights_a_version=16'h1234,weights_f_version=16'h5678;
 reg [127:0] in_data=0;reg [9:0] in_index=0;reg in_last=0;
 wire job_ready,start_ready,input_stored,in_ready,busy,child_reset,done_valid,done_error;
 wire done_saturated,done_partial;wire [8:0] done_words;wire [31:0] done_generation;
 wire out_valid,out_last;wire [127:0] out_data;wire [9:0] out_index;wire [31:0] out_generation;
 wire out_ack_valid,out_ack_ready;wire [9:0] out_ack_index;wire [31:0] out_ack_generation;
 wire param_req_valid,param_req_ready,param_req_row,param_valid,param_ready,param_last,param_error;
 wire [15:0] param_req_id;wire [1:0] param_req_island;wire [8:0] param_req_words,param_index;
 wire [127:0] param_data;
 wire a_wreq_valid,a_wreq_ready,a_w_valid,a_w_ready,a_w_last,a_w_error;
 wire [31:0] a_wreq_job,a_w_job;wire [15:0] a_wreq_seq,a_wreq_version,a_w_seq,a_w_version;
 wire [1:0] a_wreq_matrix;wire [3:0] a_wreq_head,a_w_index;
 wire [6:0] a_wreq_group;wire [5:0] a_wreq_chunk;wire [127:0] a_w_data;
 wire f_wreq_valid,f_wreq_ready,f_w_valid,f_w_ready,f_w_last,f_w_error,f_wreq_row;
 wire [15:0] f_wreq_job,f_w_job,f_wreq_seq,f_wreq_version,f_w_seq,f_w_version;
 wire [1:0] f_wreq_matrix;wire [8:0] f_wreq_group;wire [6:0] f_wreq_chunk;
 wire [4:0] f_w_index;wire [127:0] f_w_data;
 wire rom_req_valid,rom_req_ready,rom_rsp_ready;wire [7:0] rom_req_addr;
 reg rom_rsp_valid=0,rom_rsp_error=0;reg [127:0] rom_rsp_data=0;
 wire [4:0] meta_addr;wire [511:0] meta_data;
 reg [127:0] rom[0:255];reg [511:0] meta[0:16];
 reg [127:0] gx[0:575],ga[0:255],gz[0:255],aw[0:393215],fw[0:589823];
 reg sat_gold[0:0];string vectors_dir,dump_dir,rom_path,meta_path;
 reg allow_rom=1,allow_param_req=1,allow_param_data=1,allow_sink_ack=1;
 integer fault_mode=0,param_fault_mode=0,rom_delay_mode=1;
 reg r_pending=0;reg [127:0] r_word=0;reg r_error=0;integer r_delay=0;
 reg pp_active=0;reg [1:0] pp_island=0;reg pp_row=0;
 reg [8:0] pp_words=0,pp_index=0;integer pp_fault=0;
 reg pa_active=0,pf_active=0;reg [31:0] pa_job=0;
 reg [15:0] pa_seq=0,pa_ver=0,pf_job=0,pf_seq=0,pf_ver=0;
 reg [3:0] pa_index=0;reg [4:0] pf_index=0;
 block_w5_af_top dut(.*);
 assign meta_data=meta_addr<17 ? meta[meta_addr] : 512'd0;
 assign rom_req_ready=!child_reset&&allow_rom&&!r_pending&&!rom_rsp_valid;
 assign param_req_ready=!child_reset&&allow_param_req&&!pp_active;
 assign param_valid=!child_reset&&allow_param_data&&pp_active;
 assign param_index=pp_index^(pp_fault==1 ? 9'd1 : 9'd0);
 assign param_last=pp_fault==2 ? !(pp_index+9'd1==pp_words) : pp_index+9'd1==pp_words;
 assign param_error=pp_fault==3;
 assign param_data=pp_island==1 ? gx[256+int'(pp_index)] : gx[448+int'(pp_index)];
 assign a_wreq_ready=!child_reset&&!pa_active;
 assign a_w_valid=!child_reset&&pa_active;assign a_w_job=pa_job;assign a_w_seq=pa_seq;
 assign a_w_version=pa_ver;assign a_w_index=pa_index;assign a_w_last=pa_index==15;
 assign a_w_error=0;assign a_w_data=aw[int'(pa_seq)*16+int'(pa_index)];
 assign f_wreq_ready=!child_reset&&!pf_active;
 assign f_w_valid=!child_reset&&pf_active;assign f_w_job=pf_job;assign f_w_seq=pf_seq;
 assign f_w_version=pf_ver;assign f_w_index=pf_index;assign f_w_last=pf_index==15;
 assign f_w_error=0;assign f_w_data=fw[int'(pf_seq)*16+int'(pf_index)];
 // Models change payload state only through NBA at the accepting edge.
 always @(posedge clk)begin
  if(child_reset)begin
   r_pending<=0;rom_rsp_valid<=0;rom_rsp_error<=0;r_delay<=0;
   pp_active<=0;pp_index<=0;pa_active<=0;pf_active<=0;pa_index<=0;pf_index<=0;
  end else begin
   if(rom_rsp_valid&&rom_rsp_ready)rom_rsp_valid<=0;
   if(rom_req_valid&&rom_req_ready)begin
    r_pending<=1;r_word<=rom[rom_req_addr];r_error<=fault_mode==2&&rom_req_addr==0;
    if(fault_mode==1&&rom_req_addr==0)r_word<={rom[0][127:8],8'hff};
    r_delay<=rom_delay_mode;
   end
   if(r_pending)begin
    if(r_delay!=0)r_delay<=r_delay-1;
    else begin rom_rsp_valid<=1;rom_rsp_data<=r_word;rom_rsp_error<=r_error;r_pending<=0;end
   end
   if(param_req_valid&&param_req_ready)begin
    pp_active<=1;pp_island<=param_req_island;pp_row<=param_req_row;
    pp_words<=param_req_words;pp_index<=0;pp_fault<=param_fault_mode;
   end
   if(param_valid&&param_ready)begin
    if(pp_index+9'd1==pp_words)pp_active<=0;else pp_index<=pp_index+9'd1;
   end
   if(a_wreq_valid&&a_wreq_ready)begin
    pa_active<=1;pa_job<=a_wreq_job;pa_seq<=a_wreq_seq;pa_ver<=a_wreq_version;pa_index<=0;
   end
   if(a_w_valid&&a_w_ready)begin if(pa_index==15)pa_active<=0;else pa_index<=pa_index+1'b1;end
   if(f_wreq_valid&&f_wreq_ready)begin
    pf_active<=1;pf_job<=f_wreq_job;pf_seq<=f_wreq_seq;pf_ver<=f_wreq_version;pf_index<=0;
   end
   if(f_w_valid&&f_w_ready)begin if(pf_index==15)pf_active<=0;else pf_index<=pf_index+1'b1;end
  end
 end

 // External destination is a real native S and real request/ACK helper.
 // Capture is separate from the eventual ACK returned to the producer.
 reg [2:0] sink_state=0;
 reg [127:0] sink_data=0;reg [9:0] sink_index=0;
 reg [31:0] sink_generation=0;reg sink_last=0;
 wire sink_req_valid,sink_req_ready,sink_rsp_valid,sink_rsp_ready,sink_rsp_error;
 wire [127:0] sink_rsp_data;
 wire sink_s_req,sink_s_we,sink_s_ready,sink_s_valid,sink_s_take;
 wire [9:0] sink_s_addr;wire [127:0] sink_s_din,sink_s_dout;
 assign sink_req_valid=!child_reset&&sink_state==1;
 assign sink_rsp_ready=!child_reset&&sink_state==2;
 assign out_ack_valid=!child_reset&&sink_state==3&&allow_sink_ack;
 assign out_ack_index=sink_index;assign out_ack_generation=sink_generation;
 block_p2_s_ctrl u_sink_ctrl(
  .clk(clk),.resetn(!child_reset),.req_valid(sink_req_valid),.req_ready(sink_req_ready),
  .req_write(1'b1),.req_addr(sink_index),.req_data(sink_data),
  .rsp_valid(sink_rsp_valid),.rsp_ready(sink_rsp_ready),.rsp_data(sink_rsp_data),.rsp_error(sink_rsp_error),
  .s_req(sink_s_req),.s_we(sink_s_we),.s_addr(sink_s_addr),.s_din(sink_s_din),
  .s_rsp_ready(sink_s_take),.s_ready(sink_s_ready),.s_rsp_valid(sink_s_valid),.s_dout(sink_s_dout));
 block_feed_s_macro u_sink(
  .clk(clk),.reset(child_reset),.req(sink_s_req),.wr(sink_s_we),.addr(sink_s_addr),.din(sink_s_din),
  .ready(sink_s_ready),.valid(sink_s_valid),.take(sink_s_take),.dout(sink_s_dout),
  .load_valid(1'b0),.load_ready(),.load_bank(1'b0),.load_rows(4'd0),.load_tiles(3'd0),
  .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_a_base(10'd0),.load_b_base(10'd0),
  .done_valid(),.done_take(1'b0),.done_error(),.busy(),
  .a_valid(),.a_ready(1'b0),.a_bank(),.a_row(),.a_tile(),.a_wide(),.a_data(),
  .b_valid(),.b_ready(1'b0),.b_bank(),.b_tile(),.b_wide(),.b_half(),.b_data());
 always @(posedge clk)begin
  if(child_reset)begin sink_state<=0;sink_data<=0;sink_index<=0;sink_generation<=0;sink_last<=0;end
  else case(sink_state)
   0:if(out_valid)begin sink_data<=out_data;sink_index<=out_index;sink_generation<=out_generation;sink_last<=out_last;sink_state<=1;end
   1:if(sink_req_valid&&sink_req_ready)sink_state<=2;
   2:if(sink_rsp_valid&&sink_rsp_ready)begin
    if(sink_rsp_error||sink_rsp_data!==sink_data)$fatal(1,"FAIL_H2_AF real sink write ACK");sink_state<=3;end
   3:if(out_ack_valid&&out_ack_ready)sink_state<=0;
   default:$fatal(1,"FAIL_H2_AF sink state");
  endcase
 end

 integer cycles=0,cases=0,next_generation=32768,job_total=0,done_total=0;
 reg obligation=0;reg [31:0] active_generation=0;
 reg [15:0] active_av=0,active_fv=0;integer f_ids=0;
 integer ingress=0,params=0,preqs=0,host_count=0,sink_acks=0;
 integer edge_writes=0,edge_reads=0,a_starts=0,f_starts=0,a_dones=0,f_dones=0;
 integer a_sources=0,f_sources=0,a_releases=0,f_releases=0;
 integer a_requests=0,f_requests=0,a_beats=0,f_beats=0;
 integer a_execs=0,f_execs=0,ain_capture=0,ain_acks=0,fin_capture=0,fin_acks=0;
 integer f_req_expected=0,service_calls=0;
 reg epending=0,epwrite=0;integer epaddr=0;reg [127:0] epdata=0;
 reg [127:0] edge_model[0:1023];reg edge_valid[0:1023];
 reg load_credit=0,load_acked=0,store_credit=0;
 reg hold_out=0,hold_done=0,hold_rom=0,hold_svc=0;
 reg [170:0] held_out;reg [43:0] held_done;reg [7:0] held_rom;
 reg [147:0] held_svc;
 reg dumping=0;integer dump_i=0,dump_p=0,dump_a=0,dump_f=0,dump_o=0;
 function automatic integer aseq(input integer m,h,g,c);
  if(m==0)aseq=h*2048+g*32+c;
  else if(m==1)aseq=h*2048+512+g*32+c;
  else if(m==2)aseq=(h/2)*2048+1024+(h%2)*512+g*32+c;
  else aseq=16384+g*64+c;
 endfunction
 function automatic integer fseq(input integer m,g,c);
  fseq=m==2 ? 24576+g*96+c : g*64+m*32+c;
 endfunction
 task automatic byte_dump(input integer fd,input [127:0] data);
  for(integer k=0;k<16;k=k+1)$fwrite(fd,"%c",data[8*k+:8]);
 endtask

 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>220000000)$fatal(1,"FAIL_H2_AF watchdog state=%0d pc=%0d",dut.u_exec.state,dut.u_ctrl.pc);
  if(reset)begin obligation=0;hold_out=0;hold_done=0;f_ids=0;end
  else begin
   if(job_valid&&job_ready)begin
    if(obligation)$fatal(1,"FAIL_H2_AF duplicate outer admission");
    obligation=1;job_total=job_total+1;active_generation=job_generation;
    active_av=weights_a_version;active_fv=weights_f_version;
    ingress=0;params=0;preqs=0;host_count=0;sink_acks=0;edge_writes=0;edge_reads=0;
    a_starts=0;f_starts=0;a_dones=0;f_dones=0;a_sources=0;f_sources=0;a_releases=0;f_releases=0;
    a_requests=0;f_requests=0;a_beats=0;f_beats=0;a_execs=0;f_execs=0;
    ain_capture=0;ain_acks=0;fin_capture=0;fin_acks=0;f_req_expected=0;service_calls=0;
    epending=0;load_credit=0;load_acked=0;store_credit=0;hold_out=0;hold_done=0;
    for(integer k=0;k<1024;k=k+1)edge_valid[k]=0;
   end
   if(done_valid&&done_ready)begin
    if(!obligation)$fatal(1,"FAIL_H2_AF duplicate terminal");obligation=0;done_total=done_total+1;
   end
   if(child_reset)begin
    epending=0;load_credit=0;load_acked=0;store_credit=0;hold_out=0;
    hold_rom=0;hold_svc=0;f_ids=0;
   end
   if(hold_done&&(!done_valid||{done_error,done_saturated,done_partial,done_words,done_generation}!==held_done))
    $fatal(1,"FAIL_H2_AF held DONE changed");
   hold_done=done_valid&&!done_ready;held_done={done_error,done_saturated,done_partial,done_words,done_generation};
   if(obligation&&!child_reset&&!(done_valid&&done_error))begin
    if(hold_rom&&(!rom_req_valid||rom_req_addr!==held_rom))$fatal(1,"FAIL_H2_AF held ROM request changed");
    hold_rom=rom_req_valid&&!rom_req_ready;held_rom=rom_req_addr;
    if(hold_svc&&(!dut.svc_valid||{dut.svc_record,dut.svc_a_base,dut.svc_b_base}!==held_svc))
     $fatal(1,"FAIL_H2_AF held service request changed");
    hold_svc=dut.svc_valid&&!dut.svc_ready;held_svc={dut.svc_record,dut.svc_a_base,dut.svc_b_base};
    if(hold_out&&(!out_valid||{out_generation,out_index,out_last,out_data}!==held_out))$fatal(1,"FAIL_H2_AF held host offer changed");
    hold_out=out_valid&&!(out_ack_valid&&out_ack_ready);held_out={out_generation,out_index,out_last,out_data};
    if(out_valid&&(out_index!=host_count||out_generation!==active_generation||out_last!==(host_count==255)||out_data!==gz[host_count]))
     $fatal(1,"FAIL_H2_AF independent final output index=%0d",out_index);
    if(sink_state!=0&&(!out_valid||out_data!==sink_data||out_index!==sink_index||out_generation!==sink_generation||out_last!==sink_last))
     $fatal(1,"FAIL_H2_AF sink pending source withdrawn");
    if(in_valid&&in_ready)begin
     if(in_index!=ingress||in_generation!==active_generation||in_last!==(ingress==255)||in_data!==gx[ingress])$fatal(1,"FAIL_H2_AF input order");
     ingress=ingress+1;if(dumping)byte_dump(dump_i,in_data);
    end
    if(param_req_valid&&param_req_ready)begin
     if(pp_active||param_req_id!=(param_req_island==1 ? 0 : 1)||param_req_words!=(param_req_island==1 ? 192 : 128)||
        (param_req_island==1&&param_req_row))$fatal(1,"FAIL_H2_AF parameter request ABI");preqs=preqs+1;
    end
    if(param_valid&&param_ready)begin params=params+1;if(dumping)byte_dump(dump_p,param_data);end
    if(dut.svc_valid&&dut.svc_ready)service_calls=service_calls+1;
    if(dut.u_exec.a_in_valid&&dut.u_exec.a_in_ready)begin
     if(dut.u_exec.a_in_index!=ain_capture||dut.u_exec.a_in_data!==gx[ain_capture]||dut.u_exec.a_in_last!==(ain_capture==447))
      $fatal(1,"FAIL_H2_AF A frame layout");ain_capture=ain_capture+1;
    end
    if(dut.u_exec.f_in_valid&&dut.u_exec.f_in_ready)begin
     if(fin_capture>=256||dut.u_exec.f_in_data!==(fin_capture<128 ? ga[int'(dut.u_exec.row_hold)*128+fin_capture] : gx[448+fin_capture-128]))
      $fatal(1,"FAIL_H2_AF F hidden/gamma frame");fin_capture=fin_capture+1;
    end
    if(dut.u_exec.hidden_capture)begin
     if(load_credit)$fatal(1,"FAIL_H2_AF more than one accepted hidden word");load_credit=1;load_acked=0;
    end
    if(dut.u_exec.u_a.state==3&&dut.u_exec.u_a.s_valid&&dut.u_exec.u_a.s_take)begin
     ain_acks=ain_acks+1;if(ain_acks<=256)load_acked=1;
    end
    if(dut.u_exec.u_f.state==2&&dut.u_exec.u_f.s_valid&&dut.u_exec.u_f.s_take)begin
     fin_acks=fin_acks+1;if(fin_acks<=128)load_acked=1;
    end
    if(dut.u_exec.hidden_fire)begin
     if(!load_credit||!load_acked)$fatal(1,"FAIL_H2_AF edge hidden retired before real native S ACK");
     load_credit=0;load_acked=0;
    end
    if(dut.u_exec.a_start_valid&&dut.u_exec.a_start_ready)begin
     if(!dut.u_exec.a_input_stored||ain_capture!=448||ain_acks!=448||load_credit)$fatal(1,"FAIL_H2_AF A start before complete frame ACK");
     a_starts=a_starts+1;
    end
    if(dut.u_exec.f_start_valid&&dut.u_exec.f_start_ready)begin
     if(!dut.u_exec.f_input_stored||fin_capture!=256||fin_acks!=256||load_credit)$fatal(1,"FAIL_H2_AF F start before complete frame ACK");
     f_starts=f_starts+1;f_ids=f_ids+1;f_req_expected=0;
    end
    if(dut.u_exec.u_edge.s_req&&dut.u_exec.u_edge.s_ready)begin
     if(epending)$fatal(1,"FAIL_H2_AF edge ordinary port overlap");
     epending=1;epwrite=dut.u_exec.u_edge.s_we;epaddr=int'(dut.u_exec.u_edge.s_addr);epdata=dut.u_exec.u_edge.s_din;
     if(!epwrite&&!edge_valid[epaddr])$fatal(1,"FAIL_H2_AF edge read without actual prior writeACK");
    end
    if(dut.u_exec.u_edge.s_valid&&dut.u_exec.u_edge.s_take)begin
     if(!epending)$fatal(1,"FAIL_H2_AF edge ACK without one owner");
     if(epwrite)begin
      if(dut.u_exec.transfer==1)begin if(epaddr>=256||epdata!==gx[epaddr])$fatal(1,"FAIL_H2_AF IMPORT edge payload");end
      else if(dut.u_exec.transfer==3)begin
       if(dut.u_exec.island==1)begin if(epaddr<256||epaddr>=512||epdata!==ga[epaddr-256])$fatal(1,"FAIL_H2_AF real A result edge payload");end
       else if(epaddr>=256||epdata!==gz[epaddr])$fatal(1,"FAIL_H2_AF real F result edge payload");
       if(store_credit)$fatal(1,"FAIL_H2_AF duplicate source-storage credit");store_credit=1;
      end else $fatal(1,"FAIL_H2_AF unknown edge write owner");
      edge_model[epaddr]=epdata;edge_valid[epaddr]=1;edge_writes=edge_writes+1;
     end else begin
      if(dut.u_exec.u_edge.s_dout!==edge_model[epaddr])$fatal(1,"FAIL_H2_AF edge read version/value");edge_reads=edge_reads+1;
     end
     epending=0;
    end
    if(dut.u_exec.a_out_valid&&dut.u_exec.a_out_ready)begin
     if(!store_credit)$fatal(1,"FAIL_H2_AF A source T take before real edge writeACK");store_credit=0;a_sources=a_sources+1;
    end
    if(dut.u_exec.f_out_valid&&dut.u_exec.f_out_ready)begin
     if(!store_credit)$fatal(1,"FAIL_H2_AF F source T take before real edge writeACK");store_credit=0;f_sources=f_sources+1;
    end
    if(dut.u_exec.u_a.t_release_valid&&dut.u_exec.u_a.t_release_ready)a_releases=a_releases+1;
    if(dut.u_exec.u_f.state==17&&dut.u_exec.u_f.t_release_ready)f_releases=f_releases+1;
    if(dut.u_exec.a_done_valid&&dut.u_exec.a_done_ready)begin
     if(a_sources!=256||a_releases!=2)$fatal(1,"FAIL_H2_AF A DONE before output stored/release");a_dones=a_dones+1;
    end
    if(dut.u_exec.f_done_valid&&dut.u_exec.f_done_ready)begin
     if(f_sources!=f_starts*128||f_releases!=f_starts)$fatal(1,"FAIL_H2_AF F DONE before output stored/release");
     f_dones=f_dones+1;fin_capture=0;fin_acks=0;
    end
    if(sink_s_valid&&sink_s_take)begin
     if(!sink_s_we||sink_s_dout!==gz[sink_index])$fatal(1,"FAIL_H2_AF real sink S value");sink_acks=sink_acks+1;
    end
    if(out_ack_valid&&out_ack_ready)begin
     if(sink_acks!=host_count+1||out_ack_index!=host_count||out_ack_generation!==active_generation||sink_data!==gz[host_count])
      $fatal(1,"FAIL_H2_AF host ACK without matching real sink S ACK");
     host_count=host_count+1;if(dumping)byte_dump(dump_o,sink_data);
    end
    if(a_wreq_valid&&a_wreq_ready)begin
     if(pa_active||a_wreq_seq!=a_requests||a_wreq_seq!=aseq(int'(a_wreq_matrix),int'(a_wreq_head),int'(a_wreq_group),int'(a_wreq_chunk))||
        a_wreq_job!==active_generation||a_wreq_version!==active_av)$fatal(1,"FAIL_H2_AF A actual weight request");a_requests=a_requests+1;
    end
    if(f_wreq_valid&&f_wreq_ready)begin
     if(pf_active||f_wreq_seq!=f_req_expected||f_wreq_seq!=fseq(int'(f_wreq_matrix),int'(f_wreq_group),int'(f_wreq_chunk))||
        f_wreq_job!=f_ids||f_wreq_version!==active_fv||f_wreq_row!==(f_starts==2))$fatal(1,"FAIL_H2_AF F actual weight request");
     f_req_expected=f_req_expected+1;f_requests=f_requests+1;
    end
    if(a_w_valid&&a_w_ready)begin a_beats=a_beats+1;if(dumping)byte_dump(dump_a,a_w_data);end
    if(f_w_valid&&f_w_ready)begin f_beats=f_beats+1;if(dumping)byte_dump(dump_f,f_w_data);end
    if(dut.u_exec.u_a.m_cmd_valid&&dut.u_exec.u_a.m_cmd_ready&&dut.u_exec.u_a.m_cmd_op==10)a_execs=a_execs+1;
    if(dut.u_exec.u_f.m_cmd_valid&&dut.u_exec.u_f.m_cmd_ready&&dut.u_exec.u_f.m_cmd_op==10)f_execs=f_execs+1;
   end
  end
 end

 task automatic tick(input integer n);repeat(n)@(posedge clk);endtask
 task automatic mark(input string label);begin cases=cases+1;$display("CASE_PASS %s",label);end endtask
 task automatic hard_reset;begin
  @(negedge clk);reset=1;abort=0;job_valid=0;start_valid=0;in_valid=0;done_ready=0;
  allow_rom=1;allow_param_req=1;allow_param_data=1;allow_sink_ack=1;tick(3);
  @(negedge clk);reset=0;fault_mode=0;param_fault_mode=0;rom_delay_mode=1;tick(3);
  if(!job_ready||busy||done_valid||out_valid)$fatal(1,"FAIL_H2_AF reset quiescence");
 end endtask
 task automatic admit;begin
  @(negedge clk);job_generation=next_generation;next_generation=next_generation+1;
  weights_a_version=16'h1234;weights_f_version=16'h5678;job_valid=1;
  do @(posedge clk);while(!job_ready);@(negedge clk);job_valid=0;
 end endtask
 task automatic send_word(input integer n);begin
  @(negedge clk);in_valid=1;in_index=n[9:0];in_last=n==255;in_generation=active_generation;in_data=gx[n];
  do @(posedge clk);while(!in_ready);@(negedge clk);in_valid=0;
 end endtask
 task automatic frame;begin
  for(integer n=0;n<256;n=n+1)send_word(n);
  wait(input_stored);@(negedge clk);
  if(!start_ready||ingress!=256||edge_writes!=256)$fatal(1,"FAIL_H2_AF input_stored before real edge ACKs");
 end endtask
 task automatic start;begin
  @(negedge clk);start_valid=1;do @(posedge clk);while(!start_ready);@(negedge clk);start_valid=0;
 end endtask
 task automatic pulse_abort;begin
  @(negedge clk);abort=1;tick(1);@(negedge clk);abort=0;in_valid=0;start_valid=0;job_valid=0;
 end endtask
 task automatic finish(input bit error,input bit abort_ready);integer before_count;begin
  wait(done_valid);#1;
  if(done_error!==error||done_generation!==active_generation||done_words!=(error ? 0 : 256)||
     done_partial!==1'b0)$fatal(1,"FAIL_H2_AF terminal metadata err=%0d words=%0d",done_error,done_words);
  if(!error&&(done_saturated!==sat_gold[0]||host_count!=256||sink_acks!=256||a_dones!=1||f_dones!=2))
   $fatal(1,"FAIL_H2_AF premature success/native flags");
  tick(5);
  if(error&&(out_valid||a_wreq_valid||f_wreq_valid||param_req_valid||dut.u_exec.a_busy||dut.u_exec.f_busy||
     dut.u_exec.d_busy||pa_active||pf_active||pp_active||r_pending||rom_rsp_valid))
   $fatal(1,"FAIL_H2_AF error did not quiesce cohort");
  before_count=done_total;@(negedge clk);done_ready=1;abort=abort_ready;tick(1);
  @(negedge clk);done_ready=0;abort=0;tick(3);
  if(done_total!=before_count+1||done_valid||busy||!job_ready||obligation)$fatal(1,"FAIL_H2_AF terminal consumed more than once/reuse");
 end endtask
 task automatic open_dumps(input string label);begin
  dump_i=$fopen({dump_dir,"/",label,"-accepted-input.bin"},"wb");
  dump_p=$fopen({dump_dir,"/",label,"-accepted-params.bin"},"wb");
  dump_a=$fopen({dump_dir,"/",label,"-a-weights.bin"},"wb");
  dump_f=$fopen({dump_dir,"/",label,"-f-weights.bin"},"wb");
  dump_o=$fopen({dump_dir,"/",label,"-output.bin"},"wb");
  if(!dump_i||!dump_p||!dump_a||!dump_f||!dump_o)$fatal(1,"FAIL_H2_AF dump open");dumping=1;
 end endtask
 task automatic close_dumps;begin dumping=0;$fclose(dump_i);$fclose(dump_p);$fclose(dump_a);$fclose(dump_f);$fclose(dump_o);end endtask
 task automatic normal_counts(input integer expected_ids);begin
  if(ingress!=256||params!=448||preqs!=3||edge_writes!=768||edge_reads!=768||
     a_starts!=1||f_starts!=2||a_sources!=256||f_sources!=256||a_releases!=2||f_releases!=2||
     a_dones!=1||f_dones!=2||a_requests!=24576||f_requests!=73728||a_beats!=393216||f_beats!=1179648||
     a_execs!=24896||f_execs!=73728||service_calls!=41||host_count!=256||sink_acks!=256||
     epending||load_credit||store_credit||dut.u_exec.f_job_mirror!=expected_ids)
   $fatal(1,"FAIL_H2_AF full normal counts edge=%0d/%0d params=%0d svc=%0d",edge_writes,edge_reads,params,service_calls);
 end endtask
 task automatic param_failure(input integer mode);begin
  param_fault_mode=mode;admit();frame();start();finish(1,0);param_fault_mode=0;
 end endtask

 initial begin
  if(!$value$plusargs("rom=%s",rom_path)||!$value$plusargs("meta=%s",meta_path)||
     !$value$plusargs("vectors=%s",vectors_dir)||!$value$plusargs("dump_dir=%s",dump_dir))
   $fatal(1,"FAIL_H2_AF required +rom +meta +vectors +dump_dir");
  $readmemh(rom_path,rom);$readmemh(meta_path,meta);
  $readmemh({vectors_dir,"/base/input.hex"},gx);$readmemh({vectors_dir,"/base/expected-a-output.hex"},ga);
  $readmemh({vectors_dir,"/base/expected-output.hex"},gz);$readmemh({vectors_dir,"/base/a-weights.hex"},aw);
  $readmemh({vectors_dir,"/base/f-weights.hex"},fw);$readmemh({vectors_dir,"/base/expected-saturated.hex"},sat_gold);
  hard_reset();pulse_abort();tick(3);if(done_valid||busy)$fatal(1,"FAIL_H2_AF idle abort made obligation");mark("H2_IDLE_ABORT");
  fault_mode=1;admit();finish(1,0);fault_mode=0;mark("H2_ROM_UNKNOWN_REJECT");
  fault_mode=2;admit();finish(1,0);fault_mode=0;mark("H2_ROM_RESPONSE_ERROR");
  admit();@(negedge clk);in_valid=1;in_index=1;in_last=0;in_generation=active_generation;in_data=gx[0];
  finish(1,0);@(negedge clk);in_valid=0;mark("H2_INPUT_BAD_INDEX");
  admit();@(negedge clk);in_valid=1;in_index=0;in_last=0;in_generation=active_generation+1;in_data=gx[0];
  finish(1,0);@(negedge clk);in_valid=0;mark("H2_INPUT_BAD_GENERATION");
  admit();@(negedge clk);in_valid=1;in_index=0;in_last=1;in_generation=active_generation;in_data=gx[0];
  finish(1,0);@(negedge clk);in_valid=0;mark("H2_INPUT_BAD_LAST");
  admit();send_word(0);send_word(1);pulse_abort();finish(1,0);mark("H2_PARTIAL_INPUT_ABORT");
  rom_delay_mode=20;admit();wait(r_pending);hard_reset();mark("H2_RESET_ROM_PENDING");
  admit();send_word(0);wait(dut.u_exec.transfer==1);hard_reset();mark("H2_RESET_IMPORT_PENDING");
  @(negedge clk);weights_f_version=0;job_generation=next_generation;next_generation=next_generation+1;job_valid=1;
  do @(posedge clk);while(!job_ready);@(negedge clk);job_valid=0;
  frame();start();finish(1,0);if(a_starts||preqs)$fatal(1,"FAIL_H2_AF invalid F product started A");mark("H2_F_VERSION_ZERO_PRE_A_ARM");
  param_failure(1);mark("H2_PARAM_BAD_INDEX");
  param_failure(2);mark("H2_PARAM_BAD_LAST");
  param_failure(3);mark("H2_PARAM_ERROR");
  allow_param_req=0;admit();frame();start();wait(param_req_valid);tick(4);pulse_abort();finish(1,0);allow_param_req=1;mark("H2_PARAM_REQUEST_ABORT");
  allow_param_data=0;admit();frame();start();wait(pp_active);hard_reset();mark("H2_RESET_PARAM_PENDING");
  open_dumps("base");admit();frame();tick(10);
  if(done_valid||a_starts||param_req_valid||!input_stored||!start_ready)$fatal(1,"FAIL_H2_AF first ARM bypassed delayed parent start");
  start();@(negedge clk);weights_a_version=16'h9999;weights_f_version=0;
  finish(0,0);normal_counts(2);close_dumps();mark("H2_BASE_FULL_G1");
  // No hard/cohort reset between the two complete normal jobs.
  open_dumps("recovery");admit();frame();start();allow_sink_ack=0;
  wait(sink_state==3);tick(6);
  if(host_count||done_words||!out_valid||!out_ack_ready||sink_acks!=1||out_data!==gz[0])
   $fatal(1,"FAIL_H2_AF source advanced before explicit real sink ACK");
  @(negedge clk);allow_sink_ack=1;mark("H2_REAL_SINK_ACK_BACKPRESSURE");
  wait(done_valid);#1;normal_counts(4);finish(0,1);close_dumps();mark("H2_RECOVERY_FULL_G1_NO_RESET");
  if(cases!=18)$fatal(1,"FAIL_H2_AF case count");
  $display("H2_AF_STATS cycles=%0d jobs=%0d done=%0d",cycles,job_total,done_total);
  $display("PASS_H2_AF cases=%0d",cases);$finish;
 end
endmodule
