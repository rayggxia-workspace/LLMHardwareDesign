`timescale 1ns/1ps
module tb_service_bounds;
  reg clk=0;always #5 clk=~clk;
  reg reset=1,request=0,take=0;
  reg [63:0] meta=0;
  reg [127:0] operand=0;
  wire ready,response,error;
  wire [127:0] data;
  integer transactions=0;
  ucf_r256_service dut(.*);
  task automatic transact(input [63:0] fields,input [127:0] value,input bit expected_error,input [127:0] expected_data);
    integer age;
    @(negedge clk);request=1;meta=fields;operand=value;#1;age=0;
    while(!ready)begin @(negedge clk);#1;age=age+1;if(age>100)$fatal(1,"service admission stuck");end
    @(posedge clk);#1;@(negedge clk);request=0;age=0;
    while(!response)begin @(negedge clk);age=age+1;if(age>100)$fatal(1,"service response stuck");end
    repeat(4)begin
      if(!response || error!==expected_error || data!==expected_data || ready)$fatal(1,"held service response mismatch");
      @(negedge clk);
    end
    take=1;@(negedge clk);take=0;transactions=transactions+1;
  endtask
  integer first_invalid;
  initial begin
    repeat(4)@(negedge clk);reset=0;
    transact(0,128'h12345678,0,0);
    transact(2,0,0,128'h12345678);
    for(integer t=0;t<8;t=t+1)begin
      case(t)0,1:first_invalid=64;2,3,7:first_invalid=4;4,6:first_invalid=6;5:first_invalid=1;endcase
      transact((64'(first_invalid)<<5)|(64'(t)<<2),'1,1,0);
      transact((64'd1023<<5)|(64'(t)<<2),'1,1,0);
      // The original state remains intact and a new valid request still works.
      transact(2,0,0,128'h12345678);
    end
    transact(0,128'h87654321,0,0);
    transact(2,0,0,128'h87654321);
    $display("PASS service bounds explicit errors/backpressure/recovery transactions=%0d",transactions);
    $finish;
  end
  initial begin #100000;$fatal(1,"service watchdog");end
endmodule
