// Refs250: finite shared read-DMA transport. Internal MC fabric, not a leaf
// pin contract. Twelve registered clients: LC scopes0..8 and M weights9..11.
// Six 64B return skids (384B) and all ownership tables count as active area.
module mc_dma_fabric_typed_p #(
 parameter [15:0] SERIAL_LIMIT=16'hffff,
 parameter integer SKIDS_PER_CHANNEL=3
) (
 input wire clk,reset,
 // Runtime mode has independent real local and transport drain proofs.
 // A rejected request consumes VALID for diagnosis but creates no owner.
 input wire [2:0] p_mode_valid,p_mode_native64,p_mode_client_drained,
 output reg [2:0] p_mode_ready,p_mode_active,p_req_rejected,
 input wire [11:0] c_req_valid,output reg [11:0] c_req_ready,
 input wire [767:0] c_req_address,input wire [383:0] c_req_tag,
 input wire [11:0] c_req_channel,input wire [59:0] c_req_record_beats,
 output reg [11:0] c_rsp_valid,input wire [11:0] c_rsp_ready,
 output reg [383:0] c_rsp_tag,output reg [6143:0] c_rsp_data,
 input wire [11:0] c_close_valid,output reg [11:0] c_close_ready,
 input wire [383:0] c_close_tag_base,
 input wire [11:0] c_cancel_valid,output reg [11:0] c_cancel_ready,
 input wire [383:0] c_cancel_tag,
 output reg [11:0] c_cancel_ack_valid,input wire [11:0] c_cancel_ack_ready,
 output reg [383:0] c_cancel_ack_tag,output reg [11:0] c_cancel_ack_rejected,
 input wire [11:0] c_fence_valid,output wire [11:0] c_fence_ready,
 input wire [383:0] c_fence_cookie,input wire [107:0] c_fence_epoch,
 output reg [11:0] c_fence_done_valid,input wire [11:0] c_fence_done_ready,
 output reg [383:0] c_fence_done_cookie,output reg [107:0] c_fence_done_epoch,
 output reg [3:0] d_req_valid,input wire [3:0] d_req_ready,
 output reg [255:0] d_req_address,output reg [255:0] d_req_tag,
 input wire [3:0] d_rsp_valid,output reg [3:0] d_rsp_ready,
 input wire [255:0] d_rsp_tag,input wire [2047:0] d_rsp_data,
 output wire d_fence_valid,input wire d_fence_ready,output wire [31:0] d_fence_generation,
 input wire d_fence_done_valid,output wire d_fence_done_ready,
 input wire [31:0] d_fence_done_generation,
 output reg fault_valid,input wire fault_ready,output reg [7:0] fault_kind,
 output reg [3:0] fault_client,output reg [31:0] fault_local_tag,
 output reg [63:0] fault_global_tag,
 output reg [11:0] debug_beats,debug_descriptors,
 output wire [31:0] debug_generation
);
 reg [2:0] native_tag_seen;
 reg [30:0] last_native_serial[0:2];
 localparam [2:0] FREE=0,RESERVED=1,OFFERED=2,ISSUED=3,RETURNING=4;
 reg [2:0] b_state[0:63];reg [15:0] b_serial[0:63];
 reg [3:0] b_client[0:63];reg [31:0] b_local[0:63];
 reg [63:0] b_address[0:63];reg [5:0] b_desc[0:63];
 reg [63:0] desc_live,desc_closed;
 reg [3:0] desc_client[0:63];reg [31:0] desc_base[0:63];
 reg [63:0] desc_address[0:63];reg [4:0] desc_length[0:63],desc_next[0:63];
 reg [17:0] desc_accepted[0:63],desc_returned[0:63],desc_cancelled[0:63];
 localparam integer SKIDS=2*SKIDS_PER_CHANNEL;
 reg [3:0] offer_valid;reg [SKIDS-1:0] skid_valid;
 reg [5:0] offer_entry[0:3],skid_entry[0:SKIDS-1];
 // Ownership is stable from DDR return capture until the client consumes
 // this skid. Latch it beside the payload so replay never reads the beat table.
 reg [3:0] skid_client[0:SKIDS-1];
 reg [31:0] skid_local_tag[0:SKIDS-1];
 reg [5:0] skid_descriptor[0:SKIDS-1];
 reg [4:0] skid_beat[0:SKIDS-1];
 reg [511:0] skid_data[0:SKIDS-1];
 reg [11:0] response_locked;
 reg [SKIDS-1:0] response_slot[0:11],response_rr[0:11];
 wire [SKIDS-1:0] response_selected[0:11];
 reg [11:0] request_rr[0:1];reg [4:0] issue_rr[0:1];
 reg [1:0] previous_issues[0:1];
 reg [31:0] transport_generation;
 // A finite namespace exhaustion invokes actual transport purge, even when
 // a logical descriptor remains open. No old beat may remain in any stage.
 localparam [2:0] F_IDLE=0,F_DRAIN=1,F_OFFER=2,F_WAIT=3,F_REPLY=4;
 reg [2:0] fence_state;reg fence_external;reg [3:0] fence_client;
 reg [31:0] fence_cookie;reg [8:0] fence_epoch;
 wire fault_space=!fault_valid||fault_ready;
 assign d_fence_valid=fence_state==F_OFFER;
 assign d_fence_generation=transport_generation+32'd1;
 // A simultaneous invalid DDR packet owns the one diagnostic slot first.
 // Do not consume a second invalid fence completion without its diagnostic.
 assign d_fence_done_ready=fault_space&&(!d_fence_done_valid||
  (fence_state==F_WAIT&&d_fence_done_generation==transport_generation+32'd1)||
  (new_fault&&new_fault_kind==8'd2));
 assign debug_generation=transport_generation;
 function automatic [31:0] tag_base(input integer client,input [31:0] unused_tag);
  tag_base=client<9?{unused_tag[31:1],1'b0}:{unused_tag[31:5],5'd0};
 endfunction
 function automatic integer beat_index(input integer client,input [31:0] unused_tag);
  beat_index=client<9?int'({31'd0,unused_tag[0]}):int'({27'd0,unused_tag[4:0]});
 endfunction
 function automatic [63:0] global_tag(input [5:0] entry);
  global_tag={transport_generation,b_serial[entry],6'(entry),b_client[entry],6'd0};
 endfunction
 // The caller checks for an empty mask. Each step halves the search range.
 function automatic [5:0] first_set(input [63:0] mask);
  reg [63:0] remaining;
  remaining=mask;
  for(integer level=5;level>=0;level=level-1)begin
   first_set[level]=!(|(remaining & (64'hffff_ffff_ffff_ffff >> (64-(1<<level)))));
   if(first_set[level])remaining=remaining>>(1<<level);
  end
 endfunction
 // Two available slots are selected from an independent per-channel mask.
 function automatic [11:0] first_two_slots(input [31:0] available);
  reg [4:0] first_slot,second_slot;
  reg [31:0] remaining;
  first_slot=5'(first_set({32'd0,available}));
  remaining=available&~(32'd1<<first_slot);
  second_slot=5'(first_set({32'd0,remaining}));
  first_two_slots={|remaining,second_slot,|available,first_slot};
 endfunction
 // The cursor mask starts at the next client. Prefer that suffix before
 // wrapping to the lower-numbered clients.
 function automatic [11:0] first_request(input [11:0] eligible,input [11:0] cursor_mask);
  reg [11:0] suffix,scan;
  suffix=eligible&cursor_mask;
  scan=(|suffix)?suffix:eligible;
  for(integer client=0;client<12;client=client+1)
   first_request[client]=scan[client]&&!(|(scan&((12'd1<<client)-12'd1)));
 endfunction
 function automatic [3:0] request_index(input [11:0] selected);
  request_index=0;
  for(integer client=0;client<12;client=client+1)
   request_index=request_index|({4{selected[client]}}&4'(client));
 endfunction
 function automatic [11:0] before_request(input [11:0] selected,input [11:0] cursor_mask);
  reg selected_in_suffix;
  selected_in_suffix=|(selected&cursor_mask);
  for(integer client=0;client<12;client=client+1)
   before_request[client]=(cursor_mask[client]&&!selected_in_suffix)||
       (cursor_mask[client]==selected_in_suffix&&(|(selected>>(client+1))));
 endfunction

 reg [11:0] accepted_client;
 reg [3:0] grant_valid,grant_new;
 reg [3:0] grant_client[0:3];
 reg [5:0] grant_entry[0:3],grant_desc[0:3];
 reg [4:0] grant_beat[0:3],grant_length[0:3];
 reg [31:0] grant_tag[0:3],grant_base[0:3];
 reg [63:0] grant_address[0:3];
 integer cancel_client,close_desc,close_client;
 reg cancel_good,close_good;
 integer new_offer_entry[0:3];reg [3:0] offer_fire,return_capture;reg [SKIDS-1:0] skid_forward;
 integer return_entry[0:3],return_slot[0:3];
 reg new_fault;reg [7:0] new_fault_kind;reg [3:0] new_fault_client;
 reg [31:0] new_fault_local;reg [63:0] new_fault_global;
 integer issue_counts[0:1];
 wire [6:0] client_counts[0:11];
 wire [63:0] live_beats,exhausted_free_entries;
 wire [11:0] client_has_descriptor;
 wire [11:0] free_beat_slots[0:1],free_descriptor_slots[0:1];
 wire begin_auto_fence=|exhausted_free_entries;
 integer c,ch,i,j,e,d,slot,n,chosen,free_entry,free_desc;
 reg [1:0] grant;
 integer budget,held;
 wire signed [31:0] request_desc[0:11];
 wire [5:0] close_match[0:11];
 wire [11:0] close_matched,close_legal;
 reg [11:0] close_candidates;
 reg [3:0] close_candidate;
 integer first_free_beat,second_free_beat,first_free_desc,second_free_desc,new_descs;
 wire [11:0] invalid_requests,new_requests,request_has_credit;
 wire [4:0] request_beat[0:11];
 reg [11:0] request_bad_now,channel_requests,request_remaining,request_eligible,bad_in_order,request_selected;
 reg [3:0] invalid_return_lanes;
 reg [1:0] invalid_return_lane;
 reg duplicate_return,previous_lane_uses_slot;
 reg [31:0] issue_remaining;
 reg [4:0] issue_offset;
 wire [11:0] cancel_candidates=c_cancel_valid&(~c_cancel_ack_valid|c_cancel_ack_ready);
 wire [3:0] cancel_candidate=4'(first_set({52'd0,cancel_candidates}));
 wire [31:0] cancel_tag=c_cancel_tag[cancel_candidate*32+:32];
 wire [63:0] cancel_matches_reversed,issue_candidates;
 wire [5:0] cancel_match=~first_set(cancel_matches_reversed);
 wire cancel_matched=(|cancel_candidates)&&(|cancel_matches_reversed);
 for(genvar entry=0;entry<64;entry=entry+1) begin: beat_inventory
  assign live_beats[entry]=b_state[entry]!=FREE;
  // Preserve the highest matching entry, including a non-reserved match.
  assign cancel_matches_reversed[63-entry]=live_beats[entry]&&
     b_client[entry]==cancel_candidate&&b_local[entry]==cancel_tag;
  assign issue_candidates[entry]=b_state[entry]==RESERVED&&
     !(cancel_matched&&cancel_match==6'(entry));
  assign exhausted_free_entries[entry]=!live_beats[entry]&&b_serial[entry]==SERIAL_LIMIT;
 end
 for(genvar client=0;client<12;client=client+1) begin: client_inventory
  wire [63:0] owned_beats,owned_descriptors;
  for(genvar entry=0;entry<64;entry=entry+1) begin: owner_match
   assign owned_beats[entry]=live_beats[entry]&&b_client[entry]==4'(client);
   assign owned_descriptors[entry]=desc_live[entry]&&desc_client[entry]==4'(client);
  end
  assign client_counts[client]=7'($countones(owned_beats));
  assign client_has_descriptor[client]=|owned_descriptors;
 end
 for(genvar channel=0;channel<2;channel=channel+1) begin: channel_inventory
  assign free_beat_slots[channel]=first_two_slots(
      ~live_beats[channel*32+:32]&~exhausted_free_entries[channel*32+:32]);
  assign free_descriptor_slots[channel]=first_two_slots(~desc_live[channel*32+:32]);
 end
 // The request plan can suppress a same-cycle fence for its client. Select
 // the first eligible fence from the resulting mask in parallel.
 wire [11:0] fence_candidates=c_fence_valid&~accepted_client&~client_has_descriptor&
     {12{!reset&&fence_state==F_IDLE&&!begin_auto_fence}};
 wire begin_fence=|fence_candidates;
 wire [3:0] selected_fence=4'(first_set({52'd0,fence_candidates}));
 assign c_fence_ready[0]=fence_candidates[0];
 for(genvar client=1;client<12;client=client+1) begin: fence_priority
  assign c_fence_ready[client]=fence_candidates[client]&&!(|fence_candidates[client-1:0]);
 end
 assign debug_beats={6'($countones(live_beats[63:32])),6'($countones(live_beats[31:0]))};
 assign debug_descriptors={6'($countones(desc_live[63:32])),6'($countones(desc_live[31:0]))};
 // A descriptor remains live through its last held return, even if
 // backend service completed earlier. Mode updates can never overlap a new
 // request or pending close/cancel/fence, nor an unconsumed local DONE.
 always @*begin: typed_mode_admission
  for(integer m=0;m<3;m=m+1)begin
   p_mode_ready[m]=!reset&&fence_state==F_IDLE&&p_mode_client_drained[m]&&
       !c_req_valid[m]&&!c_close_valid[m]&&!c_cancel_valid[m]&&!c_cancel_ack_valid[m]&&
       !c_fence_valid[m]&&!(fault_valid&&fault_client==4'(m))&&
       client_counts[m]==7'd0&&!client_has_descriptor[m];
  end
 end
 // These physical outputs depend only on registered ownership. Keep them
 // outside the request/return planning block to expose the real acyclic
 // interface dependencies to lint, composition and synthesis.
 always @*begin: registered_backend_offer
  d_req_valid=reset?4'd0:offer_valid;d_req_address=0;d_req_tag=0;
  for(integer ol=0;ol<4;ol=ol+1)if(offer_valid[ol])begin
   d_req_address[ol*64+:64]=b_address[offer_entry[ol]];
   d_req_tag[ol*64+:64]=global_tag(offer_entry[ol]);
  end
 end
 // Select the first eligible skid in cyclic slot order. Each possible
 // cursor supplies a constant predecessor mask for each slot.
 for(genvar rc=0;rc<12;rc=rc+1)begin: response_client
  wire [SKIDS-1:0] eligible;
  for(genvar skid=0;skid<SKIDS;skid=skid+1)begin: response_slot_choice
   wire [SKIDS-1:0] head_wins;
   assign eligible[skid]=skid_valid[skid]&&skid_client[skid]==4'(rc);
   for(genvar head=0;head<SKIDS;head=head+1)begin: response_head
    localparam integer DISTANCE=(skid+SKIDS-head)%SKIDS;
    wire [SKIDS-1:0] earlier;
    for(genvar prev=0;prev<SKIDS;prev=prev+1)begin: response_predecessor
     assign earlier[prev]=((prev+SKIDS-head)%SKIDS < DISTANCE)?eligible[prev]:1'b0;
    end
    assign head_wins[head]=response_rr[rc][head]&&!(|earlier);
   end
   assign response_selected[rc][skid]=!reset&&
     (response_locked[rc]?(response_slot[rc][skid]&&skid_valid[skid]):
       (eligible[skid]&&(|head_wins)));
  end
 end
 always @*begin: registered_client_response
  c_rsp_valid=0;c_rsp_tag=0;c_rsp_data=0;
  for(integer client=0;client<12;client=client+1)begin
   c_rsp_valid[client]=|response_selected[client];
   for(integer skid=0;skid<SKIDS;skid=skid+1)begin
    c_rsp_tag[client*32+:32]=c_rsp_tag[client*32+:32]|
      ({32{response_selected[client][skid]}}&skid_local_tag[skid]);
    c_rsp_data[client*512+:512]=c_rsp_data[client*512+:512]|
      ({512{response_selected[client][skid]}}&skid_data[skid]);
   end
  end
 end
 always @*begin: actual_client_consumption
  skid_forward=0;
  for(integer client=0;client<12;client=client+1)
   skid_forward=skid_forward|(response_selected[client]&{SKIDS{c_rsp_ready[client]}});
 end
 always @*begin: registered_fence_reply
  c_fence_done_valid=0;c_fence_done_cookie=0;c_fence_done_epoch=0;
  if(!reset&&fence_state==F_REPLY&&fence_external)begin
   c_fence_done_valid[fence_client]=1;c_fence_done_cookie[int'(fence_client)*32+:32]=fence_cookie;
   c_fence_done_epoch[int'(fence_client)*9+:9]=fence_epoch;
  end
 end
 always @*offer_fire=offer_valid&d_req_ready;
 // Compare each client's tags in parallel and keep the highest matching
 // descriptor, as in the ascending overwrite scan.
 for(genvar client=0;client<12;client=client+1)begin: descriptor_lookup
  wire [31:0] request_base=tag_base(client,c_req_tag[client*32+:32]);
  wire [31:0] close_base=c_close_tag_base[client*32+:32];
  wire [63:0] request_matches,close_matches;
  for(genvar entry=0;entry<64;entry=entry+1)begin: descriptor_entry
   wire owned=desc_live[entry]&&desc_client[entry]==4'(client);
   assign request_matches[63-entry]=owned&&
      (client<3||1'(entry/32)==c_req_channel[client])&&desc_base[entry]==request_base;
   assign close_matches[63-entry]=owned&&desc_base[entry]==close_base;
  end
  wire [5:0] request_match=~first_set(request_matches);
  assign request_desc[client]=(|request_matches)?int'(request_match):-1;
  assign close_match[client]=~first_set(close_matches);
  assign close_matched[client]=|close_matches;
  assign close_legal[client]=close_matched[client]&&!desc_closed[close_match[client]]&&
    close_base==tag_base(client,close_base);
 end
 // Validate all source offers in parallel. Arbitration only selects which
 // of the eligible offers can reserve the two physical entries this cycle.
 for(genvar client=0;client<12;client=client+1)begin: request_validation
  wire [31:0] tag=c_req_tag[client*32+:32];
  wire [4:0] length=c_req_record_beats[client*5+:5];
  wire [63:0] address=c_req_address[client*64+:64];
  wire [63:0] record_address=address-{53'd0,request_beat[client],6'd0};
  wire [5:0] owner=6'(request_desc[client]);
  wire bad_record_shape;
  assign request_beat[client]=5'(beat_index(client,tag));
  assign new_requests[client]=request_desc[client]<0;
  assign request_has_credit[client]=client_counts[client]<7'd32;
  if(client<3)begin: native_or_legacy
   assign bad_record_shape=p_mode_active[client]?
      (length!=1||tag[0]||(native_tag_seen[client]&&tag[31:1]<=last_native_serial[client])):
      (length!=2||record_address[6:0]!=0);
  end else if(client<9)begin: legacy_record
   assign bad_record_shape=length!=2||record_address[6:0]!=0;
  end else begin: weight_record
   assign bad_record_shape=length!=17&&length!=18;
  end
  assign invalid_requests[client]=address[5:0]!=0||bad_record_shape||request_beat[client]>=length||
    (new_requests[client]?(request_beat[client]!=0||record_address[11]!=c_req_channel[client]):
      (owner[5]!=c_req_channel[client]||desc_closed[owner]||desc_length[owner]!=length||
       desc_next[owner]!=request_beat[client]||desc_address[owner]!=record_address));
 end
 // Compare the returned tag against fixed entries in its physical channel.
 // The entry field selects one already compared result instead of driving
 // three variable reads from the owner table.
 wire [3:0] return_owner_matches;
 for(genvar lane=0;lane<4;lane=lane+1)begin: return_owner
  wire [63:0] tag=d_rsp_tag[lane*64+:64];
  wire [31:0] entries;
  for(genvar index=0;index<32;index=index+1)begin: entry_match
   localparam integer ENTRY=(lane/2)*32+index;
   assign entries[index]=tag[14:10]==5'(index)&&b_state[ENTRY]==ISSUED&&
       tag[31:16]==b_serial[ENTRY]&&tag[9:6]==b_client[ENTRY];
  end
  assign return_owner_matches[lane]=tag[63:32]==transport_generation&&
      tag[15]==1'(lane/2)&&tag[5:0]==6'd0&&(|entries);
 end
 // Combinational plans are applied atomically by the sequential owner table.
 always @* begin
  c_req_ready=0;c_close_ready=0;c_cancel_ready=0;p_req_rejected=0;
  d_rsp_ready=0;
  return_capture=0;
  new_fault=0;new_fault_kind=0;new_fault_client=0;new_fault_local=0;new_fault_global=0;
  accepted_client=0;grant_valid=0;grant_new=0;grant=0;
  invalid_return_lanes=0;invalid_return_lane=0;
  duplicate_return=0;previous_lane_uses_slot=0;
  issue_remaining=0;issue_offset=0;
  cancel_client=-1;cancel_good=0;close_desc=-1;close_client=-1;close_good=0;
  close_candidates=0;close_candidate=0;
  request_bad_now=invalid_requests;channel_requests=0;request_remaining=0;
  request_eligible=0;bad_in_order=0;request_selected=0;
  chosen=0;free_entry=0;free_desc=0;budget=0;held=0;slot=0;n=0;e=0;d=0;c=0;
  first_free_beat=-1;second_free_beat=-1;first_free_desc=-1;second_free_desc=-1;new_descs=0;
  for(ch=0;ch<2;ch=ch+1)issue_counts[ch]=0;
  for(i=0;i<4;i=i+1)begin
   new_offer_entry[i]=-1;return_entry[i]=-1;return_slot[i]=-1;
   grant_client[i]=0;grant_entry[i]=0;grant_desc[i]=0;
   grant_beat[i]=0;grant_length[i]=0;grant_tag[i]=0;grant_base[i]=0;grant_address[i]=0;
   if(offer_fire[i])issue_counts[i/2]=issue_counts[i/2]+1;
  end
  // An entry and a skid belong to one channel. Only the other lane of
  // that channel can claim either earlier in this cycle.
  for(i=0;i<4;i=i+1)if(d_rsp_valid[i])begin
   e=int'(d_rsp_tag[i*64+10+:6]);
   duplicate_return=0;
   if(i%2!=0)duplicate_return=return_capture[i-1]&&return_entry[i-1]==e;
   if(return_owner_matches[i]&&!duplicate_return)begin
    chosen=-1;
    for(j=0;j<SKIDS_PER_CHANNEL;j=j+1)begin
     slot=(i/2)*SKIDS_PER_CHANNEL+j;
     previous_lane_uses_slot=0;
     if(i%2!=0)previous_lane_uses_slot=return_capture[i-1]&&return_slot[i-1]==slot;
     if(chosen<0&&(!skid_valid[slot]||skid_forward[slot])&&!previous_lane_uses_slot)
      chosen=slot;
    end
    if(chosen>=0)begin
     d_rsp_ready[i]=1;return_capture[i]=1;return_entry[i]=e;return_slot[i]=chosen;
    end
   end else invalid_return_lanes[i]=1;
  end
  // A blocked valid return waits for space. A malformed return competes
  // for the existing diagnostic slot, with the lowest lane taking priority.
  if(fault_space&&(|invalid_return_lanes))begin
   invalid_return_lane=2'(first_set({60'd0,invalid_return_lanes}));
   d_rsp_ready[invalid_return_lane]=1;
   new_fault=1;new_fault_kind=8'd1;new_fault_client=4'hf;
   new_fault_global=d_rsp_tag[invalid_return_lane*64+:64];
  end
  if(d_fence_done_valid&&(fence_state!=F_WAIT||d_fence_done_generation!=transport_generation+32'd1)&&fault_space&&!new_fault)begin
   new_fault=1;new_fault_kind=8'd2;new_fault_client=4'hf;new_fault_global={32'd0,d_fence_done_generation};
  end
  // Explicit cancellation can remove only a reservation not yet offered.
  // Its ACK is distinct from returned data. No offered VALID is withdrawn.
  if(|cancel_candidates)begin
   cancel_client=int'(cancel_candidate);c_cancel_ready[cancel_candidate]=1;
   cancel_good=cancel_matched&&b_state[cancel_match]==RESERVED;
  end
  // CLOSE is an actual no-more-source-issue registration, not an ACK guess.
  close_candidates=c_close_valid&(close_legal|{12{fault_space&&!new_fault}});
  if(|close_candidates)begin
   close_candidate=4'(first_set({52'd0,close_candidates}));
   close_client=int'(close_candidate);c_close_ready[close_candidate]=1;
   close_desc=close_matched[close_candidate]?int'(close_match[close_candidate]):-1;
   close_good=close_legal[close_candidate];
   if(!close_good)begin new_fault=1;new_fault_kind=8'd3;new_fault_client=close_candidate;new_fault_local=c_close_tag_base[close_candidate*32+:32];end
   if(close_good&&request_desc[close_candidate]==close_desc)request_bad_now[close_candidate]=1;
  end
  // Independent source acceptance can reserve at most two beats/channel.
  // A descriptor belongs to (client,local base) and never changes on reuse.
  if(fence_state==F_IDLE&&!begin_auto_fence)for(ch=0;ch<2;ch=ch+1)begin
   n=0;new_descs=0;
   first_free_beat=free_beat_slots[ch][5]?int'({1'(ch),free_beat_slots[ch][4:0]}):-1;
   second_free_beat=free_beat_slots[ch][11]?int'({1'(ch),free_beat_slots[ch][10:6]}):-1;
   first_free_desc=free_descriptor_slots[ch][5]?int'({1'(ch),free_descriptor_slots[ch][4:0]}):-1;
   second_free_desc=free_descriptor_slots[ch][11]?int'({1'(ch),free_descriptor_slots[ch][10:6]}):-1;
   channel_requests=c_req_valid&((ch==0)?~c_req_channel:c_req_channel);
   request_remaining=channel_requests&~request_bad_now&request_has_credit;
   for(j=0;j<2;j=j+1)begin
    free_entry=(j==0)?first_free_beat:second_free_beat;
    free_desc=(new_descs==0)?first_free_desc:second_free_desc;
    request_eligible=request_remaining&((free_desc<0)?~new_requests:12'hfff);
    if(free_entry>=0&&(|request_eligible))begin
     request_selected=first_request(request_eligible,request_rr[ch]);
     c=int'(request_index(request_selected));
     d=request_desc[c];
     grant={1'(ch),1'(j)};
     grant_new[grant]=d<0;
     if(d<0)begin d=free_desc;new_descs=new_descs+1;end
     grant_valid[grant]=1;grant_client[grant]=4'(c);
     grant_entry[grant]=6'(free_entry);grant_desc[grant]=6'(d);
     grant_beat[grant]=request_beat[c];grant_length[grant]=c_req_record_beats[c*5+:5];
     grant_tag[grant]=c_req_tag[c*32+:32];grant_base[grant]=tag_base(c,c_req_tag[c*32+:32]);
     grant_address[grant]=c_req_address[c*64+:64];
     c_req_ready=c_req_ready|request_selected;accepted_client=accepted_client|request_selected;n=n+1;
     request_remaining=request_remaining&~request_selected;
    end
   end
   // A malformed request consumes the diagnostic slot only if the scan
   // would have reached it before using the last physical reservation.
   bad_in_order=channel_requests&request_bad_now;
   if(n==2)bad_in_order=bad_in_order&before_request(request_selected,request_rr[ch]);
   if(fault_space&&!new_fault&&(|bad_in_order))begin
    request_selected=first_request(bad_in_order,request_rr[ch]);
    c=int'(request_index(request_selected));
    c_req_ready=c_req_ready|request_selected;
    p_req_rejected=p_req_rejected|request_selected[2:0];
    new_fault=1;new_fault_kind=8'd4;new_fault_client=4'(c);new_fault_local=c_req_tag[c*32+:32];
   end
  end
  // Strict rolling-three-cycle service, including future worst-case ACK of
  // every held offer. A new offer reserves real budget before asserting VALID.
  // I[t-1]+I[t]+held[t+1]<=4 => any three actual issue cycles total<=4.
  for(ch=0;ch<2;ch=ch+1)begin
   held=0;for(j=0;j<2;j=j+1)if(offer_valid[ch*2+j]&&!offer_fire[ch*2+j])held=held+1;
   budget=4-int'(previous_issues[ch])-issue_counts[ch]-held;
   // Put the round-robin head at bit zero. Clear a bit only when a lane
   // takes it so a blocked first lane leaves the head for the second lane.
   issue_remaining=32'({issue_candidates[ch*32+:32],issue_candidates[ch*32+:32]}>>issue_rr[ch]);
   for(j=0;j<2;j=j+1)begin
    slot=ch*2+j;
    if((!offer_valid[slot]||offer_fire[slot])&&budget>0&&(|issue_remaining))begin
     issue_offset=5'(first_set({32'd0,issue_remaining}));
     new_offer_entry[slot]=int'({1'(ch),5'(issue_rr[ch]+issue_offset)});
     issue_remaining[issue_offset]=0;
     budget=budget-1;
    end
   end
  end
  if(reset)begin c_req_ready=0;c_close_ready=0;c_cancel_ready=0;p_req_rejected=0;d_rsp_ready=0;end
 end
 integer r,t;
 wire empty_transport=offer_valid==0&&skid_valid==0&&live_beats==0;
 always @(posedge clk)begin
  if(reset)begin
   p_mode_active<=0;native_tag_seen<=0;
   for(r=0;r<3;r=r+1)last_native_serial[r]<=0;
   desc_live<=0;desc_closed<=0;offer_valid<=0;skid_valid<=0;response_locked<=0;
   c_cancel_ack_valid<=0;c_cancel_ack_tag<=0;c_cancel_ack_rejected<=0;
   // Reset abandons the old logical jobs, but cannot assume their external
   // transport vanished. Re-arm only after a real backend purge completion.
   transport_generation<=1;fence_state<=F_DRAIN;fence_external<=0;fence_client<=0;fence_cookie<=0;fence_epoch<=0;
   fault_valid<=0;fault_kind<=0;fault_client<=0;fault_local_tag<=0;fault_global_tag<=0;
   for(r=0;r<64;r=r+1)begin b_state[r]<=FREE;b_serial[r]<=0;b_client[r]<=0;b_local[r]<=0;b_address[r]<=0;b_desc[r]<=0;desc_client[r]<=0;desc_base[r]<=0;desc_address[r]<=0;desc_length[r]<=0;desc_next[r]<=0;desc_accepted[r]<=0;desc_returned[r]<=0;desc_cancelled[r]<=0;end
   for(r=0;r<4;r=r+1)offer_entry[r]<=0;
   for(r=0;r<SKIDS;r=r+1)begin
    skid_entry[r]<=0;skid_client[r]<=0;skid_local_tag[r]<=0;
    skid_descriptor[r]<=0;skid_beat[r]<=0;skid_data[r]<=0;
   end
   for(r=0;r<12;r=r+1)begin response_slot[r]<=0;response_rr[r]<=SKIDS'(1);end
   for(r=0;r<2;r=r+1)begin request_rr[r]<=12'hfff;issue_rr[r]<=0;previous_issues[r]<=0;end
  end else begin
   for(r=0;r<3;r=r+1)begin
    if(p_mode_valid[r]&&p_mode_ready[r])p_mode_active[r]<=p_mode_native64[r];
    if(accepted_client[r]&&p_mode_active[r])begin
     native_tag_seen[r]<=1;last_native_serial[r]<=c_req_tag[r*32+1+:31];
    end
    if(fence_state==F_REPLY&&fence_external&&fence_client==4'(r)&&c_fence_done_ready[r])native_tag_seen[r]<=0;
   end
   if(fault_valid&&fault_ready)fault_valid<=0;
   if(new_fault)begin fault_valid<=1;fault_kind<=new_fault_kind;fault_client<=new_fault_client;fault_local_tag<=new_fault_local;fault_global_tag<=new_fault_global;end
   for(r=0;r<12;r=r+1)begin
    if(c_cancel_ack_valid[r]&&c_cancel_ack_ready[r])c_cancel_ack_valid[r]<=0;
    if(c_rsp_valid[r])begin
     if(c_rsp_ready[r])begin
      response_locked[r]<=0;
      response_rr[r]<={response_selected[r][SKIDS-2:0],response_selected[r][SKIDS-1]};
     end
     else if(!response_locked[r])begin response_locked[r]<=1;response_slot[r]<=response_selected[r];end
    end
   end
   for(r=0;r<2;r=r+1)previous_issues[r]<=2'(issue_counts[r]);
   for(r=0;r<64;r=r+1)if(desc_live[r]&&desc_closed[r]&&desc_accepted[r]==(desc_returned[r]|desc_cancelled[r]))begin desc_live[r]<=0;desc_closed[r]<=0;end
   for(r=0;r<SKIDS;r=r+1)if(skid_forward[r])begin
    skid_valid[r]<=0;b_state[skid_entry[r]]<=FREE;
    desc_returned[skid_descriptor[r]][skid_beat[r]]<=1;
   end
   for(r=0;r<4;r=r+1)begin
    if(offer_fire[r])begin offer_valid[r]<=0;b_state[offer_entry[r]]<=ISSUED;end
    if(return_capture[r])begin
     skid_valid[return_slot[r]]<=1;
     skid_entry[return_slot[r]]<=6'(return_entry[r]);
     skid_client[return_slot[r]]<=b_client[return_entry[r]];
     skid_local_tag[return_slot[r]]<=b_local[return_entry[r]];
     skid_descriptor[return_slot[r]]<=b_desc[return_entry[r]];
     skid_beat[return_slot[r]]<=5'(beat_index(int'(b_client[return_entry[r]]),b_local[return_entry[r]]));
     skid_data[return_slot[r]]<=d_rsp_data[r*512+:512];
     b_state[return_entry[r]]<=RETURNING;
    end
    if(new_offer_entry[r]>=0)begin offer_valid[r]<=1;offer_entry[r]<=6'(new_offer_entry[r]);b_state[new_offer_entry[r]]<=OFFERED;issue_rr[r/2]<=5'((new_offer_entry[r]+1)%32);end
   end
   if(cancel_client>=0&&c_cancel_ready[cancel_client])begin
    c_cancel_ack_valid[cancel_client]<=1;c_cancel_ack_tag[cancel_client*32+:32]<=c_cancel_tag[cancel_client*32+:32];c_cancel_ack_rejected[cancel_client]<=!cancel_good;
    if(cancel_good)begin b_state[cancel_match]<=FREE;desc_cancelled[b_desc[cancel_match]][beat_index(cancel_client,b_local[cancel_match])]<=1;end
   end
   if(close_client>=0&&close_good)desc_closed[close_desc]<=1;
   for(r=0;r<4;r=r+1)if(grant_valid[r])begin
    b_state[grant_entry[r]]<=RESERVED;
    b_serial[grant_entry[r]]<=b_serial[grant_entry[r]]+16'd1;
    b_client[grant_entry[r]]<=grant_client[r];
    b_local[grant_entry[r]]<=grant_tag[r];
    b_address[grant_entry[r]]<=grant_address[r];
    b_desc[grant_entry[r]]<=grant_desc[r];
    if(grant_new[r])begin
     desc_live[grant_desc[r]]<=1;
     desc_closed[grant_desc[r]]<=0;
     desc_client[grant_desc[r]]<=grant_client[r];
     desc_base[grant_desc[r]]<=grant_base[r];
     desc_address[grant_desc[r]]<=grant_address[r];
     desc_length[grant_desc[r]]<=grant_length[r];
     desc_accepted[grant_desc[r]]<=18'd1;
     desc_returned[grant_desc[r]]<=0;
     desc_cancelled[grant_desc[r]]<=0;
    end else desc_accepted[grant_desc[r]][grant_beat[r]]<=1;
    desc_next[grant_desc[r]]<=grant_beat[r]+5'd1;
    if(grant_beat[r]+5'd1==grant_length[r])desc_closed[grant_desc[r]]<=1;
   end
   for(r=0;r<12;r=r+1)if(accepted_client[r])begin
    request_rr[c_req_channel[r]]<=12'hfff<<((r+1)%12);
   end
   case(fence_state)
    F_IDLE:if(begin_auto_fence||begin_fence)begin
     fence_state<=F_DRAIN;fence_external<=begin_fence;
     if(begin_fence)begin fence_client<=4'(selected_fence);fence_cookie<=c_fence_cookie[selected_fence*32+:32];fence_epoch<=c_fence_epoch[selected_fence*9+:9];end
    end
    F_DRAIN:if(empty_transport)fence_state<=F_OFFER;
    F_OFFER:if(d_fence_ready)fence_state<=F_WAIT;
    F_WAIT:if(d_fence_done_valid&&d_fence_done_ready&&d_fence_done_generation==transport_generation+32'd1)begin
     transport_generation<=transport_generation+32'd1;for(t=0;t<64;t=t+1)b_serial[t]<=0;fence_state<=fence_external?F_REPLY:F_IDLE;
    end
    F_REPLY:if(c_fence_done_ready[fence_client])fence_state<=F_IDLE;
    default:fence_state<=F_IDLE;
   endcase
  end
 end
endmodule
