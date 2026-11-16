`timescale 1ns/1ps
module tb_copy_source_router;
  logic clk,reset;
  initial clk=0;
  always #5 clk=~clk;
  logic bind_valid,bind_ready,release_valid,release_ready,bound,drained;
  logic [1:0] bind_source,bound_source;
  logic [127:0] bind_key,release_key,bound_key;
  logic u_valid,u_ready,u_response_valid,u_response_ready,u_response_error;
  logic [9:0] u_address;
  logic [31:0] u_tag,u_response_tag;
  logic [127:0] u_response_data;
  logic [3:0] source_valid,source_ready,source_response_valid,source_response_ready,source_response_error;
  logic [39:0] source_address;
  logic [127:0] source_tag,source_response_tag;
  logic [511:0] source_response_data;
  logic [31:0] fault_cycles;
  early_copy_source_router dut(.*);
  task automatic pause(input int n=1);repeat(n) @(negedge clk);endtask
  task automatic bind_to(input logic [1:0] s,input logic [127:0] key);
    bind_source=s;bind_key=key;bind_valid=1;
    do @(posedge clk);while(!bind_ready);@(negedge clk);bind_valid=0;
    assert(bound&&bound_source==s&&bound_key==key);
  endtask
  initial begin
    reset=1;bind_valid=0;release_valid=0;bind_source=0;bind_key=0;release_key=1;
    u_valid=0;u_address=17;u_tag=32'h12340005;u_response_ready=0;
    source_ready=0;source_response_valid=0;source_response_tag=0;
    source_response_data=0;source_response_error=0;
    pause(3);reset=0;pause();bind_to(2,128'h1);
    // A proffered but unaccepted source request cannot be dropped by release.
    u_valid=1;release_valid=1;pause(3);
    assert(source_valid==4'b0100&&source_address=={10'b0,10'd17,20'b0}&&source_tag=={32'b0,u_tag,64'b0});
    assert(!u_ready&&source_response_ready==4'b1111);
    assert(!release_ready&&!drained&&bound);
    bind_valid=1;bind_source=3;bind_key=9;pause();assert(!bind_ready&&bound_source==2);
    bind_valid=0;source_ready=4'b0100;#1;assert(u_ready);pause();source_ready=0;u_valid=0;
    assert(!release_ready&&!drained);
    // Wrong-tag response drains but must retain the expected read/owner.
    source_response_tag[64+:32]=u_tag+1;source_response_valid=4'b0100;
    pause();source_response_valid=0;
    assert(!u_response_valid&&!release_ready&&bound);
    source_response_tag[64+:32]=u_tag;source_response_data[256+:128]=128'habc;
    source_response_valid=4'b0100;pause(2);
    assert(u_response_valid&&!source_response_ready[2]&&u_response_data==128'habc&&u_response_tag==u_tag&&!u_response_error);
    assert(!release_ready&&bound);
    u_response_ready=1;pause();source_response_valid=0;u_response_ready=0;
    // Wrong release key cannot end the lease; one fault per proffered cycle.
    release_key=2;pause();assert(bound&&!release_ready);
    release_key=1;pause();release_valid=0;assert(!bound);
    bind_to(1,128'h2);release_key=2;
    // Old source ACK during a new binding cannot become the new source ACK.
    source_response_valid=4'b0100;pause();source_response_valid=0;
    assert(bound&&bound_source==1&&!u_response_valid);
    assert(fault_cycles==3) else $fatal(1,"router unexpected fault count %0d",fault_cycles);
    release_valid=1;pause();release_valid=0;assert(!bound&&drained);
    $display("PASS copy_source_router held offer, wrong tag/key, old source, finite drain");$finish;
  end
  initial begin #10000;$fatal(1,"router timeout");end
endmodule
