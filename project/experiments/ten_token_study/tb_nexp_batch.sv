module tb_nexp_batch;
 reg clk=0,reset=1;always #5 clk=~clk;
 reg v=0,rr=0;reg [3:0] count=0;reg [127:0] data=0;
 wire ready,ov,oe;wire [127:0] out;
 nexp_batch_adapter dut(clk,reset,v,ready,count,data,ov,rr,out,oe);
 reg rv=0,rrr=0;reg [3:0] rop=0,rc=0;reg [127:0] rd=0;
 wire rready,rov,re,rsat,rb;wire [127:0] rout;
 block_v2_n reference_n(clk,reset,rv,rready,rop,rc,32'd0,rd,128'd0,rov,rrr,rout,re,rsat,rb);
 integer ticks=0,values=0,frames=0,min_cycles=100000,max_cycles=0,scalar_cycles=0;
 always @(posedge clk)ticks=ticks+1;
 task automatic command(input [3:0] op,input [3:0] n,input [127:0] x,output [127:0] y);
  integer guard;
  begin
   @(negedge clk);rv=1;rop=op;rc=n;rd=x;rrr=0;guard=0;
   do begin @(posedge clk);guard++;if(guard>256)$fatal(1,"reference command timeout");end while(!rready);
   @(negedge clk);rv=0;rrr=1;guard=0;
   do begin @(posedge clk);guard++;if(guard>256)$fatal(1,"reference response timeout");end while(!rov);
   if(re)$fatal(1,"reference N rejected legal command");y=rout;
   @(negedge clk);rrr=0;
  end
 endtask
 task automatic check(input [3:0] n,input [127:0] x,input integer stall,input bit invalid);
  reg [127:0] expected,tmp,held;integer start,elapsed,guard,refstart;
  begin
   expected=0;refstart=ticks;
   if(!invalid)for(integer j=0;j<n;j++)begin
    command(0,0,0,tmp);
    command(1,1,{112'd0,x[16*j+:16]},tmp);
    command(1,1,0,tmp);
    command(2,0,0,tmp);
    command(3,1,{112'd0,x[16*j+:16]},tmp);
    expected[16*j+:16]=tmp[15:0];
   end
   scalar_cycles+=ticks-refstart;
   @(negedge clk);v=1;count=n;data=x;rr=0;
   do @(posedge clk);while(!ready);
   start=ticks;
   @(negedge clk);v=0;data=~x;count=0;guard=0;
   do begin @(negedge clk);guard++;if(guard>256)$fatal(1,"batch response timeout");end while(!ov);
   elapsed=ticks-start;
   if(elapsed<min_cycles)min_cycles=elapsed;if(elapsed>max_cycles)max_cycles=elapsed;
   if(oe!=invalid)$fatal(1,"wrong batch error");
   if(!invalid&&out!==expected)$fatal(1,"EXP mismatch n=%0d x=%h got=%h expected=%h",n,x,out,expected);
   held=out;
   repeat(stall)begin @(negedge clk);if(!ov||out!==held||ready)$fatal(1,"response/source lifetime changed under backpressure");end
   rr=1;@(posedge clk);@(negedge clk);rr=0;
   if(!invalid)values+=n;frames++;
  end
 endtask
 reg [127:0] x;reg [31:0] rng=32'h2401024;
 initial begin
  repeat(4)@(negedge clk);reset=0;
  // Exhaust every S16 input, including saturation and interpolation ties.
  for(integer base=-32768;base<32768;base+=8)begin
   for(integer j=0;j<8;j++)x[16*j+:16]=16'(base+j);
   check(8,x,(base&31)==0?3:0,0);
  end
  for(integer n=1;n<=7;n++)for(integer t=0;t<32;t++)begin
   for(integer j=0;j<8;j++)begin rng=(rng>>1)^(-(rng&1)&32'hd0000001);x[16*j+:16]=rng[15:0];end
   check(4'(n),x,t%5,0);
  end
  check(0,0,3,1);check(9,~128'd0,2,1);
  // Reset aborts an in-flight native transaction and discards its response.
  @(negedge clk);v=1;count=8;data=0;@(posedge clk);@(negedge clk);v=0;
  repeat(3)@(negedge clk);reset=1;repeat(3)@(negedge clk);reset=0;
  repeat(4)@(negedge clk);if(ov||!ready)$fatal(1,"reset left a stale response");
  check(8,~128'd0,4,0);
  $display("NEXP_BATCH_PASS values=%0d frames=%0d min_cycles=%0d max_cycles=%0d scalar_reference_cycles=%0d",values,frames,min_cycles,max_cycles,scalar_cycles);
  $finish;
 end
 initial begin #1000000000;$fatal(1,"watchdog");end
endmodule
