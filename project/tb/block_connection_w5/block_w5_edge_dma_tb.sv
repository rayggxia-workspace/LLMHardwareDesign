`timescale 1ns/1ps
module block_w5_edge_dma_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,cmd_valid=0,cmd_write=0,in_valid=0,in_last=0;
 reg out_ready=0,done_ready=0;
 reg [9:0] cmd_base=0,cmd_words=0,in_index=0;
 reg [127:0] in_data=0;
 wire cmd_ready,in_ready,out_valid,out_last,done_valid,done_error,busy;
 wire [127:0] out_data;
 wire [9:0] out_index,done_words;
 block_w5_edge_dma dut(.clk(clk),.reset(reset),.abort(abort),
  .cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_write(cmd_write),.cmd_base(cmd_base),.cmd_words(cmd_words),
  .in_valid(in_valid),.in_ready(in_ready),.in_data(in_data),.in_index(in_index),.in_last(in_last),
  .out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),.out_index(out_index),.out_last(out_last),
  .done_valid(done_valid),.done_ready(done_ready),.done_error(done_error),.done_words(done_words),.busy(busy));

 // Independent testbench memory model: updated from real native transactions.
 // The DUT contains no such payload array and no hierarchical RAM is assigned.
 reg [127:0] expected[0:1023];reg expected_valid[0:1023];
 reg native_pending=0,pending_write=0;
 reg [9:0] pending_addr=0;
 reg [127:0] pending_data=0;
 reg out_stalled=0,s_stalled=0,done_stalled=0;
 reg [127:0] out_saved=0,s_saved=0;
 reg [9:0] out_index_saved=0,done_words_saved=0;
 reg out_last_saved=0,done_error_saved=0;
 integer cycles=0,cases=0,commands=0,s_requests=0,s_acks=0;
 integer s_wreqs=0,s_wacks=0,s_rreqs=0,s_racks=0;
 integer input_takes=0,output_takes=0,done_takes=0;
 integer job_wacks=0,job_racks=0,job_in=0,job_out=0,job_base=0,job_count=0;
 reg job_write=0;
 integer j;
 always @(posedge clk) begin
  cycles=cycles+1;
  if(cycles>250000)$fatal(1,"FAIL_W5_EDGE_DMA watchdog");
  if(reset) begin
   native_pending=0;out_stalled=0;s_stalled=0;done_stalled=0;
   job_wacks=0;job_racks=0;job_in=0;job_out=0;
   for(j=0;j<1024;j=j+1)expected_valid[j]=0;
  end else begin
   if(cmd_valid&&cmd_ready)begin
    commands=commands+1;job_wacks=0;job_racks=0;job_in=0;job_out=0;
    job_base=cmd_base;job_count=cmd_words;job_write=cmd_write;
   end
   if(dut.leaf_reset)begin native_pending=0;out_stalled=0;s_stalled=0;end
   else begin
    if(s_stalled&&(!dut.s_valid||dut.s_dout!==s_saved))
     $fatal(1,"FAIL_W5_EDGE_DMA native response changed while stalled");
    s_stalled=dut.s_valid&&!dut.s_take;s_saved=dut.s_dout;
    if(dut.s_req&&dut.s_ready)begin
     if(native_pending)$fatal(1,"FAIL_W5_EDGE_DMA more than one native request");
     native_pending=1;pending_write=dut.s_we;pending_addr=dut.s_addr;pending_data=dut.s_din;
     s_requests=s_requests+1;
     if(dut.s_we)begin s_wreqs=s_wreqs+1;expected_valid[dut.s_addr]=0;end
     else s_rreqs=s_rreqs+1;
    end
    if(dut.s_valid&&dut.s_take)begin
     if(!native_pending)$fatal(1,"FAIL_W5_EDGE_DMA ACK without request");
     native_pending=0;s_acks=s_acks+1;
     if(pending_write)begin
      if(dut.s_dout!==pending_data)$fatal(1,"FAIL_W5_EDGE_DMA native write ACK payload");
      expected[pending_addr]=pending_data;expected_valid[pending_addr]=1;
      s_wacks=s_wacks+1;job_wacks=job_wacks+1;
     end else begin
      if(!expected_valid[pending_addr]||dut.s_dout!==expected[pending_addr])
       $fatal(1,"FAIL_W5_EDGE_DMA native real read data");
      s_racks=s_racks+1;job_racks=job_racks+1;
     end
    end
    if(in_ready&&job_wacks<=job_in)$fatal(1,"FAIL_W5_EDGE_DMA ready before actual S ACK");
    if(in_valid&&in_ready)begin
     if(!job_write||in_index!==10'(job_in)||in_last!==(job_in==job_count-1))
      $fatal(1,"FAIL_W5_EDGE_DMA source retirement order");
     if(in_data!==expected[job_base+job_in])$fatal(1,"FAIL_W5_EDGE_DMA source retired different stored data");
     input_takes=input_takes+1;job_in=job_in+1;
    end
    if(out_stalled&&(!out_valid||out_data!==out_saved||out_index!==out_index_saved||out_last!==out_last_saved))
     $fatal(1,"FAIL_W5_EDGE_DMA public output changed while stalled");
    out_stalled=out_valid&&!out_ready;out_saved=out_data;out_index_saved=out_index;out_last_saved=out_last;
    if(out_valid&&out_ready)begin
     if(job_write||out_index!==10'(job_out)||out_last!==(job_out==job_count-1)||job_racks<=job_out)
      $fatal(1,"FAIL_W5_EDGE_DMA output index/last/native ACK order");
     if(!expected_valid[job_base+job_out]||out_data!==expected[job_base+job_out])
      $fatal(1,"FAIL_W5_EDGE_DMA output actual memory value");
     output_takes=output_takes+1;job_out=job_out+1;
    end
   end
   // Public DONE is deliberately counted even when abort resets the leaves.
   if(done_stalled&&(!done_valid||done_error!==done_error_saved||done_words!==done_words_saved))
    $fatal(1,"FAIL_W5_EDGE_DMA completion changed while held");
   done_stalled=done_valid&&!done_ready;done_error_saved=done_error;done_words_saved=done_words;
   if(done_valid&&done_ready)done_takes=done_takes+1;
  end
 end

 function automatic [127:0] pattern(input integer seed,input integer index);
  reg [31:0] a,b,c,d;
  begin
   a=32'h91e10da5^(32'(seed)*32'h01010203)^32'(index);
   b=32'h7f00cafe+32'(index)*32'h10203041+32'(seed);
   c=~a^(32'(index)*32'hfedc0011);d=b^32'ha5a55a5a^32'(seed<<7);
   pattern={d,c,b,a};
  end
 endfunction
 task automatic check(input bit ok,input string why);
  if(!ok)$fatal(1,"FAIL_W5_EDGE_DMA %s cycle=%0d",why,cycles);
 endtask
 task automatic passcase(input string name);
  begin cases=cases+1;$display("CASE_PASS %s",name);end
 endtask
 task automatic hard_reset;
  begin
   @(negedge clk);reset=1;abort=0;cmd_valid=0;in_valid=0;out_ready=0;done_ready=0;
   repeat(3)@(posedge clk);
   @(negedge clk);reset=0;
   @(posedge clk);#1;
   check(cmd_ready&&!busy&&!done_valid,"hard reset idle");
  end
 endtask
 task automatic command(input bit wr,input integer base,input integer count);
  integer guard;
  begin
   @(negedge clk);cmd_valid=1;cmd_write=wr;cmd_base=10'(base);cmd_words=10'(count);
   guard=0;
   begin: cmd_wait
    forever begin
     @(posedge clk);guard=guard+1;
     if(cmd_ready)begin #1;disable cmd_wait;end
     if(guard>10000)$fatal(1,"FAIL_W5_EDGE_DMA command timeout");
    end
   end
   @(negedge clk);cmd_valid=0;
  end
 endtask
 task automatic offer(input integer index,input bit last,input [127:0] data);
  begin @(negedge clk);in_valid=1;in_index=10'(index);in_last=last;in_data=data;end
 endtask
 task automatic retire_offer;
  integer guard;
  begin
   guard=0;
   begin: offer_wait
    forever begin
     @(posedge clk);guard=guard+1;
     if(in_valid&&in_ready)begin #1;disable offer_wait;end
     if(done_valid)$fatal(1,"FAIL_W5_EDGE_DMA premature DONE during valid source");
     if(guard>10000)$fatal(1,"FAIL_W5_EDGE_DMA source retirement timeout");
    end
   end
   @(negedge clk);in_valid=0;
  end
 endtask
 task automatic send(input integer index,input integer count,input integer seed);
  begin offer(index,index==count-1,pattern(seed,index));retire_offer();end
 endtask
 task automatic await_done(input bit error,input integer words);
  integer guard;
  begin
   guard=0;
   while(!done_valid)begin @(posedge clk);#1;guard=guard+1;check(guard<10000,"DONE timeout");end
   check(done_error===error&&done_words===10'(words),"DONE error/word prefix");
  end
 endtask
 task automatic take_done(input bit with_abort);
  integer before_done;
  begin
   check(done_valid,"take existing DONE");before_done=done_takes;
   @(negedge clk);done_ready=1;abort=with_abort;
   @(posedge clk);#1;
   check(done_takes==before_done+1&&!done_valid,"DONE exactly once incl abort");
   @(negedge clk);done_ready=0;abort=0;in_valid=0;out_ready=0;
   @(posedge clk);#1;check(cmd_ready&&!busy,"return IDLE after DONE");
  end
 endtask
 task automatic drain(input integer count,input integer stall_seed);
  integer k,n,guard;
  begin
   for(k=0;k<count;k=k+1)begin
    @(negedge clk);out_ready=0;
    n=(k*3+stall_seed)%4;repeat(n)@(posedge clk);
    @(negedge clk);out_ready=1;guard=0;
    begin: read_wait
     forever begin
      @(posedge clk);guard=guard+1;
      if(out_valid&&out_ready)begin #1;disable read_wait;end
      if(done_valid)$fatal(1,"FAIL_W5_EDGE_DMA early DONE before output");
      if(guard>10000)$fatal(1,"FAIL_W5_EDGE_DMA output timeout");
     end
    end
   end
   @(negedge clk);out_ready=0;
  end
 endtask
 task automatic write_ok(input integer base,input integer count,input integer seed);
  integer k,w0,r0,a0,i0;
  begin
   w0=s_wreqs;r0=s_requests;a0=s_wacks;i0=input_takes;
   command(1,base,count);
   for(k=0;k<count;k=k+1)send(k,count,seed);
   await_done(0,count);
   check(s_wreqs-w0==count&&s_requests-r0==count&&s_wacks-a0==count&&input_takes-i0==count,
         "normal write exact req/ACK/source counts");
   take_done(0);
  end
 endtask
 task automatic read_ok(input integer base,input integer count,input integer stall_seed);
  integer r0,a0,o0;
  begin
   r0=s_rreqs;a0=s_racks;o0=output_takes;
   command(0,base,count);drain(count,stall_seed);await_done(0,count);
   check(s_rreqs-r0==count&&s_racks-a0==count&&output_takes-o0==count,"normal read exact req/ACK/output counts");
   take_done(0);
  end
 endtask
 task automatic pulse_abort;
  begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;in_valid=0;out_ready=0;end
 endtask
 task automatic wait_native_response;
  integer guard;
  begin
   guard=0;
   while(!dut.s_valid)begin @(posedge clk);#1;guard=guard+1;check(guard<10000,"native response timeout");end
  end
 endtask
 task automatic reject_command(input bit wr,input integer base,input integer count);
  integer q0;
  begin q0=s_requests;command(wr,base,count);await_done(1,0);check(s_requests==q0,"descriptor rejection has no S access");take_done(0);end
 endtask

 integer k,b,n,q0,a0,i0,o0,d0,c0;
 reg [31:0] rng=32'h13579bdf;
 initial begin
  hard_reset();passcase("W5DMA_RESET_IDLE");
  write_ok(16,16,31);passcase("W5DMA_WRITE16_ACK_BEFORE_SOURCE_RETIRE");
  read_ok(16,16,2);passcase("W5DMA_READ16_REAL_S_ORDER_LAST");
  write_ok(768,256,99);read_ok(768,256,3);passcase("W5DMA_MAX256_END1024");
  for(k=0;k<16;k=k+1)begin
   rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
   b=int'(rng%960);n=int'((rng>>12)%31)+1;
   write_ok(b,n,100+k);read_ok(b,n,k);
  end
  passcase("W5DMA_DETERMINISTIC_RANDOM_OVERLAP16");

  force dut.permit_req=1'b0;q0=s_requests;
  command(1,600,1);offer(0,1,pattern(300,0));
  repeat(8)begin @(posedge clk);#1;check(!in_ready&&s_requests==q0,"request gate holds captured source");end
  release dut.permit_req;retire_offer();await_done(0,1);take_done(0);
  passcase("W5DMA_REQUEST_GATE_HOLD");
  force dut.permit_rsp=1'b0;a0=s_wacks;i0=input_takes;
  command(1,601,1);offer(0,1,pattern(301,0));wait_native_response();
  repeat(8)begin @(posedge clk);#1;check(!in_ready&&s_wacks==a0&&input_takes==i0,"native write response gate holds source");end
  release dut.permit_rsp;retire_offer();await_done(0,1);take_done(0);
  passcase("W5DMA_NATIVE_ACK_GATE_HOLD");

  command(0,600,2);wait(out_valid);repeat(12)begin @(posedge clk);#1;check(out_valid&&!done_valid,"public output stall remains pending");end
  drain(2,0);await_done(0,2);take_done(0);passcase("W5DMA_OUTPUT_BACKPRESSURE");
  command(1,602,1);send(0,1,302);await_done(0,1);
  repeat(8)begin @(posedge clk);#1;check(done_valid&&!done_error&&busy,"held successful DONE");end
  take_done(1);passcase("W5DMA_DONE_HOLD_ABORT_READY_ONCE");

  reject_command(1,0,0);passcase("W5DMA_REJECT_COUNT0");
  reject_command(0,0,257);passcase("W5DMA_REJECT_COUNT257");
  reject_command(1,1000,25);passcase("W5DMA_REJECT_ADDRESS_WRAP");
  write_ok(1023,1,777);read_ok(1023,1,1);passcase("W5DMA_LAST_ADDRESS_ONE_WORD");
  hard_reset();q0=s_requests;command(0,600,1);await_done(1,0);
  check(s_requests==q0,"unwritten read rejected before native access");take_done(0);
  passcase("W5DMA_UNWRITTEN_READ_REJECT");

  q0=s_requests;command(1,100,2);offer(1,0,pattern(5,0));await_done(1,0);
  check(s_requests==q0,"bad initial index no write");@(negedge clk);in_valid=0;take_done(0);
  passcase("W5DMA_BAD_INDEX_NO_WRITE");
  q0=s_requests;command(1,100,2);offer(0,1,pattern(6,0));await_done(1,0);
  check(s_requests==q0,"bad last no write");@(negedge clk);in_valid=0;take_done(0);
  passcase("W5DMA_BAD_LAST_NO_WRITE");
  command(1,100,2);send(0,2,707);offer(1,0,pattern(707,1));await_done(1,1);
  @(negedge clk);in_valid=0;take_done(0);read_ok(100,1,0);
  passcase("W5DMA_BAD_METADATA_KEEP_ACK_PREFIX");
  force dut.permit_req=1'b0;q0=s_requests;command(1,200,1);offer(0,1,pattern(9,0));
  repeat(3)@(posedge clk);@(negedge clk);in_data=pattern(10,0);
  await_done(1,0);check(s_requests==q0,"source violation before native request");
  release dut.permit_req;@(negedge clk);in_valid=0;take_done(0);
  passcase("W5DMA_CHANGED_SOURCE_REJECT");

  command(1,201,2);pulse_abort();await_done(1,0);take_done(0);
  passcase("W5DMA_ABORT_BEFORE_CAPTURE");
  write_ok(202,1,18);force dut.permit_rsp=1'b0;
  command(1,202,1);offer(0,1,pattern(19,0));wait_native_response();
  check(!in_ready,"pending overwrite has no public retirement");pulse_abort();release dut.permit_rsp;
  await_done(1,0);take_done(0);q0=s_requests;command(0,202,1);await_done(1,0);
  check(s_requests==q0,"unACKed overwrite invalid not old-data-valid");take_done(0);
  passcase("W5DMA_ABORT_PENDING_ACK_INVALIDATES_OVERWRITE");
  command(1,203,1);offer(0,1,pattern(20,0));a0=s_wacks;i0=input_takes;
  while(s_wacks==a0)begin @(posedge clk);#1;end
  check(!in_ready,"native ACK precedes public source retirement");pulse_abort();
  await_done(1,1);check(input_takes==i0,"abort after ACK no source take");take_done(0);read_ok(203,1,0);
  passcase("W5DMA_ABORT_AFTER_ACK_STORED_PREFIX");
  write_ok(300,4,333);command(0,300,4);o0=output_takes;
  @(negedge clk);out_ready=1;
  while(output_takes==o0)begin @(posedge clk);#1;end
  pulse_abort();await_done(1,1);take_done(0);
  passcase("W5DMA_ABORT_READ_AFTER_OUTPUT_PREFIX");
  force dut.permit_rsp=1'b0;command(1,400,1);offer(0,1,pattern(40,0));wait_native_response();
  d0=done_takes;hard_reset();release dut.permit_rsp;
  check(done_takes==d0&&!done_valid,"hard reset no invented completion");
  command(0,400,1);await_done(1,0);take_done(0);write_ok(400,1,41);read_ok(400,1,2);
  passcase("W5DMA_RESET_PENDING_ACK_RECOVERY");
  command(1,401,1);send(0,1,42);await_done(0,1);d0=done_takes;
  hard_reset();check(done_takes==d0&&!done_valid,"reset cancels held DONE");
  passcase("W5DMA_RESET_HELD_DONE");
  write_ok(500,3,51);read_ok(500,3,1);write_ok(500,3,52);read_ok(500,3,2);
  passcase("W5DMA_NORMAL_REUSE_DIFFERENT_DATA");

  c0=commands;@(negedge clk);cmd_valid=1;cmd_write=1;cmd_base=600;cmd_words=1;
  @(posedge clk);#1;check(commands==c0+1,"held command initial admission");
  repeat(6)begin @(posedge clk);#1;check(commands==c0+1&&!cmd_ready,"held command only one admission");end
  @(negedge clk);cmd_valid=0;send(0,1,61);await_done(0,1);take_done(0);
  passcase("W5DMA_HELD_COMMAND_ACCEPT_ONCE");
  d0=done_takes;pulse_abort();repeat(3)@(posedge clk);#1;
  check(!done_valid&&done_takes==d0&&cmd_ready,"idle abort no DONE");
  passcase("W5DMA_ABORT_IDLE_NO_DONE");
  write_ok(700,1,71);command(0,700,2);drain(1,0);await_done(1,1);take_done(0);
  passcase("W5DMA_READ_INVALID_AFTER_VALID_PREFIX");
  write_ok(702,1,72);hard_reset();command(0,702,1);await_done(1,0);take_done(0);
  passcase("W5DMA_RESET_INVALIDATES_ACKED_CONTENT");

  check(cases==29,"frozen CASE count29");
  $display("W5DMA_STATS cycles=%0d cmd=%0d Sreq=%0d Sack=%0d writeACK=%0d readACK=%0d source=%0d output=%0d DONE=%0d",cycles,commands,s_requests,s_acks,s_wacks,s_racks,input_takes,output_takes,done_takes);
  $display("PASS_W5_EDGE_DMA cases=%0d",cases);$finish;
 end
endmodule
