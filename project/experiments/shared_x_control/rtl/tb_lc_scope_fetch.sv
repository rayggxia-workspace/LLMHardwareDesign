`timescale 1ns/1ps
module tb_lc_scope_fetch;
  logic clk,reset;
  initial clk=0;
  always #5 clk=~clk;
  logic init_valid,init_ready,transport_drained,start_valid,start_ready;
  logic [31:0] init_generation,start_ticket,cancel_ticket,release_ticket;
  logic [127:0] start_owner,cancel_owner,release_owner;
  logic [63:0] start_reference;
  logic [15:0] start_bytes;
  logic cancel_valid,release_valid,release_ready,fetch_valid,fetch_ready;
  logic [7:0] fetch_status;
  logic [127:0] fetch_owner;
  logic [31:0] fetch_ticket;
  logic [1023:0] descriptor_data;
  logic mc_req_valid,mc_req_ready,mc_req_channel,mc_rsp_valid,mc_rsp_ready;
  logic [63:0] mc_req_address;
  logic [31:0] mc_req_tag,mc_rsp_tag;
  logic [4:0] mc_req_record_beats;
  logic mc_close_valid,mc_close_ready;
  logic [31:0] mc_close_tag_base;
  logic [511:0] mc_rsp_data;
  logic busy,cancelled;
  logic [1:0] outstanding_beats;
  logic [1:0] confirmed_beats;
  logic [31:0] protocol_fault_cycles;
  lc_scope_fetch128 dut(.*);
  logic [511:0] data[2];
  logic [31:0] tags[2],old_tag;
  integer seed,cycle,last_return,CRC_done,requests;
  string path;
  task automatic pause(input int n=1);repeat(n) @(negedge clk);endtask
  task automatic start(input int t);
    start_ticket=32'(t);start_owner=128'(t);start_valid=1;
    do @(posedge clk);while(!start_ready);@(negedge clk);start_valid=0;
  endtask
  task automatic request(input bit half);
    while(!mc_req_valid) @(negedge clk);
    assert(mc_req_address==start_reference+(half?64'd64:0)&&mc_req_record_beats==2&&mc_req_tag[0]==half&&mc_req_channel==start_reference[11]);
    tags[half]=mc_req_tag;pause(seed%3+1);
    assert(mc_req_valid&&mc_req_tag==tags[half]);mc_req_ready=1;pause();mc_req_ready=0;
  endtask
  task automatic response(input logic [31:0] tag,input logic [511:0] value);
    mc_rsp_valid=1;mc_rsp_tag=tag;mc_rsp_data=value;
    do @(posedge clk);while(!mc_rsp_ready);@(negedge clk);mc_rsp_valid=0;
  endtask
  task automatic take_result(input logic [7:0] status_code,input bit check_data=0);
    while(!fetch_valid) @(negedge clk);
    assert(fetch_status==status_code&&fetch_owner==start_owner&&fetch_ticket==start_ticket&&busy&&outstanding_beats==0&&confirmed_beats<=2);
    if(check_data) begin assert(descriptor_data=={data[1],data[0]});end
    pause(3);assert(fetch_valid&&fetch_status==status_code&&busy);
    fetch_ready=1;pause();fetch_ready=0;
    assert(busy&&!fetch_valid); // Consumer acceptance is not lease release.
    release_owner=start_owner;release_ticket=start_ticket;release_valid=1;
    do @(posedge clk);while(!release_ready);@(negedge clk);release_valid=0;assert(!busy);
  endtask
  always @(posedge clk) if(reset)begin cycle<=0;requests<=0;end else begin
    cycle<=cycle+1;if(mc_req_valid&&mc_req_ready)requests<=requests+1;
    assert(outstanding_beats<=2);
  end
  initial begin
    reset=1;init_valid=0;init_generation=1;transport_drained=1;start_valid=0;start_ticket=0;start_owner=0;
    start_reference=64'h4000;start_bytes=128;cancel_valid=0;cancel_owner=0;cancel_ticket=0;
    release_valid=0;release_owner=0;release_ticket=0;fetch_ready=0;
    mc_req_ready=0;mc_close_ready=0;mc_rsp_valid=0;mc_rsp_tag=0;mc_rsp_data=0;seed=1;
    if($value$plusargs("SEED=%d",seed))begin end
    path="descriptor.mem";if($value$plusargs("IMAGE=%s",path))begin end;$readmemh(path,data);
    pause(3);reset=0;pause();init_valid=1;
    do @(posedge clk);while(!init_ready);@(negedge clk);init_valid=0;
    start(10);request(0);request(1);assert(outstanding_beats==2);
    release_owner=1;release_ticket=1;release_valid=1;pause();assert(!release_ready&&busy);release_valid=0;
    response(tags[0]^32'h10000,data[0]);assert(outstanding_beats==2);
    response(tags[1],data[1]);response(tags[1],data[1]);assert(outstanding_beats==1);
    response(tags[0],data[0]);last_return=cycle;
    while(!fetch_valid)@(negedge clk);CRC_done=cycle;
    assert(CRC_done-last_return==124)else $fatal(1,"inline CRC not actual124byte readback: %0d",CRC_done-last_return);
    old_tag=tags[0];take_result(0,1);
    start(11);request(0);request(1);response(old_tag,data[0]);assert(outstanding_beats==2);
    response(tags[0],data[0]^512'd1);response(tags[1],data[1]);take_result(2);
    start(12);while(!mc_req_valid)@(negedge clk);pause(3);
    tags[0]=mc_req_tag;cancel_owner=start_owner;cancel_ticket=start_ticket;cancel_valid=1;pause();cancel_valid=0;
    assert(cancelled&&mc_req_valid&&mc_req_tag==tags[0]&&busy&&!fetch_valid);
    mc_req_ready=1;pause();mc_req_ready=0;pause(3);
    assert(!mc_req_valid&&outstanding_beats==1&&!fetch_valid);response(tags[0],data[0]);pause(3);
    assert(mc_close_valid&&mc_close_tag_base==tags[0]&&!fetch_valid&&busy&&outstanding_beats==0);
    mc_close_ready=1;pause();mc_close_ready=0;take_result(3);
    start(13);request(0);request(1);response(tags[0],data[0]);response(tags[1],data[1]);pause(7);
    cancel_owner=start_owner;cancel_ticket=start_ticket;cancel_valid=1;pause();cancel_valid=0;take_result(3);
    start_bytes=64;start(14);take_result(1);start_bytes=128;
    start_reference=64'h4040;start(15);take_result(1);
    assert(requests==7&&protocol_fault_cycles>=4);
    $display("PASS lc_scope_fetch seed=%0d requests=%0d CRCcycles=%0d faults=%0d total=%0d",seed,requests,CRC_done-last_return,protocol_fault_cycles,cycle);$finish;
  end
  initial begin #100000;$fatal(1,"scope fetch timeout");end
endmodule
