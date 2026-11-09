module tb_nexp_u;
 reg clk=0,reset=1;always #5 clk=~clk;
 integer ticks=0,reads=0,writes=0,core_accept=-1,core_response=-1,checks=0;
 reg [1:0] io_v=0,io_w=0,io_take=0;reg [19:0] io_addr=0;reg [255:0] io_data=0;
 wire [1:0] io_ready,io_rsp;wire [255:0] io_result;
 reg cv=0,cs=0,ct=0,cdirect=0;reg [39:0] cm=0;reg [1:0] sources=0;
 reg [19:0] src=0;reg [9:0] dst=32;
 wire cr,done,err,sat;wire [127:0] result;
 pu_u_group #(.NEXP_BATCH(1)) dut(
  .clk,.reset,.n_cmd_valid(cv),.n_cmd_store(cs),.n_cmd_direct(cdirect),.n_done_ready(ct),.n_cmd_ready(cr),
  .n_done_valid(done),.n_done_error(err),.n_done_saturated(sat),.n_cmd_meta(cm),.n_cmd_sources(sources),.n_cmd_src(src),.n_cmd_dst(dst),.n_done_data(result),
  .n_to_e_valid(),.n_to_e_ready(1'b1),.n_to_e_data(),
  .e_cmd_valid(1'b0),.e_cmd_store(1'b0),.e_cmd_direct_a(1'b0),.e_done_ready(1'b1),.e_cmd_ready(),.e_done_valid(),.e_done_error(),.e_done_saturated(),
  .e_cmd_sources(2'd0),.e_cmd_op(4'd0),.e_cmd_shift(5'd0),.e_cmd_src(30'd0),.e_cmd_dst(10'd0),.e_done_data(),
  .e_direct_a_valid(1'b0),.e_direct_a_abort(1'b0),.e_direct_a_ready(),.e_direct_a_data(128'd0),
  .io_req_valid(io_v),.io_req_write(io_w),.io_rsp_ready(io_take),.io_req_addr(io_addr),.io_req_data(io_data),
  .io_req_ready(io_ready),.io_rsp_valid(io_rsp),.io_rsp_data(io_result));
 always @(posedge clk)begin
  ticks<=ticks+1;
  if(!reset)begin
   if(dut.request[0]&&dut.accept[0])begin if(dut.write[0])writes=writes+1;else reads=reads+1;end
   if(dut.n_valid&&dut.n_ready)core_accept=ticks;
   if(dut.nr_valid&&dut.nr_ready)core_response=ticks;
  end
 end
 task automatic access(input bit wr,input [9:0] address,input [127:0] data,output [127:0] got);
  integer guard;
  begin
   @(negedge clk);io_v=1;io_w={1'b0,wr};io_addr={10'd0,address};io_data={128'd0,data};io_take=0;guard=0;
   do begin @(posedge clk);guard++;if(guard>512)$fatal(1,"IO accept timeout");end while(!io_ready[0]);
   @(negedge clk);io_v=0;io_take=1;guard=0;
   do begin @(posedge clk);guard++;if(guard>512)$fatal(1,"IO response timeout");end while(!io_rsp[0]);
   got=io_result[127:0];@(negedge clk);io_take=0;
  end
 endtask
 task automatic command(input [3:0] op,input [3:0] count,input [31:0] param,input [1:0] arity,
                        input bit store,input bit direct,input [19:0] address,input bit expected_error,
                        input integer stall,input bit measure,input bit mode32,output [127:0] got);
  integer accepted,finished,guard,old_reads,old_writes;reg [127:0] held;
  begin
   @(negedge clk);cv=1;cm={param,count,op};sources=arity;cs=store;cdirect=direct;src=address;ct=0;
   core_accept=-1;core_response=-1;old_reads=reads;old_writes=writes;guard=0;
   do begin @(posedge clk);guard++;if(guard>2048)$fatal(1,"U command accept timeout");end while(!cr);
   accepted=ticks;
   @(negedge clk);cv=0;cm=~cm;src=~address;guard=0;
   do begin @(posedge clk);guard++;if(guard>2048)$fatal(1,"U command completion timeout");end while(!done);
   finished=ticks;got=result;held=result;
   if(err!==expected_error||(!expected_error&&sat))$fatal(1,"U completion error op=%0d count=%0d goterror=%b",op,count,err);
   if(measure)begin
    if(core_accept<accepted||core_response<core_accept||reads-old_reads!=1||writes-old_writes!=1)$fatal(1,"U service accounting");
    $display("NEXP_FULL_U mode32=%0d count=%0d accepted_to_done_cycles=%0d input_stage_cycles=%0d compute_stage_cycles=%0d output_stage_cycles=%0d S_reads=%0d S_writes=%0d",
     mode32,count,finished-accepted,core_accept-accepted,core_response-core_accept,finished-core_response,reads-old_reads,writes-old_writes);
   end
   repeat(stall)begin
    // Publish an ordinary op while the batch owns completion. It must wait.
    cv=1;cm=0;sources=0;cs=0;cdirect=0;
    @(negedge clk);if(!done||result!==held||cr)$fatal(1,"held U response/lease changed");
   end
   cv=0;ct=1;@(posedge clk);@(negedge clk);ct=0;checks++;
  end
 endtask
 reg [127:0] got,ignored,expected,raw,before_stats,after_stats;reg [15:0] x;
 task automatic scalar(input [15:0] value,output [15:0] answer);
  reg [127:0] temp,unused;
  begin
   access(1,10,{112'd0,value},unused);
   command(0,0,0,0,0,0,0,0,0,0,0,unused);
   command(1,1,0,1,0,0,20'd10,0,0,0,0,unused);
   command(1,1,0,1,0,0,20'd0,0,0,0,0,unused);
   command(2,0,0,0,0,0,0,0,0,0,0,unused);
   command(3,1,0,1,0,0,20'd10,0,0,0,0,temp);answer=temp[15:0];
  end
 endtask
 task automatic batch(input bit mode32,input integer count,input [127:0] data,input bit expected_error,input bit measure);
  integer old_writes;
  begin
   expected=0;
   if(!expected_error)for(integer i=0;i<count;i++)begin
    scalar(mode32?16'(data>>(32*i)):16'(data>>(16*i)),x);
    if(mode32)expected[32*i+:32]={16'd0,x};else expected[16*i+:16]=x;
   end
   access(1,16,data,ignored);access(1,32,128'hcafe,ignored);old_writes=writes;
   command(15,4'(count),mode32?32'h4e583332:32'h4e455850,1,1,0,20'd16,expected_error,3,measure,mode32,got);
   if(!expected_error&&got!==expected)$fatal(1,"full U computed value mismatch mode32=%0d n=%0d",mode32,count);
   access(0,32,0,got);
   if(expected_error)begin if(got!==128'hcafe||writes!=old_writes)$fatal(1,"error batch wrote S");end
   else if(got!==expected)$fatal(1,"S write ACK/readback mismatch");
  end
 endtask
 integer start_reads,start_writes;reg [31:0] edges[0:7];
 initial begin
  repeat(4)@(negedge clk);reset=0;
  access(1,0,0,ignored);
  edges[0]=32'h80000000;edges[1]=32'h7fffffff;edges[2]=32'h00008000;edges[3]=32'hffff7fff;
  edges[4]=32'h00010000;edges[5]=32'hffff0001;edges[6]=0;edges[7]=32'h1234ffff;
  for(integer n=1;n<=8;n++)begin raw=0;for(integer i=0;i<n;i++)raw[16*i+:16]=16'(i*517-2000);batch(0,n,raw,0,1);end
  for(integer n=1;n<=4;n++)begin
   for(integer t=0;t<8;t++)begin raw=0;for(integer i=0;i<n;i++)raw[32*i+:32]=edges[(i+t)%8];batch(1,n,raw,0,t==0);end
  end
  batch(0,1,128'h10000,1,0);batch(1,1,128'h100000000,1,0);
  // Invalid descriptor must not even read private S, and must not write it.
  for(integer bad=0;bad<9;bad++)begin
   start_reads=reads;start_writes=writes;
   command(15,bad==0?0:bad==1?9:bad==6?5:1,bad==2?0:bad==6?32'h4e583332:32'h4e455850,
      bad==3?0:bad==4?2:bad==8?3:1,1,bad==5,bad==7?20'h00410:20'd16,1,2,0,0,got);
   if(reads!=start_reads||writes!=start_writes)$fatal(1,"invalid descriptor accessed S");
  end
  // This destructive ABI intentionally invalidates an earlier scalar context.
  scalar(16'd12345,x);command(7,0,0,0,0,0,0,0,0,0,0,before_stats);
  access(1,16,0,ignored);command(15,4,32'h4e583332,1,1,0,20'd16,0,0,0,1,got);
  if(got!=={4{32'd32768}})$fatal(1,"zero relative EXP S32 bridge");
  command(7,0,0,0,0,0,0,0,0,0,0,after_stats);
  if(before_stats===after_stats)$fatal(1,"batch did not exercise documented clobber");
  scalar(16'd12345,x);command(7,0,0,0,0,0,0,0,0,0,0,after_stats);
  if(before_stats!==after_stats)$fatal(1,"normal op0 did not restore statistics protocol");
  // Real shared-S arbitration blocks output WRITE/ACK while an external read
  // response is held. This is a functional stress case, outside timing rows.
  access(1,16,0,ignored);
  fork
   begin
    command(15,4,32'h4e583332,1,1,0,20'd16,0,0,0,1,got);
    if(got!=={4{32'd32768}})$fatal(1,"contended output value");
   end
   begin
    wait(dut.n_valid&&dut.n_ready);
    @(negedge clk);io_v=1;io_w=0;io_addr=16;io_take=0;
    do @(posedge clk);while(!io_ready[0]);@(negedge clk);io_v=0;
    do @(negedge clk);while(!io_rsp[0]);
    wait(dut.request[0]&&dut.write[0]);
    repeat(6)begin @(negedge clk);if(done)$fatal(1,"U completed before held S write ACK");end
    io_take=1;@(posedge clk);@(negedge clk);io_take=0;
   end
  join
  access(0,32,0,got);if(got!=={4{32'd32768}})$fatal(1,"contended output ACK/readback");
  // Local-invalid hold is combinationally masked as soon as reset asserts.
  @(negedge clk);cv=1;cm={32'd0,4'd1,4'd15};sources=1;src=16;cs=1;ct=0;cdirect=0;
  do @(posedge clk);while(!cr);@(negedge clk);cv=0;
  do @(negedge clk);while(!done);
  reset=1;#1;if(done||cr)$fatal(1,"local invalid valid leaked during reset");
  repeat(3)@(negedge clk);reset=0;repeat(5)@(negedge clk);if(done)$fatal(1,"ghost local-invalid completion");
  // Reset a real in-flight batch (including N's internal command context).
  access(1,16,0,ignored);
  @(negedge clk);cv=1;cm={32'h4e583332,4'd4,4'd15};sources=1;src=16;cs=1;ct=0;
  do @(posedge clk);while(!cr);@(negedge clk);cv=0;
  wait(dut.n_valid&&dut.n_ready);repeat(4)@(negedge clk);reset=1;
  #1;if(done)$fatal(1,"batch valid during reset");repeat(3)@(negedge clk);reset=0;
  repeat(30)@(negedge clk);if(done)$fatal(1,"ghost batch after reset");
  batch(1,4,0,0,0);
  $display("NEXP_U_PASS checks=%0d S_reads=%0d S_writes=%0d",checks,reads,writes);$finish;
 end
 initial begin #20000000;$fatal(1,"U watchdog");end
endmodule
