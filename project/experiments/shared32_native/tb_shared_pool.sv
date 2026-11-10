`timescale 1ns/1ps
module tb_shared_pool;
 reg clk=0;
 always #5 clk=~clk;
 reg reset=1;
 reg cfg_valid=0,cfg_take=0;
 reg [1:0] cfg_op=0;
 reg [7:0] cfg_epoch=0;
 reg [11:0] cfg_words=0;
 wire cfg_ready,cfg_done,cfg_error;
 reg fill_valid=0,fill_take=0;
 reg [8:0] fill_addr=0;
 reg [511:0] fill_data=0;
 reg [3:0] fill_mask=0;
 wire fill_ready,fill_done,fill_error;
 reg [1:0] p_cmd_valid=0,p_cmd_bank=0,p_cmd_awide=0,p_done_take=0;
 reg [7:0] p_cmd_rows=0;
 reg [5:0] p_cmd_tiles=0;
 reg [21:0] p_cmd_base=0;
 reg [15:0] p_cmd_epoch=0;
 wire [1:0] p_cmd_ready,p_done,p_error,a_valid,a_bank,a_wide;
 reg [1:0] a_ready=0;
 wire [5:0] a_row;
 wire [3:0] a_tile;
 wire [255:0] a_data;
 wire object_valid;
 wire [7:0] object_epoch;
 wire [11:0] object_words;
 shared_a_pool32 dut(.*);

 integer checks=0,cycles=0,reads=0,writes=0,a_words=0,errors=0;
 integer descriptors=0,completions=0,fill_requests=0,fill_acks=0,cancelled_fill=0;
 integer peak0=0,peak1=0,seed=247,generation=0;
 integer unsigned rng=1;
 reg [1:0] expected_cmd_error=0;
 reg expected_live[0:1],expected_error[0:1],expected_bank[0:1],expected_wide[0:1];
 integer expected_base[0:1],expected_rows[0:1],expected_total[0:1],seen[0:1];
 reg held[0:1];
 reg [134:0] held_data[0:1];

 task automatic must(input bit condition,input string message);
  begin
   checks=checks+1;
   if(!condition)$fatal(1,"POOL_CHECK %s cycle=%0d",message,cycles);
  end
 endtask
 function automatic [127:0] word_value(input integer address,input integer version);
  reg [127:0] value;
  integer lane;
  begin
   value=0;
   for(lane=0;lane<8;lane=lane+1)value[lane*16+:16]=16'(address*17+version*101+lane*8191);
   word_value=value;
  end
 endfunction
 function automatic [511:0] line_value(input integer address,input integer version);
  reg [511:0] value;
  integer lane;
  begin
   value=0;
   for(lane=0;lane<4;lane=lane+1)value[lane*128+:128]=word_value(address*4+lane,version);
   line_value=value;
  end
 endfunction

 integer m;
 always @(posedge clk)begin
  cycles=cycles+1;
  if(reset)begin
   for(m=0;m<2;m=m+1)begin
    expected_live[m]=0;expected_error[m]=0;expected_bank[m]=0;expected_wide[m]=0;
    expected_base[m]=0;expected_rows[m]=0;expected_total[m]=0;seen[m]=0;held[m]=0;held_data[m]=0;
   end
  end else begin
   if(dut.read_fire)reads=reads+1;
   if(dut.write_fire)writes=writes+1;
   if(fill_valid&&fill_ready)fill_requests=fill_requests+1;
   if(fill_done&&fill_take)begin fill_acks=fill_acks+1;if(fill_error)errors=errors+1;end
   if(cfg_done&&cfg_take&&cfg_error)errors=errors+1;
   must(!(dut.read_fire&&dut.write_fire),"read/write phases overlap");
   must(int'(dut.fill_ack_count)+int'(dut.fill_pending)<=2,"fill response credit overflow");
   if(int'(dut.fifo_count[0])>peak0)peak0=int'(dut.fifo_count[0]);
   if(int'(dut.fifo_count[1])>peak1)peak1=int'(dut.fifo_count[1]);
   for(m=0;m<2;m=m+1)begin
    must(int'(dut.fifo_count[m])+((dut.pending_read&&int'(dut.pending_owner)==m)?1:0)<=4,"A response credit overflow");
    if(held[m])must(a_valid[m]&&
     {a_bank[m],a_row[m*3+:3],a_tile[m*2+:2],a_wide[m],a_data[m*128+:128]}==held_data[m],"stalled A changed");
    held[m]=a_valid[m]&&!a_ready[m];
    held_data[m]={a_bank[m],a_row[m*3+:3],a_tile[m*2+:2],a_wide[m],a_data[m*128+:128]};
    if(p_cmd_valid[m]&&p_cmd_ready[m])begin
     must(!expected_live[m],"descriptor replaced active scoreboard");
     expected_error[m]=expected_cmd_error[m];expected_live[m]=!expected_cmd_error[m];
     expected_base[m]=int'(p_cmd_base[m*11+:11]);expected_rows[m]=int'(p_cmd_rows[m*4+:4]);
     expected_total[m]=int'(p_cmd_rows[m*4+:4])*int'(p_cmd_tiles[m*3+:3]);
     expected_bank[m]=p_cmd_bank[m];expected_wide[m]=p_cmd_awide[m];seen[m]=0;descriptors=descriptors+1;
    end
    if(a_valid[m]&&a_ready[m])begin
     must(expected_live[m],"unexpected data from invalid/inactive descriptor");
     must(seen[m]<expected_total[m],"too many A containers");
     must(a_data[m*128+:128]==word_value(expected_base[m]+seen[m],generation),"SRAM data/address mismatch");
     must(a_bank[m]==expected_bank[m]&&a_wide[m]==expected_wide[m],"A bank/format tag mismatch");
     must(int'(a_row[m*3+:3])==seen[m]%expected_rows[m]&&int'(a_tile[m*2+:2])==seen[m]/expected_rows[m],"A row/tile order mismatch");
     seen[m]=seen[m]+1;a_words=a_words+1;
    end
    if(p_done[m])begin
     must(!p_cmd_ready[m]&&!a_valid[m],"completion did not retain descriptor ownership");
     must(p_error[m]==expected_error[m],"descriptor error mismatch");
     if(!expected_error[m])must(seen[m]==expected_total[m],"completion before all A handshakes");
     if(p_done_take[m])begin
      expected_live[m]=0;completions=completions+1;if(p_error[m])errors=errors+1;
     end
    end
   end
  end
 end

 task automatic take_cfg(input bit expected);
  integer timeout;
  begin
   timeout=0;
   while(!cfg_done)begin @(negedge clk);timeout=timeout+1;must(timeout<5000,"configuration completion timeout");end
   must(cfg_error==expected,"configuration status");
   repeat(2)begin @(negedge clk);must(cfg_done&&cfg_error==expected,"configuration completion not held");end
   cfg_take=1;@(negedge clk);cfg_take=0;
  end
 endtask
 task automatic config_cmd(input integer op,input integer epoch,input integer words,input bit expected);
  begin
   @(negedge clk);cfg_op=2'(op);cfg_epoch=8'(epoch);cfg_words=12'(words);cfg_valid=1;
   do @(posedge clk);while(!cfg_ready);
   @(negedge clk);cfg_valid=0;take_cfg(expected);
  end
 endtask
 task automatic fill_object(input integer words,input bit stall_credit,input bit hold_last_ack);
  integer line,lines,left,timeout,start_cycles,start_writes;
  begin
   lines=(words+3)/4;start_cycles=cycles;start_writes=writes;
   @(negedge clk);fill_take=!stall_credit;
   for(line=0;line<lines;line=line+1)begin
    fill_valid=1;fill_addr=9'(line);fill_data=line_value(line,generation);
    left=words-line*4;fill_mask=left>=4?4'b1111:4'((1<<left)-1);
    if(stall_credit&&line==2)begin
     repeat(6)begin @(negedge clk);must(!fill_ready,"third fill escaped two ACK credits");end
     fill_take=1;
    end
    do @(posedge clk);while(!fill_ready);
    @(negedge clk);
   end
   fill_valid=0;
   if(hold_last_ack)fill_take=0;
   else begin
    timeout=0;
    while(dut.fill_pending||fill_done)begin @(negedge clk);timeout=timeout+1;must(timeout<100,"fill drain timeout");end
    fill_take=0;
   end
   $display("POOL_MEASURE scenario=fill cycles=%0d writes=%0d words=%0d credit_stall=%0d",cycles-start_cycles,writes-start_writes,words,int'(stall_credit));
  end
 endtask
 task automatic bad_fill(input integer address,input reg [3:0] mask);
  integer before_writes;
  begin
   before_writes=writes;
   @(negedge clk);fill_addr=9'(address);fill_mask=mask;fill_data='1;fill_valid=1;fill_take=0;
   do @(posedge clk);while(!fill_ready);
   @(negedge clk);fill_valid=0;
   while(!fill_done)@(negedge clk);
   must(fill_error,"bad fill accepted");must(writes==before_writes,"bad fill touched SRAM");
   fill_take=1;@(negedge clk);fill_take=0;
  end
 endtask
 task automatic launch(
  input reg [1:0] mask,input integer base0,rows0,tiles0,epoch0,
  input integer base1,rows1,tiles1,epoch1,input reg [1:0] invalid);
  reg [1:0] accepted;
  begin
   @(negedge clk);
   p_cmd_base={11'(base1),11'(base0)};p_cmd_rows={4'(rows1),4'(rows0)};
   p_cmd_tiles={3'(tiles1),3'(tiles0)};p_cmd_epoch={8'(epoch1),8'(epoch0)};
   p_cmd_bank=2'b10;p_cmd_awide=2'b10;expected_cmd_error=invalid;p_cmd_valid=mask;
   while(p_cmd_valid!=0)begin
    @(posedge clk);accepted=p_cmd_valid&p_cmd_ready;
    @(negedge clk);p_cmd_valid=p_cmd_valid&~accepted;
   end
  end
 endtask
 task automatic drain(input reg [1:0] mask,input bit random_stall);
  integer timeout;
  begin
   timeout=0;
   while((p_done&mask)!=mask)begin
    rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
    a_ready=random_stall?{rng[4]|rng[7],rng[2]|rng[9]}:2'b11;
    @(negedge clk);timeout=timeout+1;must(timeout<2000,"descriptor drain timeout");
   end
   a_ready=0;
  end
 endtask
 task automatic retire(input reg [1:0] mask);
  begin
   must((p_done&mask)==mask,"retire before completion");
   @(negedge clk);p_done_take=mask;@(negedge clk);p_done_take=0;
  end
 endtask
 task automatic do_reset;
  begin
   @(negedge clk);cancelled_fill=cancelled_fill+int'(dut.fill_pending)+int'(dut.fill_ack_count);
   reset=1;cfg_valid=0;cfg_take=0;fill_valid=0;fill_take=0;
   p_cmd_valid=0;p_done_take=0;a_ready=0;
   repeat(3)@(negedge clk);
   reset=0;@(negedge clk);
   must(!object_valid&&p_done==0&&a_valid==0&&!fill_done&&!cfg_done,"reset did not discard ownership");
  end
 endtask

 integer mark,read_mark,word_mark,write_mark;
 initial begin
  if($value$plusargs("SEED=%d",seed))begin end
  rng=32'(seed);generation=seed;
  repeat(4)@(negedge clk);reset=0;
  config_cmd(0,17,0,1);
  config_cmd(0,17,2049,1);
  config_cmd(3,17,16,1);
  config_cmd(1,17,16,1);
  config_cmd(0,17,2048,0);
  must(object_epoch==8'd17&&object_words==12'd2048&&!object_valid,"begin status");
  bad_fill(1,4'b1111);
  bad_fill(0,4'b0011);
  fill_object(2048,1,1);
  // All writes have been issued; the last real ACK remains unconsumed.
  @(negedge clk);cfg_op=1;cfg_epoch=17;cfg_valid=1;
  repeat(5)begin @(negedge clk);must(!cfg_ready&&!object_valid,"sealed before fill ACK retirement");end
  fill_take=1;
  do @(posedge clk);while(!cfg_ready);
  @(negedge clk);cfg_valid=0;fill_take=0;take_cfg(0);
  must(object_valid,"seal did not publish object");
  config_cmd(0,18,16,1);
  config_cmd(2,18,0,1);
  @(negedge clk);fill_valid=1;fill_addr=0;fill_mask=15;write_mark=writes;
  repeat(5)begin @(negedge clk);must(!fill_ready&&writes==write_mark,"write admitted while sealed");end
  fill_valid=0;

  mark=cycles;read_mark=reads;word_mark=a_words;
  launch(3,0,8,4,17,0,8,4,17,0);
  repeat(24)@(negedge clk);
  must(dut.fifo_count[0]==4&&dut.fifo_count[1]==4,"both four-entry FIFOs not exercised");
  must(reads-read_mark==8,"stalled consumers exceeded reserved capacity");
  drain(3,0);
  must(reads-read_mark==16&&a_words-word_mark==64,"same-address consumers broadcast or lost traffic");
  repeat(4)begin @(negedge clk);must(p_done==3&&p_cmd_ready==0,"done was not held");end
  retire(3);
  $display("POOL_MEASURE scenario=simultaneous cycles=%0d reads=%0d a_words=%0d",cycles-mark,reads-read_mark,a_words-word_mark);

  mark=cycles;read_mark=reads;word_mark=a_words;
  launch(3,1021,7,4,17,2037,1,4,17,0);drain(3,1);retire(3);
  must(reads-read_mark==10&&a_words-word_mark==32,"boundary beat accounting");
  launch(3,2044,4,1,17,2047,1,1,17,0);drain(3,1);retire(3);
  $display("POOL_MEASURE scenario=boundary cycles=%0d reads=%0d a_words=%0d",cycles-mark,reads-read_mark,a_words-word_mark);

  mark=cycles;read_mark=reads;word_mark=a_words;
  launch(3,2047,2,1,17,0,1,1,16,3);drain(3,1);retire(3);
  launch(3,0,0,1,17,0,9,1,17,3);drain(3,1);retire(3);
  launch(3,0,1,0,17,0,1,5,17,3);drain(3,1);retire(3);
  must(reads==read_mark&&a_words==word_mark,"invalid descriptor issued data/read");
  $display("POOL_MEASURE scenario=invalid cycles=%0d reads=%0d a_words=%0d",cycles-mark,reads-read_mark,a_words-word_mark);

  mark=cycles;
  launch(1,7,8,4,17,0,1,1,17,0);
  @(negedge clk);cfg_op=2;cfg_epoch=17;cfg_valid=1;
  repeat(8)begin @(negedge clk);must(!cfg_ready&&object_valid&&p_cmd_ready[1]==0,"release did not wait or admitted new reader");end
  drain(1,1);
  repeat(4)begin @(negedge clk);must(!cfg_ready&&object_valid,"release ignored held P completion");end
  retire(1);
  while(!cfg_done)@(negedge clk);
  cfg_valid=0;take_cfg(0);must(!object_valid,"release kept object readable");
  $display("POOL_MEASURE scenario=release_hold cycles=%0d",cycles-mark);

  generation=seed+1;config_cmd(0,18,35,0);fill_object(35,0,0);config_cmd(1,18,0,0);
  launch(3,1,8,4,18,0,7,4,18,0);
  repeat(5)@(negedge clk);must(dut.fifo_count[0]!=0||dut.pending_read,"reset case had no live response");
  mark=cycles;do_reset();
  config_cmd(1,18,0,1);
  generation=seed+2;config_cmd(0,19,5,0);fill_object(5,0,0);config_cmd(1,19,0,0);
  launch(3,0,1,4,19,4,1,1,19,0);drain(3,1);retire(3);config_cmd(2,19,0,0);
  config_cmd(0,20,1,0);
  @(negedge clk);fill_valid=1;fill_addr=0;fill_mask=1;fill_data='1;fill_take=0;
  do @(posedge clk);while(!fill_ready);
  do_reset();
  generation=seed+3;config_cmd(0,21,1,0);fill_object(1,0,0);config_cmd(1,21,0,0);
  launch(1,0,1,1,21,0,1,1,21,0);drain(1,0);retire(1);config_cmd(2,21,0,0);
  $display("POOL_MEASURE scenario=reset_refill cycles=%0d",cycles-mark);
  must(peak0==4&&peak1==4,"FIFO capacity coverage");
  must(descriptors>completions,"reset did not cancel active descriptors");
  must(fill_requests==fill_acks+cancelled_fill&&cancelled_fill==1,"fill ACK/reset conservation");
  $display("POOL_PASS checks=%0d reads=%0d writes=%0d a_words=%0d errors=%0d descriptors=%0d completions=%0d fifo0_peak=%0d fifo1_peak=%0d fill_cancelled=%0d cycles=%0d",checks,reads,writes,a_words,errors,descriptors,completions,peak0,peak1,cancelled_fill,cycles);
  $finish;
 end
 initial begin
  repeat(30000)@(posedge clk);
  $fatal(1,"POOL_CHECK watchdog timeout");
 end
endmodule
