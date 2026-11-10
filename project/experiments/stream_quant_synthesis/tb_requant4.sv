module tb_requant4;
 parameter integer QBITS=8;
 reg clk=0,reset=1,in_valid=0,out_ready=0;
 wire in_ready,out_valid,out_error;reg [255:0] in_data=0;
 reg [63:0] in_scale=0;reg [23:0] in_shift=0;reg [2:0] in_count=0;
 wire [4*QBITS-1:0] out_data;wire [3:0] out_saturated;
 w8_requantize4 #(.QBITS(QBITS)) dut(.*);
 always #5 clk=~clk;
 integer fd,rc,count,err,checks=0;reg [127:0] expected;reg [3:0] sat;
 reg [255:0] data;reg [63:0] scales;reg [23:0] shifts;
 initial begin
  repeat(3)@(negedge clk);reset=0;
  fd=$fopen("requant-vectors.txt","r");if(fd==0)$fatal(1,"missing vectors");
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%h %h %h %d %h %h %d\n",data,scales,shifts,count,expected,sat,err);
   if(rc!=7)$fatal(1,"bad vector");
   @(negedge clk);in_valid=1;in_data=data;in_scale=scales;in_shift=shifts;in_count=3'(count);
   do @(posedge clk);while(!in_ready);
   @(negedge clk);in_valid=0;
   repeat(checks%4+1)begin
    if(!out_valid||out_data!==expected[4*QBITS-1:0]||out_saturated!==sat||out_error!==1'(err))$fatal(1,"RNE mismatch %0d",checks);
    @(negedge clk);
   end
   out_ready=1;@(posedge clk);@(negedge clk);out_ready=0;checks=checks+1;
  end
  reset=1;@(negedge clk);reset=0;
  if(out_valid)$fatal(1,"stale reset response");
  $display("REQUANT_RTL_PASS bits=%0d checks=%0d",QBITS,checks);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
