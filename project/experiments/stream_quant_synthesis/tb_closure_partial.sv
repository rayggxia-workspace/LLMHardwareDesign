module tb_closure_partial;
 reg clk; initial clk=0;
 reg reset=1,in_valid=0,out_ready=0;
 wire in_ready,out_valid,out_error;
 reg [3:0] in_count=0;
 reg [319:0] in_partial=0;reg [87:0] in_mantissa=0;reg [55:0] in_shift=0;
 reg [1023:0] in_previous=0;wire [1023:0] out_data;
 closure_partial128 dut(.*);
 always #5 clk=~clk;
 integer fd,rc,count,error,checks=0;
 reg [319:0] partial;reg [87:0] mantissa;reg [55:0] shift;
 reg [1023:0] previous,expected;
 initial begin
  repeat(3)@(negedge clk);reset=0;
  fd=$fopen("partial-vectors.txt","r");if(fd==0)$fatal(1,"vectors");
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %h %h %h %h %h %d\n",count,partial,mantissa,shift,previous,expected,error);
   if(rc!=7||count<1||count>8||(error!=0&&error!=1))$fatal(1,"format");
   @(negedge clk);in_valid=1;in_count=4'(count);in_partial=partial;in_mantissa=mantissa;in_shift=shift;in_previous=previous;
   do @(posedge clk);while(!in_ready);
   @(negedge clk);in_valid=0;
   repeat(checks%5+1)begin
    if(!out_valid||out_error!==1'(error)||(error==0&&out_data!==expected))$fatal(1,"partial mismatch %0d",checks);
    @(negedge clk);
   end
   out_ready=1;@(posedge clk);@(negedge clk);out_ready=0;checks=checks+1;
  end
  reset=1;@(negedge clk);reset=0;
  if(out_valid)$fatal(1,"reset");
  $display("PARTIAL128_PASS checks=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
