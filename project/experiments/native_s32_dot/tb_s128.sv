`timescale 1ns/1ps
module tb_s128 #(parameter integer ROWS=1);
 reg clk;initial begin clk=0;forever #5 clk=~clk;end
 reg reset=1;
 reg cmd_valid=0;wire cmd_ready;reg [1:0] cmd_kind;reg [127:0] cmd_key;reg [31:0] cmd_tag;
 reg [15:0] cmd_full_k,cmd_k_offset;reg [7:0] cmd_chunk_k;reg [3:0] cmd_n;
 reg [2:0] cmd_rows;reg [5:0] cmd_shift;reg cmd_layout;
 reg [9:0] cmd_a_base,cmd_b_base,cmd_result_base;reg cmd_sources_committed;
 reg abort_valid;reg [127:0] abort_key;wire abort_ready;
 wire rsp_valid;reg rsp_ready;wire [1:0] rsp_kind;wire [127:0] rsp_key;wire [31:0] rsp_tag;
 wire rsp_error,rsp_aborted,rsp_done;wire [ROWS*2-1:0] rsp_written_mask;
 wire s_req_valid,s_req_ready,s_req_write;wire [9:0] s_req_address;wire [127:0] s_req_wdata;
 wire s_rsp_valid,s_rsp_ready,s_rsp_error;wire [127:0] s_rsp_data;
 dot_s32_s128 #(.ROWS(ROWS)) dut(.*);
 reg [127:0] memory[0:1023];
 reg [127:0] response_data[0:1];reg response_error[0:1],response_write[0:1];
 reg [9:0] response_address[0:1];
 integer read_pointer,write_pointer,count,cycle,requests,acks,write_acks,peak,held,aborts,mode;
 integer command_requests,current_abort_mode,forced_hold;reg injected,command_live;
 reg [ROWS*2-1:0] written;
 reg [ROWS*256-1:0] golden;
 reg [9:0] current_result_base;reg [2:0] current_rows;
 reg prior_held;reg [138:0] prior_offer;
 reg prior_response_held;reg [164+ROWS*2:0] prior_response;
 wire [138:0] offer={s_req_write,s_req_address,s_req_wdata};
 wire [164+ROWS*2:0] terminal={rsp_kind,rsp_key,rsp_tag,rsp_error,rsp_aborted,rsp_done,rsp_written_mask};
 integer trace_fd;
 reg req_enable,rsp_enable,rsp_error_offer;
 reg boot_busy,boot_valid,boot_write;reg [9:0] boot_address;reg [127:0] boot_data;
 wire real_req_ready,real_rsp_valid;wire [127:0] real_rsp_data;
 assign s_req_ready=real_req_ready&&req_enable&&!boot_busy;
 assign s_rsp_valid=real_rsp_valid&&rsp_enable&&!boot_busy;
 assign s_rsp_data=real_rsp_data;
 assign s_rsp_error=rsp_error_offer;
 local_s_base storage(.clk(clk),.reset(reset),
   .req_valid(boot_valid||(!boot_busy&&s_req_valid&&req_enable)),.req_write(boot_busy?boot_write:s_req_write),
   .req_addr(boot_busy?boot_address:s_req_address),.req_data(boot_busy?boot_data:s_req_wdata),
   .req_ready(real_req_ready),.rsp_valid(real_rsp_valid),
   .rsp_ready(boot_busy||(!boot_busy&&s_rsp_ready&&rsp_enable)),.rsp_data(real_rsp_data));
 integer boot_writes,readback_words,reset_flushed,stale_abort;
 initial begin
  read_pointer=0;write_pointer=0;count=0;cycle=0;requests=0;acks=0;write_acks=0;peak=0;held=0;aborts=0;
  command_requests=0;current_abort_mode=0;forced_hold=0;injected=0;command_live=0;written=0;golden=0;
  current_result_base=0;current_rows=0;prior_held=0;prior_offer=0;prior_response_held=0;prior_response=0;abort_valid=0;
  boot_busy=0;boot_valid=0;boot_write=0;boot_address=0;boot_data=0;boot_writes=0;readback_words=0;reset_flushed=0;stale_abort=0;
  for(integer i=0;i<1024;i=i+1)memory[i]={4{32'h12345678}};
 end
 always @(negedge clk)begin
  rsp_ready=!reset&&(mode==0||$urandom_range(0,3)!=0);
  rsp_error_offer=count!=0&&response_error[read_pointer];
  req_enable=!reset&&(mode==0||$urandom_range(0,3)!=0);
  rsp_enable=!reset&&(mode==0||$urandom_range(0,3)!=0);
  abort_valid=0;
  if(command_live&&!injected&&current_abort_mode==1&&command_requests>=10)abort_valid=1;
  if(command_live&&current_abort_mode==4&&command_requests>=10)abort_valid=1;
  if(command_live&&!injected&&current_abort_mode==2&&s_req_valid&&s_req_write)begin
   abort_valid=1;req_enable=0;forced_hold=3;
  end
  if(forced_hold>0)begin req_enable=0;forced_hold=forced_hold-1;end
 end
 always @(posedge clk)begin
  cycle=cycle+1;
  if(reset)begin count=0;read_pointer=0;write_pointer=0;prior_held=0;prior_response_held=0;end
  else begin
   if(prior_held&&(!s_req_valid||offer!==prior_offer))$fatal(1,"S offer changed before acceptance");
   if(prior_response_held&&(!rsp_valid||terminal!==prior_response))$fatal(1,"terminal changed before take");
   prior_held=s_req_valid&&!s_req_ready;prior_offer=offer;if(prior_held)held=held+1;
   prior_response_held=rsp_valid&&!rsp_ready;prior_response=terminal;
   if(abort_valid&&abort_ready)begin injected=1;aborts=aborts+1;end
   if(abort_valid&&current_abort_mode==4)begin
    if(abort_ready)$fatal(1,"stale abort acquired active owner");stale_abort=stale_abort+1;
   end
   if(s_rsp_valid&&s_rsp_ready)begin
    if(count==0)$fatal(1,"orphan S ACK");
    if(!response_write[read_pointer]&&s_rsp_data!==response_data[read_pointer])$fatal(1,"S read response differs from independently staged word");
    if(response_write[read_pointer]&&!response_error[read_pointer])begin
     memory[response_address[read_pointer]]=response_data[read_pointer];
     written[$clog2(ROWS*2)'(response_address[read_pointer]-current_result_base)]=1;write_acks=write_acks+1;
    end
    $fdisplay(trace_fd,"%0d,SACK,%0d,%0d,%0d,%0d",cycle,response_write[read_pointer],response_address[read_pointer],count,command_requests);
    acks=acks+1;read_pointer=1-read_pointer;count=count-1;
   end
   if(s_req_valid&&s_req_ready)begin
    if(!command_live||count>=2)$fatal(1,"S request owner overflow/no live command");
    if(s_req_write)begin
     if(s_req_address<current_result_base||int'(s_req_address)>=int'(current_result_base)+int'(current_rows)*2)$fatal(1,"result write escaped window");
     if(s_req_wdata!==golden[(s_req_address-current_result_base)*128+:128])$fatal(1,"exact S write mismatch address=%0d got=%032h expected=%032h",s_req_address,s_req_wdata,golden[(s_req_address-current_result_base)*128+:128]);
    end
    response_data[write_pointer]=s_req_write?s_req_wdata:memory[s_req_address];
    response_error[write_pointer]=current_abort_mode==3&&!injected&&command_requests==10;
    if(response_error[write_pointer])injected=1;
    response_address[write_pointer]=s_req_address;response_write[write_pointer]=s_req_write;
    $fdisplay(trace_fd,"%0d,SREQ,%0d,%0d,%0d,%0d",cycle,s_req_write,s_req_address,count,command_requests);
    write_pointer=1-write_pointer;count=count+1;requests=requests+1;command_requests=command_requests+1;
    if(count>peak)peak=count;
   end
   if(dut.c_in_fire)$fdisplay(trace_fd,"%0d,CORE_IN,%0d,%0d,%0d,%0d",cycle,dut.c_in_kind,dut.c_in_k,dut.c_in_group,dut.core_pending);
   if(dut.c_out_fire)$fdisplay(trace_fd,"%0d,CORE_OUT,%0d,%0d,%0d,%0d",cycle,dut.c_out_kind,dut.c_out_done,dut.c_out_error,dut.core_pending);
  end
 end
 task automatic fixture(input bit write_word,input [9:0] address,input [127:0] data);
  begin
   if(count!=0||s_req_valid||boot_busy)$fatal(1,"fixture touched S before drain");
   boot_busy=1;boot_valid=1;boot_write=write_word;boot_address=address;boot_data=data;
   do @(posedge clk);while(!real_req_ready);#1;boot_valid=0;
   do @(posedge clk);while(!real_rsp_valid);
   if(!write_word&&real_rsp_data!==data)$fatal(1,"true SRAM result readback mismatch at %0d",address);
   #1;boot_busy=0;
   if(write_word)begin memory[address]=data;boot_writes=boot_writes+1;end
   else begin if(memory[address]!==data)$fatal(1,"mirrored result readback mismatch");readback_words=readback_words+1;end
  end
 endtask
 string path,trace_path;integer fd,got,action,command_count,begin_cycle;
 reg [127:0] key;reg [31:0] tag,full,offset,chunk,n,rows,shift,layout,abase,bbase,resultbase,committed,error,aborted,done,abort_mode;
 reg [ROWS*256-1:0] result;
 initial begin
  if(!$value$plusargs("vectors=%s",path)||!$value$plusargs("trace=%s",trace_path)||!$value$plusargs("mode=%d",mode))$fatal(1,"arguments missing");
  fd=$fopen(path,"r");trace_fd=$fopen(trace_path,"w");if(fd==0||trace_fd==0)$fatal(1,"files unreadable");
  command_count=0;
  repeat(4)@(negedge clk);reset=0;@(posedge clk);#1;
  while(!$feof(fd))begin
   got=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h\n",
    action,key,tag,full,offset,chunk,n,rows,shift,layout,abase,bbase,resultbase,committed,error,aborted,done,abort_mode,result);
   if(got!=19)$fatal(1,"service vector format");
   if(full>65535||offset>65535||chunk>255||n>15||rows>7||shift>63||layout>1||abase>1023||bbase>1023||resultbase>1023||committed>1||error>1||aborted>1||done>1||abort_mode>4)$fatal(1,"vector width");
   if(action==3)begin
    if(count!=0||s_req_valid)$fatal(1,"fixture wrote before S drain");fixture(1,abase[9:0],result[127:0]);
   end else begin
    golden=result;current_result_base=resultbase[9:0];current_rows=rows[2:0];
    command_requests=0;current_abort_mode=int'(abort_mode);injected=0;written=0;command_live=1;
    cmd_kind=action==4?2'd1:2'(action);cmd_key=key;cmd_tag=tag;cmd_full_k=full[15:0];cmd_k_offset=offset[15:0];
    cmd_chunk_k=chunk[7:0];cmd_n=n[3:0];cmd_rows=rows[2:0];cmd_shift=shift[5:0];cmd_layout=layout[0];
    cmd_a_base=abase[9:0];cmd_b_base=bbase[9:0];cmd_result_base=resultbase[9:0];cmd_sources_committed=committed[0];
    abort_key=abort_mode==4?key^128'd1:key;cmd_valid=1;do @(posedge clk);while(!cmd_ready);#1;begin_cycle=cycle;cmd_valid=0;
    $fdisplay(trace_fd,"%0d,CMD,%0d,%0d,%0d,%0d",begin_cycle,action,offset,chunk,tag);
    if(action==4)begin
     do @(negedge clk);while(command_requests<10||count==0||dut.core_pending==0);
     $fdisplay(trace_fd,"%0d,RESET,%0d,%0d,%0d,%0d",cycle,count,command_requests,dut.core_pending,tag);
     reset_flushed=reset_flushed+count;reset=1;command_live=0;
     repeat(3)@(posedge clk);#1;reset=0;
     repeat(4)@(posedge clk);#1;
     if(s_req_valid||s_rsp_valid||rsp_valid||count!=0)$fatal(1,"stale post-reset request/response");
    end else begin
    do @(posedge clk);while(!(rsp_valid&&rsp_ready));
    if(rsp_kind!==2'(action)||rsp_key!==key||rsp_tag!==tag||rsp_error!==error[0]||rsp_aborted!==aborted[0]||rsp_done!==done[0])
     $fatal(1,"terminal mismatch kind=%0d tag=%0d error=%0d aborted=%0d done=%0d expected %0d/%0d/%0d",rsp_kind,rsp_tag,rsp_error,rsp_aborted,rsp_done,error,aborted,done);
    if(rsp_written_mask!==written||count!=0||s_req_valid)$fatal(1,"terminal before true S ACK/mask");
    if((error!=0||action!=1)&&aborted==0&&command_requests!=0)$fatal(1,"invalid/control descriptor touched S");
    if(done!=0&&aborted==0&&error==0&&rsp_written_mask!==((ROWS*2)'(1)<<(int'(current_rows)*2))-1'b1)$fatal(1,"missing final write ACK");
    $fdisplay(trace_fd,"%0d,RSP,%0d,%0d,%0d,%0d",cycle,action,cycle-begin_cycle,command_requests,written);
    command_count=command_count+1;#1;command_live=0;
    for(integer word_index=0;word_index<ROWS*2;word_index=word_index+1)
     if(written[word_index])fixture(0,current_result_base+10'(word_index),golden[word_index*128+:128]);
    end
   end
  end
  if(requests!=acks+reset_flushed||reset_flushed==0||stale_abort==0||peak!=2||aborts!=4||write_acks!=readback_words)$fatal(1,"service conservation/abort/reset/two-owner coverage");
  if(mode!=0&&held==0)$fatal(1,"held S request not exercised");
  $display("PASS native32 S128 rows=%0d lanes=%0d mode=%0d commands=%0d req=%0d ack=%0d write_ack=%0d peak=%0d held=%0d aborts=%0d cycles=%0d real=1 boot=%0d readback=%0d flush=%0d stale_abort=%0d",
   ROWS,ROWS*4,mode,command_count,requests,acks,write_acks,peak,held,aborts,cycle,boot_writes,readback_words,reset_flushed,stale_abort);$fclose(trace_fd);$finish;
 end
 initial begin #1000000000;$fatal(1,"S128 watchdog");end
endmodule
