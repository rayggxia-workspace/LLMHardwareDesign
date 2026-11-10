module tb_closure_context;
 reg clk;initial clk=0;always #5 clk=~clk;
 reg reset=1,in_valid=0,out_ready=0,in_first=0,in_last=0;
 reg [3:0] in_context=0;reg [15:0] in_generation=0;
 reg [319:0] in_partial=0;reg [87:0] in_mantissa=0;reg [55:0] in_shift=0;
 wire in_ready,out_valid,out_error,fault;wire [3:0] out_context;wire [15:0] out_generation;wire [1023:0] out_data;
 closure_context16 dut(.*);
 integer fd,rc,c,first,last,g,error,checks=0;
 reg [1023:0] expected;
 initial begin
  repeat(3)@(negedge clk);reset=0;
  fd=$fopen("context-vectors.txt","r");if(fd==0)$fatal(1,"vectors");
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %d %d %d %h %h %h %h %d\n",c,first,last,g,in_partial,in_mantissa,in_shift,expected,error);
   if(rc!=9||c<0||c>15||g<0||g>65535||(first!=0&&first!=1)||(last!=0&&last!=1)||(error!=0&&error!=1))$fatal(1,"format");
   in_context=4'(c);in_first=1'(first);in_last=1'(last);in_generation=16'(g);in_valid=1;
   do @(posedge clk);while(!in_ready);
   @(negedge clk);in_valid=0;
   do @(negedge clk);while(!out_valid);
   repeat(checks%5+1)begin
    if(out_error!==1'(error)||out_context!==in_context||out_generation!==in_generation||
       (error==0&&out_data!==expected)||in_ready)$fatal(1,"context mismatch/ownership %0d",checks);
    @(negedge clk);
   end
   out_ready=1;@(posedge clk);@(negedge clk);out_ready=0;checks=checks+1;
   if(error!=0)begin if(!fault)$fatal(1,"missing fault");reset=1;repeat(3)@(negedge clk);reset=0;end
  end
  reset=1;repeat(3)@(negedge clk);reset=0;
  if(out_valid||fault)$fatal(1,"reset");
  $display("CONTEXT16_PASS checks=%0d",checks);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
