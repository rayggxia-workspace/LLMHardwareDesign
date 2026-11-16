`timescale 1ns/1ps
module tb_lc_program_store;
  logic clk,reset;
  initial clk=0;
  always #5 clk=~clk;
  logic lc_idle,transport_drained,cfg_valid,cfg_ready,cfg_rsp_valid,cfg_rsp_ready;
  logic [1:0] cfg_op;
  logic [31:0] cfg_generation,cfg_abi,cfg_capacity,cfg_crc,cfg_actual_crc,generation;
  logic [15:0] cfg_bytes,image_bytes;
  logic [13:0] cfg_address;
  logic [127:0] cfg_data;
  logic [7:0] cfg_status;
  logic certified,boot_busy,pm_valid,pm_ready,pm_rsp_valid,pm_rsp_ready,pm_error;
  logic [13:0] pm_address;
  logic [127:0] pm_data;
  lc_program_store_1k dut(.*);
  logic [127:0] image[22],old_image[22];
  logic [31:0] good_crc,old_crc;
  integer seed,cycle,begin_scan,end_scan;
  string path,old_path;
  task automatic pause(input int n=1);repeat(n) @(negedge clk);endtask
  task automatic cfg_request(input logic [1:0] op);
    cfg_op=op;cfg_valid=1;
    do @(posedge clk);while(!cfg_ready);@(negedge clk);cfg_valid=0;
  endtask
  task automatic cfg_receipt(input logic [7:0] expected_status);
    while(!cfg_rsp_valid) @(negedge clk);
    assert(cfg_status==expected_status) else $fatal(1,"PM cfg status %0d != %0d",cfg_status,expected_status);
    pause(seed%3);cfg_rsp_ready=1;pause();cfg_rsp_ready=0;
  endtask
  task automatic begin_image(input int gen,input logic [15:0] bytes_count=352);
    cfg_generation=32'(gen);cfg_bytes=16'(bytes_count);cfg_request(0);cfg_receipt(0);
    assert(generation==32'(gen)&&image_bytes==16'(bytes_count)&&!certified);
  endtask
  task automatic write_image(input bit old_version=0,input bit corrupt=0);
    for(integer i=0;i<22;i=i+1) begin
      cfg_address=14'(16*i);cfg_data=old_version?old_image[i]:image[i];
      if(corrupt&&i==20) cfg_data=cfg_data^128'd1;
      cfg_request(1);cfg_receipt(0);
    end
  endtask
  task automatic seal(input logic [31:0] oracle,input logic [7:0] expected_status);
    cfg_crc=oracle;cfg_request(2);begin_scan=cycle;
    assert(boot_busy&&!cfg_rsp_valid&&!certified);
    while(!cfg_rsp_valid) @(negedge clk);end_scan=cycle;
    assert(end_scan-begin_scan==352) else $fatal(1,"CRC scan unexpectedly free / unbounded %0d",end_scan-begin_scan);
    cfg_receipt(expected_status);
  endtask
  task automatic read_word(input logic [13:0] address,input bit expected_error,input logic [127:0] expected_data=0);
    pm_address=14'(address);pm_valid=1;
    do @(posedge clk);while(!pm_ready);@(negedge clk);pm_valid=0;
    while(!pm_rsp_valid) @(negedge clk);
    assert(pm_error==expected_error&&pm_data==expected_data);
    pause(seed%3);assert(pm_rsp_valid&&pm_error==expected_error&&pm_data==expected_data);
    pm_rsp_ready=1;pause();pm_rsp_ready=0;
  endtask
  always @(posedge clk) if(reset)cycle<=0;else cycle<=cycle+1;
  initial begin
    reset=1;lc_idle=1;transport_drained=1;cfg_valid=0;cfg_rsp_ready=0;cfg_op=0;
    cfg_generation=1;cfg_abi=32'h02500002;cfg_capacity=32'h02510001;cfg_crc=0;cfg_bytes=352;cfg_address=0;cfg_data=0;
    pm_valid=0;pm_rsp_ready=0;pm_address=0;seed=1;good_crc=0;old_crc=0;
    if($value$plusargs("SEED=%d",seed)) begin end
    path="kernel.mem";old_path="old-version.mem";
    if($value$plusargs("IMAGE=%s",path)) begin end
    if($value$plusargs("OLD_IMAGE=%s",old_path)) begin end
    assert($value$plusargs("CRC=%h",good_crc));assert($value$plusargs("OLD_CRC=%h",old_crc));
    $readmemh(path,image);$readmemh(old_path,old_image);
    pause(3);reset=0;pause();read_word(128,1);
    cfg_capacity=0;cfg_request(0);cfg_receipt(2);assert(!certified);cfg_capacity=32'h02510001;
    cfg_bytes=1216;cfg_request(0);cfg_receipt(2); // Existing U seven-service image cannot silently fit.
    begin_image(1);cfg_address=16;cfg_data=image[1];cfg_request(1);cfg_receipt(3);
    write_image();seal(good_crc^1,4);assert(!certified);read_word(128,1);
    begin_image(2);write_image(0,1);seal(good_crc,4);assert(!certified);
    begin_image(3);write_image(1,0);seal(old_crc,6);assert(!certified);
    begin_image(4);write_image();seal(good_crc,0);
    assert(certified&&cfg_actual_crc==good_crc);
    // Actual compact kernel fetches, not just capacity arithmetic.
    read_word(128,0,{64'h4400000000000001,64'h4100000000000000});
    read_word(144,0,{64'b0,64'h4f00000000000000});
    read_word(129,1);read_word(352,1);read_word(1024,1);
    lc_idle=0;cfg_generation=5;cfg_bytes=352;cfg_request(0);cfg_receipt(5);
    assert(certified&&generation==4);lc_idle=1;transport_drained=0;cfg_request(0);cfg_receipt(5);
    assert(certified&&generation==4);transport_drained=1;
    // A held runtime read must remain valid/stable and blocks BEGIN.
    pm_address=128;pm_valid=1;do @(posedge clk);while(!pm_ready);@(negedge clk);pm_valid=0;
    cfg_request(0);cfg_receipt(5);assert(pm_rsp_valid&&pm_data==image[8]&&certified);
    pm_rsp_ready=1;pause();pm_rsp_ready=0;
    cfg_generation=4;cfg_request(0);cfg_receipt(2);assert(certified);
    cfg_request(3);cfg_receipt(0);read_word(128,1);assert(!certified);
    $display("PASS lc_program_store seed=%0d bytes=352 instructions=3 PMbits=8192 CRCcycles=%0d totalcycles=%0d",seed,end_scan-begin_scan,cycle);$finish;
  end
  initial begin #1500000;$fatal(1,"LC PM timeout");end
endmodule
