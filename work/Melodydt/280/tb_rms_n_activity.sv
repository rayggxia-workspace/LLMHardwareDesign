`timescale 1ps/1ps
module tb_rms_n_activity;
  reg clk=0;
  always #5000 clk=~clk;
  reg reset=1,cmd_valid=0,rsp_ready=1;
  wire cmd_ready,rsp_valid,rsp_error,rsp_saturated,busy;
  reg [3:0] cmd_op=0,cmd_count=0;
  reg [31:0] cmd_param=0;
  reg [127:0] cmd_data=0,cmd_aux=0;
  wire [127:0] rsp_data;
  block_v2_n dut(.*);
  integer fd,got,words,epsilon,expected_factor;
  reg [63:0] value;
  string vectors,wave;
  time active_start,active_end,idle_end;

  task automatic command(input [3:0] op,input [3:0] count,input [31:0] param,input [127:0] data);
    integer waited;
    begin
      @(negedge clk);
      cmd_valid=1;cmd_op=op;cmd_count=count;cmd_param=param;cmd_data=data;
      waited=0;
      do begin @(posedge clk);waited=waited+1;if(waited>1000)$fatal(1,"command timeout");end while(!cmd_ready);
      #1;cmd_valid=0;waited=0;
      do begin @(posedge clk);waited=waited+1;if(waited>1000)$fatal(1,"response timeout");end while(!rsp_valid);
      if(rsp_error||rsp_saturated)$fatal(1,"N error op=%0d",op);
      if(op==11 && rsp_data[31:0]!==32'(expected_factor))
        $fatal(1,"factor mismatch got=%0d expected=%0d",rsp_data[31:0],expected_factor);
      $display("LEAF op=%0d response_wait_cycles=%0d",op,waited);
      #1;
    end
  endtask

  initial begin
    if(!$value$plusargs("vectors=%s",vectors)||!$value$plusargs("wave=%s",wave))$fatal(1,"missing args");
    $dumpfile(wave);$dumpvars(0,tb_rms_n_activity);
    fd=$fopen(vectors,"r");if(!fd)$fatal(1,"input missing");
    got=$fscanf(fd,"%d %d %d\n",words,epsilon,expected_factor);
    if(got!=3||words<=0||words>1024||epsilon<=0)$fatal(1,"invalid header");
    repeat(5)@(negedge clk);reset=0;
    repeat(5)@(negedge clk);
    active_start=$time;
    command(0,0,1,128'(32'(epsilon)));
    for(integer i=0;i<words;i=i+1)begin
      got=$fscanf(fd,"%h\n",value);if(got!=1)$fatal(1,"missing word");
      command(1,4,0,{64'd0,value});
    end
    command(2,0,0,0);
    command(11,0,0,0);
    @(negedge clk);active_end=$time;
    repeat((active_end-active_start)/10000)@(negedge clk);
    idle_end=$time;
    $display("RMS_N_PASS words=%0d active_start=%0d active_end=%0d idle_end=%0d",words,active_start,active_end,idle_end);
    #1;$finish;
  end
endmodule
