`timescale 1ns/1ps
module tb_packet128_bridge;
  logic clk,reset,core_task_valid,core_task_ready,core_task_credit;
  logic [511:0] core_task_packet,core_return_packet;
  logic [7:0] core_task_target,tx_target,rx_source;
  logic tx_valid,tx_ready,tx_sop,tx_eop,tx_credit,rx_valid,rx_ready,rx_sop,rx_eop;
  logic [127:0] tx_data,rx_data;
  logic core_return_valid,core_return_ready,drained;
  logic [31:0] frame_fault_count;
  logic [511:0] expected;
  integer seed;
  initial clk=0;
  always #1 clk=~clk;
  mc_packet128_bridge dut(.*);
  task automatic pause(input integer n=1);repeat(n) @(negedge clk);endtask
  task automatic send_rx(input logic [511:0] value,input integer bad=0);
    for(integer word_index=0;word_index<(bad==3?5:4);word_index=word_index+1) begin
      @(negedge clk);rx_valid=1;rx_data=word_index<4?value[128*word_index+:128]:128'b0;
      rx_sop=word_index==0 || (bad==1&&word_index==2);rx_eop=word_index==(bad==3?4:3);
      rx_source=(bad==2&&word_index==1)?8'd7:value[24+:8];
      do @(posedge clk);while(!rx_ready);
      @(negedge clk);rx_valid=0;
    end
  endtask
  task automatic receive(input logic [511:0] value);
    while(!core_return_valid) @(negedge clk);
    assert(core_return_packet==value) else $fatal(1,"control frame payload/admission");
    pause(seed%3+2);assert(core_return_valid&&core_return_packet==value&&!rx_ready) else $fatal(1,"control receive buffer not finite/stable");
    core_return_ready=1;pause();core_return_ready=0;
  endtask
  initial begin
    reset=1;core_task_valid=0;core_task_packet=0;core_task_target=8;core_task_credit=1;
    tx_ready=0;rx_valid=0;rx_data=0;rx_source=0;rx_sop=0;rx_eop=0;core_return_ready=0;seed=1;
    if($value$plusargs("SEED=%d",seed)) begin end
    expected={128'habc00000000000000000000000000001,128'h12345678900000000000000000000000,
              128'hfedcba00000000000000000000000000,128'h76543210000000000000000008020002};
    expected[24+:8]=8;expected[0+:16]=2;
    pause(3);reset=0;pause();core_task_packet=expected;core_task_valid=1;
    for(integer word_index=0;word_index<4;word_index=word_index+1) begin
      pause(seed%3+1);
      assert(tx_valid&&tx_data==expected[128*word_index+:128]&&tx_target==8&&tx_sop==(word_index==0)&&tx_eop==(word_index==3)&&tx_credit) else $fatal(1,"transmit flit changed under backpressure");
      assert(!core_task_ready) else $fatal(1,"core accepted before actual EOP handshake");
      tx_ready=1;@(posedge clk);assert(core_task_ready==(word_index==3));
      @(negedge clk);tx_ready=0;
    end
    core_task_valid=0;pause();assert(drained);
    send_rx(expected);receive(expected);
    for(integer bad=1;bad<=3;bad=bad+1) begin send_rx(expected,bad);receive(0);end
    // Missing SOP and early EOP is one invalid frame; never a terminal packet.
    rx_data=expected[127:0];rx_source=8;rx_sop=0;rx_eop=1;rx_valid=1;pause();rx_valid=0;receive(0);
    assert(frame_fault_count==4&&drained) else $fatal(1,"framing fault did not drain");
    send_rx(expected);receive(expected);assert(drained);
    $display("PASS packet128 seed=%0d badframes=%0d RXbytes=64 TXflits=4",seed,frame_fault_count);$finish;
  end
  initial begin #100000;$fatal(1,"frame timeout");end
endmodule
