// All simulation delays use the runner's common timescale.
// Every implementation has its own legal source and reference queue. Different
// ready timing changes admission, so cycle-by-cycle output equality is wrong.
module elastic_case #(
 parameter integer WIDTH=135,
 parameter bit OLD=1'b0
)(input wire clk,output reg done=0);
 reg reset=1,src_valid=0,dst_ready=0;
 reg [WIDTH-1:0] src_data=0;
 wire src_ready,dst_valid,empty;
 wire [WIDTH-1:0] dst_data;
 generate if(OLD) begin: old_dut
  pj_feed_hold #(.WIDTH(WIDTH)) dut(.*);
  assign empty=!dst_valid;
 end else begin: new_dut
  pj_feed_elastic #(.WIDTH(WIDTH)) dut(.*);
 end endgenerate

 reg [WIDTH-1:0] reference_queue[$];
 reg [WIDTH-1:0] expected,held_output,held_source;
 integer sent=0,received=0,discarded=0,phase=0;
 integer throughput_cycles=0,throughput_received=0;
 integer simultaneous=0,full_seen=0,stalls=0,reset_cycles=0;
 reg was_stalled=0,source_was_stalled=0,last_push=0;
 reg [31:0] random_state=32'h247e1a57 ^ 32'(WIDTH) ^ 32'(OLD);

 function automatic [WIDTH-1:0] payload(input integer token);
  reg [31:0] mixed;
  begin
   for(integer bit_index=0;bit_index<WIDTH;bit_index=bit_index+1) begin
    mixed=32'(token)*32'h9e3779b9 ^ 32'(bit_index/32)*32'h85ebca6b ^ 32'(WIDTH);
    payload[bit_index]=mixed[bit_index%32];
   end
  end
 endfunction
 function automatic [31:0] advance_random(input [31:0] value);
  reg [31:0] x;
  begin x=value^(value<<13);x=x^(x>>17);advance_random=x^(x<<5);end
 endfunction

 always @(posedge clk) begin
  if(reset) begin
   discarded=discarded+reference_queue.size();reference_queue.delete();
   was_stalled=0;source_was_stalled=0;last_push=0;reset_cycles=reset_cycles+1;
   if(!OLD && (src_ready || dst_valid || !empty))
    $fatal(1,"ELASTIC_RESET_MASK width=%0d",WIDTH);
  end else begin
   if(dst_valid !== (reference_queue.size()!=0))
    $fatal(1,"VALID_REFERENCE width=%0d old=%0d depth=%0d",WIDTH,OLD,reference_queue.size());
   if(empty !== (reference_queue.size()==0))
    $fatal(1,"EMPTY_REFERENCE width=%0d old=%0d",WIDTH,OLD);
   if(!OLD && src_ready !== (reference_queue.size()<2))
    $fatal(1,"READY_REFERENCE width=%0d",WIDTH);
   if(was_stalled && (!dst_valid || dst_data !== held_output))
    $fatal(1,"OUTPUT_CHANGED_UNDER_STALL width=%0d old=%0d",WIDTH,OLD);
   if(source_was_stalled && (!src_valid || src_data !== held_source))
    $fatal(1,"BENCH_SOURCE_PROTOCOL width=%0d old=%0d",WIDTH,OLD);
   if(phase==1) begin
    throughput_cycles=throughput_cycles+1;
    if(dst_valid && dst_ready) throughput_received=throughput_received+1;
   end
   if(reference_queue.size()==2) full_seen=full_seen+1;
   if(src_valid && src_ready && dst_valid && dst_ready) simultaneous=simultaneous+1;
   if(dst_valid && !dst_ready) stalls=stalls+1;
   was_stalled=dst_valid && !dst_ready;held_output=dst_data;
   source_was_stalled=src_valid && !src_ready;held_source=src_data;
   if(dst_valid && dst_ready) begin
    if(reference_queue.size()==0) $fatal(1,"REFERENCE_UNDERFLOW");
    expected=reference_queue.pop_front();
    if(dst_data !== expected) $fatal(1,"DATA_ORDER width=%0d old=%0d received=%0d",WIDTH,OLD,received);
    received=received+1;
   end
   last_push=src_valid && src_ready;
   if(last_push) begin reference_queue.push_back(src_data);sent=sent+1;end
   if(reference_queue.size()>(OLD?1:2)) $fatal(1,"CAPACITY width=%0d old=%0d",WIDTH,OLD);
   if(sent!=received+discarded+reference_queue.size()) $fatal(1,"CONSERVATION");
  end
 end

 // Drive only at falling edges. Toggle sink-ready between edges to verify
 // source-ready does not depend on it; sample handshakes at rising edges.
 task automatic tick(input bit valid_request,input bit ready_request,
                     input bit reset_request,input integer next_phase);
  reg ready_snapshot;
  begin
   @(negedge clk);
   reset=reset_request;phase=next_phase;dst_ready=ready_request;
   if(reset_request) begin src_valid=1;src_data=payload(sent);end
   else if(!src_valid || last_push) begin src_valid=valid_request;src_data=payload(sent);end
   #1;ready_snapshot=src_ready;dst_ready=!ready_request;
   #1;
   if(!OLD && src_ready !== ready_snapshot) $fatal(1,"COMBINATIONAL_SINK_READY_PATH width=%0d",WIDTH);
   dst_ready=ready_request;
   @(posedge clk);#1;
   if(reset_request && dst_valid) $fatal(1,"RESET_VALID_NOT_CLEARED width=%0d old=%0d",WIDTH,OLD);
  end
 endtask

 initial begin
  repeat(3) tick(0,0,1,0);
  // A reset cancels any held source request; explicitly deassert while reset.
  @(negedge clk);src_valid=0;
  tick(0,1,0,0);
  tick(1,1,0,0); // Prime one output before the measured steady-state interval.
  repeat(256) tick(1,1,0,1);
  repeat(8) tick(0,1,0,0);
  if(throughput_cycles!=256 || throughput_received!=(OLD?128:256))
   $fatal(1,"THROUGHPUT width=%0d old=%0d cycles=%0d received=%0d",WIDTH,OLD,throughput_cycles,throughput_received);
  // Fill, retain under a long stall, recover, and drain.
  repeat(8) tick(1,0,0,2);
  repeat(5) tick(0,0,0,2);
  repeat(10) tick(0,1,0,2);
  // Reset with occupied slots and an asserted source. Invalid payload must
  // never emerge in the next epoch; source admission is blocked in reset.
  repeat(4) tick(1,0,0,3);
  repeat(2) tick(1,0,1,3);
  @(negedge clk);src_valid=0;
  tick(0,1,0,3);
  for(integer cycle_index=0;cycle_index<2000;cycle_index=cycle_index+1) begin
   random_state=advance_random(random_state);
   tick(random_state[0] || random_state[3],random_state[5] || random_state[9],
        cycle_index==501 || cycle_index==502 || cycle_index==1457 || cycle_index==1458,4);
  end
  repeat(12) tick(0,1,0,0);
  if(reference_queue.size()!=0 || dst_valid || sent!=received+discarded)
   $fatal(1,"FINAL_DRAIN width=%0d old=%0d",WIDTH,OLD);
  if(stalls==0 || discarded==0 || reset_cycles<7) $fatal(1,"COVERAGE_COMMON");
  if(!OLD && (full_seen==0 || simultaneous<256)) $fatal(1,"COVERAGE_ELASTIC");
  if(OLD && simultaneous!=0) $fatal(1,"OLD_UNEXPECTED_SIMULTANEOUS");
  $display("ELASTIC_CASE_PASS width=%0d old=%0d cycles=%0d throughput_beats=%0d sent=%0d received=%0d reset_discarded=%0d stalls=%0d full_cycles=%0d simultaneous=%0d",WIDTH,OLD,throughput_cycles,throughput_received,sent,received,discarded,stalls,full_seen,simultaneous);
  done=1;
 end
