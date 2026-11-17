`timescale 1ps/1ps
module tb_rms_e32;
  reg clk=0, reset=1, in_valid=0, out_ready=0;
  reg [63:0] in_data=0;
  reg [7:0] in_shift=0;
  wire in_ready,out_valid,out_error;
  wire [63:0] out_data;
  wire [3:0] out_clipped;
  e_s32_ap64 dut(.clk,.reset,.in_valid,.in_ready,.in_data,.in_op(4'd2),
    .in_mask(4'hf),.in_shift,.in_minus(3'b0),.out_valid,.out_ready,.out_data,.out_clipped,.out_error);
  always #1667 clk=~clk;
  integer cycle=0;
  always @(posedge clk) cycle<=cycle+1;
  reg [63:0] a0,a1,b0,b1,y0,y1;
  integer fd,n,shift_value,start_cycle,count=0,elapsed,min_cycles=100000,max_cycles=0;
  string vectors;
  task automatic send(input reg[63:0] value);
    in_data=value; in_valid=1;
    do @(posedge clk); while(!in_ready);
    @(negedge clk); in_valid=0;
  endtask
  task automatic receive_word(input reg[63:0] expected_value);
    do @(posedge clk); while(!out_valid);
    if(out_error || out_clipped || out_data !== expected_value)
      $fatal(1,"E32 mismatch case=%0d expected=%h actual=%h clip=%h err=%b",count,expected_value,out_data,out_clipped,out_error);
    @(negedge clk);
  endtask
  initial begin
    if(!$value$plusargs("vectors=%s",vectors)) $fatal(1,"missing vectors");
    fd=$fopen(vectors,"r"); if(!fd) $fatal(1,"cannot read vectors");
    repeat(4) @(negedge clk); reset=0;
    while(!$feof(fd)) begin
      n=$fscanf(fd,"%d %h %h %h %h %h %h\n",shift_value,a0,a1,b0,b1,y0,y1);
      if(n!=7) $fatal(1,"bad vector record");
      in_shift=8'(shift_value); start_cycle=cycle;
      send(a0); send(a1); send(b0); send(b1);
      out_ready=1;
      receive_word(y0); receive_word(y1); out_ready=0;
      elapsed=cycle-start_cycle;
      if(elapsed<min_cycles) min_cycles=elapsed;
      if(elapsed>max_cycles) max_cycles=elapsed;
      count=count+1;
    end
    if(count==0) $fatal(1,"no vectors");
    $display("RMS_E32_PASS cases=%0d min_driver_cycles=%0d max_driver_cycles=%0d",count,min_cycles,max_cycles);
    $finish;
  end
  initial begin #100000000000; $fatal(1,"watchdog"); end
endmodule
