`timescale 1ns/1ps
// Finite fixture program drives the actual physical-port M leaf, both local
// packers, real four-bank S and exact merge. LC ISA execution is not modeled
// as free: every command/response flit is clocked and traced below. This
// fixture is not a deployed LC/MC program image or a physical timing claim.
module tb_product;
 reg clk;initial begin clk=0;forever #5 clk=~clk;end
 reg reset=1;
 reg lc_valid=0,lc_sop=0,lc_eop=0;wire lc_ready;reg [127:0] lc_data;
 wire lr_valid,lr_sop,lr_eop;reg lr_ready;wire [127:0] lr_data;
 wire a_valid,a_ready;wire [255:0] a_data;reg [31:0] a_session;reg [2:0] a_beat;
 wire mc_req_valid,mc_req_ready,mc_req_channel,mc_rsp_valid,mc_rsp_ready;
 wire [63:0] mc_req_address;wire [31:0] mc_req_tag,mc_rsp_tag;wire [4:0] mc_req_record_beats;
 wire [511:0] mc_rsp_data;
 wire mc_close_valid,mc_close_ready;wire [31:0] mc_close_tag_base;
 wire mc_fence_req_valid,mc_fence_done_ready;wire [31:0] mc_fence_req_cookie;
 wire [8:0] mc_fence_req_epoch;reg fence_live;reg [31:0] fence_cookie;reg [8:0] fence_epoch;
 wire fault_interrupt;
 m_native_leaf_s32 m(.clk,.reset,.lc_valid,.lc_ready,.lc_sop,.lc_eop,.lc_data,
  .lr_valid,.lr_ready,.lr_sop,.lr_eop,.lr_data,.a_valid,.a_ready,.a_data,.a_session,.a_beat,
  .mc_req_valid,.mc_req_ready,.mc_req_address,.mc_req_tag,.mc_req_channel,.mc_req_record_beats,
  .mc_close_valid,.mc_close_ready,.mc_close_tag_base,.mc_rsp_valid,.mc_rsp_ready,.mc_rsp_tag,.mc_rsp_data,
  .mc_fence_req_valid,.mc_fence_req_ready(1'b1),.mc_fence_req_cookie,.mc_fence_req_epoch,
  .mc_fence_done_valid(fence_live),.mc_fence_done_ready,.mc_fence_done_cookie(fence_cookie),
  .mc_fence_done_epoch(fence_epoch),.fault_interrupt);
 reg bind_valid=0,release_valid=0;wire bind_ready,bind_ack_valid,bind_ack_error,release_ready;
 reg [127:0] bind_key;wire [127:0] bind_ack_key;
 reg [63:0] bind_record_base;reg [31:0] bind_scalar_base,bind_k_stride,bind_n_stride;
 reg [7:0] bind_length;reg [3:0] bind_n;reg [2:0] bind_digit;reg bind_k_major;
 wire source_fault,source_active,source_quiescent,cancel_ready;wire [3:0] source_reason;
 wire [31:0] source_fault_tag;wire [63:0] source_fault_address;wire [4:0] source_returned;
 wire ws_valid,ws_ready,wr_valid,wr_ready;wire [31:0] ws_address,ws_tag,wr_tag;wire [127:0] wr_data;
 dynamic_s32_weight_source source(.clk,.reset,.bind_valid,.bind_ready,.bind_key,.bind_record_base,
  .bind_scalar_base,.bind_k_stride,.bind_n_stride,.bind_length,.bind_n,.bind_digit,.bind_k_major,
  .bind_ack_valid,.bind_ack_ready(1'b1),.bind_ack_key,.bind_ack_error,
  .release_valid,.release_ready,.release_key(bind_key),.cancel_valid(1'b0),.cancel_ready,.cancel_key(128'd0),
  .close_valid(mc_close_valid),.close_ready(mc_close_ready),.close_tag_base(mc_close_tag_base),
  .req_valid(mc_req_valid),.req_ready(mc_req_ready),.req_address(mc_req_address),.req_tag(mc_req_tag),.req_record_beats(mc_req_record_beats),
  .rsp_valid(mc_rsp_valid),.rsp_ready(mc_rsp_ready),.rsp_tag(mc_rsp_tag),.rsp_data(mc_rsp_data),
  .s_valid(ws_valid),.s_ready(ws_ready),.s_address(ws_address),.s_tag(ws_tag),
  .r_valid(wr_valid),.r_ready(wr_ready),.r_tag(wr_tag),.r_data(wr_data),.r_error(1'b0),
  .fault_valid(source_fault),.fault_ready(1'b0),.fault_reason(source_reason),.fault_tag(source_fault_tag),
  .fault_address(source_fault_address),.active(source_active),.quiescent(source_quiescent),.returned_beats(source_returned));
 reg ap_cmd=0;wire ap_ready,ap_valid,ap_take,ap_error,ap_weight;wire [31:0] ap_tag;wire [511:0] ap_data;
 reg [31:0] ap_base;reg [2:0] ap_digit;reg [4:0] ap_k;
 wire as_valid,as_ready,ar_valid,ar_ready;wire [31:0] as_address,as_tag,ar_tag;wire [127:0] ar_data;
 reg zero_a=0,zero_valid=0;
 dynamic_s32_packer a_packer(.clk,.reset,.cmd_valid(ap_cmd),.cmd_ready(ap_ready),.cmd_tag(a_session),
  .cmd_weight(1'b0),.cmd_k_major(1'b0),.cmd_digit(ap_digit),.cmd_scalar_base(ap_base),
  .cmd_k_stride(32'd1),.cmd_n_stride(32'd0),.cmd_k_count(ap_k),.cmd_n_count(3'd1),
  .s_valid(as_valid),.s_ready(as_ready),.s_address(as_address),.s_tag(as_tag),
  .r_valid(ar_valid),.r_ready(ar_ready),.r_tag(ar_tag),.r_data(ar_data),.r_error(1'b0),
  .out_valid(ap_valid),.out_ready(ap_take),.out_tag(ap_tag),.out_weight(ap_weight),.out_error(ap_error),.out_data(ap_data));
 assign a_valid=zero_a ? zero_valid : ap_valid;
 assign a_data=zero_a ? 256'd0 : ap_data[255:0];
 assign ap_take=!zero_a && a_ready;
 reg booting=1,boot_valid=0,boot_write=1;reg [9:0] boot_address;reg [127:0] boot_data;
 reg final_write=0;
 wire bank_ready,bank_valid;wire [127:0] bank_data;
 reg response_owner;reg [31:0] response_tag;reg allow_request,allow_response;
 wire bank_req_valid=booting ? boot_valid : (ws_valid || as_valid) && allow_request;
 wire [31:0] selected_address=ws_valid ? ws_address : as_address;
 wire [31:0] selected_tag=ws_valid ? ws_tag : as_tag;
 wire bank_rsp_ready=booting ? 1'b1 : allow_response && (response_owner ? ar_ready : wr_ready);
 local_s_base storage(.clk,.reset,.req_valid(bank_req_valid),.req_write(booting && boot_write),
  .req_addr(booting ? boot_address : selected_address[9:0]),.req_data(boot_data),
  .req_ready(bank_ready),.rsp_valid(bank_valid),.rsp_ready(bank_rsp_ready),.rsp_data(bank_data));
 assign ws_ready=!booting && allow_request && bank_ready;
 assign as_ready=!booting && !ws_valid && allow_request && bank_ready;
 assign wr_valid=!booting && !response_owner && allow_response && bank_valid;
 assign ar_valid=!booting && response_owner && allow_response && bank_valid;
 assign wr_tag=response_tag;assign ar_tag=response_tag;assign wr_data=bank_data;assign ar_data=bank_data;
 reg merge_valid=0,merge_take=0;wire merge_ready,merge_out,merge_error,merge_done;
 reg [1:0] merge_kind;reg [127:0] merge_key;reg [31:0] merge_tag;
 reg [15:0] merge_full,merge_kk;reg [7:0] merge_length;reg [3:0] merge_n;
 reg [1:0] merge_ai;reg [2:0] merge_bi;reg [5:0] merge_shift;reg [255:0] merge_raw;
 wire [1:0] merge_out_kind;wire [127:0] merge_out_key;wire [31:0] merge_out_tag;wire [255:0] merge_data;
 dynamic_s32_merge merge(.clk,.reset,.in_valid(merge_valid),.in_ready(merge_ready),.in_kind(merge_kind),
  .in_key(merge_key),.in_tag(merge_tag),.in_full_k(merge_full),.in_kk(merge_kk),.in_length(merge_length),
  .in_n(merge_n),.in_ai(merge_ai),.in_bi(merge_bi),.in_shift(merge_shift),.in_raw(merge_raw),
  .out_valid(merge_out),.out_ready(merge_take),.out_kind(merge_out_kind),.out_key(merge_out_key),
  .out_tag(merge_out_tag),.out_error(merge_error),.out_done(merge_done),.out_data(merge_data));
 integer cycle,mc_requests,mc_returns,a_beats,s_reads,s_acks,partial_count,lc_words,lr_words,boot_writes,result_writes,result_reads;
 reg [511:0] lr_frame;reg [1:0] lr_index;reg [31:0] last_event[0:15];
 reg [255:0] observed_raw;reg [1:0] observed_bank;reg [15:0] observed_generation;
 reg [31:0] current_record;reg [31:0] sequence_number=1;reg [15:0] scope_generation=0;
 reg [127:0] words[0:7];
 integer ideal_mode=0;
 initial begin if($value$plusargs("ideal=%d",ideal_mode))begin end end
 always @(negedge clk)begin
  if(reset)begin lr_ready=0;allow_request=0;allow_response=0;end
  else begin
   lr_ready=ideal_mode!=0 || $urandom_range(0,3)!=0;
   allow_request=ideal_mode!=0 || $urandom_range(0,3)!=0;
   allow_response=ideal_mode!=0 || $urandom_range(0,3)!=0;
  end
 end
 always @(posedge clk)begin
  if(reset)begin
   cycle=0;mc_requests=0;mc_returns=0;a_beats=0;s_reads=0;s_acks=0;partial_count=0;lc_words=0;lr_words=0;boot_writes=0;result_writes=0;result_reads=0;
   response_owner=0;response_tag=0;lr_frame=0;lr_index=0;fence_live=0;fence_cookie=0;fence_epoch=0;
   for(integer j=0;j<16;j=j+1)last_event[j]=0;
  end else begin
   cycle=cycle+1;
   if(source_fault)$fatal(1,"source fault %0d tag%0d address%0d",source_reason,source_fault_tag,source_fault_address);
   if(fault_interrupt)$fatal(1,"actual product fault interrupt");
   if(ws_valid && as_valid)$fatal(1,"fixture requests two S sources without arbiter");
   if(!booting && bank_req_valid && bank_ready)begin
    if(selected_address[31:10]!=0)$fatal(1,"actual16KiB S overflow");
    response_owner=!ws_valid;response_tag=selected_tag;s_reads=s_reads+1;
    $display("JOINT_S_REQ cycle=%0d owner=%0d address=%0d",cycle,!ws_valid,selected_address);
   end
   if(!booting && bank_valid && bank_rsp_ready)begin s_acks=s_acks+1;$display("JOINT_S_ACK cycle=%0d",cycle);end
   if(mc_req_valid && mc_req_ready)begin
    if(mc_req_record_beats!=17)$fatal(1,"not complete ordinary W-first record");
    mc_requests=mc_requests+1;$display("JOINT_LOCAL_MC_REQ cycle=%0d channel=%0d tag=%0d",cycle,mc_req_channel,mc_req_tag);
   end
   if(mc_rsp_valid && mc_rsp_ready)begin mc_returns=mc_returns+1;$display("JOINT_LOCAL_MC_RETURN cycle=%0d tag=%0d",cycle,mc_rsp_tag);end
   if(a_valid && a_ready)begin
    if(!zero_a && (ap_tag!=a_session || ap_weight || ap_error || ap_data[511:256]!=0))$fatal(1,"actual A packet identity");
    a_beats=a_beats+1;$display("JOINT_A cycle=%0d record=%0d beat=%0d",cycle,current_record,a_beat);
   end
   if(lc_valid && lc_ready)begin lc_words=lc_words+1;$display("JOINT_LC cycle=%0d data=%032h",cycle,lc_data);end
   if(lr_valid && lr_ready)begin
    if(lr_sop && lr_index!=0)$fatal(1,"nested LR frame");
    lr_frame[lr_index*128+:128]=lr_data;lr_words=lr_words+1;
    if(lr_eop)begin
     $display("JOINT_LR_FRAME cycle=%0d value=%0128h",cycle,lr_frame);
     if(lr_frame[31:0]!=32'h02504d02 || lr_frame[47:40]!=0)$fatal(1,"LR ABI/error");
     last_event[lr_frame[35:32]]=lr_frame[79:48];
     if(lr_frame[39:32]==1)begin observed_bank=lr_frame[129:128];observed_generation=lr_frame[145:130];end
     if(lr_frame[39:32]==4 && lr_frame[112])begin
      observed_raw=lr_frame[511:256];partial_count=partial_count+1;
      $display("JOINT_RAW cycle=%0d record=%0d value=%064h",cycle,current_record,observed_raw);
     end
     lr_index=0;lr_frame=0;
    end else lr_index=lr_index+1'b1;
   end
   if(mc_fence_req_valid)begin fence_live=1;fence_cookie=mc_fence_req_cookie;fence_epoch=mc_fence_req_epoch;end
   else if(fence_live && mc_fence_done_ready)fence_live=0;
  end
 end
 task automatic header(input [3:0] opcode,input [3:0] length,input [31:0] session,input [31:0] record_id);
  begin
   for(integer j=0;j<8;j=j+1)words[j]=0;
   words[0]={16'd0,scope_generation,record_id,session,4'd0,4'd0,length,opcode,16'h4d02};
  end
 endtask
 task automatic send(input integer length);
  begin
   for(integer j=0;j<length;j=j+1)begin
    lc_data=words[j];lc_sop=j==0;lc_eop=j==length-1;lc_valid=1;
    do @(posedge clk);while(!lc_ready);#1;lc_valid=0;
   end
   lc_sop=0;lc_eop=0;
  end
 endtask
 task automatic wait_event(input [31:0] session,input [3:0] event_id);
  begin while(last_event[event_id]!=session)begin @(posedge clk);#1;end end
 endtask
 task automatic store_word(input [9:0] address,input [127:0] data);
  begin
   boot_write=1;boot_address=address;boot_data=data;boot_valid=1;
   do @(posedge clk);while(!bank_ready);#1;boot_valid=0;
   while(!bank_valid)begin @(posedge clk);#1;end
   @(posedge clk);#1;
   if(final_write)result_writes=result_writes+1;else boot_writes=boot_writes+1;
   $display("JOINT_WRITE_ACK cycle=%0d final=%0d address=%0d",cycle,final_write,address);
  end
 endtask
 task automatic read_result(input [9:0] address,input [127:0] expected);
  begin
   boot_write=0;boot_address=address;boot_valid=1;
   do @(posedge clk);while(!bank_ready);#1;boot_valid=0;
   while(!bank_valid)begin @(posedge clk);#1;end
   if(bank_data!==expected)$fatal(1,"final persistent S32 readback differs");
   @(posedge clk);#1;result_reads=result_reads+1;
  end
 endtask
 task automatic merge_packet(input bit expect_done,input [255:0] expected);
  begin
   merge_valid=1;do @(posedge clk);while(!merge_ready);#1;merge_valid=0;
   while(!merge_out)begin @(posedge clk);#1;end
   if(merge_error || merge_done!=expect_done || merge_out_kind!=merge_kind ||
      merge_out_key!=merge_key || merge_out_tag!=merge_tag || merge_data!==expected)$fatal(1,"joint merge failure");
   if(expect_done)begin
    booting=1;final_write=1;
    store_word(10'd300,merge_data[127:0]);store_word(10'd301,merge_data[255:128]);
    if(!merge_out || merge_data!==expected)$fatal(1,"merge source released before true S write ACKs");
    final_write=0;read_result(10'd300,expected[127:0]);read_result(10'd301,expected[255:128]);
    booting=0;boot_write=1;
   end
   merge_take=1;@(posedge clk);#1;merge_take=0;merge_tag=merge_tag+1'b1;
  end
 endtask
 string path;integer fd,got,cases=0,full,n,shift,major,length,offset,index,scalar_index,valid_k;
 reg [31:0] av[0:511],bv[0:4095];reg [255:0] final_expected,partial_expected;
 reg [127:0] word_data;reg [31:0] sid,alloc_sid,exec_sid;
 initial begin
  if(!$value$plusargs("vectors=%s",path))$fatal(1,"joint vectors missing");
  fd=$fopen(path,"r");if(fd==0)$fatal(1,"joint vectors unreadable");
  repeat(4)@(negedge clk);reset=0;@(posedge clk);#1;merge_tag=0;
  while(!$feof(fd))begin
   got=$fscanf(fd,"%d %d %d %d\n",full,n,shift,major);if(got!=4)$fatal(1,"joint header");
   if(full<1 || full>512 || n<1 || n>8 || shift<0 || shift>63 || major<0 || major>1)$fatal(1,"joint shape/shift admission");
   $display("JOINT_CASE_BEGIN cycle=%0d case=%0d K=%0d N=%0d major=%0d",cycle,cases,full,n,major);
   for(integer k=0;k<full;k=k+1)begin got=$fscanf(fd,"%h\n",av[k]);if(got!=1)$fatal(1,"joint A");end
   for(integer k=0;k<full*n;k=k+1)begin got=$fscanf(fd,"%h\n",bv[k]);if(got!=1)$fatal(1,"joint B");end
   got=$fscanf(fd,"%h\n",final_expected);if(got!=1)$fatal(1,"joint final");
   merge_kind=0;merge_key=128'(cases+123);merge_full=16'(full);merge_n=4'(n);merge_shift=6'(shift);
   merge_kk=0;merge_ai=0;merge_bi=0;merge_length=128;merge_raw=0;merge_packet(0,256'd0);
   for(offset=0;offset<full;offset=offset+128)begin
    length=full-offset>128 ? 128 : full-offset;booting=1;
    for(integer w=0;w<256;w=w+1)begin
     word_data=0;
     for(integer lane=0;lane<4;lane=lane+1)begin
      scalar_index=w*4+lane;
      index=major!=0 ? (scalar_index/8)*n+scalar_index%8 : (scalar_index%128)*n+scalar_index/128;
      if((major!=0 ? scalar_index/8 : scalar_index%128)<length &&
         (major!=0 ? scalar_index%8 : scalar_index/128)<n)
       word_data[lane*32+:32]=bv[offset*n+index];
     end
     store_word(10'(w),word_data);
    end
    for(integer w=0;w<32;w=w+1)begin
     word_data=0;for(integer lane=0;lane<4;lane=lane+1)
      if(w*4+lane<length)word_data[lane*32+:32]=av[offset+w*4+lane];
     store_word(10'(256+w),word_data);
    end
    booting=0;
    for(integer ai=0;ai<3;ai=ai+1)for(integer bi=0;bi<5;bi=bi+1)begin
     current_record=32'(cases*1000+offset/128*15+ai*5+bi+1);
     $display("JOINT_PARTIAL_BEGIN cycle=%0d record=%0d case=%0d kk=%0d ai=%0d bi=%0d",cycle,current_record,cases,offset,ai,bi);
     got=$fscanf(fd,"%h\n",partial_expected);if(got!=1)$fatal(1,"joint partial");
     bind_key=merge_key;bind_record_base=64'h100000+{21'd0,current_record,11'd0};
     bind_scalar_base=0;bind_k_stride=major!=0 ? 32'd8 : 32'd1;
     bind_n_stride=major!=0 ? 32'd1 : 32'd128;bind_length=8'(length);bind_n=4'(n);
     bind_digit=3'(bi);bind_k_major=major!=0;bind_valid=1;
     do @(posedge clk);while(!bind_ready);#1;bind_valid=0;
     if(!bind_ack_valid || bind_ack_error || bind_ack_key!=bind_key)$fatal(1,"joint source binding");
     scope_generation=scope_generation+1'b1;sid=sequence_number;sequence_number=sequence_number+1'b1;
     header(1,8,sid,0);words[1]=128'h00000001000002500000000100000101;words[2]=merge_key;
     words[3][31:0]=32'd128|(32'(n)<<16);words[7][31:0]=32'h53333251;words[7][63:32]=32'h4b313633;
     send(8);wait_event(sid,10);
     sid=sequence_number;sequence_number=sequence_number+1'b1;header(4,1,sid,0);send(1);wait_event(sid,4);
     alloc_sid=sequence_number;sequence_number=sequence_number+1'b1;header(2,2,alloc_sid,current_record);
     words[1][63:0]=bind_record_base;send(2);wait_event(alloc_sid,2);
     if(source_returned!=17 || !release_ready)$fatal(1,"EXEC before true17 local returns/FILL");
     release_valid=1;@(posedge clk);#1;release_valid=0;
     if(source_active || !source_quiescent || cancel_ready)$fatal(1,"joint source not released");
     exec_sid=sequence_number;sequence_number=sequence_number+1'b1;header(3,2,exec_sid,current_record);
     words[1][1:0]=observed_bank;words[1][17:2]=observed_generation;
     words[1][33:18]=16'(current_record+17);words[1][66]=current_record[0];
     words[1][82:67]=16'(current_record+3);words[1][88:83]=0;words[1][120:89]=exec_sid;
     send(2);a_session=exec_sid;ap_digit=3'(ai);
     for(integer beat=0;beat<8;beat=beat+1)begin
      a_beat=3'(beat);valid_k=length-beat*16;
      if(valid_k<=0)begin zero_a=1;zero_valid=1;do @(posedge clk);while(!a_ready);#1;zero_valid=0;zero_a=0;end
      else begin
       ap_base=32'(1024+beat*16);ap_k=5'(valid_k>16 ? 16 : valid_k);ap_cmd=1;
       do @(posedge clk);while(!ap_ready);#1;ap_cmd=0;
       do @(posedge clk);while(!(ap_valid && a_ready));#1;
      end
     end
     wait_event(exec_sid,3);wait_event(exec_sid,4);
     if(observed_raw!==partial_expected)$fatal(1,"real product raw differs from independent partial");
     merge_kind=1;merge_kk=16'(offset);merge_length=8'(length);merge_ai=2'(ai);merge_bi=3'(bi);merge_raw=observed_raw;
     merge_packet(offset+length==full && ai==2 && bi==4,
       offset+length==full && ai==2 && bi==4 ? final_expected : 256'd0);
     $display("JOINT_PARTIAL_DONE cycle=%0d record=%0d",cycle,current_record);
    end
   end
   $display("JOINT_CASE_DONE cycle=%0d case=%0d",cycle,cases);cases=cases+1;
  end
  if(mc_requests!=mc_returns || s_reads!=s_acks || partial_count*17!=mc_returns || partial_count*8!=a_beats ||
     result_writes!=cases*2 || result_reads!=cases*2)
   $fatal(1,"joint traffic/ownership conservation");
  $display("PASS dynamic_product cases=%0d partials=%0d LOCAL64returns=%0d S128reads=%0d ACKs=%0d Abeats=%0d LC128flits=%0d LR128flits=%0d stagedS128writes=%0d finalS128writeACKs=%0d validationReadbacks=%0d DDRbytes=0 cycles=%0d",
   cases,partial_count,mc_returns,s_reads,s_acks,a_beats,lc_words,lr_words,boot_writes,result_writes,result_reads,cycle);$finish;
 end
 initial begin #1000000000;$fatal(1,"joint watchdog");end
endmodule
