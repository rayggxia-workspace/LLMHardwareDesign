// Issue247 R3: optional S32 x W8/S96 finite service, separate from native P16.
// K-major, N-interleaved W8 source layout is gathered into one K16 packet.
// Connect these ports to ONE existing four-bank 16KiB 1RW store. This module
// never asserts read and write requests together. It contains no private SRAM.
module r3_m_finite #(parameter integer BUFFERS=1) (
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,
 input wire [2:0] cmd_ctx,input wire [31:0] cmd_tag,
 input wire [15:0] cmd_ki,cmd_total_k,
 input wire [4:0] cmd_k,input wire [3:0] cmd_n,
 input wire [5:0] cmd_shift,input wire cmd_first,cmd_last,
 input wire [13:0] cmd_a_addr,cmd_b_addr,cmd_out_addr,
 output wire done_valid,input wire done_ready,
 output wire [2:0] done_ctx,output wire [31:0] done_tag,
 output wire [15:0] done_next_k,output wire done_last,done_error,
 output wire [7:0] done_saturated,output wire [255:0] done_data,
 output wire busy,
 output wire s_read_valid,input wire s_read_ready,output wire [7:0] s_read_addr,
 input wire s_read_rsp_valid,output wire s_read_rsp_take,input wire [511:0] s_read_data,
 output wire s_write_valid,input wire s_write_ready,output wire [9:0] s_write_addr,
 output wire [127:0] s_write_data,
 input wire s_write_ack_valid,output wire s_write_ack_take
);
 localparam [1:0] EMPTY=0,LOADING=1,READY=2;
 localparam [1:0] W_IDLE=0,W_ACTIVE=1,W_HOLD=2;
 reg [1:0] state[0:BUFFERS-1];
 reg [511:0] packet_a[0:BUFFERS-1];
 reg [1535:0] packet_b[0:BUFFERS-1];
 reg [31:0] packet_sequence[0:BUFFERS-1],next_sequence;
 reg [2:0] packet_ctx[0:BUFFERS-1],read_issued[0:BUFFERS-1],read_received[0:BUFFERS-1],read_needed[0:BUFFERS-1];
 reg [2:0] packet_reservation[0:BUFFERS-1];
 reg [15:0] packet_end[0:BUFFERS-1];
 reg [4:0] packet_k[0:BUFFERS-1];reg [3:0] packet_n[0:BUFFERS-1];
 reg [5:0] packet_shift[0:BUFFERS-1];reg packet_first[0:BUFFERS-1],packet_last[0:BUFFERS-1];
 reg [13:0] packet_a_addr[0:BUFFERS-1],packet_b_addr[0:BUFFERS-1];
 reg [7:0] context_active,context_closing,completion_valid,completion_error,completion_last,completion_release;
 reg [31:0] context_tag[0:7],completion_tag[0:7];
 reg [15:0] context_reserved[0:7],context_committed[0:7],context_total[0:7],completion_next[0:7];
 reg [3:0] context_n[0:7];reg [5:0] context_shift[0:7];reg [13:0] context_out[0:7];
 // A fixed eight-entry completion FIFO bounds all accepted commands, including
 // sources already transferred to the leaf and responses held by the caller.
 reg [2:0] completion_ctx[0:7],reservation_head,reservation_tail;
 reg [3:0] reservation_count;
 reg [1:0] write_phase;reg [2:0] write_reservation;reg [1:0] write_issued,write_acked;
 reg [255:0] write_result;reg [7:0] write_saturation;
 reg [9:0] write_base;
 // At most two S read requests, including their pending SRAM responses.
 reg read_head,read_tail;reg [1:0] read_count;
 reg read_buffer[0:1];reg [1:0] read_part[0:1];
 // The leaf commits at the third advancing edge (accept, reduction, commit).
 reg p0_valid,p1_valid,p2_valid;reg [2:0] p0_ctx,p1_ctx,p0_reservation,p1_reservation,p2_reservation,result_reservation;
 reg [15:0] p0_end,p1_end;reg p0_last,p1_last;
 integer free_id,load_id,ready_id,allocate_id;
 reg free_found,load_found,ready_found,descriptor_ok;
 reg [16:0] command_end,a_limit,b_limit,out_limit;
 reg [8:0] b_span;
 reg [2:0] b_reads;
 wire leaf_ready,leaf_valid,leaf_out_valid,leaf_out_ready,leaf_error;
 wire [2:0] leaf_out_ctx;wire [255:0] leaf_result;wire [7:0] leaf_saturation;
 reg [1023:0] leaf_b;
 wire leaf_fire=leaf_valid&&leaf_ready;
 wire read_pop=s_read_rsp_valid&&s_read_rsp_take;
 wire read_push=s_read_valid&&s_read_ready;
 wire write_push=s_write_valid&&s_write_ready;
 wire write_pop=s_write_ack_valid&&s_write_ack_take;
 wire command_fire=cmd_valid&&cmd_ready;
 wire completion_pop=done_valid&&done_ready;

 function automatic overlap;
  input [16:0] a0,a1,b0,b1;
  begin overlap=a0<b1&&b0<a1;end
 endfunction

 always @* begin
  free_id=0;load_id=0;ready_id=0;free_found=0;load_found=0;ready_found=0;
  for(integer slot=0;slot<BUFFERS;slot=slot+1)begin
   if(state[slot]==EMPTY&&!free_found)begin free_found=1;free_id=slot;end
   if(state[slot]==LOADING&&read_issued[slot]<read_needed[slot]&&
      (!load_found||$signed(packet_sequence[slot]-packet_sequence[load_id])<0))begin load_found=1;load_id=slot;end
   if(state[slot]==READY&&(!ready_found||$signed(packet_sequence[slot]-packet_sequence[ready_id])<0))begin
    ready_found=1;ready_id=slot;
   end
  end
  allocate_id=free_found?free_id:ready_id;
  command_end={1'b0,cmd_ki}+{12'd0,cmd_k};
  a_limit={3'd0,cmd_a_addr}+17'd64;
  b_limit={3'd0,cmd_b_addr}+17'(cmd_k*cmd_n);
  out_limit={3'd0,cmd_out_addr}+17'd32;
  b_span={3'd0,cmd_b_addr[5:0]}+9'(cmd_k*cmd_n);
  b_reads=3'((b_span+9'd63)>>6);
  descriptor_ok=cmd_k>=1&&cmd_k<=16&&cmd_n>=1&&cmd_n<=8&&
   cmd_total_k!=0&&command_end<=17'd65535&&command_end<={1'b0,cmd_total_k}&&
   cmd_last==(command_end=={1'b0,cmd_total_k})&&
   cmd_a_addr[5:0]==0&&cmd_out_addr[3:0]==0&&
   a_limit<=17'd16384&&b_limit<=17'd16384&&out_limit<=17'd16384;
  if(cmd_first)begin
   if(cmd_ki!=0||context_active[cmd_ctx])descriptor_ok=0;
  end else if(!context_active[cmd_ctx]||context_closing[cmd_ctx]||cmd_ki!=context_reserved[cmd_ctx]||
    cmd_tag!=context_tag[cmd_ctx]||cmd_total_k!=context_total[cmd_ctx]||
    cmd_n!=context_n[cmd_ctx]||cmd_shift!=context_shift[cmd_ctx]||
    cmd_out_addr!=context_out[cmd_ctx])descriptor_ok=0;
  // Output staging words are exclusive for the whole context session.
  // Live input leases end at leaf accept; external writers must observe them.
  if(overlap({3'd0,cmd_a_addr},a_limit,{3'd0,cmd_out_addr},out_limit)||
     overlap({3'd0,cmd_b_addr},b_limit,{3'd0,cmd_out_addr},out_limit))descriptor_ok=0;
  for(integer c=0;c<8;c=c+1)if(context_active[c])begin
   if(overlap({3'd0,cmd_a_addr},a_limit,{3'd0,context_out[c]},{3'd0,context_out[c]}+17'd32)||
      overlap({3'd0,cmd_b_addr},b_limit,{3'd0,context_out[c]},{3'd0,context_out[c]}+17'd32)||
      (cmd_first&&overlap({3'd0,cmd_out_addr},out_limit,{3'd0,context_out[c]},{3'd0,context_out[c]}+17'd32)))descriptor_ok=0;
  end
  for(integer slot=0;slot<BUFFERS;slot=slot+1)if(state[slot]!=EMPTY)begin
   if(overlap({3'd0,cmd_out_addr},out_limit,{3'd0,packet_a_addr[slot]},{3'd0,packet_a_addr[slot]}+17'd64)||
      overlap({3'd0,cmd_out_addr},out_limit,{3'd0,packet_b_addr[slot]},
       {3'd0,packet_b_addr[slot]}+17'(packet_k[slot]*packet_n[slot])))descriptor_ok=0;
  end
  leaf_b=0;
  for(integer column=0;column<8;column=column+1)
   for(integer k=0;k<16;k=k+1)
    if(ready_found&&column<packet_n[ready_id]&&k<packet_k[ready_id])
     leaf_b[8*(column*16+k)+:8]=packet_b[ready_id][8*(int'(packet_b_addr[ready_id][5:0])+k*int'(packet_n[ready_id])+column)+:8];
 end

 assign cmd_ready=!reset&&(reservation_count<8||completion_pop)&&(!descriptor_ok||free_found||leaf_fire);
 // Reservations permit prefetch, but arithmetic issue still observes the
 // committed frontier (including a same-edge genuine commit bypass).
 assign leaf_valid=!reset&&ready_found&&
  (context_committed[packet_ctx[ready_id]]==packet_end[ready_id]-{11'd0,packet_k[ready_id]}||
   (p1_valid&&p1_ctx==packet_ctx[ready_id]&&p1_end==packet_end[ready_id]-{11'd0,packet_k[ready_id]}));
 assign leaf_out_ready=!reset&&write_phase==W_IDLE;
 m_s32_stream_candidate #(.K(16),.N(8),.ROWS(8)) leaf(
  .clk,.reset,.in_valid(leaf_valid),.in_ready(leaf_ready),.in_row(packet_ctx[ready_id]),
  .in_first(packet_first[ready_id]),.in_last(packet_last[ready_id]),
  .in_k({1'b0,packet_k[ready_id]}),.in_n(packet_n[ready_id]),
  .in_round_shift(packet_shift[ready_id]),.in_b_shift(5'd0),.in_b_unsigned(1'b0),
  .in_a(packet_a[ready_id]),.in_b(leaf_b),
  .out_valid(leaf_out_valid),.out_ready(leaf_out_ready),.out_row(leaf_out_ctx),
  .out_data(leaf_result),.out_saturated(leaf_saturation),.out_error(leaf_error)
 );
 assign s_write_valid=!reset&&write_phase==W_ACTIVE&&write_issued<2;
 assign s_write_addr=write_base+{8'd0,write_issued};
 assign s_write_data=write_result[128*int'(write_issued[0])+:128];
 assign s_write_ack_take=!reset&&write_phase==W_ACTIVE&&write_acked<write_issued;
 assign s_read_valid=!reset&&load_found&&!s_write_valid&&(read_count<2||read_pop);
 assign s_read_addr=read_issued[load_id]==0?packet_a_addr[load_id][13:6]:
  packet_b_addr[load_id][13:6]+8'(read_issued[load_id]-1'b1);
 assign s_read_rsp_take=!reset&&read_count!=0;
 assign done_valid=!reset&&reservation_count!=0&&completion_valid[reservation_head];
 assign done_ctx=completion_ctx[reservation_head];assign done_tag=completion_tag[reservation_head];
 assign done_next_k=completion_next[reservation_head];assign done_last=completion_last[reservation_head];
 assign done_error=completion_error[reservation_head];
 assign done_data=completion_release[reservation_head]?write_result:256'd0;
 assign done_saturated=completion_release[reservation_head]?write_saturation:8'd0;
 assign busy=reservation_count!=0;

 always @(posedge clk)begin
  if(reset)begin
   context_active<=0;context_closing<=0;completion_valid<=0;completion_error<=0;
   completion_last<=0;completion_release<=0;reservation_head<=0;reservation_tail<=0;reservation_count<=0;
   write_phase<=W_IDLE;write_reservation<=0;write_issued<=0;write_acked<=0;
   write_result<=0;write_saturation<=0;write_base<=0;
   read_head<=0;read_tail<=0;read_count<=0;next_sequence<=0;
   p0_valid<=0;p1_valid<=0;p2_valid<=0;p0_ctx<=0;p1_ctx<=0;p0_end<=0;p1_end<=0;p0_last<=0;p1_last<=0;
   p0_reservation<=0;p1_reservation<=0;p2_reservation<=0;result_reservation<=0;
   for(integer i=0;i<8;i=i+1)begin
    context_tag[i]<=0;context_reserved[i]<=0;context_committed[i]<=0;context_total[i]<=0;
    context_n[i]<=0;context_shift[i]<=0;context_out[i]<=0;
    completion_ctx[i]<=0;completion_tag[i]<=0;completion_next[i]<=0;
   end
   for(integer i=0;i<2;i=i+1)begin read_buffer[i]<=0;read_part[i]<=0;end
   for(integer slot=0;slot<BUFFERS;slot=slot+1)begin
    state[slot]<=EMPTY;packet_a[slot]<=0;packet_b[slot]<=0;packet_sequence[slot]<=0;
    packet_ctx[slot]<=0;packet_reservation[slot]<=0;packet_end[slot]<=0;packet_k[slot]<=0;packet_n[slot]<=0;
    packet_shift[slot]<=0;packet_first[slot]<=0;packet_last[slot]<=0;
    packet_a_addr[slot]<=0;packet_b_addr[slot]<=0;
    read_issued[slot]<=0;read_received[slot]<=0;read_needed[slot]<=0;
   end
  end else begin
   if(completion_pop)begin
    completion_valid[reservation_head]<=0;reservation_head<=reservation_head+1'b1;
    if(completion_release[reservation_head])begin
     context_active[completion_ctx[reservation_head]]<=0;
     context_closing[completion_ctx[reservation_head]]<=0;
     context_reserved[completion_ctx[reservation_head]]<=0;
     context_committed[completion_ctx[reservation_head]]<=0;write_phase<=W_IDLE;
    end
   end
   case({command_fire,completion_pop})
    2'b10:reservation_count<=reservation_count+1'b1;
    2'b01:reservation_count<=reservation_count-1'b1;
    default:begin end
   endcase
   // Match the leaf's global stall/advance exactly; no guessed timer retires
   // a context while the arithmetic pipeline is held by output backpressure.
   if(leaf_ready)begin
    p2_valid<=p1_valid;p2_reservation<=p1_reservation;
    p1_valid<=p0_valid;p1_ctx<=p0_ctx;p1_end<=p0_end;p1_last<=p0_last;p1_reservation<=p0_reservation;
    p0_valid<=leaf_fire;
    if(leaf_fire)begin
     p0_ctx<=packet_ctx[ready_id];p0_end<=packet_end[ready_id];p0_last<=packet_last[ready_id];
     p0_reservation<=packet_reservation[ready_id];
    end
    if(p1_valid)begin
     context_committed[p1_ctx]<=p1_end;
     completion_next[p1_reservation]<=p1_end;
     if(!p1_last)completion_valid[p1_reservation]<=1;
    end
    if(p2_valid)result_reservation<=p2_reservation;
   end
   // Source ownership transfers into the leaf product registers on this edge.
   // Allocation below may safely reuse this same physical slot immediately.
   if(leaf_fire)state[ready_id]<=EMPTY;
   if(read_push)begin
    read_buffer[read_tail]<=1'(load_id);read_part[read_tail]<=2'(read_issued[load_id]);read_tail<=!read_tail;
    read_issued[load_id]<=read_issued[load_id]+1'b1;
   end
   if(read_pop)begin
    if(read_part[read_head]==0)packet_a[read_buffer[read_head]]<=s_read_data;
    else packet_b[read_buffer[read_head]][512*(int'(read_part[read_head])-1)+:512]<=s_read_data;
    read_received[read_buffer[read_head]]<=read_received[read_buffer[read_head]]+1'b1;
    if(read_received[read_buffer[read_head]]+1'b1==read_needed[read_buffer[read_head]])state[read_buffer[read_head]]<=READY;
    read_head<=!read_head;
   end
   case({read_push,read_pop})
    2'b10:read_count<=read_count+1'b1;
    2'b01:read_count<=read_count-1'b1;
    default:begin end
   endcase
   if(leaf_out_valid&&leaf_out_ready)begin
    write_reservation<=result_reservation;write_result<=leaf_result;write_saturation<=leaf_saturation;
    write_base<=context_out[leaf_out_ctx][13:4];write_issued<=0;write_acked<=0;
    completion_release[result_reservation]<=1;completion_error[result_reservation]<=leaf_error;
    if(leaf_error)begin completion_valid[result_reservation]<=1;write_phase<=W_HOLD;end
    else write_phase<=W_ACTIVE;
   end
   if(write_push)write_issued<=write_issued+1'b1;
   if(write_pop)begin
    write_acked<=write_acked+1'b1;
    if(write_acked==1)begin
     write_phase<=W_HOLD;completion_valid[write_reservation]<=1;
    end
   end
   if(command_fire)begin
    reservation_tail<=reservation_tail+1'b1;completion_ctx[reservation_tail]<=cmd_ctx;
    completion_tag[reservation_tail]<=cmd_tag;completion_last[reservation_tail]<=cmd_last;
    completion_release[reservation_tail]<=0;completion_error[reservation_tail]<=!descriptor_ok;
    completion_next[reservation_tail]<=context_reserved[cmd_ctx];
    completion_valid[reservation_tail]<=!descriptor_ok;
    if(descriptor_ok)begin
     state[allocate_id]<=LOADING;packet_sequence[allocate_id]<=next_sequence;next_sequence<=next_sequence+1'b1;
     packet_ctx[allocate_id]<=cmd_ctx;packet_reservation[allocate_id]<=reservation_tail;packet_end[allocate_id]<=command_end[15:0];
     packet_k[allocate_id]<=cmd_k;packet_n[allocate_id]<=cmd_n;packet_shift[allocate_id]<=cmd_shift;
     packet_first[allocate_id]<=cmd_first;packet_last[allocate_id]<=cmd_last;
     packet_a_addr[allocate_id]<=cmd_a_addr;packet_b_addr[allocate_id]<=cmd_b_addr;
     read_issued[allocate_id]<=0;read_received[allocate_id]<=0;read_needed[allocate_id]<=1'b1+b_reads;
     context_reserved[cmd_ctx]<=command_end[15:0];
     if(cmd_last)context_closing[cmd_ctx]<=1;
     if(cmd_first)begin
      context_active[cmd_ctx]<=1;context_tag[cmd_ctx]<=cmd_tag;context_committed[cmd_ctx]<=0;
      context_total[cmd_ctx]<=cmd_total_k;context_n[cmd_ctx]<=cmd_n;
      context_shift[cmd_ctx]<=cmd_shift;context_out[cmd_ctx]<=cmd_out_addr;
     end
    end
   end
  end
 end
 // Supported experiment capacities are deliberately finite and explicit.
 initial begin
  if(BUFFERS!=1&&BUFFERS!=2)$fatal(1,"R3 supports exactly one or two packet buffers");
 end
endmodule
