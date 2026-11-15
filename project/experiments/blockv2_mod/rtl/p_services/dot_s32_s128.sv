// Refs #252/#253. Candidate finite single-S128 frontend for exact native dot.
// ROWS=1/2/4 is a hardware variant, not extra free read ports. Each query
// owns eight CSA pairs in the core. Two four-K cache tiles contain
// 2*(ROWS+8)*16B=288/320/384B real registers; no additional SRAM.
// S responses are untagged and in order, with exactly two actual owners.
// Reset is a coherent service/S reset. A local cancel drains every accepted
// response and keeps an already offered request stable until it is accepted.
module dot_s32_s128 #(
 parameter integer ROWS=1, parameter bit REFILL_NEXT=0,parameter bit CHECKPOINT=0,
 parameter integer AV_MAX_K=128
) (
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,input wire [1:0] cmd_kind,
 input wire [127:0] cmd_key,input wire [31:0] cmd_tag,
 input wire [15:0] cmd_full_k,cmd_k_offset,input wire [7:0] cmd_chunk_k,
 input wire [3:0] cmd_n,input wire [2:0] cmd_rows,input wire [5:0] cmd_shift,
 input wire cmd_layout, // 0: B N-major (QK); 1: B K-major (AV)
 input wire [9:0] cmd_a_base,cmd_b_base,cmd_result_base,
 input wire cmd_sources_committed,
 input wire abort_valid,input wire [127:0] abort_key,output wire abort_ready,
 output reg rsp_valid,input wire rsp_ready,output reg [1:0] rsp_kind,
 output reg [127:0] rsp_key,output reg [31:0] rsp_tag,
 output reg rsp_error,rsp_aborted,rsp_done,
 output reg [ROWS*2-1:0] rsp_written_mask,
 output wire s_req_valid,input wire s_req_ready,output wire s_req_write,
 output wire [9:0] s_req_address,output wire [127:0] s_req_wdata,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data,
 input wire s_rsp_error
);
 localparam [2:0] IDLE=0,BEGIN_SEND=1,BEGIN_WAIT=2,RUN=3,SNAPSHOT_PREP=4,SNAPSHOT_RUN=5;
 localparam [1:0] FREE=0,FILL=1,READY=2;
 localparam integer WORDS=ROWS+8;
 reg [2:0] state;
 reg owned,aborting,abort_fault,core_finished,cancel_sent;
 reg [1:0] current_kind;reg [127:0] key;reg [31:0] tag;
 reg [15:0] full_k,next_chunk,chunk_offset;
 reg [7:0] chunk_k,tile_cursor,next_consume;
 reg [3:0] n;reg [2:0] rows;reg [5:0] shift;
 reg layout;reg [9:0] a_base,b_base,result_base;
 reg [1:0] slot_state[0:1];reg [7:0] slot_first[0:1];reg [2:0] slot_length[0:1];
 reg [3:0] slot_total[0:1],slot_returned[0:1];
 reg [127:0] cache[0:1][0:WORDS-1];
 reg fill_active,fill_slot,consume_active,consume_slot,consume_group;
 reg [3:0] fill_offered;reg [2:0] consume_k;
 reg [3:0] writes_offered,writes_acked;
 reg [3:0] core_pending;
 reg [31:0] step_serial,reply_serial;
 // One registered S offer plus exactly two accepted response-owner entries.
 // A held offer can refill on its accepting edge. Expose it only with
 // available credit, including a true concurrent response take. Once
 // exposed and stalled, credit cannot be lost without that offer firing.
 reg offer_valid,offer_slot;reg [3:0] offer_index;
 reg q_read,q_write;reg [1:0] q_count;
 reg q_is_write[0:1],q_slot[0:1];reg [3:0] q_index[0:1];
 reg dot_req_write;
 reg [9:0] dot_req_address;
 reg [127:0] dot_req_wdata;
 reg snap_restore,snap_committed;
 reg [9:0] snap_base;
 reg [$clog2(ROWS*5)-1:0] snap_index;
 wire snap_start,snap_ready,snap_cmd_ready,snap_done_valid,snap_abort_ready,snap_state_out_valid,snap_state_in_ready;
 wire snap_req_valid,snap_req_write,snap_rsp_ready,snap_done_error,snap_done_aborted;
 wire [9:0] snap_req_address;
 wire [31:0] snap_done_tag;
 wire [$clog2(ROWS*5+3)-1:0] snap_done_count;
 wire [127:0] snap_state_in_word,snap_state_out_word,snap_req_data;
 wire snapshot_running=CHECKPOINT&&state==SNAPSHOT_RUN;
 wire dot_rsp_ready=!reset&&q_count!=0;
 assign s_rsp_ready=snapshot_running?snap_rsp_ready:dot_rsp_ready;
 wire ack_fire=!snapshot_running&&s_rsp_valid&&dot_rsp_ready;
 assign s_req_valid=snapshot_running?snap_req_valid:(!reset&&offer_valid&&(q_count<2||ack_fire));
 assign s_req_write=snapshot_running?snap_req_write:dot_req_write;
 assign s_req_address=snapshot_running?snap_req_address:dot_req_address;
 assign s_req_wdata=snapshot_running?snap_req_data:dot_req_wdata;
 wire req_fire=!snapshot_running&&s_req_valid&&s_req_ready;
 wire quiet=q_count==0&&!offer_valid;
 wire [3:0] read_offer_index=fill_offered+{3'd0,(req_fire&&!s_req_write)};
 wire [3:0] write_offer_index=writes_offered+{3'd0,(req_fire&&s_req_write)};
 assign cmd_ready=!reset&&state==IDLE&&!rsp_valid;
 assign abort_ready=snapshot_running?snap_abort_ready&&abort_key==key:
     (!reset&&state==RUN&&owned&&!aborting&&!rsp_valid&&abort_key==key);
 wire abort_fire=state==RUN&&abort_valid&&abort_ready;
 wire stop=aborting||abort_fire;
 // Same two real S credits and the same two operand slots. Start the
 // next slot on the final accepting edge of the previous fill. The first
 // row-0 word already has a known address; register that offer on this
 // edge as well, without changing any held offer or response ownership.
 wire last_fill_request=fill_active&&req_fire&&!s_req_write&&read_offer_index==slot_total[fill_slot];
 wire alloc_slot=slot_state[0]!=FREE;
 wire alloc_fill=(!fill_active||(REFILL_NEXT&&last_fill_request))&&tile_cursor<chunk_k&&
     (slot_state[0]==FREE||slot_state[1]==FREE);
 wire c_in_ready,c_out_valid,c_out_error,c_out_done;
 reg c_in_valid;reg [1:0] c_in_kind;reg [15:0] c_in_k;
 reg c_in_group;reg [31:0] c_in_tag;
 reg [ROWS*32-1:0] c_in_a;reg [127:0] c_in_b;
 wire [1:0] c_out_kind;wire [127:0] c_out_key;wire [31:0] c_out_tag;
 wire [ROWS*256-1:0] c_out_data;
 wire final_packet=c_out_valid&&c_out_kind==1&&c_out_done&&!c_out_error;
 wire c_out_ready=!final_packet || (!abort_fire&&quiet&&
  (aborting || writes_acked==({1'b0,rows}<<1)));
 wire c_in_fire=c_in_valid&&c_in_ready;
 wire c_out_fire=c_out_valid&&c_out_ready;
 wire core_reply_bad=c_out_key!=key||(c_out_kind==1?c_out_tag!=reply_serial:c_out_tag!=tag);
 // Existing command kind 3 is reserved for optional S80 checkpoint I/O.
 // cmd_layout=0 saves the live owner, 1 restores a committed matching image.
 // A-base names the checkpoint region and K-offset names its exact next K.
 wire [12:0] snap_end_address={3'd0,cmd_a_base}+13'(ROWS*5+2);
 wire [12:0] snap_result_end={3'd0,(cmd_layout?cmd_result_base:result_base)}+
       ({10'd0,(cmd_layout?cmd_rows:rows)}<<1);
 wire [12:0] snap_result_begin={3'd0,(cmd_layout?cmd_result_base:result_base)};
 wire snap_address_valid=snap_end_address<=1024&&snap_result_end<=1024&&
      (snap_end_address<=snap_result_begin||snap_result_end<={3'd0,cmd_a_base});
 wire snap_save_valid=owned&&cmd_key==key&&cmd_k_offset==next_chunk&&next_chunk!=0&&next_chunk<full_k;
 wire snap_restore_valid=!owned&&cmd_sources_committed&&cmd_k_offset!=0&&cmd_k_offset<cmd_full_k&&
      cmd_n!=0&&cmd_n<=8&&cmd_rows!=0&&int'(cmd_rows)<=ROWS;
 assign snap_start=CHECKPOINT&&cmd_valid&&cmd_ready&&cmd_kind==3&&quiet&&core_pending==0&&
      snap_address_valid&&(cmd_layout?snap_restore_valid:snap_save_valid);
 wire [127:0] snap_metadata={32'h5338_3001,40'd0,full_k,next_chunk,n,rows,shift,layout,result_base};
 wire snap_end=snapshot_running&&snap_done_valid;
 wire snap_pass=!snap_done_error&&!snap_done_aborted&&snap_done_tag==tag&&
      snap_done_count==$clog2(ROWS*5+3)'(ROWS*5+2);
 dot_s32_core #(.ROWS(ROWS),.CHECKPOINT(CHECKPOINT)) core(
  .clk(clk),.reset(reset),.in_valid(c_in_valid),.in_ready(c_in_ready),
  .in_kind(c_in_kind),.in_key(key),.in_tag(c_in_tag),.in_full_k(full_k),
  .in_k(c_in_k),.in_group(c_in_group),.in_n(n),.in_rows(rows),.in_shift(shift),
  .in_a(c_in_a),.in_b(c_in_b),.out_valid(c_out_valid),.out_ready(c_out_ready),
  .out_kind(c_out_kind),.out_key(c_out_key),.out_tag(c_out_tag),
  .out_error(c_out_error),.out_done(c_out_done),.out_data(c_out_data),
  .snapshot_start(snap_start),.snapshot_restore(cmd_layout),.snapshot_end(snap_end),.snapshot_commit(snap_pass),
  .snapshot_k(next_chunk),.snapshot_index(snap_index),.snapshot_load(snap_state_out_valid),
  .snapshot_load_data(snap_state_out_word),.snapshot_ready(snap_ready),.snapshot_read_data(snap_state_in_word));
 if(CHECKPOINT)begin: checkpoint_codec
  dot_s80_checkpoint #(.WORDS(ROWS*5)) codec(
   .clk(clk),.reset(reset),.cmd_valid(state==SNAPSHOT_PREP&&snap_ready),.cmd_ready(snap_cmd_ready),
   .cmd_restore(snap_restore),.cmd_committed(snap_committed),.cmd_tag(tag),.cmd_key(key),.cmd_metadata(snap_metadata),
   .cmd_base(snap_base),.abort_valid(abort_valid&&snapshot_running&&abort_key==key),.abort_ready(snap_abort_ready),
   .abort_tag(tag),.state_in_valid(1'b1),.state_in_ready(snap_state_in_ready),.state_in_word(snap_state_in_word),
   .state_out_valid(snap_state_out_valid),.state_out_ready(1'b1),.state_out_word(snap_state_out_word),
   .s_req_valid(snap_req_valid),.s_req_ready(snapshot_running&&s_req_ready),.s_req_write(snap_req_write),
   .s_req_address(snap_req_address),.s_req_data(snap_req_data),.s_rsp_valid(snapshot_running&&s_rsp_valid),
   .s_rsp_ready(snap_rsp_ready),.s_rsp_data(s_rsp_data),.s_rsp_error(s_rsp_error),.done_valid(snap_done_valid),
   .done_ready(snapshot_running),.done_tag(snap_done_tag),.done_error(snap_done_error),
   .done_aborted(snap_done_aborted),.done_ack_count(snap_done_count));
 end else begin: no_checkpoint_codec
  assign snap_cmd_ready=0;assign snap_done_valid=0;assign snap_done_tag=0;assign snap_done_count=0;
  assign snap_abort_ready=0;assign snap_state_out_valid=0;assign snap_state_in_ready=0;assign snap_state_out_word=0;
  assign snap_req_valid=0;assign snap_req_write=0;assign snap_req_address=0;assign snap_req_data=0;assign snap_rsp_ready=0;
  assign snap_done_error=0;assign snap_done_aborted=0;
 end
 always @*begin
  c_in_valid=0;c_in_kind=1;c_in_k=0;c_in_group=0;c_in_tag=step_serial;c_in_a=0;c_in_b=0;
  if(state==BEGIN_SEND)begin c_in_valid=1;c_in_kind=0;c_in_tag=tag;end
  else if(state==RUN)begin
   if(aborting&&quiet&&core_pending==0&&!core_finished&&!cancel_sent)begin
    c_in_valid=1;c_in_kind=2;c_in_tag=tag;
   end else if(!stop&&consume_active&&!final_packet)begin
    c_in_valid=1;c_in_kind=1;c_in_group=consume_group;
    c_in_k=chunk_offset+{8'd0,slot_first[consume_slot]}+{13'd0,consume_k};
    for(integer r=0;r<ROWS;r=r+1)
     if(r<int'(rows))c_in_a[r*32+:32]=cache[consume_slot][r][consume_k*32+:32];
    for(integer c=0;c<4;c=c+1)begin
     if(c+(consume_group?4:0)<int'(n))begin
      if(layout)c_in_b[c*32+:32]=cache[consume_slot][ROWS+int'(consume_k)*2+int'(consume_group)][c*32+:32];
      else c_in_b[c*32+:32]=cache[consume_slot][ROWS+c+(consume_group?4:0)][consume_k*32+:32];
     end
    end
   end
  end
 end
 // QK reserves a K128 chunk. AV reserves the configured number of K rows.
 // A/B/result cannot alias. Sources must have true producer ACK proof before
 // CHUNK is offered; this flag is a contract input, not a guessed cache hit.
 wire [12:0] a_end={3'd0,cmd_a_base}+13'(int'(rows)*(layout ? AV_MAX_K/4 : 32));
 wire [12:0] b_end={3'd0,cmd_b_base}+(layout?13'(AV_MAX_K*2):13'(int'(n)*32));
 wire [12:0] r_end={3'd0,result_base}+13'(int'(rows)*2);
 wire chunk_bad=!owned||cmd_key!=key||!cmd_sources_committed||cmd_k_offset!=next_chunk||
  cmd_chunk_k==0||cmd_chunk_k>(layout?8'(AV_MAX_K):8'd128)||
  {1'b0,cmd_k_offset}+{9'd0,cmd_chunk_k}>{1'b0,full_k}||
  ((cmd_chunk_k&8'd3)!=0&&{1'b0,cmd_k_offset}+{9'd0,cmd_chunk_k}!={1'b0,full_k})||
  a_end>1024||b_end>1024||r_end>1024||
  ({3'd0,cmd_a_base}<b_end&&{3'd0,cmd_b_base}<a_end)||
  ({3'd0,cmd_a_base}<r_end&&{3'd0,result_base}<a_end)||
  ({3'd0,cmd_b_base}<r_end&&{3'd0,result_base}<b_end);
 wire [3:0] bword=read_offer_index-{1'b0,rows};
 wire [3:0] local_b_k=n>4?{1'b0,bword[3:1]}:bword;
 wire local_b_group=n>4&&bword[0];
 wire [7:0] remaining_k=chunk_k-tile_cursor;
 reg [3:0] cache_index;
 reg [9:0] address_value;
 reg [2:0] allocate_length;
 reg [3:0] allocate_total;
 always @*begin
  allocate_length=remaining_k>=8'd4 ? 3'd4 : remaining_k[2:0];
  allocate_total={1'b0,rows}+(layout?(n>4?{allocate_length,1'b0}:{1'b0,allocate_length}):n);
  cache_index=read_offer_index;address_value=0;
  // The admitted raw window bounds and finite fill count prove all these
  // addresses. Use the actual 1/2-group bit decomposition, not a dynamic
  // divider or 32-bit software-style address arithmetic.
  if(read_offer_index<{1'b0,rows})address_value=a_base+{1'b0,read_offer_index,5'd0}+{4'd0,slot_first[fill_slot][7:2]};
  else if(layout)begin
   cache_index=4'(ROWS)+{local_b_k[2:0],local_b_group};
   address_value=b_base+(({2'd0,slot_first[fill_slot]}+{6'd0,local_b_k})<<1)+{9'd0,local_b_group};
  end else begin
   cache_index=4'(ROWS)+bword;address_value=b_base+{1'b0,bword,5'd0}+{4'd0,slot_first[fill_slot][7:2]};
  end
 end
 task automatic respond(input fault,aborted,done);
  begin rsp_valid<=1;rsp_kind<=current_kind;rsp_key<=key;rsp_tag<=tag;
   rsp_error<=fault;rsp_aborted<=aborted;rsp_done<=done;state<=IDLE;end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;owned<=0;aborting<=0;abort_fault<=0;core_finished<=0;cancel_sent<=0;
   current_kind<=0;key<=0;tag<=0;full_k<=0;next_chunk<=0;chunk_offset<=0;chunk_k<=0;
   tile_cursor<=0;next_consume<=0;n<=0;rows<=0;shift<=0;layout<=0;a_base<=0;b_base<=0;result_base<=0;
   fill_active<=0;fill_slot<=0;fill_offered<=0;consume_active<=0;consume_slot<=0;consume_group<=0;consume_k<=0;
   writes_offered<=0;writes_acked<=0;core_pending<=0;step_serial<=0;reply_serial<=0;
   rsp_valid<=0;rsp_kind<=0;rsp_key<=0;rsp_tag<=0;rsp_error<=0;rsp_aborted<=0;rsp_done<=0;rsp_written_mask<=0;
   offer_valid<=0;dot_req_write<=0;dot_req_address<=0;dot_req_wdata<=0;offer_slot<=0;offer_index<=0;
   snap_restore<=0;snap_committed<=0;snap_base<=0;snap_index<=0;
   q_read<=0;q_write<=0;q_count<=0;
   for(integer slot=0;slot<2;slot=slot+1)begin
    slot_state[slot]<=FREE;slot_first[slot]<=0;slot_length[slot]<=0;slot_total[slot]<=0;slot_returned[slot]<=0;
    q_is_write[slot]<=0;q_slot[slot]<=0;q_index[slot]<=0;
   end
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   case({c_in_fire,c_out_fire})
    2'b10:core_pending<=core_pending+1'b1;
    2'b01:core_pending<=core_pending-1'b1;
    default:begin end
   endcase
   case({req_fire,ack_fire})
    2'b10:q_count<=q_count+1'b1;
    2'b01:q_count<=q_count-1'b1;
    default:begin end
   endcase
   if(req_fire)begin
    offer_valid<=0;q_is_write[q_write]<=s_req_write;q_slot[q_write]<=offer_slot;
    q_index[q_write]<=offer_index;q_write<=!q_write;
    if(s_req_write)writes_offered<=writes_offered+1'b1;
    else begin
     fill_offered<=fill_offered+1'b1;
     if(read_offer_index==slot_total[fill_slot])fill_active<=0;
    end
   end
   if(ack_fire)begin
    q_read<=!q_read;
    if(s_rsp_error)begin aborting<=1;abort_fault<=1;end
    if(q_is_write[q_read])begin
     writes_acked<=writes_acked+1'b1;
     if(!s_rsp_error)rsp_written_mask[$clog2(ROWS*2)'(q_index[q_read])]<=1;
    end else begin
     cache[q_slot[q_read]][q_index[q_read]]<=s_rsp_data;
     slot_returned[q_slot[q_read]]<=slot_returned[q_slot[q_read]]+1'b1;
     if(slot_returned[q_slot[q_read]]+1'b1==slot_total[q_slot[q_read]])begin
      slot_state[q_slot[q_read]]<=READY;
     end
    end
   end
   if(abort_fire)begin aborting<=1;abort_fault<=1;end
   if(c_in_fire)begin
    if(state==BEGIN_SEND)state<=BEGIN_WAIT;
    else if(c_in_kind==2)cancel_sent<=1;
    else begin
     step_serial<=step_serial+1'b1;
     if(n>4&&!consume_group)consume_group<=1;
     else begin
      consume_group<=0;
      if(consume_k+1'b1==slot_length[consume_slot])begin
       slot_state[consume_slot]<=FREE;consume_active<=0;next_consume<=next_consume+{5'd0,slot_length[consume_slot]};consume_k<=0;
      end else consume_k<=consume_k+1'b1;
     end
    end
   end
   if(c_out_fire)begin
    if(c_out_kind==1)reply_serial<=reply_serial+1'b1;
    if(c_out_error||core_reply_bad)begin
     if(state==BEGIN_WAIT)begin owned<=0;respond(1,0,0);end
     else begin aborting<=1;abort_fault<=1;end
    end else if(state==BEGIN_WAIT)begin owned<=1;respond(0,0,0);end
    else if(c_out_done)begin
     owned<=0;core_finished<=1;
     if(!aborting&&c_out_kind==1)respond(0,0,1);
    end
   end
   if(cmd_valid&&cmd_ready)begin
    current_kind<=cmd_kind;tag<=cmd_tag;rsp_written_mask<=0;
    aborting<=0;abort_fault<=0;core_finished<=0;cancel_sent<=0;
    if(snap_start)begin
     snap_restore<=cmd_layout;snap_committed<=cmd_sources_committed;snap_base<=cmd_a_base;snap_index<=0;
     if(cmd_layout)begin
      key<=cmd_key;full_k<=cmd_full_k;next_chunk<=cmd_k_offset;n<=cmd_n;rows<=cmd_rows;
      shift<=cmd_shift;layout<=cmd_b_base[0];result_base<=cmd_result_base;
     end
     state<=SNAPSHOT_PREP;
    end else if(cmd_kind==0&&!owned)begin
     key<=cmd_key;full_k<=cmd_full_k;n<=cmd_n;rows<=cmd_rows;shift<=cmd_shift;layout<=cmd_layout;
     result_base<=cmd_result_base;next_chunk<=0;state<=BEGIN_SEND;
    end else if(cmd_kind==1&&!chunk_bad)begin
     a_base<=cmd_a_base;b_base<=cmd_b_base;chunk_offset<=cmd_k_offset;chunk_k<=cmd_chunk_k;
     tile_cursor<=0;next_consume<=0;fill_active<=0;consume_active<=0;
     writes_offered<=0;writes_acked<=0;state<=RUN;
     for(integer slot=0;slot<2;slot=slot+1)slot_state[slot]<=FREE;
    end else if(cmd_kind==2&&owned&&cmd_key==key)begin
     aborting<=1;state<=RUN;fill_active<=0;consume_active<=0;
    end else begin
     rsp_valid<=1;rsp_kind<=cmd_kind;rsp_key<=cmd_key;rsp_tag<=cmd_tag;rsp_error<=1;rsp_aborted<=0;rsp_done<=0;
    end
   end
   if(CHECKPOINT)begin
    if(state==SNAPSHOT_PREP&&snap_ready&&snap_cmd_ready)state<=SNAPSHOT_RUN;
    if(snap_state_in_ready||snap_state_out_valid)snap_index<=snap_index+1'b1;
    if(snap_end)begin
     if(snap_pass)owned<=snap_restore;
     respond(!snap_pass,snap_done_aborted,0);
    end
   end
   if(state==RUN)begin
    // No new read/write is created after cancel; an existing registered
    // offer survives and is accounted by the same response-owner FIFO.
    if((!offer_valid||req_fire)&&!stop)begin
     if(final_packet&&write_offer_index<({1'b0,rows}<<1))begin
      offer_valid<=1;dot_req_write<=1;dot_req_address<=result_base+{6'd0,write_offer_index};
      dot_req_wdata<=c_out_data[write_offer_index*128+:128];offer_slot<=0;offer_index<=write_offer_index;
     end else if(REFILL_NEXT&&alloc_fill)begin
      offer_valid<=1;dot_req_write<=0;dot_req_address<=a_base+{4'd0,tile_cursor[7:2]};
      offer_slot<=alloc_slot;offer_index<=0;
     end else if(fill_active&&read_offer_index<slot_total[fill_slot]&&int'(cache_index)<WORDS)begin
      offer_valid<=1;dot_req_write<=0;dot_req_address<=address_value;
      offer_slot<=fill_slot;offer_index<=cache_index;
     end
    end
    if(!stop&&alloc_fill)begin
     fill_slot<=alloc_slot;fill_active<=1;fill_offered<=0;
     slot_state[alloc_slot]<=FILL;slot_first[alloc_slot]<=tile_cursor;
     slot_length[alloc_slot]<=allocate_length;slot_total[alloc_slot]<=allocate_total;
     slot_returned[alloc_slot]<=0;tile_cursor<=tile_cursor+{5'd0,allocate_length};
    end
    if(!stop&&!consume_active)begin
     if(slot_state[0]==READY&&slot_first[0]==next_consume)begin consume_slot<=0;consume_active<=1;consume_k<=0;consume_group<=0;end
     else if(slot_state[1]==READY&&slot_first[1]==next_consume)begin consume_slot<=1;consume_active<=1;consume_k<=0;consume_group<=0;end
    end
    if(aborting&&core_finished&&core_pending==0&&quiet)begin
     fill_active<=0;consume_active<=0;for(integer slot=0;slot<2;slot=slot+1)slot_state[slot]<=FREE;
     respond(abort_fault,1,1);
    end else if(!stop&&next_consume==chunk_k&&!consume_active&&!fill_active&&core_pending==0&&quiet&&!c_out_valid)begin
     next_chunk<=chunk_offset+{8'd0,chunk_k};respond(0,0,0);
    end
   end
  end
 end
endmodule
