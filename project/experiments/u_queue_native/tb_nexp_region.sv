module tb_nexp_region #(parameter integer FORMAT16=1,DEPTH=0,PIPE=0);
 `include "tb_u_ports.svh"
 reg start=0,finish=0,scale_ok=1;reg [11:0] count=0;reg [9:0] inbase=0,outbase=512;
 wire start_ready,region_done,region_error;wire [11:0] completed,frames;
 pu_nexp_region sequence_unit(.clk,.reset,.start_valid(start),.start_ready,.input_s16(FORMAT16!=0),.input_q5_10(scale_ok),
  .elements(count),.input_base(inbase),.output_base(outbase),.done_valid(region_done),.done_ready(finish),.done_error(region_error),
  .completed_values(completed),.completed_commands(frames),.n_cmd_valid(nv),.n_cmd_ready(nready),.n_cmd_meta(nmeta),.n_cmd_src(nsrc),.n_cmd_dst(ndst),
  .n_done_valid(ndone),.n_done_ready(ntake),.n_done_error(nerror));
 reg [47:0] values[0:22015];string path;
 integer sr=0,sw=0,acks=0,kind=0,descriptors=0,valid_cases=0,invalid_cases=0,total_values=0;
 integer region_cycles=0,region_reads=0,region_writes=0,region_commands=0;
 reg [127:0] word_data,got,ignored;
 always @(posedge clk)if(!reset)begin
  if(dut.request[0]&&dut.accept[0])begin kind=dut.write[0];if(kind)sw++;else sr++;end
  if(dut.response[0]&&dut.take[0]&&kind)acks++;
  if(nv&&nready)begin
   descriptors++;
   if(nmeta[39:8]!=(FORMAT16?32'h4e583136:32'h4e583332)||nmeta[7:4]==0||nmeta[7:4]>(FORMAT16?8:4))$fatal(1,"region descriptor format");
  end
 end
 task automatic invoke(input integer n,input integer stall,input bit bad,output integer elapsed);
  integer before_tick,old_r,old_w,old_ack,old_desc;reg [24:0] held;
  begin
   old_r=sr;old_w=sw;old_ack=acks;old_desc=descriptors;
   @(negedge clk);count=12'(n);start=1;finish=0;
   do @(posedge clk);while(!start_ready);before_tick=ticks;
   @(negedge clk);start=0;
   do @(posedge clk);while(!region_done);
   elapsed=ticks-before_tick+1;
   if(region_error!==bad)$fatal(1,"region error result");
   held={region_error,completed,frames};
   repeat(stall)begin @(negedge clk);if(!region_done||{region_error,completed,frames}!==held)$fatal(1,"region completion backpressure");end
   if(bad)begin
    if(sr!=old_r||sw!=old_w||descriptors!=old_desc||completed!=0||frames!=0)$fatal(1,"bad region touched S");invalid_cases++;
   end else begin
    if(completed!=n||frames!=(n+(FORMAT16?7:3))/(FORMAT16?8:4)||sr-old_r!=frames||sw-old_w!=(n+3)/4||acks-old_ack!=sw-old_w||descriptors-old_desc!=frames)$fatal(1,"region count/ACK accounting");
    valid_cases++;total_values+=n;
   end
   @(negedge clk);finish=1;@(posedge clk);@(negedge clk);finish=0;
  end
 endtask
 task automatic region_tile(input integer n,input integer offset,input bit measure);
  integer elapsed,old_r,old_w,old_cmd,perword,index;
  begin
   perword=FORMAT16?8:4;
   for(integer w=0;w<(n+perword-1)/perword;w++)begin
    word_data='1;
    for(integer j=0;j<perword;j++)begin
     index=w*perword+j;
     if(index<n)begin
      if(FORMAT16)word_data[16*j+:16]=values[offset+index][47:32];
      else word_data[32*j+:32]={{16{values[offset+index][47]}},values[offset+index][47:32]};
     end
    end
    access(0,1,10'(w),word_data,0,ignored);
   end
   for(integer w=0;w<(n+3)/4+1;w++)if(512+w<1024)access(0,1,10'(512+w),'1,0,ignored);
   old_r=sr;old_w=sw;old_cmd=descriptors;invoke(n,n%5,0,elapsed);
   if(measure)begin region_cycles+=elapsed;region_reads+=sr-old_r;region_writes+=sw-old_w;region_commands+=descriptors-old_cmd;end
   for(integer w=0;w<(n+3)/4;w++)begin
    word_data=0;for(integer j=0;j<4;j++)if(w*4+j<n)word_data[32*j+:32]=values[offset+w*4+j][31:0];
    access(0,0,10'(512+w),0,0,got);if(got!==word_data)$fatal(1,"region numeric format=%0d offset=%0d word=%0d got=%h expected=%h",FORMAT16,offset,w,got,word_data);
   end
   if(512+(n+3)/4<1024)begin access(0,0,10'(512+(n+3)/4),0,0,got);if(got!==128'hffffffffffffffffffffffffffffffff)$fatal(1,"region tail guard overwritten");end
   if(!measure)$display("REGION_TILE format16=%0d elements=%0d cycles=%0d",FORMAT16,n,elapsed);
  end
 endtask
 initial begin
  integer elapsed;
  if(!$value$plusargs("VALUES=%s",path))$fatal(1,"missing values");$readmemh(path,values);
  repeat(4)@(negedge clk);reset=0;
  invoke(0,2,1,elapsed);invoke(2049,2,1,elapsed);
  scale_ok=0;invoke(8,2,1,elapsed);scale_ok=1;
  outbase=0;invoke(8,2,1,elapsed);outbase=1023;invoke(8,2,1,elapsed);outbase=512;
  inbase=1023;invoke(16,2,1,elapsed);inbase=0;
  // Reset during an accepted memory transaction, then reload and reissue.
  access(0,1,0,0,0,ignored);@(negedge clk);count=8;start=1;
  do @(posedge clk);while(!start_ready);@(negedge clk);start=0;
  do @(posedge clk);while(!(dut.request[0]&&dut.accept[0]));
  @(negedge clk);reset=1;repeat(3)@(negedge clk);reset=0;
  repeat(35)begin @(negedge clk);if(ndone||region_done)$fatal(1,"region reset ghost");end
  for(integer n=1;n<=17;n++)region_tile(n,0,0);
  region_tile(63,0,0);region_tile(64,0,0);region_tile(65,0,0);region_tile(2048,0,0);
  for(integer offset=0;offset<22016;offset+=64)region_tile(64,offset,1);
  $display("REGION_MEASURE format16=%0d elements=22016 tiles=344 cycles=%0d reads=%0d writes=%0d descriptors=%0d",FORMAT16,region_cycles,region_reads,region_writes,region_commands);
  $display("REGION_PASS valid_cases=%0d invalid_cases=%0d values=%0d reset_cuts=1",valid_cases,invalid_cases,total_values);$finish;
 end
endmodule
