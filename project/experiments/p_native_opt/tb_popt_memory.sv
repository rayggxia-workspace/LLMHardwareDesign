module tb_popt_memory #(parameter bit BANK_RW=1'b1);
 reg clk=0;always #5 clk=~clk;
 reg reset=1,req=0,wr=0,take=1,wide_req=0,wide_take=1;
 reg [9:0] addr=0;reg [127:0] din=0;reg [7:0] wide_addr=0;
 wire ready,valid,wide_ready,wide_valid;
 wire [127:0] dout;wire [511:0] wide_dout;
 wire parallel_physical;wire [3:0] physical_w_mask;wire physical_n;
 generate if(BANK_RW)begin: banked
  block_feed_s16k_bank_rw #(.ECHO_WRITE_DATA(1'b0)) dut(.*);
  assign physical_w_mask=dut.w_issue_mask;assign physical_n=dut.n_fire;
  assign parallel_physical=dut.n_fire&&(|dut.w_issue_mask);
  always @(posedge clk) if(!reset && (dut.n_mask&dut.w_issue_mask)!=0) $fatal(1,"BANK_DOUBLE_OWNED");
 end else begin: baseline
  block_feed_s16k_sram #(.ECHO_WRITE_DATA(1'b0)) dut(.*);
  assign physical_w_mask=dut.w_fire?4'b1111:4'b0000;assign physical_n=dut.n_fire;
  assign parallel_physical=0;
 end endgenerate
 reg [127:0] reference_words[0:1023],n_expected[0:8191];
 reg [511:0] w_expected[0:2047];
 integer np=0,nc=0,wp=0,wc=0,cycles=0,parallel_cycles=0,bank_ops=0;
 integer n_wait=0,w_wait=0,max_n_wait=0,max_w_wait=0;
 reg monitor_fair=0,stall_n=0,stall_w=0;
 reg [127:0] old_n;reg [511:0] old_w;
 always @(posedge clk)begin
  cycles=cycles+1;
  if(reset)begin np=0;nc=0;wp=0;wc=0;stall_n=0;stall_w=0;n_wait=0;w_wait=0;end
  else begin
   if(stall_n&&(!valid||dout!==old_n))$fatal(1,"N_RESPONSE_STABILITY");
   if(stall_w&&(!wide_valid||wide_dout!==old_w))$fatal(1,"W_RESPONSE_STABILITY");
   stall_n=valid&&!take;old_n=dout;stall_w=wide_valid&&!wide_take;old_w=wide_dout;
   if(wide_req&&wide_ready)begin
    for(integer b=0;b<4;b=b+1)w_expected[wp][128*b+:128]=reference_words[{wide_addr,2'b00}+10'(b)];
    wp=wp+1;
   end
   if(req&&ready)begin
    n_expected[np]=wr?128'b0:reference_words[addr];np=np+1;
    if(wr)reference_words[addr]=din;
   end
   if(valid&&take)begin
    if(nc>=np||dout!==n_expected[nc])$fatal(1,"N_RESPONSE_ORDER got=%h want=%h",dout,n_expected[nc]);
    nc=nc+1;
   end
   if(wide_valid&&wide_take)begin
    if(wc>=wp||wide_dout!==w_expected[wc])$fatal(1,"W_SNAPSHOT_OR_ORDER");wc=wc+1;
   end
   if(parallel_physical)parallel_cycles=parallel_cycles+1;
   bank_ops=bank_ops+int'(physical_n)+$countones(physical_w_mask);
   if(monitor_fair)begin
    n_wait=req&&!ready?n_wait+1:0;w_wait=wide_req&&!wide_ready?w_wait+1:0;
    if(n_wait>max_n_wait)max_n_wait=n_wait;if(w_wait>max_w_wait)max_w_wait=w_wait;
    if(BANK_RW&&(n_wait>6||w_wait>6))$fatal(1,"BOUNDED_FAIRNESS");
   end
  end
 end
 task automatic tick;@(posedge clk);@(negedge clk);endtask
 task automatic send_n(input bit write_word,input [9:0] address,input [127:0] value);
  req=1;wr=write_word;addr=address;din=value;
  do @(posedge clk);while(!ready);@(negedge clk);req=0;
 endtask
 task automatic send_w(input [7:0] line);
  wide_req=1;wide_addr=line;do @(posedge clk);while(!wide_ready);@(negedge clk);wide_req=0;
 endtask
 task automatic drain;
  while(nc!=np||wc!=wp)tick();tick();
 endtask
 task automatic reset_group;
  reset=1;req=0;wide_req=0;take=1;wide_take=1;monitor_fair=0;
  #1;if(ready||valid||wide_ready||wide_valid||physical_n||physical_w_mask!=0)$fatal(1,"RESET_ADMISSION");
  repeat(3)tick();reset=0;repeat(2)tick();
  if(valid||wide_valid)$fatal(1,"RESET_STALE_RESPONSE");
 endtask
 integer c0,n0,w0,p0,b0;
 initial begin
  reset_group();
  for(integer i=0;i<1024;i=i+1)send_n(1,10'(i),{96'b0,32'(i+100)});
  drain();
  // No conflict: a wide command must retain the original one-return-stage
  // latency, and all four real banks are selected on its acceptance edge.
  c0=cycles;send_w(8'd8);
  while(!wide_valid)tick();
  if(cycles-c0!=2)$fatal(1,"UNCONTENDED_WIDE_LATENCY got=%0d",cycles-c0);
  drain();
  // Wide line10 and ordinary write word40 collide. The complete wide
  // snapshot precedes the write; holding the reply must not hold its row lock.
  wide_take=0;
  fork send_w(8'd10);send_n(1,10'd40,128'h123456);join
  while(!wide_valid)tick();repeat(8)tick();
  take=1;while(nc!=np)tick();wide_take=1;drain();
  // Independently stalled response ownership. A held wide reply cannot block
  // writes; a full narrow response queue cannot block subsequent wide reads.
  wide_take=0;send_w(8'd20);while(!wide_valid)tick();
  for(integer i=0;i<8;i=i+1)send_n(1,10'(400+i),128'(i+99));
  while(nc!=np)tick();if(!wide_valid)$fatal(1,"LOST_HELD_WIDE");wide_take=1;drain();
  take=0;send_n(0,10'd400,0);send_n(0,10'd401,0);repeat(3)tick();
  req=1;wr=0;addr=402;repeat(4)begin if(ready)$fatal(1,"N_RESERVATION_OVERFLOW");tick();end
  for(integer i=0;i<8;i=i+1)send_w(8'(30+i));
  while(wc!=wp)tick();take=1;
  do @(posedge clk);while(!ready);@(negedge clk);req=0;drain();
  // Saturated same-bank contention, both sinks always available. No timing
  // oracle: each driver advances only on its own real request handshake.
  c0=cycles;n0=np;w0=wp;p0=parallel_cycles;b0=bank_ops;monitor_fair=1;
  fork
   begin for(integer i=0;i<64;i=i+1)send_n(i[0],10'(512+4*(i%16)),128'(2000+i));end
   begin for(integer i=0;i<32;i=i+1)send_w(8'(160+i%16));end
  join
  monitor_fair=0;drain();
  if(np-n0!=64||wp-w0!=32||bank_ops-b0!=192|| (BANK_RW&&parallel_cycles-p0==0))$fatal(1,"PHYSICAL_TRANSACTION_ACCOUNTING");
  $display("POPT_MEMORY_MEASURE bank_rw=%0d cycles=%0d narrow=64 wide=32 bank_operations=192 parallel_cycles=%0d max_n_wait=%0d max_w_wait=%0d",BANK_RW,cycles-c0,parallel_cycles-p0,max_n_wait,max_w_wait);
  // Deterministic pseudorandom source/sink traffic; requests remain stable
  // while stalled. Explicit independent response backpressure is applied.
  fork
   begin for(integer i=0;i<80;i=i+1)begin repeat(i%3)tick();send_n((i%3)!=0,10'((i*73)%1024),128'(7000+i));end end
   begin for(integer i=0;i<40;i=i+1)begin repeat(i%4)tick();send_w(8'((i*29)%256));end end
   begin for(integer i=0;i<500;i=i+1)begin take=(i%7)!=2;wide_take=(i%11)>2;tick();end take=1;wide_take=1;end
  join
  drain();
  // Reset with held narrow+wide replies drops ownership, never SRAM contents.
  take=0;wide_take=0;fork send_n(0,10'd40,0);send_w(8'd10);join
  while(!valid||!wide_valid)tick();repeat(3)tick();reset_group();
  send_n(0,10'd40,0);send_w(8'd10);drain();
  $display("POPT_MEMORY_PASS bank_rw=%0d scoreboards=2 snapshot=1 response_stability=1 reservation=1 fairness=1 reset=1",BANK_RW);
  $finish;
 end
 initial begin #3000000;$fatal(1,"MEMORY_TIMEOUT");end
endmodule
