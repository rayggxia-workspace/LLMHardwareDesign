module tb_popt_local #(parameter bit BANK_RW=1'b1,REUSE_A=1'b0);
 reg clk=0;always #5 clk=~clk;
 reg reset=1,req_valid=0,req_write=0,rsp_ready=1;
 reg [9:0] req_addr=0;reg [127:0] req_data=0;
 wire req_ready,rsp_valid;wire [127:0] rsp_data;
 reg load_valid=0,load_bank=1,load_a_wide=0,load_b_wide=0,load_reuse_b=0;
 reg [3:0] load_rows=0;reg [2:0] load_tiles=0;
 reg [9:0] load_a_base=0,load_b_base=64;
 wire load_ready,done_valid,done_error;
 reg done_take=0,a_ready=0,b_ready=0;
 wire a_valid,a_bank,a_wide,b_valid,b_bank,b_wide,b_half;
 wire [2:0] a_row;wire [1:0] a_tile,b_tile;
 wire [127:0] a_data;wire [511:0] b_data;
 local_s_p #(.ENABLE_BANK_RW(BANK_RW),.ENABLE_REUSE_A(REUSE_A)) dut(.*);
 reg [127:0] reference_words[0:1023],n_expected[0:8191];
 integer np=0,nc=0,ac=0,bc=0,cycles=0,wide_commands=0,write_owned=0;
 integer expected_rows=0,expected_tiles=0,expected_wide=0,expected_reuse=0;
 integer n_base=0,w_base=64;
 reg expected_error=0,owned=0;
 reg n_stall=0,a_stall=0,b_stall=0;
 reg [127:0] old_n;reg [134:0] old_a;reg [516:0] old_b;
 reg [511:0] want_b;
 always @(posedge clk)begin
  cycles=cycles+1;
  if(reset)begin np=0;nc=0;ac=0;bc=0;owned=0;n_stall=0;a_stall=0;b_stall=0;end
  else begin
   if(n_stall&&(!rsp_valid||rsp_data!==old_n))$fatal(1,"LOCAL_RESPONSE_STABILITY");
   if(a_stall&&(!a_valid||{a_bank,a_row,a_tile,a_wide,a_data}!==old_a))$fatal(1,"LOCAL_A_STABILITY");
   if(b_stall&&(!b_valid||{b_bank,b_tile,b_wide,b_half,b_data}!==old_b))$fatal(1,"LOCAL_B_STABILITY");
   n_stall=rsp_valid&&!rsp_ready;old_n=rsp_data;
   a_stall=a_valid&&!a_ready;old_a={a_bank,a_row,a_tile,a_wide,a_data};
   b_stall=b_valid&&!b_ready;old_b={b_bank,b_tile,b_wide,b_half,b_data};
   if(load_valid&&load_ready)owned=1;
   if(req_valid&&req_ready)begin
    n_expected[np]=req_write?128'b0:reference_words[req_addr];np=np+1;
    if(req_write)begin
     if(owned)begin
      write_owned=write_owned+1;
      if((expected_rows>0&&int'(req_addr)>=n_base&&int'(req_addr)<n_base+expected_tiles*(expected_rows>4?8:4))||
         (!expected_reuse&&int'(req_addr)>=w_base&&int'(req_addr)<w_base+expected_tiles*(expected_wide?8:4)))
       $fatal(1,"ACTIVE_LOAD_INPUT_OVERWRITTEN");
     end
     reference_words[req_addr]=req_data;
    end
   end
   if(rsp_valid&&rsp_ready)begin
    if(nc>=np||rsp_data!==n_expected[nc])$fatal(1,"LOCAL_RESPONSE_ORDER");nc=nc+1;
   end
   if(dut.wide_req&&dut.wide_ready)wide_commands=wide_commands+1;
   if(a_valid&&a_ready)begin
    if(expected_error||expected_rows==0||ac>=expected_rows*expected_tiles||a_bank!==load_bank||a_wide!==load_a_wide||
       int'(a_row)!=ac%expected_rows||int'(a_tile)!=ac/expected_rows||
       a_data!==reference_words[n_base+(ac/expected_rows)*(expected_rows>4?8:4)+ac%expected_rows])$fatal(1,"LOCAL_A_DATA_OR_TAG");
    ac=ac+1;
   end
   if(b_valid&&b_ready)begin
    for(integer j=0;j<4;j=j+1)want_b[128*j+:128]=reference_words[w_base+bc*4+j];
    if(expected_error||expected_reuse||bc>=expected_tiles*(expected_wide?2:1)||b_bank!==load_bank||b_wide!==load_b_wide||
       int'(b_tile)!=bc/(expected_wide?2:1)||b_half!==(expected_wide?1'(bc%2):1'b0)||b_data!==want_b)
       $fatal(1,"LOCAL_B_DATA_OR_TAG");bc=bc+1;
   end
   if(done_valid&&done_take)owned=0;
  end
 end
 task automatic tick;@(posedge clk);@(negedge clk);endtask
 task automatic write_word(input [9:0] address,input [127:0] value);
  req_valid=1;req_write=1;req_addr=address;req_data=value;
  do @(posedge clk);while(!req_ready);@(negedge clk);req_valid=0;
 endtask
 task automatic read_word(input [9:0] address);
  req_valid=1;req_write=0;req_addr=address;
  do @(posedge clk);while(!req_ready);@(negedge clk);req_valid=0;
 endtask
 task automatic drain;while(np!=nc)tick();tick();endtask
 task automatic reset_group;
  reset=1;req_valid=0;load_valid=0;rsp_ready=1;done_take=0;a_ready=0;b_ready=0;
  #1;if(req_ready||rsp_valid||load_ready||done_valid||a_valid||b_valid)$fatal(1,"LOCAL_RESET_ADMISSION");
  repeat(3)tick();reset=0;repeat(2)tick();
  if(rsp_valid||done_valid||a_valid||b_valid)$fatal(1,"LOCAL_RESET_STALE");
 endtask
 task automatic configure(input integer rows,input integer tiles,input bit bw,input bit rb,input bit error);
  load_rows=4'(rows);load_tiles=3'(tiles);load_b_wide=bw;load_reuse_b=rb;
  expected_rows=rows;expected_tiles=tiles;expected_wide=int'(bw);expected_reuse=int'(rb);expected_error=error;
  n_base=int'(load_a_base);w_base=int'(load_b_base);ac=0;bc=0;
 endtask
 task automatic load_job(input integer hold_cycles);
  load_valid=1;do @(posedge clk);while(!load_ready);@(negedge clk);load_valid=0;
  repeat(hold_cycles)tick();
  a_ready=1;b_ready=1;
  while(!done_valid)tick();
  if(done_error!==expected_error||ac!=(expected_error?0:expected_rows*expected_tiles)||
     bc!=(expected_error||expected_reuse?0:expected_tiles*(expected_wide?2:1)))$fatal(1,"LOCAL_COMPLETION_EARLY_OR_ERROR");
  repeat(4)begin
   if(!done_valid||done_error!==expected_error||a_valid||b_valid)$fatal(1,"LOCAL_DONE_STABILITY");tick();
  end
  done_take=1;tick();done_take=0;a_ready=0;b_ready=0;
 endtask
 integer c0,n0,w0,o0;
 initial begin
  reset_group();
  for(integer i=0;i<1024;i=i+1)write_word(10'(i),{96'b0,32'(300+i)});
  drain();configure(8,2,0,0,0);
  c0=cycles;n0=np;w0=wide_commands;o0=write_owned;
  fork
   load_job(32);
   begin for(integer i=0;i<64;i=i+1)write_word(10'(256+i),128'(9000+i));end
  join
  drain();
  if(np-n0!=64||wide_commands-w0!=6||(BANK_RW&&write_owned-o0==0)||(!BANK_RW&&write_owned-o0!=0))$fatal(1,"LOCAL_CONCURRENT_ACCOUNTING");
  $display("POPT_LOCAL_MEASURE bank_rw=%0d reuse_a=%0d cycles=%0d narrow_writes=64 wide_reads=6 A_beats=16 B_beats=2 writes_while_load_owned=%0d",BANK_RW,REUSE_A,cycles-c0,write_owned-o0);
  // The whole LOAD range, not merely the currently gathered line, is leased.
  configure(8,2,1,0,0);
  fork load_job(12);write_word(10'd7,128'h7654);join drain();
  configure(4,1,0,0,0);
  fork load_job(12);write_word(10'd65,128'habcd);join drain();
  // Default rows0 is invalid. With explicit A reuse, B-only leaves A's
  // address range empty while the complete B input range remains protected.
  configure(0,1,0,0,!REUSE_A);o0=write_owned;
  fork load_job(24);write_word(10'd0,128'h4321);join drain();
  if(BANK_RW&&REUSE_A&&write_owned-o0==0)$fatal(1,"BONLY_A_RANGE_NOT_EMPTY");
  configure(0,1,0,1,1);load_job(0);
  // Held feeder data plus held ordinary ACK are cancelled by whole reset.
  configure(8,2,0,0,0);load_valid=1;
  do @(posedge clk);while(!load_ready);@(negedge clk);load_valid=0;
  if(BANK_RW)begin
   rsp_ready=0;write_word(10'd500,128'h9876);while(!rsp_valid)tick();
  end
  while(!a_valid&&!b_valid)tick();repeat(5)tick();reset_group();
  read_word(10'd7);drain();configure(4,1,0,0,0);load_job(0);
  $display("POPT_LOCAL_PASS bank_rw=%0d reuse_a=%0d load_range_guard=1 rows0_contract=1 feeder_scoreboard=1 done_ack=1 reset=1",BANK_RW,REUSE_A);
  $finish;
 end
 initial begin #3000000;$fatal(1,"LOCAL_TIMEOUT");end
endmodule
