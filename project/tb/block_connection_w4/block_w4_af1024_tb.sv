`timescale 1ns/1ps
// Fixed parent AFULL -> two baseline F1024 calls. File golden is independent.
module block_w4_af1024_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,job_valid=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
 reg [31:0] job_generation=0,in_generation=0;reg [15:0] weights_a_version=16'h1234,weights_f_version=16'h5678;
 reg [127:0] in_data=0;reg [9:0] in_index=0;reg in_last=0;
 wire job_ready,in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,done_partial;
 wire [8:0] done_words;wire [31:0] done_generation,out_generation;
 wire out_valid,out_last;wire [127:0] out_data;wire [9:0] out_index;
 wire a_wreq_valid;reg a_wreq_ready=1;wire [31:0] a_wreq_job;wire [15:0] a_wreq_seq,a_wreq_version;
 wire [1:0] a_wreq_matrix;wire [3:0] a_wreq_head;wire [6:0] a_wreq_group;wire [5:0] a_wreq_chunk;
 wire a_w_ready,a_w_valid;wire [31:0] a_w_job;wire [15:0] a_w_seq,a_w_version;
 wire [3:0] a_w_index;wire a_w_last,a_w_error;wire [127:0] a_w_data;
 wire f_wreq_valid;reg f_wreq_ready=1;wire [15:0] f_wreq_job,f_wreq_seq,f_wreq_version;
 wire [1:0] f_wreq_matrix;wire [8:0] f_wreq_group;wire [6:0] f_wreq_chunk;wire f_wreq_row;
 wire f_w_ready,f_w_valid;wire [15:0] f_w_job,f_w_seq,f_w_version;
 wire [4:0] f_w_index;wire f_w_last,f_w_error;wire [127:0] f_w_data;
 block_w4_af1024_top dut(.*);
 reg [127:0] gx[0:575],ga[0:255],gz[0:255],aw[0:393215],fw[0:589823];
 reg [127:0] fn[0:255],fg[0:767],fu[0:767],fm[0:767],fd[0:255],fz[0:255],base_z[0:127];
 reg sat_parent[0:0],sat_a[0:0],sat_f[0:1];
 string vectors_dir,dump_dir,fixture_name;integer dump_i=0,dump_a=0,dump_f=0,dump_o=0;reg dumping=0;
 reg pa_active=0,pf_active=0;reg [31:0] pa_job=0;reg [15:0] pa_seq=0,pa_ver=0,pf_job=0,pf_seq=0,pf_ver=0;
 reg [3:0] pa_i=0;reg [4:0] pf_i=0;integer pa_fault=0,pf_fault=0,a_fault_mode=0,f_fault_mode=0;
 reg provider_gap=0;integer pa_delay=0,pf_delay=0;
 assign a_w_valid=pa_active&&pa_delay==0;
 assign a_w_job=pa_job+(pa_fault==3?32'd1:pa_fault==7?-32'd1:32'd0);
 assign a_w_seq=pa_seq+(pa_fault==4?16'd1:16'd0);assign a_w_version=pa_ver^(pa_fault==5?16'd1:16'd0);
 assign a_w_index=pa_i^(pa_fault==1?4'd1:4'd0);assign a_w_last=pa_fault==2?!(pa_i==15):pa_i==15;
 assign a_w_error=pa_fault==6;assign a_w_data=aw[int'(pa_seq)*16+int'(pa_i)];
 assign f_w_valid=pf_active&&pf_delay==0;
 assign f_w_job=pf_job+(pf_fault==3?16'd1:pf_fault==7?-16'd1:16'd0);
 assign f_w_seq=pf_seq+(pf_fault==4?16'd1:16'd0);assign f_w_version=pf_ver^(pf_fault==5?16'd1:16'd0);
 assign f_w_index=pf_i^(pf_fault==1?5'd16:5'd0);assign f_w_last=pf_fault==2?!(pf_i==15):pf_i==15;
 assign f_w_error=pf_fault==6;assign f_w_data=fw[int'(pf_seq)*16+int'(pf_i)];
 // Providers move state only with NBA, preserving data across the accepting edge.
 always @(posedge clk)begin
  if(dut.child_reset)begin pa_active<=0;pf_active<=0;pa_i<=0;pf_i<=0;pa_delay<=0;pf_delay<=0;end
  else begin
   if(a_wreq_valid&&a_wreq_ready)begin
    if(pa_active)$fatal(1,"FAIL_AF1024 overlapping A request");
    pa_active<=1;pa_job<=a_wreq_job;pa_seq<=a_wreq_seq;pa_ver<=a_wreq_version;pa_i<=0;pa_fault<=a_fault_mode;pa_delay<=provider_gap?2:0;
   end else if(pa_delay!=0)pa_delay<=pa_delay-1;
   if(a_w_valid&&a_w_ready)begin
    if(pa_i==15||pa_fault!=0)pa_active<=0;else begin pa_i<=pa_i+1'b1;pa_delay<=provider_gap?int'(pa_i)%3:0;end
   end
   if(f_wreq_valid&&f_wreq_ready)begin
    if(pf_active)$fatal(1,"FAIL_AF1024 overlapping F request");
    pf_active<=1;pf_job<=f_wreq_job;pf_seq<=f_wreq_seq;pf_ver<=f_wreq_version;pf_i<=0;pf_fault<=f_fault_mode;pf_delay<=provider_gap?2:0;
   end else if(pf_delay!=0)pf_delay<=pf_delay-1;
   if(f_w_valid&&f_w_ready)begin
    // A single old-job probe is drained, then the actual current request follows.
    if(pf_fault==7)begin pf_fault<=0;pf_delay<=3;end
    else if(pf_i==15||pf_fault!=0)pf_active<=0;else begin pf_i<=pf_i+1'b1;pf_delay<=provider_gap?int'(pf_i)%3:0;end
   end
  end
 end
 integer cycles=0,cases=0,next_generation=16384,jobs=0,done_takes=0,ingress=0,starts=0;
 reg tracking=0,obligation=0,inject_a_meta=0,inject_f_meta=0,inject_f_m=0;
 reg [31:0] active_generation=0;reg [15:0] active_av=0,active_fv=0;
 integer host_takes=0,y_captures=0,y_retires=0,gamma_captures=0;integer ix=0,host_count=0,ay_takes=0,ai=0,astart=0,adone=0,fstart=0,fdone=0,ajobs=0;
 reg y_pending=0;integer y_addr=0;reg [127:0] y_data=0;
 integer f_input_count=0,f_input_acks=0,f_output_count=0,current_row=0,a_req_index=0,f_req_index=0,f_old_beats=0;
 integer aq=0,aa=0,awrite=0,aread=0,fq=0,fa=0,fwrite_count=0,fread_count=0;
 integer amc=0,amr=0,anc=0,anr=0,aec=0,aer=0,aload=0,aflow=0,abflow=0,awide=0;
 integer fmc=0,fmr=0,fnc=0,fnr=0,fec=0,fer=0,fgsvc=0,fgpairs=0,fgretired=0,fload=0,fflow=0,fbflow=0,fwide=0;
 integer arq=0,arb=0,frq=0,frb=0,atakes=0,ftakes=0,arel=0,frel=0;
 integer aj0,j0,dt0,i0,st0;integer q0,aa0,aw0,ar0,fq0,fa0,fw0,fr0,am0,amr0,an0,anr0,ae0,aer0,al0,af0,ab0,awd0;
 integer fm0,fmr0,fn0,fnr0,fe0,fer0,fg0,fp0,fpr0,fl0,ff0,fb0,fwd0,arq0,arb0,frq0,frb0,at0,ft0,arel0,frel0,ast0,ad0,fs0,fd0;
 reg apending=0,fpending=0,apwrite=0,fpwrite=0;integer apaddr=0,fpaddr=0,fpowner=0,fp_matrix=0,fp_group=0;
 reg [127:0] apdata=0,fpdata=0,aram[0:1023],fram[0:1023];reg a_written[0:1023],f_written[0:1023];
 reg hold_done=0,hold_out=0;reg [43:0] old_done;reg [170:0] old_out;
 function automatic integer aseq;input integer matrix,head,group_i,chunk;begin
  if(matrix==0)aseq=head*2048+group_i*32+chunk;
  else if(matrix==1)aseq=head*2048+512+group_i*32+chunk;
  else if(matrix==2)aseq=(head/2)*2048+1024+(head%2)*512+group_i*32+chunk;
  else aseq=16384+group_i*64+chunk;
 end endfunction
 function automatic integer fseq;input integer matrix,group_i,chunk;begin
  fseq=matrix==2?24576+group_i*96+chunk:group_i*64+matrix*32+chunk;
 end endfunction
 function automatic [127:0] f_projection;input integer matrix,group_i;begin
  f_projection=matrix==0?fg[current_row*384+group_i]:matrix==1?fu[current_row*384+group_i]:fd[current_row*128+group_i];
 end endfunction
 function automatic [127:0] f_read_carrier;input integer half;integer j;reg [127:0] compact;reg signed [15:0] v;begin
  compact=f_projection(int'(dut.u_f.matrix),int'(dut.u_f.group_index));f_read_carrier=0;
  for(j=0;j<4;j=j+1)begin v=compact[(half*4+j)*16+:16];f_read_carrier[32*j+:32]={{16{v[15]}},v};end
 end endfunction
 function automatic [511:0] f_bword;input integer tile;begin
  f_bword=0;for(integer j=0;j<4;j=j+1)f_bword[128*j+:128]=fw[int'(dut.u_f.request_seq)*16+tile*4+j];
 end endfunction
 task automatic bytes_out;input integer file;input [127:0] data;begin for(integer j=0;j<16;j=j+1)$fwrite(file,"%c",data[j*8+:8]);end endtask
 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>500000000)$fatal(1,"FAIL_AF1024 watchdog state=%0d cases=%0d",dut.state,cases);
  if(reset)begin apending=0;fpending=0;hold_done=0;hold_out=0;obligation=0;end
  else begin
   if(hold_done&&(!done_valid||{done_error,done_saturated,done_partial,done_words,done_generation}!==old_done))$fatal(1,"FAIL_AF1024 held parent DONE");
   hold_done=done_valid&&!done_ready;old_done={done_error,done_saturated,done_partial,done_words,done_generation};
   if(dut.child_reset)begin apending=0;fpending=0;hold_out=0;y_pending=0;end
   else begin
    if(hold_out&&!inject_f_meta&&(!out_valid||{out_data,out_index,out_last,out_generation}!==old_out))$fatal(1,"FAIL_AF1024 held parent output");
    hold_out=out_valid&&!out_ready&&!inject_f_meta;old_out={out_data,out_index,out_last,out_generation};
   end
   if(job_valid&&job_ready)begin
    if(obligation)$fatal(1,"FAIL_AF1024 second admitted obligation");obligation=1;jobs=jobs+1;
    active_generation=job_generation;active_av=weights_a_version;active_fv=weights_f_version;
   end
   if(done_valid&&done_ready)begin
    if(!obligation||done_generation!==active_generation)$fatal(1,"FAIL_AF1024 unowned completion");done_takes=done_takes+1;obligation=0;
   end
   if(tracking&&!dut.child_reset)begin
    if(in_valid&&in_ready)begin
     ingress=ingress+1;
     if(in_generation==active_generation&&in_index==ix&&in_last==(ix==575))begin
      if(in_data!==gx[ix])$fatal(1,"FAIL_AF1024 parent input payload");ix=ix+1;if(dumping)bytes_out(dump_i,in_data);
     end
    end
    if(start_valid&&start_ready)begin if(ix!=576||ai!=448)$fatal(1,"FAIL_AF1024 parent start incomplete frame");starts=starts+1;end
    if(dut.a_job_valid&&dut.a_job_ready)ajobs=ajobs+1;
    if(dut.a_in_valid&&dut.a_in_ready)begin
     if(ai>=448||dut.u_a.in_data!==gx[ai]||dut.u_a.in_generation!==active_generation||dut.u_a.in_index!=ai||dut.u_a.in_last!==(ai==447))$fatal(1,"FAIL_AF1024 reconstructed A frame metadata");ai=ai+1;
    end
    if(dut.a_start_valid&&dut.a_start_ready)begin if(a_written[575]!==1'b1||ai!=448)$fatal(1,"FAIL_AF1024 A start before last real A ACK");astart=astart+1;end
    if(dut.a_out_valid&&dut.a_out_ready)begin
     if(inject_a_meta||dut.a_out_index!=ay_takes||dut.a_out_last!==(ay_takes==255)||dut.a_out_data!==ga[ay_takes])$fatal(1,"FAIL_AF1024 A output accepted wrong payload/metadata");
     if(!y_pending||dut.a_out_data!==y_data||f_input_acks<y_addr+1||(dut.f_in_valid&&dut.f_in_ready))$fatal(1,"FAIL_AF1024 A retire before actual F S ACK/double capture");
     y_pending=0;ay_takes=ay_takes+1;y_retires=y_retires+1;
    end
    if(dut.f_in_valid&&dut.f_in_ready)begin
     if(f_input_count<128)begin
      if(y_pending||!dut.a_out_valid||dut.a_out_ready||dut.a_out_index!=ay_takes||dut.f_in_data!==dut.a_out_data||dut.f_in_data!==ga[current_row*128+f_input_count])$fatal(1,"FAIL_AF1024 one-credit bit-preserved A to F capture");
      y_pending=1;y_addr=f_input_count;y_data=dut.f_in_data;y_captures=y_captures+1;
     end else begin if(dut.f_in_data!==gx[448+f_input_count-128])$fatal(1,"FAIL_AF1024 independent F gamma replay");gamma_captures=gamma_captures+1;end
     f_input_count=f_input_count+1;
    end
    if(dut.f_start_valid&&dut.f_start_ready)begin
     if(f_input_count!=256||f_input_acks!=256||!dut.f_input_stored||active_fv==0)$fatal(1,"FAIL_AF1024 F start before actual destination stored");
     fstart=fstart+1;
    end
    if(dut.a_done_valid&&dut.a_done_ready)begin
     if(dut.a_done_error||dut.a_done_saturated!==sat_a[0]||ay_takes!=256||arel-arel0!=2)$fatal(1,"FAIL_AF1024 A DONE without real T release");adone=adone+1;
    end
    if(dut.f_done_valid&&dut.f_done_ready)begin
     if(dut.f_done_error||dut.f_done_saturated!==sat_f[current_row]||f_output_count!=128||frel-frel0!=current_row+1)$fatal(1,"FAIL_AF1024 F DONE before actual output/release");
     fdone=fdone+1;current_row=current_row+1;f_input_count=0;f_input_acks=0;f_output_count=0;f_req_index=0;
     for(integer z=0;z<1024;z=z+1)f_written[z]=0;
    end
    if(current_row==0&&fstart-fs0==1&&fdone==fd0)begin
     if(ay_takes!=128||!dut.u_a.t_read_valid||dut.u_a.t_owner!=2||dut.u_a.t_read_index!=128||dut.u_a.t_read_data!==ga[128]||dut.u_a.t_generation!==active_generation||dut.u_a.t_word_count!=256||dut.a_done_valid)$fatal(1,"FAIL_AF1024 A source T not retained across full F0");
    end
    if(a_wreq_valid&&a_wreq_ready)begin
     if(a_wreq_job!==active_generation||a_wreq_version!==active_av||a_wreq_seq!=a_req_index||a_req_index!=aseq(int'(a_wreq_matrix),int'(a_wreq_head),int'(a_wreq_group),int'(a_wreq_chunk)))$fatal(1,"FAIL_AF1024 A request order/identity");
     a_req_index=a_req_index+1;arq=arq+1;
    end
    if(f_wreq_valid&&f_wreq_ready)begin
     if(f_wreq_job!==dut.f_job_mirror||f_wreq_version!==active_fv||f_wreq_row!==current_row[0]||f_wreq_seq!=f_req_index||f_req_index!=fseq(int'(f_wreq_matrix),int'(f_wreq_group),int'(f_wreq_chunk)))$fatal(1,"FAIL_AF1024 F request order/row/version");
     f_req_index=f_req_index+1;frq=frq+1;
    end
    if(a_w_valid&&a_w_ready)begin arb=arb+1;if(dumping)bytes_out(dump_a,a_w_data);end
    if(f_w_valid&&f_w_ready)begin
     if(pf_fault==7)f_old_beats=f_old_beats+1;else begin frb=frb+1;if(dumping)bytes_out(dump_f,f_w_data);end
    end
    if(dut.u_a.s_req&&dut.u_a.s_ready)begin
     if(apending)$fatal(1,"FAIL_AF1024 A S overlap");apending=1;apwrite=dut.u_a.s_we;apaddr=int'(dut.u_a.s_addr);apdata=dut.u_a.s_din;aq=aq+1;
     if(apwrite)begin
      if(astart==ast0)begin
       if(apdata!==gx[apaddr<384?apaddr:384+apaddr-512])$fatal(1,"FAIL_AF1024 actual A input write");
      end
      awrite=awrite+1;
     end else aread=aread+1;
    end
    if(dut.u_a.s_valid&&dut.u_a.s_take)begin
     if(!apending)$fatal(1,"FAIL_AF1024 A ACK unowned");aa=aa+1;
     if(apwrite)begin aram[apaddr]=apdata;a_written[apaddr]=1;end
     else if(!a_written[apaddr]||dut.u_a.s_dout!==aram[apaddr])$fatal(1,"FAIL_AF1024 A S read wrong ACK/version");apending=0;
    end
    if(dut.u_f.s_req&&dut.u_f.s_ready)begin
     if(fpending)$fatal(1,"FAIL_AF1024 F S overlap");fpending=1;fpwrite=dut.u_f.s_we;fpaddr=int'(dut.u_f.s_addr);fpdata=dut.u_f.s_din;fpowner=int'(dut.u_f.owner);fp_matrix=int'(dut.u_f.matrix);fp_group=int'(dut.u_f.group_index);fq=fq+1;
     if(fpwrite)begin
      if(fstart-fs0==current_row)begin
       if(fpaddr!=f_input_acks||fpdata!==(fpaddr<128?ga[current_row*128+fpaddr]:gx[448+fpaddr-128]))$fatal(1,"FAIL_AF1024 actual F input/gamma S write");
      end else if(fpowner==3)begin
       if(fpaddr<256||fpaddr>=384||fpdata!==fn[current_row*128+fpaddr-256])$fatal(1,"FAIL_AF1024 F full RMS1024 numeric write");
      end else if(fpowner==2)begin
       if(fpaddr<384||fpaddr>=768||fpdata!==fm[current_row*384+fpaddr-384])$fatal(1,"FAIL_AF1024 F3072 mid numeric write");
      end else if(fpowner==1)begin
       if(fpaddr<768||fpaddr>=896||fpdata!==fz[current_row*128+fpaddr-768])$fatal(1,"FAIL_AF1024 F residual Z numeric write");
      end else if(dut.u_f.local_tag==3&&fpdata!==f_projection(fp_matrix,fp_group))$fatal(1,"FAIL_AF1024 F gate/up/down fullK numeric write");
      else if(dut.u_f.local_tag==5&&fpdata!==fw[int'(dut.u_f.request_seq)*16+fpaddr-912])$fatal(1,"FAIL_AF1024 F weight write ordering");
      fwrite_count=fwrite_count+1;
     end else fread_count=fread_count+1;
    end
    if(dut.u_f.s_valid&&dut.u_f.s_take)begin
     if(!fpending)$fatal(1,"FAIL_AF1024 F ACK unowned");fa=fa+1;
     if(fpwrite)begin fram[fpaddr]=fpdata;f_written[fpaddr]=1;if(fstart-fs0==current_row)f_input_acks=f_input_acks+1;end
     else if(!f_written[fpaddr]||dut.u_f.s_dout!==fram[fpaddr])$fatal(1,"FAIL_AF1024 F S read wrong ACK/version");fpending=0;
    end
    if(dut.u_a.m_cmd_valid&&dut.u_a.m_cmd_ready)amc=amc+1;if(dut.u_a.m_rsp_valid&&dut.u_a.m_rsp_ready)amr=amr+1;
    if(dut.u_a.n_cmd_valid&&dut.u_a.n_cmd_ready)anc=anc+1;if(dut.u_a.n_native_rsp_valid&&dut.u_a.n_native_rsp_ready)anr=anr+1;
    if(dut.u_a.e_in_valid&&dut.u_a.e_in_ready)aec=aec+1;if(dut.u_a.e_out_valid&&dut.u_a.e_out_ready)aer=aer+1;
    if(dut.u_a.load_valid&&dut.u_a.load_ready)aload=aload+1;if(dut.u_a.a_valid&&dut.u_a.a_ready)aflow=aflow+1;if(dut.u_a.b_valid&&dut.u_a.b_ready)abflow=abflow+1;if(dut.u_a.u_s.feeder.mem_req&&dut.u_a.u_s.feeder.mem_ready)awide=awide+1;
    if(dut.u_f.m_cmd_valid&&dut.u_f.m_cmd_ready)fmc=fmc+1;
    if(dut.u_f.m_rsp_valid&&dut.u_f.m_rsp_ready)begin
     if(!inject_f_m&&!dut.u_f.m_rsp_error&&(dut.u_f.m_phase==3||dut.u_f.m_phase==4)&&dut.u_f.m_rsp_data!==f_read_carrier(dut.u_f.m_phase==4))$fatal(1,"FAIL_AF1024 F M READ carrier numeric");fmr=fmr+1;
    end
    if(dut.u_f.n_cmd_valid&&dut.u_f.n_cmd_ready)fnc=fnc+1;if(dut.u_f.n_native_rsp_valid&&dut.u_f.n_native_rsp_ready)fnr=fnr+1;
    if(dut.u_f.e_in_valid&&dut.u_f.e_in_ready)fec=fec+1;if(dut.u_f.e_out_valid&&dut.u_f.e_out_ready)fer=fer+1;
    if(dut.u_f.g_req_valid&&dut.u_f.g_req_ready)fgsvc=fgsvc+1;if(dut.u_f.g_in_valid&&dut.u_f.g_in_ready)fgpairs=fgpairs+1;if(dut.u_f.g_out_valid&&dut.u_f.g_out_ready)fgretired=fgretired+1;
    if(dut.u_f.load_valid&&dut.u_f.load_ready)fload=fload+1;
    if(dut.u_f.a_valid&&dut.u_f.a_ready)begin
     if(dut.u_f.a_row!=0||!dut.u_f.a_wide||dut.u_f.a_data!==(dut.u_f.matrix==2?fm[current_row*384+int'(dut.u_f.chunk_index)*4+int'(dut.u_f.a_tile)]:fn[current_row*128+int'(dut.u_f.chunk_index)*4+int'(dut.u_f.a_tile)]))$fatal(1,"FAIL_AF1024 F A128 actual layout");fflow=fflow+1;
    end
    if(dut.u_f.b_valid&&dut.u_f.b_ready)begin
     if(dut.u_f.b_wide||dut.u_f.b_half||dut.u_f.b_data!==f_bword(int'(dut.u_f.b_tile)))$fatal(1,"FAIL_AF1024 F B512 actual layout");fbflow=fbflow+1;
    end if(dut.u_f.u_s.feeder.mem_req&&dut.u_f.u_s.feeder.mem_ready)fwide=fwide+1;
    if(dut.u_a.t_read_valid&&dut.u_a.t_read_take)atakes=atakes+1;
    if(dut.u_f.t_read_valid&&dut.u_f.t_read_take)ftakes=ftakes+1;
    if(dut.u_a.t_release_valid&&dut.u_a.t_release_ready)arel=arel+1;
    if(dut.u_f.state==17&&dut.u_f.t_release_ready)frel=frel+1;
    if(out_valid&&out_ready)begin
     if(inject_f_meta||out_generation!==active_generation||out_index!=host_count||out_last!==(host_count==255)||out_data!==gz[host_count])$fatal(1,"FAIL_AF1024 host Z payload/metadata");
     if(!(dut.f_out_valid&&dut.f_out_ready))$fatal(1,"FAIL_AF1024 host take not paired F take");
     if(fixture_name=="base"&&host_count<128)base_z[host_count]=out_data;
     if(fixture_name=="future_changed"&&host_count<128&&out_data!==base_z[host_count])$fatal(1,"FAIL_AF1024 future token changed causal Z0");
     if(dumping)bytes_out(dump_o,out_data);host_count=host_count+1;host_takes=host_takes+1;f_output_count=f_output_count+1;
    end
   end
  end
 end
 task automatic tick;input integer n;begin repeat(n)begin @(posedge clk);#1;end end endtask
 task automatic mark;input string id;begin cases=cases+1;$display("CASE_PASS %s",id);$fflush();end endtask
 task automatic load_fixture;input string name;begin
  fixture_name=name;
  $readmemh({vectors_dir,"/",name,"/input.hex"},gx);$readmemh({vectors_dir,"/",name,"/a-weights.hex"},aw);$readmemh({vectors_dir,"/",name,"/f-weights.hex"},fw);
  $readmemh({vectors_dir,"/",name,"/expected-a-output.hex"},ga);$readmemh({vectors_dir,"/",name,"/expected-output.hex"},gz);
  $readmemh({vectors_dir,"/",name,"/expected-saturated.hex"},sat_parent);$readmemh({vectors_dir,"/",name,"/expected-a-saturated.hex"},sat_a);$readmemh({vectors_dir,"/",name,"/expected-f-saturated.hex"},sat_f);
  $readmemh({vectors_dir,"/",name,"/stage/f-norm.hex"},fn);$readmemh({vectors_dir,"/",name,"/stage/f-gate.hex"},fg);$readmemh({vectors_dir,"/",name,"/stage/f-up.hex"},fu);$readmemh({vectors_dir,"/",name,"/stage/f-mid.hex"},fm);$readmemh({vectors_dir,"/",name,"/stage/f-down.hex"},fd);$readmemh({vectors_dir,"/",name,"/stage/f-z.hex"},fz);
 end endtask
 task automatic snapshot;begin
  aj0=ajobs;j0=jobs;dt0=done_takes;i0=ingress;st0=starts;
  q0=aq;aa0=aa;aw0=awrite;ar0=aread;fq0=fq;fa0=fa;fw0=fwrite_count;fr0=fread_count;
  am0=amc;amr0=amr;an0=anc;anr0=anr;ae0=aec;aer0=aer;al0=aload;af0=aflow;ab0=abflow;awd0=awide;
  fm0=fmc;fmr0=fmr;fn0=fnc;fnr0=fnr;fe0=fec;fer0=fer;fg0=fgsvc;fp0=fgpairs;fpr0=fgretired;fl0=fload;ff0=fflow;fb0=fbflow;fwd0=fwide;
  arq0=arq;arb0=arb;frq0=frq;frb0=frb;at0=atakes;ft0=ftakes;arel0=arel;frel0=frel;ast0=astart;ad0=adone;fs0=fstart;fd0=fdone;
 end endtask
 task automatic admit;begin
  @(negedge clk);tracking=1;ix=0;host_count=0;ay_takes=0;ai=0;f_input_count=0;f_input_acks=0;f_output_count=0;current_row=0;a_req_index=0;f_req_index=0;y_pending=0;inject_a_meta=0;inject_f_meta=0;inject_f_m=0;
  for(integer z=0;z<1024;z=z+1)begin a_written[z]=0;f_written[z]=0;end
  snapshot();job_generation=next_generation;next_generation=next_generation+1;job_valid=1;
  do begin @(posedge clk);end while(!job_ready);@(negedge clk);job_valid=0;
  if(!busy)$fatal(1,"FAIL_AF1024 admitted parent not busy");
 end endtask
 task automatic send_word;input integer index;begin
  @(negedge clk);in_valid=1;in_data=gx[index];in_generation=active_generation;in_index=index[9:0];in_last=index==575;
  do begin @(posedge clk);end while(!in_ready);@(negedge clk);in_valid=0;
 end endtask
 task automatic frame;begin for(integer z=0;z<576;z=z+1)send_word(z);wait(input_stored);@(negedge clk);if(!start_ready)$fatal(1,"FAIL_AF1024 complete parent frame not startable");end endtask
 task automatic run_job;begin @(negedge clk);start_valid=1;do begin @(posedge clk);end while(!start_ready);@(negedge clk);start_valid=0;end endtask
 task automatic pulse_abort;begin @(negedge clk);abort=1;tick(1);@(negedge clk);abort=0;job_valid=0;in_valid=0;start_valid=0;out_ready=0;end endtask
 task automatic hard_reset;begin
  @(negedge clk);reset=1;abort=0;job_valid=0;in_valid=0;start_valid=0;out_ready=0;done_ready=0;tick(3);
  @(negedge clk);reset=0;tracking=0;a_fault_mode=0;f_fault_mode=0;provider_gap=0;inject_a_meta=0;inject_f_meta=0;inject_f_m=0;tick(3);
  if(busy||done_valid||out_valid||!job_ready)$fatal(1,"FAIL_AF1024 coordinated parent reset");
 end endtask
 task automatic finish;input bit err;input integer words;input bit abort_ready;integer before_take;begin
  wait(done_valid);#1;
  if(done_error!==err||done_words!=words||host_count!=words||done_partial!==(err&&words!=0)||done_generation!==active_generation)$fatal(1,"FAIL_AF1024 parent terminal fields err=%0d words=%0d",done_error,done_words);
  if(!err&&(done_saturated!==sat_parent[0]||adone-ad0!=1||fdone-fd0!=2||arel-arel0!=2||frel-frel0!=2))$fatal(1,"FAIL_AF1024 successful parent DONE before children/release/SAT");
  tick(4);before_take=done_takes;@(negedge clk);done_ready=1;abort=abort_ready;tick(1);@(negedge clk);done_ready=0;abort=0;tick(2);
  if(done_takes!=before_take+1||done_valid||busy||!job_ready||obligation)$fatal(1,"FAIL_AF1024 terminal exactly once/reuse");tracking=0;
 end endtask
 task automatic take_until;input integer count;begin
  @(negedge clk);out_ready=1;wait(host_count==count);@(negedge clk);out_ready=0;
 end endtask
 task automatic normal_counts;begin
  if(jobs-j0!=1||ingress-i0!=576||starts-st0!=1||ajobs-aj0!=1||ai!=448||ay_takes!=256||astart-ast0!=1||adone-ad0!=1||fstart-fs0!=2||fdone-fd0!=2||host_count!=256||current_row!=2)$fatal(1,"FAIL_AF1024 parent/child normal lifecycle counts");
  if(aq-q0!=806408||aa-aa0!=806408||awrite-aw0!=600424||aread-ar0!=205984||fq-fq0!=1776152||fa-fa0!=1776152||fwrite_count-fw0!=1478168||fread_count-fr0!=297984||apending||fpending)$fatal(1,"FAIL_AF1024 actual S ACK counts A=%0d/%0d F=%0d/%0d",aq-q0,aa-aa0,fq-fq0,fa-fa0);
  if(amc-am0!=30336||amr-amr0!=30336||anc-an0!=2340||anr-anr0!=2340||aec-ae0!=1024||aer-aer0!=1024||aload-al0!=24896||aflow-af0!=197632||abflow-ab0!=99328||awide-awd0!=198144)$fatal(1,"FAIL_AF1024 unchanged real A body counts");
  if(fmc-fm0!=80896||fmr-fmr0!=80896||fnc-fn0!=516||fnr-fnr0!=516||fec-fe0!=256||fer-fer0!=256||fgsvc-fg0!=768||fgpairs-fp0!=3072||fgretired-fpr0!=3072||fload-fl0!=73728||fflow-ff0!=294912||fbflow-fb0!=294912||fwide-fwd0!=589824)$fatal(1,"FAIL_AF1024 unchanged real F body counts");
  if(arq-arq0!=24576||arb-arb0!=393216||frq-frq0!=73728||frb-frb0!=1179648||atakes-at0!=512||ftakes-ft0!=256||arel-arel0!=2||frel-frel0!=2)$fatal(1,"FAIL_AF1024 provider/T normal counts");
 end endtask
 task automatic open_dumps;input string name;begin
  dump_i=$fopen({dump_dir,"/",name,"-accepted-input.bin"},"wb");dump_a=$fopen({dump_dir,"/",name,"-accepted-a-weights.bin"},"wb");dump_f=$fopen({dump_dir,"/",name,"-accepted-f-weights.bin"},"wb");dump_o=$fopen({dump_dir,"/",name,"-output.bin"},"wb");
  if(!dump_i||!dump_a||!dump_f||!dump_o)$fatal(1,"FAIL_AF1024 dump open");dumping=1;
 end endtask
 task automatic close_dumps;begin dumping=0;$fclose(dump_i);$fclose(dump_a);$fclose(dump_f);$fclose(dump_o);end endtask
 task automatic normal;input string name;input bit dumping_now,terminal_abort_ready;begin
  load_fixture(name);if(dumping_now)open_dumps(name);admit();frame();
  @(negedge clk);weights_a_version=16'h9999;weights_f_version=0;
  if(name=="base")begin
   @(negedge clk);force dut.permit_a_start=0;run_job();force dut.f_done_saturated=1'b1;tick(5);
   @(negedge clk);release dut.f_done_saturated;release dut.permit_a_start;
   wait(out_valid);tick(4);take_until(128);
   wait(dut.row_index&&dut.f_started&&dut.a_closed);@(negedge clk);force dut.a_done_saturated=1'b1;tick(5);@(negedge clk);release dut.a_done_saturated;
   take_until(256);
  end else if(name=="boundary")begin
   @(negedge clk);force dut.permit_f_feed=0;force dut.permit_f_start=0;force dut.permit_f_done=0;force dut.permit_a_done=0;run_job();
   wait(dut.a_out_valid);tick(4);if(ay_takes||f_input_count||dut.a_out_data!==ga[0])$fatal(1,"FAIL_AF1024 source hold before F ingress");
   @(negedge clk);force dut.u_f.permit_s_rsp=0;release dut.permit_f_feed;
   wait(f_input_count==1);wait(dut.u_f.s_valid);tick(4);
   if(ay_takes||f_input_acks||dut.a_out_index!=0||!y_pending)$fatal(1,"FAIL_AF1024 first Y retired before real F S ACK");
   @(negedge clk);release dut.u_f.permit_s_rsp;
   wait(ay_takes==127);@(negedge clk);force dut.u_f.permit_s_rsp=0;
   wait(f_input_count==128);wait(dut.u_f.s_valid);tick(4);
   if(ay_takes!=127||f_input_acks!=127||dut.a_out_index!=127||!y_pending)$fatal(1,"FAIL_AF1024 final Y retired before real F S ACK");
   @(negedge clk);release dut.u_f.permit_s_rsp;wait(dut.f_input_stored);tick(4);
   if(dut.f_start_valid||fstart!=fs0||ay_takes!=128)$fatal(1,"FAIL_AF1024 F start gate/source row preservation");
   @(negedge clk);release dut.permit_f_start;wait(out_valid);tick(4);take_until(128);wait(dut.f_done_valid);tick(4);
   if(dut.row_index||ay_takes!=128||fdone!=fd0)$fatal(1,"FAIL_AF1024 next row before F0 DONE consume");
   @(negedge clk);release dut.permit_f_done;take_until(256);wait(fdone-fd0==2);tick(4);
   if(done_valid||!dut.a_done_valid||dut.a_closed)$fatal(1,"FAIL_AF1024 parent DONE before A terminal collector");
   @(negedge clk);release dut.permit_a_done;
  end else begin run_job();wait(out_valid);tick(4);take_until(256);end
  finish(0,256,terminal_abort_ready);normal_counts();if(dumping_now)close_dumps();weights_a_version=16'h1234;weights_f_version=16'h5678;
 end endtask
 task automatic begin_run;begin load_fixture("base");a_fault_mode=0;f_fault_mode=0;admit();frame();run_job();end endtask
 task automatic bad_a_provider;input integer mode;integer before_q,before_w;begin
  @(negedge clk);force dut.u_a.permit_wrx=0;begin_run();@(negedge clk);a_fault_mode=mode;
  do begin @(posedge clk);end while(!(a_wreq_valid&&a_wreq_ready));#1;before_q=aq;before_w=awrite;
  @(negedge clk);release dut.u_a.permit_wrx;finish(1,0,0);a_fault_mode=0;
  if(aq!=before_q||awrite!=before_w||ay_takes||fstart!=fs0)$fatal(1,"FAIL_AF1024 rejected A provider side effect");
 end endtask
 task automatic bad_f_provider;input integer mode;integer before_q,before_w;begin
  @(negedge clk);force dut.u_f.permit_wrx=0;begin_run();@(negedge clk);f_fault_mode=mode;
  do begin @(posedge clk);end while(!(f_wreq_valid&&f_wreq_ready));#1;before_q=fq;before_w=fwrite_count;
  @(negedge clk);release dut.u_f.permit_wrx;finish(1,0,0);f_fault_mode=0;
  if(fq!=before_q||fwrite_count!=before_w||host_count)$fatal(1,"FAIL_AF1024 rejected F provider side effect");
 end endtask
 initial begin
  if(!$value$plusargs("vectors=%s",vectors_dir)||!$value$plusargs("dump_dir=%s",dump_dir))$fatal(1,"FAIL_AF1024 require +vectors/+dump_dir");
  hard_reset();load_fixture("base");
  pulse_abort();tick(3);if(done_valid||busy)$fatal(1,"FAIL_AF1024 idle abort obligation");mark("AF1024_IDLE_ABORT");
  @(negedge clk);weights_f_version=0;admit();finish(1,0,0);if(ajobs!=aj0||aq!=q0||fq!=fq0)$fatal(1,"FAIL_AF1024 version0 admitted child");weights_f_version=16'h5678;mark("AF1024_REJECT_F_VERSION_ZERO_BEFORE_A_ADMIT");
  @(negedge clk);force dut.f_job_mirror=16'hfffe;admit();release dut.f_job_mirror;finish(1,0,0);if(ajobs!=aj0)$fatal(1,"FAIL_AF1024 insufficient two F IDs admitted child");mark("AF1024_TWO_F_ID_RESERVATION_GUARD");
  admit();send_word(0);@(negedge clk);start_valid=1;tick(3);if(start_ready||astart!=ast0)$fatal(1,"FAIL_AF1024 partial frame start");@(negedge clk);start_valid=0;pulse_abort();finish(1,0,0);mark("AF1024_PARTIAL_INPUT_EARLY_START_ABORT");
  admit();for(integer j=0;j<447;j=j+1)send_word(j);wait(aa-aa0==447);@(negedge clk);force dut.u_a.permit_s_rsp=0;
  send_word(447);for(integer j=448;j<576;j=j+1)send_word(j);@(negedge clk);start_valid=1;tick(5);
  if(input_stored||start_ready||astart!=ast0||ix!=576)$fatal(1,"FAIL_AF1024 parent gamma bank bypassed A last write ACK");
  @(negedge clk);start_valid=0;release dut.u_a.permit_s_rsp;wait(input_stored);pulse_abort();finish(1,0,0);mark("AF1024_LAST_A_ACK_WITH_COMPLETE_PARENT_GAMMA");
  admit();wait(in_ready);@(negedge clk);in_valid=1;in_generation=active_generation;in_index=1;in_last=0;in_data=gx[0];tick(1);@(negedge clk);in_valid=0;finish(1,0,0);if(aq!=q0)$fatal(1,"FAIL_AF1024 bad parent index escaped A");
  admit();wait(in_ready);@(negedge clk);in_valid=1;in_generation=active_generation;in_index=0;in_last=1;in_data=gx[0];tick(1);@(negedge clk);in_valid=0;finish(1,0,0);if(aq!=q0)$fatal(1,"FAIL_AF1024 bad parent last escaped A");
  admit();wait(in_ready);@(negedge clk);in_valid=1;in_generation=active_generation-1;in_index=0;in_last=0;in_data=gx[0];tick(1);@(negedge clk);in_valid=0;finish(1,0,0);if(aq!=q0)$fatal(1,"FAIL_AF1024 stale parent generation escaped A");mark("AF1024_PARENT_BAD_METADATA_NO_CHILD_WRITE");
  normal("base",1,0);mark("AF1024_BASE_FULL_REAL_A_TO_TWO_F_ROWS");
  provider_gap=1;normal("future_changed",1,0);provider_gap=0;mark("AF1024_FUTURE_CHANGED_CAUSAL_Z0_BIT_PRESERVED");
  normal("boundary",1,0);mark("AF1024_BOUNDARY_HANDOFF_START_DONE_GATES");
  load_fixture("base");weights_a_version=0;admit();frame();@(negedge clk);weights_a_version=16'h7777;weights_f_version=16'h8888;run_job();wait(a_wreq_valid);
  if(a_wreq_version!=0||dut.f_version_hold!=16'h5678)$fatal(1,"FAIL_AF1024 independent captured A/F versions");pulse_abort();finish(1,0,0);weights_a_version=16'h1234;weights_f_version=16'h5678;mark("AF1024_A_ZERO_AND_INDEPENDENT_VERSION_CAPTURE");
  begin_run();@(negedge clk);a_wreq_ready=0;wait(a_wreq_valid);tick(4);if(a_w_ready)$fatal(1,"FAIL_AF1024 A response before request accept");@(negedge clk);a_wreq_ready=1;pulse_abort();finish(1,0,0);mark("AF1024_A_PROVIDER_REQUEST_BACKPRESSURE");
  load_fixture("base");admit();send_word(0);@(negedge clk);force f_w_valid=1'b1;force f_w_job=16'd0;tick(4);
  if(f_w_ready||frq!=frq0||fq!=fq0)$fatal(1,"FAIL_AF1024 F provider active before child start");@(negedge clk);release f_w_valid;release f_w_job;pulse_abort();finish(1,0,0);mark("AF1024_F_PROVIDER_DISABLED_BEFORE_F_START");
  bad_a_provider(1);bad_a_provider(2);bad_a_provider(7);mark("AF1024_A_PROVIDER_BAD_INDEX_LAST_OLD_TAG");
  bad_a_provider(6);mark("AF1024_A_PROVIDER_ERROR_PROPAGATION");
  begin_run();wait(f_input_count==1);wait(dut.u_f.h_rsp_valid);@(negedge clk);force dut.u_f.h_rsp_error=1'b1;
  do begin @(posedge clk);end while(!(dut.u_f.h_rsp_valid&&dut.u_f.h_rsp_ready));@(negedge clk);release dut.u_f.h_rsp_error;finish(1,0,0);
  if(ay_takes!=0||f_input_count!=1||fstart!=fs0)$fatal(1,"FAIL_AF1024 dropped F partial frame accepted more source");mark("AF1024_F_PRESTART_FRAME_ERROR_WITHOUT_CHILD_DONE");
  begin_run();wait(dut.a_out_valid);@(negedge clk);inject_a_meta=1;force dut.a_out_generation=32'd0;tick(1);@(negedge clk);release dut.a_out_generation;finish(1,0,0);
  if(ay_takes||f_input_count)$fatal(1,"FAIL_AF1024 bad A metadata entered F");mark("AF1024_A_OUTPUT_METADATA_GATE");
  begin_run();wait(f_input_count==255);wait(dut.u_f.in_ready);@(negedge clk);force dut.u_f.permit_s_rsp=0;wait(f_input_count==256);wait(dut.u_f.s_valid);tick(5);
  if(dut.f_input_stored||dut.f_start_valid||f_input_acks!=255||ay_takes!=128)$fatal(1,"FAIL_AF1024 F last gamma ACK bypassed start");
  pulse_abort();@(negedge clk);release dut.u_f.permit_s_rsp;finish(1,0,0);mark("AF1024_F_LAST_GAMMA_ACK_GATES_START");
  @(negedge clk);force dut.permit_f_start=0;begin_run();wait(dut.f_input_stored);tick(4);if(fstart!=fs0||ay_takes!=128)$fatal(1,"FAIL_AF1024 deferred F start source hold");
  pulse_abort();@(negedge clk);release dut.permit_f_start;finish(1,0,0);mark("AF1024_F_START_DEFERRED_ABORT");
  bad_f_provider(1);mark("AF1024_F_PROVIDER_BAD_INDEX");bad_f_provider(5);mark("AF1024_F_PROVIDER_BAD_VERSION");
  @(negedge clk);force dut.u_f.permit_wrx=0;begin_run();@(negedge clk);f_fault_mode=7;
  do begin @(posedge clk);end while(!(f_wreq_valid&&f_wreq_ready));#1;
  begin : stale_probe
   integer old_q,old_w,old_stale;old_q=fq;old_w=fwrite_count;old_stale=f_old_beats;
   wait(f_old_beats==old_stale+1);tick(2);if(fq!=old_q||fwrite_count!=old_w||done_valid)$fatal(1,"FAIL_AF1024 inherited F stale drain mutated current task");
  end
  pulse_abort();@(negedge clk);release dut.u_f.permit_wrx;f_fault_mode=0;finish(1,0,0);mark("AF1024_F_OLD_TAG_DRAIN_WITHOUT_CURRENT_S_WRITE");
  begin_run();wait(dut.u_a.n_cmd_valid&&dut.u_a.n_cmd_op==1);@(negedge clk);force dut.u_a.n_cmd_op=4'd15;
  do begin @(posedge clk);end while(!(dut.u_a.n_cmd_valid&&dut.u_a.n_cmd_ready));@(negedge clk);release dut.u_a.n_cmd_op;finish(1,0,0);mark("AF1024_A_NATIVE_N_ERROR");
  begin_run();wait(dut.u_a.m_cmd_valid&&dut.u_a.m_cmd_op==10);@(negedge clk);force dut.u_a.m_cmd_data=64'h1488d;
  do begin @(posedge clk);end while(!(dut.u_a.m_cmd_valid&&dut.u_a.m_cmd_ready));@(negedge clk);release dut.u_a.m_cmd_data;finish(1,0,0);mark("AF1024_A_NATIVE_M_ERROR");
  begin_run();wait(dut.u_f.n_cmd_valid&&dut.u_f.n_cmd_op==1);@(negedge clk);force dut.u_f.n_cmd_op=4'd15;
  do begin @(posedge clk);end while(!(dut.u_f.n_cmd_valid&&dut.u_f.n_cmd_ready));@(negedge clk);release dut.u_f.n_cmd_op;finish(1,0,0);mark("AF1024_F_NATIVE_N_ERROR");
  begin_run();wait(dut.u_f.g_in_valid);@(negedge clk);force dut.u_f.g_in_fn=3'd4;
  do begin @(posedge clk);end while(!(dut.u_f.g_in_valid&&dut.u_f.g_in_ready));@(negedge clk);release dut.u_f.g_in_fn;finish(1,0,0);mark("AF1024_F_NATIVE_G_ERROR");
  @(negedge clk);force dut.permit_a_start=0;begin_run();tick(5);if(astart!=ast0)$fatal(1,"FAIL_AF1024 A started despite parent deferred gate");pulse_abort();@(negedge clk);release dut.permit_a_start;finish(1,0,0);mark("AF1024_PARENT_RUN_BEFORE_A_START_ABORT");
  begin_run();wait(f_input_count>=129);pulse_abort();finish(1,0,0);mark("AF1024_PARTIAL_F_GAMMA_FEED_ABORT");
  load_fixture("base");admit();send_word(0);hard_reset();mark("AF1024_HARD_RESET_PARTIAL_INPUT");
  begin_run();wait(dut.u_a.state==16);hard_reset();mark("AF1024_HARD_RESET_A_WEIGHT_PENDING");
  begin_run();wait(out_valid);tick(4);take_until(1);pulse_abort();finish(1,1,0);mark("AF1024_HOST_PREFIX_ABORT_PARTIAL");
  begin_run();take_until(128);wait(dut.row_index&&dut.u_f.n_cmd_valid&&dut.u_f.n_cmd_op==1);@(negedge clk);force dut.u_f.n_cmd_op=4'd15;
  do begin @(posedge clk);end while(!(dut.u_f.n_cmd_valid&&dut.u_f.n_cmd_ready));@(negedge clk);release dut.u_f.n_cmd_op;finish(1,128,0);mark("AF1024_SECOND_F_ROW_ERROR_RETAINS_FIRST_ROW");
  begin_run();wait(dut.f_out_valid);@(negedge clk);inject_f_meta=1;force dut.f_out_index=10'd1;out_ready=1;tick(1);@(negedge clk);out_ready=0;release dut.f_out_index;finish(1,0,0);mark("AF1024_F_OUTPUT_METADATA_NOT_PUBLISHED");
  begin_run();wait(out_valid);tick(4);hard_reset();mark("AF1024_HARD_RESET_HELD_F_OUTPUT");
  normal("base",0,1);mark("AF1024_FULL_RECOVERY_HELD_DONE_ABORT_READY");
  if(cases!=34)$fatal(1,"FAIL_AF1024 declared CASE count=%0d",cases);
  $display("AF1024_COUNTS cycles=%0d jobs=%0d input=%0d AS=%0d/%0d FS=%0d/%0d AM=%0d/%0d FM=%0d/%0d Aweights=%0d Fweights=%0d Atake=%0d Ftake=%0d Arelease=%0d Frelease=%0d Ycapture=%0d Yretire=%0d gamma=%0d host=%0d done=%0d",cycles,jobs,ingress,aq,aa,fq,fa,amc,amr,fmc,fmr,arb,frb,atakes,ftakes,arel,frel,y_captures,y_retires,gamma_captures,host_takes,done_takes);
  $display("PASS_AF1024 cases=%0d",cases);$finish;
 end
endmodule