endmodule

module load_completion_case(input wire clk,output reg done=0);
 reg reset=1,a_valid=0,b_valid=0,a_take=0,b_take=0,enable_done=0;
 wire a_ready,b_ready,a_out_valid,b_out_valid,a_empty,b_empty;
 wire [134:0] a_data;
 wire [516:0] b_data;
 reg completed=0;
 bit unsafe_gate;
 initial unsafe_gate=$test$plusargs("NEGATIVE_READY_EMPTY");
 pj_feed_elastic #(.WIDTH(135)) a(.clk,.reset,.src_valid(a_valid),.src_ready(a_ready),
   .src_data(135'h12345),.dst_valid(a_out_valid),.dst_ready(a_take),.dst_data(a_data),.empty(a_empty));
 pj_feed_elastic #(.WIDTH(517)) b(.clk,.reset,.src_valid(b_valid),.src_ready(b_ready),
   .src_data(517'h98765),.dst_valid(b_out_valid),.dst_ready(b_take),.dst_data(b_data),.empty(b_empty));
 wire feeder_done=enable_done && !completed;
 wire correct_take=feeder_done && a_empty && b_empty;
 wire old_ready_predicate=feeder_done && a_ready && b_ready;
 wire tested_take=unsafe_gate ? old_ready_predicate : correct_take;
 always @(posedge clk) begin
  if(reset) completed<=0;
  else begin
   if(tested_take && (!a_empty || !b_empty)) begin
    $display("EXPECTED_NEGATIVE_READY_AS_EMPTY_DETECTED");
    $fatal(1,"LOAD_COMPLETION_BEFORE_OUTPUT_RETIREMENT");
   end
   if(tested_take) completed<=1;
  end
 end
 initial begin
  repeat(3) @(negedge clk);
  reset=0;a_valid=1;b_valid=1;
  @(negedge clk);a_valid=0;b_valid=0;enable_done=1;#1;
  // One beat per channel: both are not-full but neither is empty.
  if(!a_ready || !b_ready || a_empty || b_empty || !a_out_valid || !b_out_valid)
   $fatal(1,"LOAD_GATE_SETUP");
  if(!old_ready_predicate || correct_take) $fatal(1,"NEGATIVE_PREDICATE_NOT_EXERCISED");
  repeat(4) @(negedge clk);
  if(completed) $fatal(1,"LOAD_COMPLETION_DURING_STALL");
  a_take=1;
  @(negedge clk);a_take=0;
  if(!a_empty || b_empty || correct_take || completed) $fatal(1,"B_STILL_PENDING");
  if(b_data!==517'h98765) $fatal(1,"B_PAYLOAD_CHANGED");
  b_take=1;
  @(negedge clk);b_take=0;
  if(!a_empty || !b_empty || !correct_take || completed) $fatal(1,"LAST_BEAT_RETIREMENT");
  @(negedge clk);
  if(!completed || correct_take || feeder_done) $fatal(1,"LOAD_COMPLETION_NOT_ACKNOWLEDGED");
  $display("LOAD_EXPLICIT_EMPTY_PASS negative_ready_predicate_exercised=1 a=%h",a_data);
  done=1;
 end
endmodule

module bench_compare;
 reg clk=0;
 always #5 clk=~clk;
 wire [4:0] done;
 elastic_case #(.WIDTH(135),.OLD(1)) old_a(clk,done[0]);
 elastic_case #(.WIDTH(135),.OLD(0)) new_a(clk,done[1]);
 elastic_case #(.WIDTH(517),.OLD(1)) old_b(clk,done[2]);
 elastic_case #(.WIDTH(517),.OLD(0)) new_b(clk,done[3]);
 load_completion_case completion(clk,done[4]);
 initial begin
  wait(&done);
  $display("ELASTIC_COMPARE_PASS cases=4 load_explicit_empty=1 widths=135,517");
  $finish;
 end
 initial begin
  repeat(10000) @(posedge clk);
  $fatal(1,"ELASTIC_COMPARE_WATCHDOG");
 end
endmodule
