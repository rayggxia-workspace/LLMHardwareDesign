`timescale 1ns/1ps
module tb_dma_credit_pool #(parameter logic [5:0] CLASS_ID=0);
  logic clk,reset,halt,init_valid,transport_drained,init_ready,session_valid;
  logic [31:0] init_generation,protocol_fault_count;
  logic [2:0] reserve_valid,reserve_channel,reserve_ready,post_valid,post_ready,return_valid,return_unissued_cancel,return_ready;
  logic [11:0] reserve_owner;
  logic [191:0] reserve_ticket,post_ticket,return_ticket;
  logic [2:0] offer_valid,offer_ready;
  logic [191:0] offer_ticket;
  logic [6:0] occupied_total;
  logic [11:0] occupied_channels;
  logic [53:0] occupied_targets;
  logic [63:0] tickets[64],old_ticket,new_ticket;
  logic [31:0] faults;
  integer seed;
  initial clk=0;
  always #1 clk=~clk;
  mc_dma_credit_pool #(.CLASS_ID(CLASS_ID)) dut(.*);
  task automatic pause(input integer n=1);repeat(n) @(negedge clk);endtask
  task automatic reserve(input bit channel,input logic [3:0] owner_id,output logic [63:0] result);
    @(negedge clk);reserve_channel[0]=channel;reserve_owner[3:0]=owner_id;reserve_valid=1;
    do @(posedge clk);while(!reserve_ready[0]);result=reserve_ticket[63:0];
    @(negedge clk);reserve_valid=0;
  endtask
  task automatic post(input logic [63:0] value,input bit already_offered=0);
    @(negedge clk);offer_ticket[63:0]=value;offer_valid=already_offered?0:1;post_ticket[63:0]=value;post_valid=1;
    @(posedge clk);assert(post_ready==7&&offer_ready==7);@(negedge clk);post_valid=0;offer_valid=0;
  endtask
  task automatic give_back(input logic [63:0] value,input bit unissued=0);
    @(negedge clk);return_ticket[63:0]=value;return_unissued_cancel[0]=unissued;return_valid=1;
    @(posedge clk);assert(return_ready==7);@(negedge clk);return_valid=0;
  endtask
  initial begin
    reset=1;halt=0;init_valid=0;init_generation=1;transport_drained=0;
    reserve_valid=0;reserve_channel=0;reserve_owner=0;post_valid=0;post_ticket=0;
    offer_valid=0;offer_ticket=0;
    return_valid=0;return_unissued_cancel=0;return_ticket=0;seed=1;
    if($value$plusargs("SEED=%d",seed)) begin end
    pause(3);reset=0;pause();init_valid=1;pause();
    assert(!session_valid&&!init_ready) else $fatal(1,"cold credit init lacked transport drain");
    transport_drained=1;pause();init_valid=0;transport_drained=0;pause();
    assert(session_valid) else $fatal(1,"credit boot");
    for(integer i=0;i<32;i=i+1) begin reserve(0,0,tickets[i]);post(tickets[i]);end
    assert(occupied_channels==12'd32&&occupied_total==32&&occupied_targets[5:0]==32) else $fatal(1,"channel0/target0 bound");
    reserve_owner[3:0]=2;reserve_channel[0]=0;pause();
    assert(!reserve_ready[0]) else $fatal(1,"channel0 borrowed channel1 capacity");
    reserve_channel[0]=1;pause();assert(reserve_ready[0]) else $fatal(1,"channel1 blocked by channel0 full");
    for(integer i=32;i<64;i=i+1) begin reserve(1,1,tickets[i]);post(tickets[i]);end
    assert(occupied_total==64&&occupied_channels=={6'd32,6'd32}) else $fatal(1,"two channel capacity");
    faults=protocol_fault_count;
    old_ticket=tickets[0];give_back(old_ticket^64'h40); // wrong source owner
    give_back(old_ticket^64'h10000); // wrong serial
    give_back(old_ticket^64'h100000000); // wrong session generation
    give_back(old_ticket^64'h1); // wrong credit class
    give_back(old_ticket,1); // issued request cannot cancel/free before response
    assert(protocol_fault_count==faults+5&&occupied_total==64) else $fatal(1,"bad ticket freed outstanding DMA");
    give_back(old_ticket);assert(occupied_total==63);
    reserve(0,0,new_ticket);assert(new_ticket!=old_ticket&&occupied_total==64);
    give_back(old_ticket);assert(occupied_total==64&&protocol_fault_count==faults+6) else $fatal(1,"late return freed reused credit");
    post(new_ticket);tickets[0]=new_ticket;
    for(integer i=0;i<64;i=i+1) give_back(tickets[i]);
    assert(occupied_total==0&&occupied_channels==0&&occupied_targets==0) else $fatal(1,"credit did not drain");
    // Three simultaneous reservations are real distinct entries, not one slot
    // replicated in three ready signals. They do not grant DDR bandwidth.
    reserve_owner={4'd2,4'd1,4'd0};reserve_channel=3'b010;reserve_valid=7;
    @(posedge clk);assert(reserve_ready==7);tickets[0]=reserve_ticket[63:0];tickets[1]=reserve_ticket[127:64];tickets[2]=reserve_ticket[191:128];
    assert(tickets[0]!=tickets[1]&&tickets[0]!=tickets[2]&&tickets[1]!=tickets[2]);
    @(negedge clk);reserve_valid=0;halt=1;pause();assert(reserve_ready==0&&occupied_total==3);
    give_back(tickets[0],1); // reserved but never proffered to DDR
    offer_ticket[63:0]=tickets[1];offer_valid=1;pause();offer_valid=0;
    give_back(tickets[1],1);assert(occupied_total==2&&protocol_fault_count==faults+7) else $fatal(1,"offered request cancelled before real acceptance/drain");
    post(tickets[1],1);post(tickets[2]);
    init_generation=2;transport_drained=1;init_valid=1;pause();assert(!init_ready&&occupied_total==2);
    init_valid=0;transport_drained=0;
    give_back(tickets[2]);pause(seed%3);give_back(tickets[1]);assert(occupied_total==0);
    init_valid=1;transport_drained=0;pause();assert(!init_ready);transport_drained=1;pause();init_valid=0;halt=0;
    give_back(tickets[1]);assert(occupied_total==0&&protocol_fault_count==faults+8) else $fatal(1,"old-session late return accepted");
    reserve(0,8,new_ticket);give_back(new_ticket,1);assert(occupied_total==0);
    reserve(0,8,new_ticket);post(new_ticket);
    return_ticket[63:0]=new_ticket;return_ticket[127:64]=new_ticket;return_unissued_cancel=0;return_valid=3;
    pause();return_valid=0;assert(occupied_total==0&&protocol_fault_count==faults+9) else $fatal(1,"simultaneous duplicate return retired twice");
    $display("PASS MC credits class=%0d seed=%0d faults=%0d channels=32+32 targets=9 max_each=32",CLASS_ID,seed,protocol_fault_count);
    $finish;
  end
  initial begin #100000; $fatal(1,"credit timeout");end
endmodule
