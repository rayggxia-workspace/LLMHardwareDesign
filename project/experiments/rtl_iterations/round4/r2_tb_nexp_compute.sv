module tb_nexp_compute #(parameter integer DIRECT=1);
 reg clk=0,reset=1;always #5 clk=~clk;
 integer ticks=0,checks=0,values=0,frames=0,n_commands=0;
 integer direct_commands=0,other_commands=0;
 always @(posedge clk)if(!reset&&nv&&nready)begin
  if(nm[3:0]==12)direct_commands++;else other_commands++;
 end
 always @(posedge clk)begin ticks<=ticks+1;if(nv&&nready)n_commands<=n_commands+1;end
 reg v=0,take=0;reg [63:0] meta=0;reg [127:0] a=0;
 wire ready,ov,oe,os;wire [127:0] answer;
 wire nv,nready,nr,nrr,ne,ns;wire [63:0] nm;wire [127:0] na,nb,no;
 pu_nexp_shared #(.NEXP_DIRECT(DIRECT)) dut(.clk,.reset,.exec_valid(v),.exec_ready(ready),.exec_meta(meta),.exec_a(a),.exec_b(128'd0),
  .result_valid(ov),.result_ready(take),.result_data(answer),.result_error(oe),.result_saturated(os),
  .n_valid(nv),.n_ready(nready),.n_meta(nm),.n_a(na),.n_b(nb),
  .n_result_valid(nr),.n_result_ready(nrr),.n_result(no),.n_error(ne),.n_saturated(ns));
 block_v2_n #(.NEXP_DIRECT(DIRECT)) only_native_N(.clk,.reset,.cmd_valid(nv),.cmd_ready(nready),.cmd_op(nm[3:0]),.cmd_count(nm[7:4]),
  .cmd_param(nm[39:8]),.cmd_data(na),.cmd_aux(nb),.rsp_valid(nr),.rsp_ready(nrr),.rsp_data(no),.rsp_error(ne),.rsp_saturated(ns),.busy());
 // Separate golden N is testbench-only, not a second production resource.
 reg rv=0,rt=0;reg [3:0] rop=0,rc=0;reg [127:0] rd=0;
 wire rr,rov,re;wire [127:0] result_ref;
 block_v2_n reference_N(.clk,.reset,.cmd_valid(rv),.cmd_ready(rr),.cmd_op(rop),.cmd_count(rc),.cmd_param(32'd0),
  .cmd_data(rd),.cmd_aux(128'd0),.rsp_valid(rov),.rsp_ready(rt),.rsp_data(result_ref),.rsp_error(re),.rsp_saturated(),.busy());
 task automatic ref_command(input [3:0] op,input [3:0] n,input [127:0] data,output [127:0] result);
  integer guard;
  begin
   @(negedge clk);rv=1;rop=op;rc=n;rd=data;rt=0;guard=0;
   do begin @(posedge clk);guard++;if(guard>512)$fatal(1,"reference accept timeout");end while(!rr);
   @(negedge clk);rv=0;rt=1;guard=0;
   do begin @(posedge clk);guard++;if(guard>512)$fatal(1,"reference response timeout");end while(!rov);
   if(re)$fatal(1,"reference rejected legal scalar");result=result_ref;
   @(negedge clk);rt=0;
  end
 endtask
 task automatic golden(input bit mode32,input integer count,input [127:0] data,output [127:0] result);
  reg [15:0] x;reg [127:0] ignored,single;
  begin
   result=0;
   for(integer i=0;i<count;i++)begin
    x=mode32?16'(data>>(32*i)):16'(data>>(16*i));
    ref_command(0,0,0,ignored);ref_command(1,1,{112'd0,x},ignored);ref_command(1,1,0,ignored);
    ref_command(2,0,0,ignored);ref_command(3,1,{112'd0,x},single);
    if(mode32)result[32*i+:32]={16'd0,single[15:0]};else result[16*i+:16]=single[15:0];
   end
  end
 endtask
 task automatic check(input bit mode32,input integer count,input [127:0] data,input bit error,input integer stall,input bit unused_bad=0);
  reg [127:0] expected,held;integer guard,start_cmd;
  begin
   if(!error)golden(mode32,count,data,expected);else expected=0;
   @(negedge clk);meta={24'd0,mode32?32'h4e583332:32'h4e455850,4'(count),4'd15};a=data;v=1;take=0;guard=0;start_cmd=n_commands;
   do begin @(posedge clk);guard++;if(guard>512)$fatal(1,"compute accept timeout");end while(!ready);
   @(negedge clk);v=1;meta=0;a=~data;guard=0;
   do begin
    @(negedge clk);guard++;if(guard>512)$fatal(1,"compute response timeout");
    if(ready)$fatal(1,"ordinary command admitted inside exclusive batch");
   end while(!ov);
   if(oe!==error||os)$fatal(1,"compute error/saturated mismatch mode=%0d count=%0d",mode32,count);
   if(answer!==expected)$fatal(1,"compute numeric mismatch mode=%0d n=%0d in=%h got=%h expect=%h",mode32,count,data,answer,expected);
   if(unused_bad&&n_commands!=start_cmd)$fatal(1,"bad payload issued native BEGIN/clobber");
   held=answer;
   repeat(stall)begin
    // A normal command is held against the owner to prove no interleaving.
    v=1;meta=64'd0;
    @(negedge clk);if(!ov||answer!==held||ready)$fatal(1,"owner/result changed under backpressure");
   end
   v=0;take=1;@(posedge clk);@(negedge clk);take=0;
   frames++;if(!error)values+=count;checks++;
  end
 endtask
 task automatic timing(input bit mode32,input integer count);
  integer accepted,responded,next_accepted,guard;reg [63:0] tag;
  begin
   tag={24'd0,mode32?32'h4e583332:32'h4e455850,4'(count),4'd15};
   @(negedge clk);meta=tag;a=0;v=1;take=0;
   do @(posedge clk);while(!ready);accepted=ticks;
   @(negedge clk);v=0;take=1;guard=0;
   do begin @(posedge clk);guard++;if(guard>512)$fatal(1,"timing first timeout");end while(!ov);
   responded=ticks;if(oe)$fatal(1,"timing first error");
   @(negedge clk);meta=tag;v=1;take=0;
   do @(posedge clk);while(!ready);next_accepted=ticks;
   @(negedge clk);v=0;take=1;guard=0;
   do begin @(posedge clk);guard++;if(guard>512)$fatal(1,"timing second timeout");end while(!ov);
   if(oe)$fatal(1,"timing second error");
   @(negedge clk);take=0;
   $display("NEXP_COMPUTE mode32=%0d count=%0d accepted_to_done_cycles=%0d accepted_to_next_accept_cycles=%0d",mode32,count,responded-accepted,next_accepted-accepted);
  end
 endtask
 reg [127:0] data;reg [31:0] rng=32'h24716abc;reg [31:0] edge32[0:11];
 initial begin
  repeat(4)@(negedge clk);reset=0;
  // The entire signed16 numerical domain, with unchanged native scalar oracle.
  for(integer base=-32768;base<32768;base+=8)begin
   data=0;for(integer j=0;j<8;j++)data[16*j+:16]=16'(base+j);
   check(0,8,data,0,(base&511)==0?3:0);
  end
  edge32[0]=32'h80000000;edge32[1]=32'h7fffffff;edge32[2]=32'hffff0000;edge32[3]=32'h00010000;
  edge32[4]=32'h00008000;edge32[5]=32'hffff7fff;edge32[6]=32'h0000ffff;edge32[7]=32'hffff0001;
  edge32[8]=0;edge32[9]=1;edge32[10]=32'hffff8000;edge32[11]=32'h1234c000;
  for(integer n=1;n<=4;n++)for(integer t=0;t<96;t++)begin
   data=0;
   for(integer j=0;j<n;j++)begin
    rng=(rng>>1)^(-(rng&1)&32'hd0000001);
    data[32*j+:32]=t<12?edge32[(t+j)%12]:rng;
   end
   check(1,n,data,0,t%5);
  end
  for(integer n=1;n<=7;n++)begin data=0;for(integer j=0;j<n;j++)data[16*j+:16]=16'(j*101-222);check(0,n,data,0,2);end
  check(0,0,0,1,2,1);check(0,9,0,1,2,1);check(1,5,0,1,2,1);
  check(0,1,128'h00010000,1,2,1);check(1,1,128'h0000000100000000,1,2,1);
  // Reset drops an accepted batch and its internal native response.
  @(negedge clk);v=1;meta={24'd0,32'h4e455850,4'd8,4'd15};a=0;take=0;
  do @(posedge clk);while(!ready);@(negedge clk);v=0;
  repeat(4)@(negedge clk);reset=1;repeat(3)@(negedge clk);reset=0;
  repeat(10)@(negedge clk);if(ov||!ready)$fatal(1,"reset left ghost compute response");
  for(integer n=1;n<=8;n++)timing(0,n);
  for(integer n=1;n<=4;n++)timing(1,n);
  $display("NEXP_NATIVE_PATH direct_mode=%0d op12_commands=%0d other_commands=%0d",DIRECT,direct_commands,other_commands);
  $display("NEXP_COMPUTE_PASS checks=%0d values=%0d frames=%0d",checks,values,frames);$finish;
 end
 initial begin #2000000000;$fatal(1,"compute watchdog");end
endmodule
