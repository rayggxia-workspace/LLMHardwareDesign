module tb_m_stream #(parameter integer K=16);
 reg clk=0,reset=1;always #5 clk=~clk;
 reg valid=0,ready_out=0,first=0,last=0,bu=0;reg [2:0] row=0;
 reg [4:0] bs=0;reg [3:0] n=0;reg [5:0] shift=0,count=0;
 reg [K*32-1:0] a=0;reg [K*8*8-1:0] b=0;
 wire ready,ov,err;wire [2:0] orow;wire [255:0] out;wire [7:0] sat;
 m_s32_stream_candidate #(.K(K)) dut(clk,reset,valid,ready,row,first,last,count,n,shift,bs,bu,a,b,ov,ready_out,orow,out,sat,err);
 integer ticks=0,responses=0,accepted=0,consecutive=0,longest=0;reg [31:0] rng=32'h2401024;
 reg stalled=0;reg [267:0] held;
 always @(posedge clk)begin
  ticks=ticks+1;
  if(!reset)begin
   if(valid&&ready)begin accepted++;consecutive++;if(consecutive>longest)longest=consecutive;end
   else consecutive=0;
   if(stalled&&{orow,err,sat,out}!==held)$fatal(1,"output changed while stalled");
   stalled=ov&&!ready_out;held={orow,err,sat,out};
   if(ov&&ready_out)begin $display("M_RESULT %0d %0d %0d %02h %064h",responses,orow,err,sat,out);responses++;end
  end else stalled=0;
 end
 always @(negedge clk)begin
  rng=(rng>>1)^(-(rng&1)&32'hd0000001);
  ready_out=!reset&&rng[0]&&ticks%64>=8;
 end
 integer f,total_packets,fields,r,ff,ll,kk,nn,ss,bbs,uu;reg [K*32-1:0] aa;reg [K*8*8-1:0] bb;
 initial begin
  repeat(4)@(negedge clk);reset=0;
  f=$fopen("m-input.txt","r");if(!f)$fatal(1,"missing m-input.txt");
  fields=$fscanf(f,"%d\n",total_packets);if(fields!=1)$fatal(1,"bad header");
  for(integer i=0;i<total_packets;i++)begin
   fields=$fscanf(f,"%d %d %d %d %d %d %d %d %h %h\n",r,ff,ll,kk,nn,ss,bbs,uu,aa,bb);
   if(fields!=10)$fatal(1,"bad input packet %0d",i);
   @(negedge clk);valid=1;row=3'(r);first=1'(ff);last=1'(ll);count=6'(kk);n=4'(nn);shift=6'(ss);bs=5'(bbs);bu=1'(uu);a=aa;b=bb;
   do @(posedge clk);while(!ready);
   if(i%31==0)begin @(negedge clk);valid=0;a=~aa;b=~bb;repeat(3)@(negedge clk);end
  end
  @(negedge clk);valid=0;a=~aa;b=~bb;
  $fclose(f);repeat(96)@(negedge clk);
  if(accepted!=total_packets||longest<16)$fatal(1,"input throughput/count failed");
  $display("M_STREAM_FINISHED packets=%0d responses=%0d ticks=%0d longest_II1=%0d",total_packets,responses,ticks,longest);$finish;
 end
 initial begin #1000000000;$fatal(1,"watchdog");end
endmodule
