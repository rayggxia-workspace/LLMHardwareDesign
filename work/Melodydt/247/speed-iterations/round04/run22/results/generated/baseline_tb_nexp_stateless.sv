// Native state preservation uses the actual N, without peeking at simulation time.
module tb_nexp_stateless;
 localparam integer LANES=2;
 reg clk=0,reset=1;always #5 clk=~clk;
 reg cv=0,take=0;reg [3:0] op=0,count=0;reg [31:0] param=0;
 reg [127:0] data=0,aux=0;wire ready,valid,error,sat;wire [127:0] answer;
 integer checks=0,cases=0;
 block_v2_n #(.NEXP_DIRECT(1)) dut(.clk,.reset,.cmd_valid(cv),.cmd_ready(ready),.cmd_op(op),.cmd_count(count),
  .cmd_param(param),.cmd_data(data),.cmd_aux(aux),.rsp_valid(valid),.rsp_ready(take),.rsp_data(answer),.rsp_error(error),.rsp_saturated(sat),.busy());
 function automatic [4095:0] persistent;
  reg [4095:0] bits;
  begin
   bits=4096'({dut.mode,dut.context_valid,dut.statistics_final,dut.factor_valid,dut.epsilon,dut.factor,dut.exp_sum,
    dut.count,dut.exp_count,dut.replayed,dut.sum,dut.sumsq,dut.maximum,dut.minimum,
    dut.selected,dut.top_count,dut.scan_index,dut.best_index,dut.top_k,dut.top_round,dut.top_loading,dut.best_valid,
    dut.best_value,dut.best_id,dut.chosen});
   for(integer i=0;i<40;i++)bits={bits[4063:0],dut.top_id[i],dut.top_score[i]};
   persistent=bits;
  end
 endfunction
 task automatic command(input [3:0] operation,input [3:0] n,input [31:0] configuration,
   input [127:0] operand,input [127:0] other,input bit expected_error,input integer hold_cycles,output [127:0] got);
  integer guard;reg [127:0] held;reg held_error,held_sat;
  begin
   @(negedge clk);cv=1;op=operation;count=n;param=configuration;data=operand;aux=other;take=0;guard=0;
   do begin @(posedge clk);guard++;if(guard>1024)$fatal(1,"native accept timeout");end while(!ready);
   @(negedge clk);cv=0;op=15;data=~operand;aux=~other;guard=0;
   do begin @(negedge clk);guard++;if(guard>1024)$fatal(1,"native response timeout");end while(!valid);
   if(error!==expected_error)$fatal(1,"native error op=%0d",operation);
   got=answer;held=answer;held_error=error;held_sat=sat;
   repeat(hold_cycles)begin
    @(negedge clk);if(!valid||ready||answer!==held||error!==held_error||sat!==held_sat)$fatal(1,"native response stability");
   end
   take=1;@(posedge clk);@(negedge clk);take=0;checks++;
  end
 endtask
 task automatic probe;
  reg [4095:0] before_state;reg [127:0] got,operand;
  begin
   before_state=persistent();operand={16'sd32767,16'sd1,16'sd0,-16'sd1,-16'sd8192,-16'sd16384,-16'sd20000,16'sh8000};
   command(12,8,0,operand,0,0,4,got);
   if(persistent()!==before_state)$fatal(1,"op12 modified persistent N state");
   if(got[15:0]!==0||got[31:16]!==0||got[127:112]!==16'd32768)$fatal(1,"op12 edge values");
   for(integer bad=0;bad<5;bad++)begin
    command(12,bad==0?0:bad==1?9:1,bad==2?1:0,bad==4?128'h10000:0,bad==3?1:0,1,2,got);
    if(got!==0||persistent()!==before_state)$fatal(1,"invalid op12 changed state/output");
   end
   cases++;
  end
 endtask
 reg [127:0] ignored,got,statistics;
 initial begin
  repeat(4)@(negedge clk);reset=0;
  // No context is required; arbitrary payload registers remain undisturbed.
  probe();
  command(0,0,0,0,0,0,0,ignored);
  command(1,8,0,{8{16'd10}},0,0,0,ignored);probe();
  command(7,0,0,0,0,0,0,statistics);command(2,0,0,0,0,0,0,ignored);probe();
  command(3,4,0,{4{32'h000a000a}},0,0,0,ignored);probe();
  command(3,4,0,{4{32'h000a000a}},0,0,0,ignored);command(4,0,0,0,0,0,0,ignored);probe();
  command(11,0,0,0,0,0,0,got);if(got[31:0]==0)$fatal(1,"factor setup");
  command(6,3,0,{80'd0,{3{16'd32768}}},0,0,0,ignored);probe();
  command(6,5,0,{48'd0,{5{16'd32768}}},0,0,0,ignored);probe();
  if(dut.replayed!=8)$fatal(1,"softmax replay cursor");
  command(0,0,1,1,0,0,0,ignored);command(1,8,0,{8{16'd10}},0,0,0,ignored);
  command(2,0,0,0,0,0,0,ignored);probe();
  command(5,3,0,{80'd0,{3{16'd10}}},{80'd0,{3{16'd1024}}},0,0,ignored);probe();
  command(5,5,0,{48'd0,{5{16'd10}}},{48'd0,{5{16'd1024}}},0,0,ignored);
  if(dut.replayed!=8)$fatal(1,"RMS replay cursor");
  command(8,0,2,0,0,0,0,ignored);
  command(9,4,0,{16'd4,16'sd30,16'd3,-16'sd7,16'd2,16'sd10,16'd1,16'sd20},0,0,0,ignored);probe();
  command(10,0,0,0,0,0,0,got);probe();
  // Reset while op12 is executing, then while its output is held.
  for(integer delay_edges=0;delay_edges<12;delay_edges++)begin
   @(negedge clk);cv=1;op=12;count=8;param=0;data=0;aux=0;take=0;
   do @(posedge clk);while(!ready);@(negedge clk);cv=0;
   repeat(delay_edges)@(negedge clk);reset=1;repeat(2)@(negedge clk);reset=0;
   repeat(14)@(negedge clk);if(valid||!ready)$fatal(1,"op12 reset left ghost response");
   checks++;
  end
  probe();
  lane_report();
  $display("STATELESS_PASS cases=%0d checks=%0d reset_cases=12",cases,checks);$finish;
 end
 initial begin #20000000;$fatal(1,"stateless watchdog");end

 integer lane_pending=0,lane_count=0,lane_one_steps=0;
 integer lane_completed=0,lane_checked=0,lane_steps=0,lane_cycles=0;
 integer lane_hist[1:8];integer lane_hist_steps[1:8];
 initial for(integer i=1;i<=8;i++)begin lane_hist[i]=0;lane_hist_steps[i]=0;end
 always @(posedge clk)begin
  lane_cycles<=lane_cycles+1;
  if(reset)begin lane_pending=0;lane_one_steps=0;end
  else begin
   if(valid&&take&&lane_pending!=0)begin
    if(error)begin
     if(lane_one_steps!=0)$fatal(1,"invalid native op12 executed CALC");
    end else begin
     if(lane_count<1||lane_count>8||lane_one_steps!=(lane_count+LANES-1)/LANES)
      $fatal(1,"actual op12 CALC steps mismatch count=%0d lanes=%0d steps=%0d",lane_count,LANES,lane_one_steps);
     lane_completed++;lane_checked++;lane_steps+=lane_one_steps;
     lane_hist[lane_count]++;lane_hist_steps[lane_count]+=lane_one_steps;
    end
    lane_pending=0;
   end
   if(cv&&ready&&op==12)begin
    if(lane_pending!=0)$fatal(1,"overlapping native op12 ownership");
    lane_pending=1;lane_count=int'(count);lane_one_steps=0;
   end
   if(dut.phase==dut.CALC&&dut.operation==12)begin
    if(lane_pending==0)$fatal(1,"CALC without accepted op12");
    lane_one_steps++;
   end
  end
 end
 task automatic lane_report;
  begin
   $display("NEXP_LANE_PATH direct_mode=%0d direct_lanes=%0d op12_completed=%0d calc_steps=%0d checked_commands=%0d",1'b1,LANES,lane_completed,lane_steps,lane_checked);
   for(integer i=1;i<=8;i++)$display("NEXP_LANE_COUNT count=%0d commands=%0d calc_steps=%0d",i,lane_hist[i],lane_hist_steps[i]);
  end
 endtask
 // Passive trace is injected into BOTH exact-R2 and candidate tests. It adds
 // no stimulus/delay and compares all accepted native commands/responses.
 always @(posedge clk)if(!reset)begin
  if(dut.cmd_valid&&dut.cmd_ready)
   $display("R4_TRACE CMD c=%0d op=%0d count=%0d param=%h data=%h aux=%h",lane_cycles,dut.cmd_op,dut.cmd_count,dut.cmd_param,dut.cmd_data,dut.cmd_aux);
  if(dut.rsp_valid&&dut.rsp_ready)
   $display("R4_TRACE RSP c=%0d data=%h error=%0d sat=%0d",lane_cycles,dut.rsp_data,dut.rsp_error,dut.rsp_saturated);
 end
endmodule
