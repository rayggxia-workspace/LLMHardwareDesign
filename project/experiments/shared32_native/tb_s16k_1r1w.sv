`timescale 1ns/1ps
// Public-port scoreboard; compile with the actual 256x128 SRAM model.
module tb_s16k_1r1w #(parameter bit ECHO_WRITE_DATA=1'b1);
 reg clk=0;
 always #5 clk=~clk;
 reg reset=1,cold_reset=1;
 reg req=0,wr=0,take=1;
 reg [9:0] addr=0;
 reg [127:0] din=0;
 wire ready,valid;
 wire [127:0] dout;
 reg wide_req=0,wide_take=1;
 reg [7:0] wide_addr=0;
 wire wide_ready,wide_valid;
 wire [511:0] wide_dout;
 reg wide_write_req=0,wide_write_take=1;
 reg [7:0] wide_write_addr=0;
 reg [511:0] wide_write_data=0;
 reg [3:0] wide_write_mask=0;
 wire wide_write_ready,wide_write_valid;
`ifdef USE_POWER_PINS
 wire vdd=1'b1,gnd=1'b0;
`endif
 block_feed_s16k_1r1w #(.ECHO_WRITE_DATA(ECHO_WRITE_DATA)) dut(.*);

 reg [127:0] reference[0:1023];
 reg initialized[0:1023];
 reg [127:0] narrow_expected[0:16383];
 reg [511:0] read_expected[0:16383];
 integer narrow_cycle[0:16383],read_cycle[0:16383],write_cycle[0:16383];
 integer nh=0,nt=0,rh=0,rt=0,wh=0,wt=0;
 integer cycles=0,reads=0,writes=0,simultaneous=0,same_line=0;
 integer n_responses=0,r_responses=0,w_responses=0,canceled=0;
 integer cold_events=0,warm_events=0;
 reg previous_cold=0,previous_warm=0;
 reg observed_n=0,observed_r=0,observed_w=0;
 reg held_n=0,held_r=0,held_w=0;
 reg [127:0] held_n_data;
 reg [511:0] held_r_data;
 reg [15:0] masks_seen=0;
 reg [31:0] rng=32'h31a759c5;
 integer seed=1;
 integer run_reads,run_writes,run_simultaneous,run_cycles;

 function automatic [31:0] random_word;
  begin
   rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
   random_word=rng;
  end
 endfunction
 function automatic [511:0] pattern(input integer row,input integer epoch);
  begin
   for(integer lane=0;lane<4;lane=lane+1)
    pattern[128*lane+:128]={32'(epoch),32'(row),32'(lane),32'(row^epoch^(lane*12345))};
  end
 endfunction
 task automatic tick;
  begin @(posedge clk);#1;end
 endtask
 task automatic idle_inputs;
  begin req=0;wide_req=0;wide_write_req=0;take=1;wide_take=1;wide_write_take=1;end
 endtask
 task automatic drain;
  begin
   @(negedge clk);idle_inputs();
   repeat(8)tick();
   if(nh!=nt||rh!=rt||wh!=wt)$fatal(1,"scoreboard did not drain");
  end
 endtask
 task automatic initialize_all(input integer epoch);
  begin
   for(integer row=0;row<256;row=row+1)begin
    @(negedge clk);idle_inputs();
    wide_write_req=1;wide_write_addr=8'(row);
    wide_write_data=pattern(row,epoch);wide_write_mask=4'hf;
    tick();if(!observed_w)$fatal(1,"initialization write throughput");
   end
   drain();
  end
 endtask

 // All expectation reads are captured before applying writes at the same
 // edge, independently establishing read-before-write across all lane masks.
 always @(posedge clk)begin: scoreboard
  integer word_index;
  reg accepted_read,accepted_write;
  reg [7:0] accepted_read_line,accepted_write_line;
  cycles=cycles+1;
  if(cycles>12000)$fatal(1,"watchdog");
  observed_n=req&&ready;observed_r=wide_req&&wide_ready;
  observed_w=wide_write_req&&wide_write_ready;
  if(cold_reset&&!previous_cold)cold_events=cold_events+1;
  if(reset&&!previous_warm&&!cold_reset)warm_events=warm_events+1;
  previous_cold=cold_reset;previous_warm=reset;
  if(reset||cold_reset)begin
   if(ready||wide_ready||wide_write_ready||valid||wide_valid||wide_write_valid)
    $fatal(1,"reset interface not quiescent");
   canceled=canceled+(nt-nh)+(rt-rh)+(wt-wh);
   nh=0;nt=0;rh=0;rt=0;wh=0;wt=0;
   held_n=0;held_r=0;held_w=0;
   if(cold_reset)for(integer i=0;i<1024;i=i+1)initialized[i]=0;
  end else begin
   if(held_n&&(!valid||dout!==held_n_data))$fatal(1,"narrow response changed under backpressure");
   if(held_r&&(!wide_valid||wide_dout!==held_r_data))$fatal(1,"wide read changed under backpressure");
   if(held_w&&!wide_write_valid)$fatal(1,"write ACK changed under backpressure");
   if(valid&&take)begin
    if(nh==nt||cycles<=narrow_cycle[nh])$fatal(1,"early or unsolicited narrow response");
    if(dout!==narrow_expected[nh])$fatal(1,"narrow mismatch response=%0d got=%h expected=%h",nh,dout,narrow_expected[nh]);
    nh=nh+1;n_responses=n_responses+1;
   end
   if(wide_valid&&wide_take)begin
    if(rh==rt||cycles<=read_cycle[rh])$fatal(1,"early or unsolicited wide response");
    if(wide_dout!==read_expected[rh])$fatal(1,"wide mismatch response=%0d got=%h expected=%h",rh,wide_dout,read_expected[rh]);
    rh=rh+1;r_responses=r_responses+1;
   end
   if(wide_write_valid&&wide_write_take)begin
    if(wh==wt||cycles<=write_cycle[wh])$fatal(1,"early or unsolicited write ACK");
    wh=wh+1;w_responses=w_responses+1;
   end
   held_n=valid&&!take;held_n_data=dout;
   held_r=wide_valid&&!wide_take;held_r_data=wide_dout;
   held_w=wide_write_valid&&!wide_write_take;
   if(observed_r)begin
    for(integer lane=0;lane<4;lane=lane+1)begin
     word_index=int'(wide_addr)*4+lane;
     if(!initialized[word_index])$fatal(1,"TB attempted cold-invalid read");
     read_expected[rt][128*lane+:128]=reference[word_index];
    end
    read_cycle[rt]=cycles;rt=rt+1;reads=reads+1;
   end
   if(observed_n)begin
    word_index=int'(addr);
    if(wr)narrow_expected[nt]=ECHO_WRITE_DATA?din:128'b0;
    else begin
     if(!initialized[word_index])$fatal(1,"TB attempted cold-invalid narrow read");
     narrow_expected[nt]=reference[word_index];reads=reads+1;
    end
    narrow_cycle[nt]=cycles;nt=nt+1;
   end
   // A narrow and a wide request cannot consume the same logical port.
   if(observed_n&&!wr&&observed_r)$fatal(1,"two logical read ports accepted");
   if(observed_n&&wr&&observed_w)$fatal(1,"two logical write ports accepted");
   accepted_read=observed_r||(observed_n&&!wr);
   accepted_write=observed_w||(observed_n&&wr);
   accepted_read_line=observed_r?wide_addr:addr[9:2];
   accepted_write_line=observed_w?wide_write_addr:addr[9:2];
   if(accepted_read&&accepted_write)begin
    simultaneous=simultaneous+1;
    if(accepted_read_line==accepted_write_line)same_line=same_line+1;
   end
   if(observed_n&&wr)begin
    reference[int'(addr)]=din;initialized[int'(addr)]=1;writes=writes+1;
   end
   if(observed_w)begin
    masks_seen[wide_write_mask]=1;
    for(integer lane=0;lane<4;lane=lane+1)if(wide_write_mask[lane])begin
     word_index=int'(wide_write_addr)*4+lane;
     reference[word_index]=wide_write_data[128*lane+:128];initialized[word_index]=1;
    end
    write_cycle[wt]=cycles;wt=wt+1;writes=writes+1;
   end
   if(nt-nh>2||rt-rh>2||wt-wh>2)$fatal(1,"response credits exceeded two including in-flight");
  end
 end

 for(genvar lane=0;lane<4;lane=lane+1)begin: physical_lane_checks
  for(genvar copy=0;copy<2;copy=copy+1)begin: physical_copy_checks
   always @(posedge clk)if(!reset&&!cold_reset)
    if(dut.lanes[lane].copies[copy].selected_read&&dut.lanes[lane].copies[copy].selected_write)
     $fatal(1,"real 1RW macro received read and write at the same edge");
  end
 end

 initial begin: test
  reg [31:0] choice;
  reg [511:0] data_word;
  if($value$plusargs("SEED=%d",seed))begin end
  rng=32'(seed)^32'h31a759c5;
  repeat(3)tick();
  @(negedge clk);reset=0;cold_reset=0;
  initialize_all(1);

  run_reads=reads;run_writes=writes;run_simultaneous=simultaneous;run_cycles=cycles;
  // Every edge must accept a complete 64B read AND a complete 64B write.
  for(integer i=0;i<256;i=i+1)begin
   @(negedge clk);idle_inputs();
   wide_req=1;wide_addr=8'(i);
   wide_write_req=1;wide_write_addr=8'(i+73);
   wide_write_data=pattern(i,2);wide_write_mask=4'hf;
   tick();if(!observed_r||!observed_w)$fatal(1,"sustained independent 1R1W throughput failed");
  end
  if(reads-run_reads!=256||writes-run_writes!=256||simultaneous-run_simultaneous!=256)
   $fatal(1,"throughput accounting");
  $display("S16K_1R1W_THROUGHPUT cycles=%0d reads=%0d writes=%0d simultaneous_rw=%0d read_bytes=16384 write_bytes=16384",
   cycles-run_cycles,reads-run_reads,writes-run_writes,simultaneous-run_simultaneous);
  drain();

  // Repeated aliases and every mask, including empty and partial writes.
  for(integer i=0;i<128;i=i+1)begin
   @(negedge clk);idle_inputs();wide_req=1;wide_addr=8'(i%5);
   wide_write_req=1;wide_write_addr=wide_addr;
   wide_write_data=pattern(i,3);wide_write_mask=4'(i%16);
   tick();if(!observed_r||!observed_w)$fatal(1,"same-line 1R1W acceptance");
  end
  drain();
  // Concurrent narrow writes/wide reads, followed by the other direction.
  for(integer i=0;i<256;i=i+1)begin
   @(negedge clk);idle_inputs();req=1;wr=1;addr=10'(i%20);
   data_word=pattern(i,4);din=data_word[127:0];wide_req=1;wide_addr=addr[9:2];
   tick();if(!observed_n||!observed_r)$fatal(1,"narrow-write/wide-read acceptance");
  end
  drain();
  for(integer i=0;i<128;i=i+1)begin
   @(negedge clk);idle_inputs();req=1;wr=0;addr=10'(i%20);
   wide_write_req=1;wide_write_addr=addr[9:2];wide_write_data=pattern(i,5);wide_write_mask=4'hf;
   tick();if(!observed_n||!observed_w)$fatal(1,"narrow-read/wide-write acceptance");
  end
  drain();

  // Three clients, output stalls and stable unaccepted requests.
  for(integer i=0;i<2400;i=i+1)begin
   @(negedge clk);
   if(!req||observed_n)begin
    choice=random_word();req=choice[0]|choice[1];wr=choice[2];addr=choice[12:3];
    data_word=pattern(i,6);din=data_word[127:0];
   end
   if(!wide_req||observed_r)begin choice=random_word();wide_req=choice[0]|choice[1];wide_addr=choice[9:2];end
   if(!wide_write_req||observed_w)begin
    choice=random_word();wide_write_req=choice[0]|choice[1];wide_write_addr=choice[9:2];
    wide_write_mask=choice[13:10];wide_write_data=pattern(i,7);
   end
   choice=random_word();take=choice[0]|choice[1];wide_take=choice[2]|choice[3];wide_write_take=choice[4]|choice[5];
   tick();
  end
  // Drain still-held requests legally before changing the commands.
  @(negedge clk);take=1;wide_take=1;wide_write_take=1;
  while(req||wide_req||wide_write_req)begin
   tick();@(negedge clk);
   if(observed_n)req=0;if(observed_r)wide_req=0;if(observed_w)wide_write_req=0;
  end
  drain();

  // Warm reset after acceptance but before the macro's low-phase commit.
  @(negedge clk);idle_inputs();wide_write_req=1;wide_write_addr=8'd91;
  wide_write_data=pattern(91,8);wide_write_mask=4'hf;
  wide_req=1;wide_addr=8'd91;wide_take=0;wide_write_take=0;
  tick();if(!observed_w||!observed_r)$fatal(1,"reset setup request rejected");
  #1;reset=1; // Accepted write remains committed; its response is canceled.
  repeat(2)tick();
  @(negedge clk);idle_inputs();reset=0;
  wide_req=1;wide_addr=8'd91;tick();if(!observed_r)$fatal(1,"warm-reset reread rejected");
  drain();

  // Fill response storage, reset held responses, and preserve the data.
  @(negedge clk);idle_inputs();take=0;wide_take=0;wide_write_take=0;
  req=1;wr=0;addr=10'd364;wide_req=1;wide_addr=8'd91;
  wide_write_req=1;wide_write_addr=8'd177;wide_write_mask=4'hf;wide_write_data=pattern(177,9);
  repeat(20)tick();
  if(nt-nh!=2||rt-rh!=2||wt-wh!=2)$fatal(1,"response queues did not reserve exactly two slots");
  @(negedge clk);reset=1;repeat(2)tick();
  @(negedge clk);idle_inputs();reset=0;wide_req=1;wide_addr=8'd177;
  tick();drain();

  // Cold reset intentionally invalidates memory; no reads before rewrite.
  @(negedge clk);idle_inputs();wide_write_req=1;wide_write_addr=8'd17;
  wide_write_data=pattern(17,10);wide_write_mask=4'hf;wide_write_take=0;
  tick();#1;cold_reset=1;repeat(2)tick();
  for(integer lane=0;lane<4;lane=lane+1)if(dut.live[lane]!==256'b0)$fatal(1,"cold reset did not clear location table");
  @(negedge clk);idle_inputs();cold_reset=0;
  initialize_all(11);
  for(integer row=0;row<256;row=row+1)begin
   @(negedge clk);wide_req=1;wide_addr=8'(row);tick();
   if(!observed_r)$fatal(1,"post-cold sweep acceptance");
  end
  drain();
  if(masks_seen!==16'hffff||same_line<100||cold_events!=2||warm_events!=2||canceled<3)
   $fatal(1,"coverage missing masks=%h same=%0d cold=%0d warm=%0d cancel=%0d",masks_seen,same_line,cold_events,warm_events,canceled);
  $display("S16K_1R1W_MEASURE seed=%0d cycles=%0d simultaneous_rw=%0d same_line=%0d reads=%0d writes=%0d narrow_responses=%0d wide_read_responses=%0d wide_write_responses=%0d canceled=%0d cold_resets=%0d warm_resets=%0d logical_bytes=16384 physical_bytes=32768 macros=8 live_bits=1024",
   seed,cycles,simultaneous,same_line,reads,writes,n_responses,r_responses,w_responses,canceled,cold_events,warm_events);
  $display("S16K_1R1W_PASS");$finish;
 end
endmodule
