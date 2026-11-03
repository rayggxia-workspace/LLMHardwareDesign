`timescale 1ns/1ps
// Completion-register protocol only: no native AF or external side-effect proof.
module block_w5_completion_hold_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,in_valid=0,in_error=0,in_saturated=0,out_ready=0;
 reg [8:0] in_words=0;reg [31:0] in_generation=0;
 wire in_ready,out_valid,out_error,out_saturated,out_partial;
 wire [8:0] out_words;wire [31:0] out_generation;
 block_w5_completion_hold dut(.*);
 integer cycles=0,cases=0,accepted=0,retired=0,cancelled=0,credit=0;
 reg [43:0] expected=0,held_tuple=0;
 reg was_stalled=0;
 wire [43:0] output_tuple={out_error,out_saturated,out_partial,out_words,out_generation};
 task fail(input string why);$fatal(1,"FAIL_W5_COMPLETION_HOLD %s cycle=%0d",why,cycles);endtask
 always @(posedge clk)begin
  cycles=cycles+1;
  if(reset)begin
   if(credit)cancelled=cancelled+1;credit=0;was_stalled=0;
   if(in_ready||out_valid)fail("reset gates handshake");
  end else begin
   if(was_stalled&&(!out_valid||output_tuple!==held_tuple))fail("terminal changed while held");
   if(in_valid&&in_ready&&out_valid&&out_ready)fail("implicit fallthrough/replace");
   if(out_valid&&out_ready)begin
    if(credit!=1||output_tuple!==expected)fail("unexpected/duplicate terminal");
    retired=retired+1;credit=0;
   end
   if(in_valid&&in_ready)begin
    if(credit!=0)fail("overwrote pending event");
    accepted=accepted+1;credit=1;
    expected={in_error,in_saturated,(in_error&&(in_words!=0)),in_words,in_generation};
   end
   if(out_valid&&output_tuple!==expected)fail("captured tuple mismatch");
   was_stalled=out_valid&&!out_ready;held_tuple=output_tuple;
  end
  if(cycles>1000)fail("watchdog");
 end
 task ticks(input integer n);repeat(n)@(negedge clk);endtask
 task mark(input string id);begin cases=cases+1;$display("CASE_PASS %s",id);$fflush();end endtask
 task offer(input bit error,input bit sat,input [8:0] words,input [31:0] generation);
  begin
   @(negedge clk);in_valid=1;in_error=error;in_saturated=sat;in_words=words;in_generation=generation;
   if(!in_ready)fail("offer requires empty slot");
   @(posedge clk);@(negedge clk);in_valid=0;
   if(!out_valid||in_ready||output_tuple!=={error,sat,(error&&(words!=0)),words,generation})fail("capture did not hold");
  end
 endtask
 task consume;
  integer old_retired;
  begin
   old_retired=retired;out_ready=1;@(posedge clk);@(negedge clk);out_ready=0;
   if(out_valid||!in_ready||retired!=old_retired+1)fail("consume exactly once");
  end
 endtask
 initial begin
  ticks(3);reset=0;ticks(2);
  if(out_valid||!in_ready||accepted||retired)fail("empty reset state");mark("W5_HOLD_RESET_EMPTY");
  offer(0,0,0,32'h10203040);ticks(3);consume();mark("W5_HOLD_SUCCESS_ZERO_WORDS");
  offer(0,1,256,32'habcdef01);ticks(3);consume();mark("W5_HOLD_SUCCESS_256_SATURATED");
  offer(1,0,0,32'h201);ticks(3);consume();mark("W5_HOLD_ERROR_ZERO_NO_PARTIAL");
  offer(1,0,1,32'h202);
  in_error=0;in_saturated=1;in_words=256;in_generation=32'hdeadbeef;ticks(5);
  if(output_tuple!=={1'b1,1'b0,1'b1,9'd1,32'h202})fail("late prefix/error changes escaped holding");
  consume();mark("W5_HOLD_ERROR_PREFIX1_LATE_INPUT_CHANGE");
  offer(1,1,256,32'h203);
  in_error=0;in_saturated=0;in_words=0;in_generation=0;ticks(5);
  if(output_tuple!=={1'b1,1'b1,1'b1,9'd256,32'h203})fail("late poison convergence changed completion");
  consume();mark("W5_HOLD_ERROR_PREFIX256_LATE_INPUT_CHANGE");
  offer(0,0,128,32'h301);in_valid=1;in_error=1;in_saturated=1;in_words=1;in_generation=32'h302;
  ticks(5);if(in_ready||accepted-retired-cancelled!=1)fail("pending event overwritten");
  in_valid=0;consume();mark("W5_HOLD_BACKPRESSURE_REJECTS_OVERWRITE");
  offer(0,0,16,32'h401);in_valid=1;in_error=1;in_saturated=0;in_words=2;in_generation=32'h402;
  out_ready=1;@(posedge clk);@(negedge clk);
  if(out_valid||!in_ready||credit!=0)fail("same-edge replacement occurred");
  // The next distinct clock edge may accept the waiting event, not the prior one.
  out_ready=0;@(posedge clk);@(negedge clk);in_valid=0;
  if(!out_valid||out_generation!=32'h402||!out_partial)fail("next event was lost");
  consume();mark("W5_HOLD_NO_SAME_EDGE_REPLACEMENT");
  offer(1,0,1,32'h501);consume();out_ready=1;ticks(5);out_ready=0;
  if(credit||out_valid)fail("duplicate consume");mark("W5_HOLD_CONSUME_ONLY_ONCE");
  offer(0,1,256,32'h601);@(negedge clk);reset=1;in_valid=1;in_error=1;in_words=1;
  ticks(3);in_valid=0;reset=0;ticks(2);
  if(out_valid||!in_ready||credit)fail("reset did not cancel held event");mark("W5_HOLD_RESET_CANCELS_PENDING");
  // A ready sink must not consume an event before it has been registered.
  out_ready=1;@(negedge clk);in_valid=1;in_error=1;in_saturated=1;in_words=256;in_generation=32'h701;
  @(posedge clk);@(negedge clk);in_valid=0;
  if(!out_valid||credit!=1)fail("empty-slot fallthrough");
  @(posedge clk);@(negedge clk);out_ready=0;
  if(out_valid||credit)fail("ready-sink consumption");mark("W5_HOLD_REGISTERED_READY_SINK");
  offer(0,0,256,32'h801);ticks(4);consume();mark("W5_HOLD_RECOVERY_AFTER_RESET");
  if(cases!=12||credit!=0||accepted!=retired+cancelled)fail("global event conservation");
  $display("W5_HOLD_COUNTS accepted=%0d retired=%0d reset_cancelled=%0d",accepted,retired,cancelled);
  $display("PASS_W5_COMPLETION_HOLD cases=%0d",cases);$fflush();$finish;
 end
endmodule
