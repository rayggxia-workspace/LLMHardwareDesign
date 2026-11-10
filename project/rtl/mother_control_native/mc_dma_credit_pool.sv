`timescale 1ns/1ps
// MC-owned finite credit bank. Instantiate separately for CLASS_ID=0 (64B
// beats) and CLASS_ID=1 (record descriptors); each has TWO channels x32.
// Allocation is a reservation, POST is actual downstream issue, RETURN is
// real completion. Unissued cancellation may release RESERVED, never ISSUED.
// No payload buffering and no inference of issue/completion from LC idleness.
module mc_dma_credit_pool #(parameter logic [5:0] CLASS_ID=0)(
  input logic clk,reset,halt,
  input logic init_valid,input logic [31:0] init_generation,
  input logic transport_drained,
  output logic init_ready,session_valid,
  input logic [2:0] reserve_valid,reserve_channel,
  input logic [11:0] reserve_owner,
  output logic [2:0] reserve_ready,
  output logic [191:0] reserve_ticket,
  input logic [2:0] offer_valid,
  input logic [191:0] offer_ticket,
  output logic [2:0] offer_ready,
  input logic [2:0] post_valid,
  input logic [191:0] post_ticket,
  output logic [2:0] post_ready,
  input logic [2:0] return_valid,return_unissued_cancel,
  input logic [191:0] return_ticket,
  output logic [2:0] return_ready,
  output logic [6:0] occupied_total,
  output logic [11:0] occupied_channels,
  output logic [53:0] occupied_targets,
  output logic [31:0] protocol_fault_count
);
  typedef enum logic [1:0] {FREE,RESERVED,OFFERED,ISSUED} credit_state_t;
  credit_state_t state[64],next_state[64];
  logic [3:0] owner[64],next_owner[64];
  logic [15:0] serial[64],next_serial[64];
  logic [31:0] generation,fault_next;
  integer counts[9];
  integer lane,slot,chosen,target;
  logic [5:0] return_slot,post_slot;
  logic [63:0] ticket;
  logic match;
  assign init_ready=!reset && transport_drained && occupied_total==0 && init_generation>generation;
  assign post_ready={3{!reset&&session_valid}};
  assign offer_ready={3{!reset&&session_valid}};
  assign return_ready={3{!reset&&session_valid}};
  always_comb begin
    occupied_total=0;occupied_channels=0;occupied_targets=0;
    for(integer entry=0;entry<64;entry=entry+1) if(state[entry]!=FREE) begin
      occupied_total=occupied_total+1'b1;
      occupied_channels[6*(entry/32)+:6]=occupied_channels[6*(entry/32)+:6]+1'b1;
      if(owner[entry]<9) occupied_targets[6*owner[entry]+:6]=occupied_targets[6*owner[entry]+:6]+1'b1;
    end
  end
  always_comb begin
    for(slot=0;slot<64;slot=slot+1) begin
      next_state[slot]=state[slot];next_owner[slot]=owner[slot];next_serial[slot]=serial[slot];
    end
    reserve_ready=0;reserve_ticket=0;fault_next=protocol_fault_count;
    counts[0]=0;counts[1]=0;counts[2]=0;counts[3]=0;counts[4]=0;
    counts[5]=0;counts[6]=0;counts[7]=0;counts[8]=0;
    ticket=0;match=0;return_slot=0;post_slot=0;chosen=-1;target=0;
    // In lane order, a duplicate simultaneous return is accepted only once.
    for(lane=0;lane<3;lane=lane+1) if(return_valid[lane]&&return_ready[lane]) begin
      ticket=return_ticket[64*lane+:64];return_slot=ticket[15:10];
      match=ticket[63:32]==generation && ticket[31:16]==next_serial[return_slot] &&
          ticket[9:6]==next_owner[return_slot] && ticket[5:0]==CLASS_ID &&
          (return_unissued_cancel[lane] ? next_state[return_slot]==RESERVED : next_state[return_slot]==ISSUED);
      if(match) next_state[return_slot]=FREE;
      else if(fault_next!=32'hffffffff) fault_next=fault_next+1;
    end
    for(lane=0;lane<3;lane=lane+1) if(offer_valid[lane]&&offer_ready[lane]) begin
      ticket=offer_ticket[64*lane+:64];post_slot=ticket[15:10];
      match=ticket[63:32]==generation && ticket[31:16]==next_serial[post_slot] &&
          ticket[9:6]==next_owner[post_slot] && ticket[5:0]==CLASS_ID && next_state[post_slot]==RESERVED;
      if(match) next_state[post_slot]=OFFERED;
      else if(fault_next!=32'hffffffff) fault_next=fault_next+1;
    end
    for(lane=0;lane<3;lane=lane+1) if(post_valid[lane]&&post_ready[lane]) begin
      ticket=post_ticket[64*lane+:64];post_slot=ticket[15:10];
      match=ticket[63:32]==generation && ticket[31:16]==next_serial[post_slot] &&
          ticket[9:6]==next_owner[post_slot] && ticket[5:0]==CLASS_ID && next_state[post_slot]==OFFERED;
      if(match) next_state[post_slot]=ISSUED;
      else if(fault_next!=32'hffffffff) fault_next=fault_next+1;
    end
    for(slot=0;slot<64;slot=slot+1) if(next_state[slot]!=FREE) begin
      if(next_owner[slot]<9) counts[next_owner[slot]]=counts[next_owner[slot]]+1;
    end
    for(lane=0;lane<3;lane=lane+1) begin
      target=int'(reserve_owner[4*lane+:4]);chosen=-1;
      for(slot=31;slot>=0;slot=slot-1) if(next_state[32*int'(reserve_channel[lane])+slot]==FREE &&
          next_serial[32*int'(reserve_channel[lane])+slot]!=16'hffff) chosen=32*int'(reserve_channel[lane])+slot;
      if(!reset && session_valid && !halt && !init_valid && target<9 && chosen>=0 && counts[target]<32) begin
        reserve_ready[lane]=1;
        reserve_ticket[64*lane+:64]={generation,next_serial[chosen]+16'd1,6'(chosen),4'(target),CLASS_ID};
        if(reserve_valid[lane]) begin
          next_state[chosen]=RESERVED;next_owner[chosen]=4'(target);next_serial[chosen]=next_serial[chosen]+1'b1;
          counts[target]=counts[target]+1;
        end
      end
    end
  end
  always_ff @(posedge clk) begin
    if(reset) begin
      generation<=0;session_valid<=0;protocol_fault_count<=0;
      for(integer entry=0;entry<64;entry=entry+1) begin state[entry]<=FREE;owner[entry]<=0;serial[entry]<=0;end
    end else begin
      protocol_fault_count<=fault_next;
      for(integer entry=0;entry<64;entry=entry+1) begin state[entry]<=next_state[entry];owner[entry]<=next_owner[entry];serial[entry]<=next_serial[entry];end
      if(init_valid&&init_ready) begin
        generation<=init_generation;session_valid<=1;
        // Same generation never resets serial; a new session requires actual
        // transport drain, so old tickets cannot alias a freshly cleared slot.
        for(integer entry=0;entry<64;entry=entry+1) serial[entry]<=0;
      end
`ifndef SYNTHESIS
      assert(occupied_total<=64 && occupied_channels[5:0]<=32 && occupied_channels[11:6]<=32) else $fatal(1,"MC channel credits overflow");
      for(integer group=0;group<9;group=group+1) assert(occupied_targets[6*group+:6]<=32) else $fatal(1,"MC target credits overflow");
`endif
    end
  end
endmodule
