module tb_closure_finalize;
 reg clk;initial clk=0;always #5 clk=~clk;
 reg reset=1,in_valid=0,out_ready=0;
 reg [3:0] in_count=0;reg [1023:0] in_data=0;reg [6:0] in_shift=0;reg [255:0] in_bias=0;
 wire in_ready,out_valid,out_error;wire [255:0] out_data;
 closure_finalize128 dut(.*);
 integer fd,rc,n,s,error,checks=0;reg [255:0] expected;
 initial begin
  repeat(3)@(negedge clk);reset=0;
  fd=$fopen("finalize-vectors.txt","r");if(fd==0)$fatal(1,"vectors");
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %d %h %h %h %d\n",n,s,in_data,in_bias,expected,error);
   if(rc!=6||n<1||n>8||s<0||s>127||(error!=0&&error!=1))$fatal(1,"format");
   in_count=4'(n);in_shift=7'(s);in_valid=1;do @(posedge clk);while(!in_ready);
   @(negedge clk);in_valid=0;
   repeat(checks%4+1)begin
    if(!out_valid||out_error!==1'(error)||(error==0&&out_data!==expected))$fatal(1,"RNE/bias/range %0d",checks);
    @(negedge clk);
   end
   out_ready=1;@(posedge clk);@(negedge clk);out_ready=0;checks=checks+1;
  end
  reset=1;repeat(3)@(negedge clk);reset=0;if(out_valid)$fatal(1,"reset");
  $display("FINALIZE128_PASS checks=%0d",checks);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
