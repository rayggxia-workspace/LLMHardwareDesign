// Multi-S descriptor DMA with bounded slots and two-level round-robin.
// Native memory transactions, NOT AXI/JEDEC: request {write1,id16,address40,data128}
// and response {status2,id16,data128}. Each grant transfers exactly one word.
// LOAD credit retires at actual S write ACK; STORE at memory write response.
module hbm_group_dma #(
 parameter integer GROUPS=4,S_PER_GROUP=4,SLOTS=8,
 parameter integer NS=GROUPS*S_PER_GROUP,CHANNELS=4
)(
 input wire clk,reset,
 input wire [2:0] channel_count,input wire [3:0] credit_limit,
 input wire [NS-1:0] desc_valid,desc_write,complete_ready,
 output wire [NS-1:0] desc_ready,
 input wire [NS*40-1:0] desc_address_flat,input wire [NS*10-1:0] desc_local_flat,
 input wire [NS*11-1:0] desc_words_flat,input wire [NS*16-1:0] desc_tag_flat,
 output reg [NS-1:0] complete_valid,output wire [NS*2-1:0] complete_status_flat,
 output wire [NS*16-1:0] complete_tag_flat,output wire [NS*11-1:0] completed_words_flat,
 output wire [NS-1:0] busy,output reg protocol_error,
 output wire [CHANNELS-1:0] mem_valid,input wire [CHANNELS-1:0] mem_ready,
 output wire [CHANNELS*185-1:0] mem_data_flat,
 input wire [CHANNELS-1:0] response_valid,output wire [CHANNELS-1:0] response_ready,
 input wire [CHANNELS*146-1:0] response_data_flat,
 output wire [NS-1:0] s_req,s_wr,s_take,
 output wire [NS*10-1:0] s_address_flat,output wire [NS*128-1:0] s_data_flat,
 input wire [NS-1:0] s_ready,s_valid,input wire [NS*128-1:0] s_result_flat,
 output wire [NS*4-1:0] live_count_flat,
 output reg [CHANNELS-1:0] grant_valid,output wire [CHANNELS*4-1:0] grant_s_flat,
 output wire [NS-1:0] eligible_debug
);
 wire [39:0] desc_address[NS];wire [9:0] desc_local[NS];wire [10:0] desc_words[NS];wire [15:0] desc_tag[NS];
 reg [1:0] complete_status[NS];reg [15:0] complete_tag[NS];reg [10:0] completed_words[NS];
 wire [145:0] response_data[CHANNELS];wire [127:0] s_result[NS];
 reg [3:0] live_count[NS],grant_s[CHANNELS];
 localparam [2:0] FREE=0,LOAD_WAIT=1,LOAD_READY=2,LOAD_PORT=3,
                  STORE_PORT=4,STORE_READY=5,STORE_WAIT=6;
 reg [NS-1:0] active,direction,failed;
 reg [39:0] base[NS];reg [9:0] local_base[NS];
 reg [10:0] length[NS],next_word[NS];reg [3:0] credits[NS];
 reg [15:0] task_tag[NS];
 reg [2:0] state[NS][SLOTS];reg [15:0] identity[NS][SLOTS];
 reg [8:0] generation[NS][SLOTS];reg [9:0] word_address[NS][SLOTS];
 reg [39:0] external_address[NS][SLOTS];reg [127:0] payload[NS][SLOTS];
 reg [1:0] port_phase[NS];reg [2:0] port_slot[NS],data_rr[NS];
 reg [2:0] group_rr[CHANNELS],local_rr[GROUPS];
 reg [CHANNELS-1:0] pending;reg [184:0] pending_data[CHANNELS];
 integer free_slot[NS],load_slot[NS],store_slot[NS];
 reg [NS-1:0] eligible;
 assign eligible_debug=eligible;
 wire config_ok=(channel_count==1||channel_count==2||channel_count==4)&&
                int'(channel_count)<=CHANNELS&&credit_limit>0&&int'(credit_limit)<=SLOTS;
 function automatic integer route;
  input integer g;
  begin case(channel_count)3'd1:route=0;3'd2:route=g%2;default:route=g%4;endcase end
 endfunction
 for(genvar s=0;s<NS;s=s+1)begin: signals
  assign desc_address[s]=desc_address_flat[s*40+:40];assign desc_local[s]=desc_local_flat[s*10+:10];
  assign desc_words[s]=desc_words_flat[s*11+:11];assign desc_tag[s]=desc_tag_flat[s*16+:16];
  assign complete_status_flat[s*2+:2]=complete_status[s];assign complete_tag_flat[s*16+:16]=complete_tag[s];
  assign completed_words_flat[s*11+:11]=completed_words[s];assign live_count_flat[s*4+:4]=live_count[s];
  assign s_result[s]=s_result_flat[s*128+:128];
  assign desc_ready[s]=!reset&&!active[s]&&!complete_valid[s]&&!protocol_error;
  assign busy[s]=active[s];
  assign s_req[s]=!reset&&port_phase[s]==1;
  assign s_wr[s]=direction[s]==0;
  assign s_address_flat[s*10+:10]=word_address[s][port_slot[s]];
  assign s_data_flat[s*128+:128]=payload[s][port_slot[s]];
  assign s_take[s]=!reset&&port_phase[s]==2;
 end
 for(genvar ch=0;ch<CHANNELS;ch=ch+1)begin: memory_ports
  assign mem_valid[ch]=!reset&&pending[ch];assign mem_data_flat[ch*185+:185]=pending_data[ch];
  assign response_data[ch]=response_data_flat[ch*146+:146];assign grant_s_flat[ch*4+:4]=grant_s[ch];
  assign response_ready[ch]=!reset;
 end
 integer s,j,k;
 always @* begin
  eligible=0;
  for(integer si=0;si<NS;si=si+1)begin
   live_count[si]=0;free_slot[si]=-1;load_slot[si]=-1;store_slot[si]=-1;
   for(integer sl=0;sl<SLOTS;sl=sl+1)begin
    if(state[si][sl]!=FREE)live_count[si]=live_count[si]+1'b1;
    if(state[si][sl]==FREE&&free_slot[si]<0)free_slot[si]=sl;
   end
   for(integer off=0;off<SLOTS;off=off+1)begin
    if(state[si][(int'(data_rr[si])+off)%SLOTS]==LOAD_READY&&load_slot[si]<0)
     load_slot[si]=(int'(data_rr[si])+off)%SLOTS;
    if(state[si][(int'(data_rr[si])+off)%SLOTS]==STORE_READY&&store_slot[si]<0)
     store_slot[si]=(int'(data_rr[si])+off)%SLOTS;
   end
   eligible[si]=active[si]&&!protocol_error&&
     ((!direction[si]&&!failed[si]&&next_word[si]<length[si]&&live_count[si]<credits[si]&&free_slot[si]>=0)||
      (direction[si]&&store_slot[si]>=0));
  end
 end
 integer selected[CHANNELS];
 always @* begin
  for(integer ch=0;ch<CHANNELS;ch=ch+1)begin
   selected[ch]=-1;
   for(integer go=0;go<GROUPS;go=go+1)
    for(integer so=0;so<S_PER_GROUP;so=so+1)
     if(selected[ch]<0&&route((int'(group_rr[ch])+go)%GROUPS)==ch&&
        eligible[((int'(group_rr[ch])+go)%GROUPS)*S_PER_GROUP+
                 (int'(local_rr[(int'(group_rr[ch])+go)%GROUPS])+so)%S_PER_GROUP])
      selected[ch]=((int'(group_rr[ch])+go)%GROUPS)*S_PER_GROUP+
                    (int'(local_rr[(int'(group_rr[ch])+go)%GROUPS])+so)%S_PER_GROUP;
  end
 end
 integer chosen,slot,rs,rslot;reg [15:0] rid;reg [40:0] end_address;
 always @(posedge clk)begin
  if(reset)begin
   active<=0;direction<=0;failed<=0;complete_valid<=0;protocol_error<=0;pending<=0;grant_valid<=0;
   for(s=0;s<NS;s=s+1)begin
    base[s]<=0;local_base[s]<=0;length[s]<=0;next_word[s]<=0;credits[s]<=0;task_tag[s]<=0;
    complete_status[s]<=0;complete_tag[s]<=0;completed_words[s]<=0;
    port_phase[s]<=0;port_slot[s]<=0;data_rr[s]<=0;
    for(j=0;j<SLOTS;j=j+1)begin
     state[s][j]<=FREE;identity[s][j]<=0;generation[s][j]<=0;word_address[s][j]<=0;
     external_address[s][j]<=0;payload[s][j]<=0;
    end
   end
   for(j=0;j<CHANNELS;j=j+1)begin group_rr[j]<=0;pending_data[j]<=0;grant_s[j]<=0;end
   for(j=0;j<GROUPS;j=j+1)local_rr[j]<=0;
  end else begin
   grant_valid<=0;
   for(s=0;s<NS;s=s+1)begin
    if(complete_valid[s]&&complete_ready[s])complete_valid[s]<=0;
    if(desc_valid[s]&&desc_ready[s])begin
     end_address={1'b0,desc_address[s]}+({30'd0,desc_words[s]}<<4);
     task_tag[s]<=desc_tag[s];completed_words[s]<=0;
     if(!config_ok||desc_words[s]==0||int'(desc_local[s])+int'(desc_words[s])>1024||
        desc_address[s][3:0]!=0||(end_address[40]&&end_address[39:0]!=0))begin
      complete_valid[s]<=1;complete_tag[s]<=desc_tag[s];complete_status[s]<=2;
     end else begin
      active[s]<=1;direction[s]<=desc_write[s];failed[s]<=0;
      base[s]<=desc_address[s];local_base[s]<=desc_local[s];length[s]<=desc_words[s];
      next_word[s]<=0;credits[s]<=credit_limit;
     end
    end
    if(active[s]&&live_count[s]==0&&port_phase[s]==0&&(failed[s]||next_word[s]==length[s]))begin
     active[s]<=0;complete_valid[s]<=1;complete_tag[s]<=task_tag[s];
     complete_status[s]<=failed[s]?2'd3:2'd0;
    end
    if(port_phase[s]==1&&s_ready[s])port_phase[s]<=2;
    if(port_phase[s]==2&&s_valid[s])begin
     slot=int'(port_slot[s]);port_phase[s]<=0;data_rr[s]<=3'((slot+1)%SLOTS);
     if(direction[s])begin payload[s][slot]<=s_result[s];state[s][slot]<=STORE_READY;end
     else begin state[s][slot]<=FREE;completed_words[s]<=completed_words[s]+1'b1;end
    end
    if(active[s]&&port_phase[s]==0&&!protocol_error)begin
     if(!direction[s]&&load_slot[s]>=0)begin
      slot=load_slot[s];port_slot[s]<=3'(slot);port_phase[s]<=1;state[s][slot]<=LOAD_PORT;
     end else if(direction[s]&&!failed[s]&&next_word[s]<length[s]&&
                 live_count[s]<credits[s]&&free_slot[s]>=0)begin
      slot=free_slot[s];port_slot[s]<=3'(slot);port_phase[s]<=1;state[s][slot]<=STORE_PORT;
      word_address[s][slot]<=local_base[s]+10'(next_word[s]);
      external_address[s][slot]<=base[s]+(40'(next_word[s])<<4);
      generation[s][slot]<=generation[s][slot]+1'b1;
      identity[s][slot]<={9'(generation[s][slot]+1'b1),4'(s),3'(slot)};
      next_word[s]<=next_word[s]+1'b1;
     end
    end
   end
   for(k=0;k<CHANNELS;k=k+1)begin
    if(pending[k]&&mem_ready[k])pending[k]<=0;
    if((!pending[k]||mem_ready[k])&&selected[k]>=0)begin
     chosen=selected[k];slot=direction[chosen]?store_slot[chosen]:free_slot[chosen];
     pending[k]<=1;grant_valid[k]<=1;grant_s[k]<=4'(chosen);
     group_rr[k]<=3'((chosen/S_PER_GROUP+1)%GROUPS);
     local_rr[chosen/S_PER_GROUP]<=3'((chosen%S_PER_GROUP+1)%S_PER_GROUP);
     if(direction[chosen])begin
      state[chosen][slot]<=STORE_WAIT;
      pending_data[k]<={1'b1,identity[chosen][slot],external_address[chosen][slot],payload[chosen][slot]};
      data_rr[chosen]<=3'((slot+1)%SLOTS);
     end else begin
      rid={9'(generation[chosen][slot]+1'b1),4'(chosen),3'(slot)};
      identity[chosen][slot]<=rid;generation[chosen][slot]<=generation[chosen][slot]+1'b1;
      word_address[chosen][slot]<=local_base[chosen]+10'(next_word[chosen]);
      external_address[chosen][slot]<=base[chosen]+(40'(next_word[chosen])<<4);
      state[chosen][slot]<=LOAD_WAIT;next_word[chosen]<=next_word[chosen]+1'b1;
      pending_data[k]<={1'b0,rid,base[chosen]+(40'(next_word[chosen])<<4),128'd0};
     end
    end
    if(response_valid[k]&&response_ready[k])begin
     rid=response_data[k][143:128];rs=int'(rid[6:3]);rslot=int'(rid[2:0]);
     if(rs>=NS||rslot>=SLOTS)protocol_error<=1;
     else if(!active[rs]||identity[rs][rslot]!=rid||route(rs/S_PER_GROUP)!=k||
             (state[rs][rslot]!=LOAD_WAIT&&state[rs][rslot]!=STORE_WAIT))protocol_error<=1;
     else if(response_data[k][145:144]!=0)begin
      state[rs][rslot]<=FREE;failed[rs]<=1;
     end else if(state[rs][rslot]==LOAD_WAIT)begin
      payload[rs][rslot]<=response_data[k][127:0];state[rs][rslot]<=LOAD_READY;
     end else begin
      state[rs][rslot]<=FREE;completed_words[rs]<=completed_words[rs]+1'b1;
     end
    end
   end
  end
 end
endmodule
