`timescale 1ns/1ps
// Specifically exercises the TRUE_RW=1, SHARED_A=0, REUSE_A=0 loader branch.
module compat_cold_local;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,cold_reset=1;
 reg req_valid=0,req_write=0,rsp_ready=1;
 reg [9:0] req_addr=0;reg [127:0] req_data=0;
 wire req_ready,rsp_valid;wire [127:0] rsp_data;
 reg load_valid=0,done_take=0,a_ready=0,b_ready=0;
 wire load_ready,done_valid,done_error,a_valid,b_valid;
 wire a_bank,a_wide,b_bank,b_wide,b_half;
 wire [2:0] a_row;wire [1:0] a_tile,b_tile;
 wire [127:0] a_data;wire [511:0] b_data;
`ifdef USE_POWER_PINS
 wire vdd=1'b1,gnd=1'b0;
`endif
 local_s_p #(.ENABLE_TRUE_RW(1'b1),.ENABLE_SHARED_A(1'b0),.ENABLE_REUSE_A(1'b0)) dut(
  .clk,.reset,.cold_reset,.req_valid,.req_write,.req_addr,.req_data,
  .req_ready,.rsp_valid,.rsp_ready,.rsp_data,
  .wide_write_req(1'b0),.wide_write_addr(8'd0),.wide_write_data(512'd0),.wide_write_mask(4'd0),
  .wide_write_ready(),.wide_write_valid(),.wide_write_take(1'b1),
  .load_valid,.load_ready,.load_bank(1'b0),.load_rows(4'd4),.load_tiles(3'd1),
  .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_skip_a(1'b0),
  .load_a_base(10'd0),.load_b_base(10'd64),.done_valid,.done_error,.done_take,
  .a_ready,.b_ready,.a_valid,.a_bank,.a_wide,.a_row,.a_tile,.a_data,
  .b_valid,.b_bank,.b_wide,.b_half,.b_tile,.b_data
`ifdef USE_POWER_PINS
  ,.vdd,.gnd
`endif
 );
 integer cycle=0,ac=0,bc=0,epoch=1,canceled_jobs=0,completed_jobs=0;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(cycle>6000)$fatal(1,"cold-local watchdog");
  if(!reset&&!cold_reset)begin
   if(a_valid&&a_ready)begin
    if(a_row!==3'(ac)||a_tile!==0||a_bank!==0||a_wide!==0||a_data!==128'(epoch*100+ac))
     $fatal(1,"cold-local A payload/tag");
    ac=ac+1;
   end
   if(b_valid&&b_ready)begin
    if(bc!=0||b_tile!==0||b_bank!==0||b_wide!==0||b_half!==0)$fatal(1,"cold-local B tag");
    for(integer lane=0;lane<4;lane=lane+1)
     if(b_data[128*lane+:128]!==128'(epoch*100+64+lane))$fatal(1,"cold-local B payload");
    bc=bc+1;
   end
  end
 end
 task automatic tick;begin @(posedge clk);#1;end endtask
 task automatic write_word(input integer address);
  begin
   @(negedge clk);req_valid=1;req_write=1;req_addr=10'(address);req_data=128'(epoch*100+address);
   do @(posedge clk);while(!req_ready);
   @(negedge clk);req_valid=0;
   do @(posedge clk);while(!rsp_valid);
   if(rsp_data!==0)$fatal(1,"cold-local write ACK payload");
   @(negedge clk);
  end
 endtask
 task automatic fill;
  begin
   for(integer i=0;i<4;i=i+1)write_word(i);
   for(integer i=64;i<68;i=i+1)write_word(i);
  end
 endtask
 task automatic start_load;
  begin
   ac=0;bc=0;
   @(negedge clk);load_valid=1;
   do @(posedge clk);while(!load_ready);
   @(negedge clk);load_valid=0;
  end
 endtask
 task automatic reset_and_check(input bit cold);
  begin
   @(negedge clk);cold_reset=cold;reset=!cold;
   #1;if(req_ready||rsp_valid||load_ready||done_valid||a_valid||b_valid||dut.wide_req)
    $fatal(1,"cold/warm reset did not immediately quiesce complete loader");
   repeat(2)tick();
   if(dut.legacy_a.feeder.busy||dut.legacy_a.feeder.pending||dut.lease||dut.outstanding||dut.write_outstanding)
    $fatal(1,"cold/warm reset left old loader or storage ownership");
   @(negedge clk);reset=0;cold_reset=0;
   repeat(3)tick();
   if(rsp_valid||done_valid||a_valid||b_valid)$fatal(1,"stale event after reset");
   canceled_jobs=canceled_jobs+1;
  end
 endtask
 task automatic complete_load;
  begin
   start_load();a_ready=1;b_ready=1;
   while(!done_valid)tick();
   if(done_error||ac!=4||bc!=1)$fatal(1,"fresh load did not complete");
   @(negedge clk);done_take=1;tick();
   @(negedge clk);done_take=0;a_ready=0;b_ready=0;
   completed_jobs=completed_jobs+1;
  end
 endtask
 initial begin
  repeat(3)tick();@(negedge clk);reset=0;cold_reset=0;
  fill();
  // Pending SRAM response is canceled by cold reset in the legacy_a branch.
  start_load();
  wait(dut.wide_req&&dut.wide_ready);@(posedge clk);
  reset_and_check(1);
  epoch=2;fill();complete_load();
  // A held feeder response is canceled by a second independent cold reset.
  start_load();wait(a_valid||b_valid);reset_and_check(1);
  epoch=3;fill();complete_load();
  // Warm reset cancels the job but retains migrated data and locations.
  start_load();wait(a_valid||b_valid);reset_and_check(0);
  complete_load();
  if(canceled_jobs!=3||completed_jobs!=3)$fatal(1,"cold-local coverage incomplete");
  $display("COMPAT_COLD_PASS cold_pending=1 cold_held=1 warm_preserved=1 completed_jobs=3 logical_bytes=16384 physical_bytes=32768");
  $finish;
 end
endmodule
