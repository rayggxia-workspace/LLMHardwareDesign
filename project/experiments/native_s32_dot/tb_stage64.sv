`timescale 1ns/1ps
module tb_stage64;
 reg clk;initial begin clk=0;forever #5 clk=~clk;end
 reg reset,cmd_valid,cancel_valid,reject_valid,raw_valid,done_ready;
 wire cmd_ready,cmd_admit,cancel_ready,reject_ready,raw_ready,unexpected_return,done_valid,done_cancelled,done_error;
 reg [31:0] cmd_tag,cancel_tag,reject_tag,raw_tag;wire [31:0] done_tag;
 reg [9:0] cmd_dst;reg [1:0] cmd_first;reg [2:0] cmd_words;
 reg [511:0] raw_data;
 wire [3:0] done_written_mask;
 wire s_req_valid,s_req_ready,s_rsp_valid,s_rsp_ready,s_rsp_error;
 wire [9:0] s_req_address;
 wire [127:0] s_req_wdata;
 dot_s32_stage64 dut(.*);

 reg check_read,read_valid,request_allowed,response_allowed,block_request,inject_error;
 reg [9:0] read_address;
 wire real_req_ready,real_rsp_valid;
 wire [127:0] real_rsp_data;
 assign s_req_ready=real_req_ready&&request_allowed&&!block_request&&!check_read;
 assign s_rsp_valid=real_rsp_valid&&response_allowed&&!check_read;
 assign s_rsp_error=inject_error&&s_rsp_valid;
 local_s_base storage(.clk(clk),.reset(reset),
   .req_valid(check_read?read_valid:s_req_valid&&request_allowed&&!block_request),
   .req_write(!check_read),.req_addr(check_read?read_address:s_req_address),
   .req_data(s_req_wdata),.req_ready(real_req_ready),.rsp_valid(real_rsp_valid),
   .rsp_ready(check_read||s_rsp_ready&&response_allowed),.rsp_data(real_rsp_data));

 integer mode,trace,cycle,requests,acks,returns,done_count,reads,held,peak,pending;
 integer frame_req,frame_ack,latency,start_cycle,raws2,raws4,min2,min4,max2,max4;
 reg [127:0] expected[0:1023];
 reg held_req,held_raw,held_done;
 reg [137:0] last_req;
 reg [543:0] last_raw;
 reg [37:0] last_done;
 always @(negedge clk)begin
  request_allowed=mode==0||$urandom_range(0,3)!=0;
  response_allowed=mode==0||$urandom_range(0,4)!=0;
 end
 always @(posedge clk)begin
  cycle=cycle+1;
  if(reset)begin
   held_req=0;held_raw=0;held_done=0;pending=0;
  end else begin
   if(held_req&&(!s_req_valid||{s_req_address,s_req_wdata}!==last_req))$fatal(1,"S offer changed under hold");
   if(held_raw&&(!raw_valid||{raw_tag,raw_data}!==last_raw))$fatal(1,"raw fixture withdrew a held offer");
   if(held_done&&(!done_valid||{done_tag,done_error,done_cancelled,done_written_mask}!==last_done))
    $fatal(1,"terminal changed under hold");
   held_req=s_req_valid&&!s_req_ready;
   last_req={s_req_address,s_req_wdata};
   held_raw=raw_valid&&!raw_ready;last_raw={raw_tag,raw_data};
   held_done=done_valid&&!done_ready;last_done={done_tag,done_error,done_cancelled,done_written_mask};
   if(held_req)held=held+1;
   if(cmd_valid&&cmd_ready)$fdisplay(trace,"%0d,CMD,%0d,%0d,%0d,%0d,%0d",cycle,cmd_tag,cmd_dst,cmd_first,cmd_words,cmd_admit);
   if(cancel_valid&&cancel_ready)$fdisplay(trace,"%0d,CANCEL,%0d",cycle,cancel_tag);
   if(reject_valid&&reject_ready)$fdisplay(trace,"%0d,REJECT,%0d",cycle,reject_tag);
   if(s_rsp_valid&&s_rsp_ready)begin
    if(pending<1)$fatal(1,"orphan write ACK");
    $fdisplay(trace,"%0d,SACK,%0d,%0d",cycle,raw_tag,s_rsp_error);
    pending=pending-1;acks=acks+1;frame_ack=frame_ack+1;
   end
   if(s_req_valid&&s_req_ready)begin
    if(!raw_valid||pending>=2||s_req_wdata!==expected[s_req_address])$fatal(1,"request invalid address=%0d",s_req_address);
    $fdisplay(trace,"%0d,SREQ,%0d,%0d",cycle,raw_tag,s_req_address);
    pending=pending+1;requests=requests+1;frame_req=frame_req+1;
    if(pending>peak)peak=pending;
   end
   if(raw_valid&&raw_ready)begin
    if(frame_req!=frame_ack||pending!=0)$fatal(1,"MC slot released before true S ACK");
    returns=returns+1;
    $fdisplay(trace,"%0d,RAW_ACK,%0d,%0d",cycle,raw_tag,frame_ack);
   end
   if(done_valid&&done_ready)begin
    done_count=done_count+1;
    $fdisplay(trace,"%0d,DONE,%0d,%0d,%0d,%0d",cycle,done_tag,done_cancelled,done_error,done_written_mask);
   end
  end
 end

 task automatic command(input [31:0] id,input [9:0] dst,input [1:0] first_word,input [2:0] words,input bit ok);
  cmd_tag=id;cmd_dst=dst;cmd_first=first_word;cmd_words=words;cmd_valid=1;
  do @(posedge clk);while(!cmd_ready);
  if(cmd_admit!==ok)$fatal(1,"command admission mismatch tag=%0d",id);
  #1;cmd_valid=0;
 endtask
 task automatic cancel(input [31:0] id);
  cancel_tag=id;cancel_valid=1;
  @(posedge clk);if(!cancel_ready)$fatal(1,"lost valid cancel");
  #1;cancel_valid=0;
 endtask
 task automatic receive_raw(input [31:0] id,input [9:0] dst,input [1:0] first_word,input [2:0] words,input integer normal);
  frame_req=0;frame_ack=0;
  for(integer i=0;i<4;i=i+1)raw_data[i*128+:128]={$urandom,$urandom,$urandom,$urandom};
  for(integer i=0;i<int'(words);i=i+1)expected[int'(dst)+i]=raw_data[(int'(first_word)+i)*128+:128];
  raw_tag=id;raw_valid=1;start_cycle=cycle+1;
  $fdisplay(trace,"%0d,RAW_FIRST,%0d,%0d",start_cycle,id,words);
  do @(posedge clk);while(!raw_ready);
  #1;raw_valid=0;latency=cycle-start_cycle;
  if(normal!=0)begin
   if(frame_req!=int'(words)||frame_ack!=int'(words))$fatal(1,"wrong raw word count");
   if(words==2)begin
    raws2=raws2+1;if(latency<min2)min2=latency;if(latency>max2)max2=latency;
   end
   if(words==4)begin
    raws4=raws4+1;if(latency<min4)min4=latency;if(latency>max4)max4=latency;
   end
  end
 endtask
 task automatic terminal(input [31:0] id,input bit cancelled,input bit error,input [3:0] mask);
  done_ready=1;
  do @(posedge clk);while(!done_valid);
  if({done_tag,done_cancelled,done_error,done_written_mask}!=={id,cancelled,error,mask})
   $fatal(1,"terminal id=%0d expected=%0d cancel/error/mask=%0d/%0d/%h",done_tag,id,done_cancelled,done_error,done_written_mask);
  #1;done_ready=0;
 endtask
 task automatic readback(input [9:0] address);
  check_read=1;read_valid=1;read_address=address;
  do @(posedge clk);while(!real_req_ready);
  #1;read_valid=0;
  do @(posedge clk);while(!real_rsp_valid);
  if(real_rsp_data!==expected[address])$fatal(1,"real SRAM readback mismatch address=%0d",address);
  #1;check_read=0;reads=reads+1;
 endtask

 string trace_path;
 initial begin
  mode=0;if(!$value$plusargs("mode=%d",mode)||!$value$plusargs("trace=%s",trace_path))$fatal(1,"missing inputs");
  trace=$fopen(trace_path,"w");if(trace==0)$fatal(1,"trace open");
  reset=1;cmd_valid=0;cancel_valid=0;reject_valid=0;raw_valid=0;done_ready=0;
  cmd_tag=0;cancel_tag=0;reject_tag=0;raw_tag=0;cmd_dst=0;cmd_first=0;cmd_words=0;raw_data=0;
  check_read=0;read_valid=0;block_request=0;inject_error=0;read_address=0;
  cycle=0;requests=0;acks=0;returns=0;done_count=0;reads=0;held=0;peak=0;pending=0;
  raws2=0;raws4=0;min2=1000;min4=1000;max2=0;max4=0;
  repeat(4) @(posedge clk);#1;reset=0;
  for(integer j=0;j<48;j=j+1)begin
   command(32'(4*j+2),10'(j*8),0,4,1);
   if(cmd_ready)$fatal(1,"duplicate tag was offered");
   command(32'(4*j+4),10'(j*8+4),j[0] ? 2'd2 : 2'd0,2,1);
   cmd_tag=32'hace02468;#1;
   if(cmd_ready)$fatal(1,"third owner was offered");
   receive_raw(32'(4*j+4),10'(j*8+4),j[0] ? 2'd2 : 2'd0,2,1);
   receive_raw(32'(4*j+2),10'(j*8),0,4,1);
   terminal(32'(4*j+4),0,0,3);terminal(32'(4*j+2),0,0,15);
   for(integer w=0;w<6;w=w+1)readback(10'(j*8+w));
  end
  command(32'd800,10'd520,0,0,0);terminal(32'd800,0,1,0);
  command(32'd802,10'd520,3,2,0);terminal(32'd802,0,1,0);
  command(32'd804,10'd1023,0,2,0);terminal(32'd804,0,1,0);
  command(32'd806,10'd520,0,4,1);
  command(32'd808,10'd522,0,2,0);terminal(32'd808,0,1,0);
  cancel(32'd806);receive_raw(32'd806,10'd520,0,4,0);terminal(32'd806,1,0,0);
  command(32'd810,10'd530,0,4,1);block_request=1;
  fork
   receive_raw(32'd810,10'd530,0,4,0);
   begin
    wait(s_req_valid);repeat(2) @(negedge clk);#1;cancel(32'd810);
    repeat(3) @(negedge clk);#1;block_request=0;
   end
  join
  terminal(32'd810,1,0,1);readback(10'd530);
  command(32'd812,10'd540,0,4,1);inject_error=1;
  receive_raw(32'd812,10'd540,0,4,0);
  if(frame_req<1||frame_req>3)$fatal(1,"error drain sent an unbounded number of writes");
  terminal(32'd812,0,1,0);inject_error=0;
  for(integer i=0;i<frame_req;i=i+1)readback(10'd540+10'(i));
  command(32'd816,10'd550,0,4,1);
  reject_tag=32'd814;reject_valid=1;
  @(posedge clk);if(reject_ready)$fatal(1,"foreign fabric reject consumed");
  #1;reject_tag=32'd816;
  @(posedge clk);if(!reject_ready)$fatal(1,"real fabric reject did not drain local command");
  #1;reject_valid=0;
  terminal(32'd816,0,1,0);
  @(negedge clk);#1;raw_valid=1;raw_tag=32'd814;#1;
  if(!unexpected_return||raw_ready||s_req_valid)$fatal(1,"foreign return was claimed");
  // Clear this protocol-negative offer without a sampling edge: a real
  // fabric must hold/diagnose it upstream instead of dropping it.
  raw_valid=0;
  if(requests!=acks||pending!=0||peak!=2||raws2!=48||raws4!=48||returns!=99||done_count!=104||held==0)
   $fatal(1,"fixture coverage/ownership incomplete");
  $fclose(trace);
  $display("PASS dot S128 stage64 mode=%0d req=%0d ack=%0d raw=%0d done=%0d readback=%0d peak=%0d held=%0d two=%0d:%0d four=%0d:%0d cycles=%0d",
    mode,requests,acks,returns,done_count,reads,peak,held,min2,max2,min4,max4,cycle);
  $finish;
 end
 initial begin #1000000;$fatal(1,"stage64 watchdog");end
endmodule
