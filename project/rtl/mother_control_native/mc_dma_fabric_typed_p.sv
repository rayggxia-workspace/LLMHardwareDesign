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
 input wire [11:0] c_fence_valid,output reg [11:0] c_fence_ready,
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
 localparam integer SKID_BITS=$clog2(SKIDS);
 reg [3:0] offer_valid;reg [SKIDS-1:0] skid_valid;
 reg [5:0] offer_entry[0:3],skid_entry[0:SKIDS-1];
 reg [511:0] skid_data[0:SKIDS-1];
 reg [11:0] response_locked;reg [SKID_BITS-1:0] response_slot[0:11],response_rr[0:11];
 reg [3:0] request_rr[0:1];reg [4:0] issue_rr[0:1];
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

 integer accepted_entry[0:11],accepted_desc[0:11];reg [11:0] accepted_new;
 integer forwarded_slot[0:11],cancel_entry,cancel_client,close_desc,close_client;
 reg cancel_good,close_good;
 integer new_offer_entry[0:3];reg [3:0] offer_fire,return_capture;reg [SKIDS-1:0] skid_forward,selected_skids;
 integer return_entry[0:3],return_slot[0:3];
 reg new_fault;reg [7:0] new_fault_kind;reg [3:0] new_fault_client;
 reg [31:0] new_fault_local;reg [63:0] new_fault_global;
 reg begin_fence,begin_auto_fence;integer selected_fence;
 integer beat_counts[0:1],desc_counts[0:1],client_counts[0:11],issue_counts[0:1];
 integer c,ch,i,j,k,e,d,slot,n,chosen,free_entry,free_desc;
 reg bad,found;
 integer req_beat,req_length,budget,held;
 reg [31:0] req_tag,req_base;reg [63:0] req_address,req_record_address;
 reg [63:0] allocated_beats,allocated_desc,selected_offers,selected_returns;
 // A descriptor remains live through its last held return, even if
 // backend service completed earlier. Mode updates can never overlap a new
 // request or pending close/cancel/fence, nor an unconsumed local DONE.
 always @*begin: typed_mode_admission
  integer m,x;
  for(m=0;m<3;m=m+1)begin
   p_mode_ready[m]=!reset&&fence_state==F_IDLE&&p_mode_client_drained[m]&&
       !c_req_valid[m]&&!c_close_valid[m]&&!c_cancel_valid[m]&&!c_cancel_ack_valid[m]&&
       !c_fence_valid[m]&&!(fault_valid&&fault_client==4'(m));
   for(x=0;x<64;x=x+1)begin
    if(desc_live[x]&&desc_client[x]==4'(m))p_mode_ready[m]=0;
    if(b_state[x]!=FREE&&b_client[x]==4'(m))p_mode_ready[m]=0;
   end
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
 always @*begin: registered_client_response
  integer rc,rj,rs,choice;
  c_rsp_valid=0;c_rsp_tag=0;c_rsp_data=0;rs=0;choice=0;
  for(rc=0;rc<12;rc=rc+1)begin
   choice=-1;forwarded_slot[rc]=-1;
   if(response_locked[rc])choice=int'(response_slot[rc]);
   else for(rj=0;rj<SKIDS;rj=rj+1)begin
    rs=(int'(response_rr[rc])+rj)%SKIDS;
    if(choice<0&&skid_valid[rs]&&int'(b_client[skid_entry[rs]])==rc)choice=rs;
   end
   if(!reset&&choice>=0&&skid_valid[choice])begin
    c_rsp_valid[rc]=1;c_rsp_tag[rc*32+:32]=b_local[skid_entry[choice]];
    c_rsp_data[rc*512+:512]=skid_data[choice];forwarded_slot[rc]=choice;
   end
  end
 end
 always @*begin: actual_client_consumption
  skid_forward=0;
  for(integer fc=0;fc<12;fc=fc+1)if(c_rsp_valid[fc]&&c_rsp_ready[fc])skid_forward[forwarded_slot[fc]]=1;
 end
 always @*begin: registered_fence_reply
  c_fence_done_valid=0;c_fence_done_cookie=0;c_fence_done_epoch=0;
  if(!reset&&fence_state==F_REPLY&&fence_external)begin
   c_fence_done_valid[fence_client]=1;c_fence_done_cookie[int'(fence_client)*32+:32]=fence_cookie;
   c_fence_done_epoch[int'(fence_client)*9+:9]=fence_epoch;
  end
 end
 always @*offer_fire=offer_valid&d_req_ready;
 // Combinational plans are applied atomically by the sequential owner table.
 always @* begin
  c_req_ready=0;c_close_ready=0;c_cancel_ready=0;p_req_rejected=0;
  c_fence_ready=0;
  d_rsp_ready=0;
  return_capture=0;
  selected_skids=0;
  new_fault=0;new_fault_kind=0;new_fault_client=0;new_fault_local=0;new_fault_global=0;
  accepted_new=0;allocated_beats=0;allocated_desc=0;selected_offers=0;selected_returns=0;
  cancel_entry=-1;cancel_client=-1;cancel_good=0;close_desc=-1;close_client=-1;close_good=0;
  begin_fence=0;begin_auto_fence=0;selected_fence=-1;
  req_tag=0;req_base=0;req_address=0;req_record_address=0;req_beat=0;req_length=0;
  chosen=0;bad=0;free_entry=0;free_desc=0;found=0;budget=0;held=0;slot=0;n=0;e=0;d=0;
  for(ch=0;ch<2;ch=ch+1)begin beat_counts[ch]=0;desc_counts[ch]=0;issue_counts[ch]=0;end
  for(c=0;c<12;c=c+1)begin accepted_entry[c]=-1;accepted_desc[c]=-1;client_counts[c]=0;end
  for(i=0;i<4;i=i+1)begin
   new_offer_entry[i]=-1;return_entry[i]=-1;return_slot[i]=-1;
   if(offer_fire[i])issue_counts[i/2]=issue_counts[i/2]+1;
  end
  for(i=0;i<64;i=i+1)begin
   if(b_state[i]!=FREE)begin beat_counts[i/32]=beat_counts[i/32]+1;client_counts[b_client[i]]=client_counts[b_client[i]]+1;end
   if(desc_live[i])desc_counts[i/32]=desc_counts[i/32]+1;
   if(b_state[i]==FREE&&b_serial[i]==SERIAL_LIMIT)begin_auto_fence=1;
  end
  for(ch=0;ch<2;ch=ch+1)begin debug_beats[ch*6+:6]=6'(beat_counts[ch]);debug_descriptors[ch*6+:6]=6'(desc_counts[ch]);end
  // Reject transport duplicates without changing any owner's data/credit.
  for(i=0;i<4;i=i+1)if(d_rsp_valid[i])begin
   e=int'(d_rsp_tag[i*64+10+:6]);
   if(b_state[e]==ISSUED&&global_tag(6'(e))==d_rsp_tag[i*64+:64]&&e/32==i/2&&!selected_returns[e])begin
    // Each DDR lane may land in any free skid in its channel. The
    // shared finite pool avoids tying one blocked client to a return lane.
    chosen=-1;
    for(j=0;j<SKIDS_PER_CHANNEL;j=j+1)begin
     slot=(i/2)*SKIDS_PER_CHANNEL+j;
     if(chosen<0&&(!skid_valid[slot]||skid_forward[slot])&&!selected_skids[slot])chosen=slot;
    end
    if(chosen>=0)begin d_rsp_ready[i]=1;return_capture[i]=1;return_entry[i]=e;return_slot[i]=chosen;selected_skids[chosen]=1;selected_returns[e]=1;end
   end else if(fault_space&&!new_fault)begin
    d_rsp_ready[i]=1;new_fault=1;new_fault_kind=8'd1;new_fault_client=4'hf;new_fault_global=d_rsp_tag[i*64+:64];
   end
  end
  if(d_fence_done_valid&&(fence_state!=F_WAIT||d_fence_done_generation!=transport_generation+32'd1)&&fault_space&&!new_fault)begin
   new_fault=1;new_fault_kind=8'd2;new_fault_client=4'hf;new_fault_global={32'd0,d_fence_done_generation};
  end
  // Explicit cancellation can remove only a reservation not yet offered.
  // Its ACK is distinct from returned data. No offered VALID is withdrawn.
  for(c=0;c<12;c=c+1)if(cancel_client<0&&c_cancel_valid[c]&&(!c_cancel_ack_valid[c]||c_cancel_ack_ready[c]))begin
   cancel_client=c;c_cancel_ready[c]=1;
   for(i=0;i<64;i=i+1)if(b_state[i]!=FREE&&int'(b_client[i])==c&&b_local[i]==c_cancel_tag[c*32+:32])cancel_entry=i;
   cancel_good=cancel_entry>=0&&b_state[cancel_entry]==RESERVED;
  end
  // CLOSE is an actual no-more-source-issue registration, not an ACK guess.
  for(c=0;c<12;c=c+1)if(close_client<0&&c_close_valid[c])begin
   d=-1;for(i=0;i<64;i=i+1)if(desc_live[i]&&int'(desc_client[i])==c&&desc_base[i]==c_close_tag_base[c*32+:32])d=i;
   close_good=d>=0&&!desc_closed[d]&&c_close_tag_base[c*32+:32]==tag_base(c,c_close_tag_base[c*32+:32]);
   if(close_good||(fault_space&&!new_fault))begin
    close_client=c;close_desc=d;c_close_ready[c]=1;
    if(!close_good)begin new_fault=1;new_fault_kind=8'd3;new_fault_client=4'(c);new_fault_local=c_close_tag_base[c*32+:32];end
   end
  end
  // Independent source acceptance can reserve at most two beats/channel.
  // A descriptor belongs to (client,local base) and never changes on reuse.
  if(fence_state==F_IDLE&&!begin_auto_fence)for(ch=0;ch<2;ch=ch+1)begin
   n=0;
   for(k=0;k<12;k=k+1)begin
    c=(int'(request_rr[ch])+k)%12;
    if(c_req_valid[c]&&int'(c_req_channel[c])==ch&&n<2)begin
     req_tag=c_req_tag[c*32+:32];req_base=tag_base(c,req_tag);req_beat=beat_index(c,req_tag);req_length=int'(c_req_record_beats[c*5+:5]);req_address=c_req_address[c*64+:64];req_record_address=req_address-64'(req_beat*64);
     d=-1;
     for(j=0;j<64;j=j+1)if((c<3||j/32==ch)&&desc_live[j]&&int'(desc_client[j])==c&&desc_base[j]==req_base)d=j;
     bad=req_address[5:0]!=0||(c>=9&&(req_length!=17&&req_length!=18))||req_beat>=req_length;
     if(c<3&&p_mode_active[c])begin
      bad=bad||req_length!=1||req_tag[0]||
          (native_tag_seen[c]&&req_tag[31:1]<=last_native_serial[c]);
     end else if(c<9)bad=bad||req_length!=2||req_record_address[6:0]!=0;
     if(d<0)bad=bad||req_beat!=0||int'(req_record_address[11])!=ch;
     else bad=bad||d/32!=ch||desc_closed[d]||int'(desc_length[d])!=req_length||
           int'(desc_next[d])!=req_beat||desc_address[d]!=req_record_address;
     if(close_client==c&&close_good&&close_desc==d)bad=1;
     free_entry=-1;free_desc=-1;
     for(j=0;j<32;j=j+1)begin
      i=ch*32+j;if(free_entry<0&&b_state[i]==FREE&&b_serial[i]!=SERIAL_LIMIT&&!allocated_beats[i])free_entry=i;
      if(free_desc<0&&!desc_live[i]&&!allocated_desc[i])free_desc=i;
     end
     if(bad)begin
      if(fault_space&&!new_fault)begin c_req_ready[c]=1;if(c<3)p_req_rejected[c]=1;new_fault=1;new_fault_kind=8'd4;new_fault_client=4'(c);new_fault_local=req_tag;end
     end else if(free_entry>=0&&(d>=0||free_desc>=0)&&client_counts[c]<32)begin
      if(d<0)begin d=free_desc;accepted_new[c]=1;allocated_desc[d]=1;end
      c_req_ready[c]=1;accepted_entry[c]=free_entry;accepted_desc[c]=d;allocated_beats[free_entry]=1;n=n+1;
     end
    end
   end
  end
  // Strict rolling-three-cycle service, including future worst-case ACK of
  // every held offer. A new offer reserves real budget before asserting VALID.
  // I[t-1]+I[t]+held[t+1]<=4 => any three actual issue cycles total<=4.
  for(ch=0;ch<2;ch=ch+1)begin
   held=0;for(j=0;j<2;j=j+1)if(offer_valid[ch*2+j]&&!offer_fire[ch*2+j])held=held+1;
   budget=4-int'(previous_issues[ch])-issue_counts[ch]-held;
   for(j=0;j<2;j=j+1)begin
    slot=ch*2+j;
    if((!offer_valid[slot]||offer_fire[slot])&&budget>0)begin
     chosen=-1;
     for(k=0;k<32;k=k+1)begin
      e=ch*32+(int'(issue_rr[ch])+k)%32;
      if(chosen<0&&b_state[e]==RESERVED&&!selected_offers[e]&&!(cancel_good&&cancel_entry==e))chosen=e;
     end
     if(chosen>=0)begin new_offer_entry[slot]=chosen;selected_offers[chosen]=1;budget=budget-1;end
    end
   end
  end
  if(fence_state==F_IDLE&&!begin_auto_fence)for(c=0;c<12;c=c+1)if(selected_fence<0&&c_fence_valid[c])begin
   found=accepted_entry[c]>=0;for(i=0;i<64;i=i+1)if(desc_live[i]&&int'(desc_client[i])==c)found=1;
   if(!found)begin selected_fence=c;c_fence_ready[c]=1;begin_fence=1;end
  end
  if(reset)begin c_req_ready=0;c_close_ready=0;c_cancel_ready=0;p_req_rejected=0;c_fence_ready=0;d_rsp_ready=0;end
 end
 integer r,t;reg empty_transport;
 always @* begin empty_transport=offer_valid==0&&skid_valid==0;for(integer z=0;z<64;z=z+1)if(b_state[z]!=FREE)empty_transport=0;end
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
   for(r=0;r<SKIDS;r=r+1)begin skid_entry[r]<=0;skid_data[r]<=0;end
   for(r=0;r<12;r=r+1)begin response_slot[r]<=0;response_rr[r]<=0;end
   for(r=0;r<2;r=r+1)begin request_rr[r]<=0;issue_rr[r]<=0;previous_issues[r]<=0;end
  end else begin
   for(r=0;r<3;r=r+1)begin
    if(p_mode_valid[r]&&p_mode_ready[r])p_mode_active[r]<=p_mode_native64[r];
    if(accepted_entry[r]>=0&&p_mode_active[r])begin
     native_tag_seen[r]<=1;last_native_serial[r]<=c_req_tag[r*32+1+:31];
    end
    if(fence_state==F_REPLY&&fence_external&&fence_client==4'(r)&&c_fence_done_ready[r])native_tag_seen[r]<=0;
   end
   if(fault_valid&&fault_ready)fault_valid<=0;
   if(new_fault)begin fault_valid<=1;fault_kind<=new_fault_kind;fault_client<=new_fault_client;fault_local_tag<=new_fault_local;fault_global_tag<=new_fault_global;end
   for(r=0;r<12;r=r+1)begin
    if(c_cancel_ack_valid[r]&&c_cancel_ack_ready[r])c_cancel_ack_valid[r]<=0;
    if(c_rsp_valid[r])begin
     if(c_rsp_ready[r])begin response_locked[r]<=0;response_rr[r]<=SKID_BITS'((forwarded_slot[r]+1)%SKIDS);end
     else if(!response_locked[r])begin response_locked[r]<=1;response_slot[r]<=SKID_BITS'(forwarded_slot[r]);end
    end
   end
   for(r=0;r<2;r=r+1)previous_issues[r]<=2'(issue_counts[r]);
   for(r=0;r<64;r=r+1)if(desc_live[r]&&desc_closed[r]&&desc_accepted[r]==(desc_returned[r]|desc_cancelled[r]))begin desc_live[r]<=0;desc_closed[r]<=0;end
   for(r=0;r<SKIDS;r=r+1)if(skid_forward[r])begin
    skid_valid[r]<=0;b_state[skid_entry[r]]<=FREE;desc_returned[b_desc[skid_entry[r]]][beat_index(int'(b_client[skid_entry[r]]),b_local[skid_entry[r]])]<=1;
   end
   for(r=0;r<4;r=r+1)begin
    if(offer_fire[r])begin offer_valid[r]<=0;b_state[offer_entry[r]]<=ISSUED;end
    if(return_capture[r])begin skid_valid[return_slot[r]]<=1;skid_entry[return_slot[r]]<=6'(return_entry[r]);skid_data[return_slot[r]]<=d_rsp_data[r*512+:512];b_state[return_entry[r]]<=RETURNING;end
    if(new_offer_entry[r]>=0)begin offer_valid[r]<=1;offer_entry[r]<=6'(new_offer_entry[r]);b_state[new_offer_entry[r]]<=OFFERED;issue_rr[r/2]<=5'((new_offer_entry[r]+1)%32);end
   end
   if(cancel_client>=0&&c_cancel_ready[cancel_client])begin
    c_cancel_ack_valid[cancel_client]<=1;c_cancel_ack_tag[cancel_client*32+:32]<=c_cancel_tag[cancel_client*32+:32];c_cancel_ack_rejected[cancel_client]<=!cancel_good;
    if(cancel_good)begin b_state[cancel_entry]<=FREE;desc_cancelled[b_desc[cancel_entry]][beat_index(cancel_client,b_local[cancel_entry])]<=1;end
   end
   if(close_client>=0&&close_good)desc_closed[close_desc]<=1;
   for(r=0;r<12;r=r+1)if(accepted_entry[r]>=0)begin
    b_state[accepted_entry[r]]<=RESERVED;b_serial[accepted_entry[r]]<=b_serial[accepted_entry[r]]+16'd1;b_client[accepted_entry[r]]<=4'(r);b_local[accepted_entry[r]]<=c_req_tag[r*32+:32];b_address[accepted_entry[r]]<=c_req_address[r*64+:64];b_desc[accepted_entry[r]]<=6'(accepted_desc[r]);
    if(accepted_new[r])begin
     desc_live[accepted_desc[r]]<=1;desc_closed[accepted_desc[r]]<=0;desc_client[accepted_desc[r]]<=4'(r);desc_base[accepted_desc[r]]<=tag_base(r,c_req_tag[r*32+:32]);desc_address[accepted_desc[r]]<=c_req_address[r*64+:64];desc_length[accepted_desc[r]]<=c_req_record_beats[r*5+:5];desc_accepted[accepted_desc[r]]<=18'd1;desc_returned[accepted_desc[r]]<=0;desc_cancelled[accepted_desc[r]]<=0;
    end else desc_accepted[accepted_desc[r]][beat_index(r,c_req_tag[r*32+:32])]<=1;
    desc_next[accepted_desc[r]]<=5'(beat_index(r,c_req_tag[r*32+:32])+1);if(beat_index(r,c_req_tag[r*32+:32])+1==int'(c_req_record_beats[r*5+:5]))desc_closed[accepted_desc[r]]<=1;
    request_rr[c_req_channel[r]]<=4'((r+1)%12);
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
