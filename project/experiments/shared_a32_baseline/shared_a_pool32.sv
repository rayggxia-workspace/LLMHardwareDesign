// Native S8/S16 A-container pool. Eight actual 4KiB 1RW SRAM macros.
// One immutable object, two independent readers, no broadcast or local-S copy.
module shared_a_pool32 (
 input wire clk,reset,
 input wire cfg_valid,input wire [1:0] cfg_op,
 input wire [7:0] cfg_epoch,input wire [11:0] cfg_words,
 output wire cfg_ready,output reg cfg_done,cfg_error,input wire cfg_take,
 input wire fill_valid,input wire [8:0] fill_addr,
 input wire [511:0] fill_data,input wire [3:0] fill_mask,
 output wire fill_ready,fill_done,fill_error,input wire fill_take,
 input wire [1:0] p_cmd_valid,p_cmd_bank,p_cmd_awide,
 input wire [7:0] p_cmd_rows,input wire [5:0] p_cmd_tiles,
 input wire [21:0] p_cmd_base,input wire [15:0] p_cmd_epoch,
 output wire [1:0] p_cmd_ready,output reg [1:0] p_done,p_error,
 input wire [1:0] p_done_take,
 output wire [1:0] a_valid,a_bank,a_wide,input wire [1:0] a_ready,
 output wire [5:0] a_row,output wire [3:0] a_tile,
 output wire [255:0] a_data,
 output wire object_valid,output wire [7:0] object_epoch,
 output wire [11:0] object_words
`ifdef USE_POWER_PINS
 ,inout wire vdd,gnd
`endif
);
 localparam [1:0] EMPTY=2'd0,FILL=2'd1,SEALED=2'd2;
 reg [1:0] state;
 reg [7:0] epoch_q;
 reg [11:0] words_q,accepted_words,written_words;
 reg [9:0] next_fill_line;
 assign object_valid=!reset&&state==SEALED;
 assign object_epoch=epoch_q;
 assign object_words=words_q;

 // Fill ACK FIFO has two credits including the operation in flight.
 reg fill_pending,fill_pending_error;
 reg [2:0] fill_pending_words;
 reg fill_ack_data[0:1];
 reg fill_ack_head,fill_ack_tail;
 reg [1:0] fill_ack_count;
 assign fill_done=!reset&&fill_ack_count!=0;
 assign fill_error=fill_done&&fill_ack_data[fill_ack_head];
 wire fill_pop=fill_done&&fill_take;
 wire [2:0] fill_reserved={1'b0,fill_ack_count}+{2'b0,fill_pending};
 assign fill_ready=!reset&&state==FILL&&(fill_reserved<3'd2||fill_pop);
 wire fill_fire=fill_valid&&fill_ready;
 wire [11:0] fill_remaining=words_q-accepted_words;
 wire [2:0] fill_words=fill_remaining>=12'd4 ? 3'd4 : fill_remaining[2:0];
 wire [3:0] expected_mask=fill_words==3'd4 ? 4'b1111 :
                          fill_words==3'd3 ? 4'b0111 :
                          fill_words==3'd2 ? 4'b0011 :
                          fill_words==3'd1 ? 4'b0001 : 4'b0000;
 wire fill_legal=accepted_words<words_q&&{1'b0,fill_addr}==next_fill_line&&fill_mask==expected_mask;
 wire write_fire=fill_fire&&fill_legal;

 reg [1:0] active;
 reg bank_q[0:1],wide_q[0:1];
 reg [3:0] rows_q[0:1];
 reg [5:0] total_words[0:1],sent_words[0:1];
 reg [11:0] next_word[0:1],end_word[0:1];
 reg [2:0] row_q[0:1];
 reg [1:0] tile_q[0:1];

 reg [511:0] fifo_data[0:1][0:3];
 reg [1:0] fifo_cursor[0:1][0:3];
 reg [2:0] fifo_limit[0:1][0:3];
 reg [1:0] fifo_head[0:1],fifo_tail[0:1];
 reg [2:0] fifo_count[0:1];
 wire [1:0] a_fire,fifo_pop,read_request;
 reg pending_read,pending_owner,pending_group;
 reg [1:0] pending_first;
 reg [2:0] pending_limit;
 reg round_robin;

 wire clients_idle=active==0&&p_done==0&&!pending_read&&fifo_count[0]==0&&fifo_count[1]==0;
 wire fill_drained=accepted_words==words_q&&written_words==words_q&&!fill_pending&&fill_ack_count==0;
 wire matching_epoch=cfg_epoch==epoch_q;
 wire wait_seal=cfg_valid&&cfg_op==2'd1&&state==FILL&&matching_epoch&&!fill_drained;
 wire wait_release=cfg_valid&&cfg_op==2'd2&&state==SEALED&&matching_epoch&&!clients_idle;
 wire release_requested=cfg_valid&&cfg_op==2'd2&&state==SEALED&&matching_epoch;
 assign cfg_ready=!reset&&!cfg_done&&!wait_seal&&!wait_release;
 wire cfg_fire=cfg_valid&&cfg_ready;

 wire [6:0] command_words[0:1];
 wire [12:0] command_end[0:1];
 wire [1:0] command_legal;
 genvar client;
 generate for(client=0;client<2;client=client+1)begin: consumers
  assign p_cmd_ready[client]=!reset&&state==SEALED&&!active[client]&&!p_done[client]&&!release_requested;
  assign command_words[client]={3'b0,p_cmd_rows[client*4+:4]}*{4'b0,p_cmd_tiles[client*3+:3]};
  assign command_end[client]={2'b0,p_cmd_base[client*11+:11]}+{6'b0,command_words[client]};
  assign command_legal[client]=p_cmd_epoch[client*8+:8]==epoch_q&&
   p_cmd_rows[client*4+:4]>=4'd1&&p_cmd_rows[client*4+:4]<=4'd8&&
   p_cmd_tiles[client*3+:3]>=3'd1&&p_cmd_tiles[client*3+:3]<=3'd4&&
   command_end[client]<={1'b0,words_q};
  assign a_valid[client]=!reset&&active[client]&&fifo_count[client]!=0;
  assign a_fire[client]=a_valid[client]&&a_ready[client];
  assign a_bank[client]=bank_q[client];
  assign a_wide[client]=wide_q[client];
  assign a_row[client*3+:3]=row_q[client];
  assign a_tile[client*2+:2]=tile_q[client];
  assign a_data[client*128+:128]=a_valid[client]?
   fifo_data[client][fifo_head[client]][128*int'(fifo_cursor[client][fifo_head[client]])+:128]:128'b0;
  assign fifo_pop[client]=a_fire[client]&&
   ({1'b0,fifo_cursor[client][fifo_head[client]]}+3'd1==fifo_limit[client][fifo_head[client]]);
  wire [3:0] reserved={1'b0,fifo_count[client]}+
   ((pending_read&&pending_owner==1'(client))?4'd1:4'd0);
  assign read_request[client]=!reset&&state==SEALED&&active[client]&&next_word[client]<end_word[client]&&
   (reserved<4'd4||fifo_pop[client]);
 end endgenerate

 wire read_fire=|read_request;
 wire grant_owner=read_request[round_robin]?round_robin:!round_robin;
 wire [8:0] read_line=next_word[grant_owner][10:2];
 wire [1:0] read_first=next_word[grant_owner][1:0];
 wire [11:0] read_remaining=end_word[grant_owner]-next_word[grant_owner];
 wire [2:0] line_room=3'd4-{1'b0,read_first};
 wire [2:0] read_words=read_remaining>={9'b0,line_room}?line_room:read_remaining[2:0];
 wire [2:0] read_limit={1'b0,read_first}+read_words;

 // Bank index {group,lane}; depth is the low eight bits of a 64B line.
 // Fill and service phases never overlap. Both readers compete for one grant.
 wire [1023:0] bank_data;
 genvar bank;
 generate for(bank=0;bank<8;bank=bank+1)begin: banks
  wire writing=write_fire&&fill_addr[8]==1'(bank/4)&&fill_mask[bank%4];
  wire reading=read_fire&&read_line[8]==1'(bank/4);
  wire [7:0] address=read_fire?read_line[7:0]:fill_addr[7:0];
  s_sram_256x128_freepdk45 memory(
   .clk0(clk),.csb0(!(writing||reading)),.web0(!writing),.addr0(address),
   .din0(fill_data[(bank%4)*128+:128]),.dout0(bank_data[bank*128+:128])
`ifdef USE_POWER_PINS
   ,.vdd,.gnd
`endif
  );
 end endgenerate
 wire [511:0] returning_data=pending_group?bank_data[1023:512]:bank_data[511:0];

 integer i;
 always @(posedge clk)begin
  if(reset)begin
   state<=EMPTY;epoch_q<=0;words_q<=0;accepted_words<=0;written_words<=0;next_fill_line<=0;
   cfg_done<=0;cfg_error<=0;fill_pending<=0;fill_pending_error<=0;fill_pending_words<=0;
   fill_ack_head<=0;fill_ack_tail<=0;fill_ack_count<=0;
   active<=0;p_done<=0;p_error<=0;pending_read<=0;pending_owner<=0;pending_group<=0;
   pending_first<=0;pending_limit<=0;round_robin<=0;
   for(i=0;i<2;i=i+1)begin
    bank_q[i]<=0;wide_q[i]<=0;rows_q[i]<=0;total_words[i]<=0;sent_words[i]<=0;
    next_word[i]<=0;end_word[i]<=0;row_q[i]<=0;tile_q[i]<=0;
    fifo_head[i]<=0;fifo_tail[i]<=0;fifo_count[i]<=0;
   end
  end else begin
   if(cfg_done&&cfg_take)cfg_done<=0;
   if(cfg_fire)begin
    cfg_done<=1;cfg_error<=0;
    case(cfg_op)
     2'd0:begin
      if(state!=EMPTY||cfg_words==0||cfg_words>12'd2048)cfg_error<=1;
      else begin
       state<=FILL;epoch_q<=cfg_epoch;words_q<=cfg_words;
       accepted_words<=0;written_words<=0;next_fill_line<=0;
      end
     end
     2'd1:begin
      if(state!=FILL||!matching_epoch)cfg_error<=1;
      else state<=SEALED;
     end
     2'd2:begin
      if(state!=SEALED||!matching_epoch)cfg_error<=1;
      else state<=EMPTY;
     end
     default:cfg_error<=1;
    endcase
   end

   fill_pending<=fill_fire;
   if(fill_fire)begin
    fill_pending_error<=!fill_legal;fill_pending_words<=fill_words;
   end
   if(write_fire)begin
    accepted_words<=accepted_words+{9'b0,fill_words};next_fill_line<=next_fill_line+1'b1;
   end
   if(fill_pending)begin
    fill_ack_data[fill_ack_tail]<=fill_pending_error;fill_ack_tail<=!fill_ack_tail;
    if(!fill_pending_error)written_words<=written_words+{9'b0,fill_pending_words};
   end
   if(fill_pop)fill_ack_head<=!fill_ack_head;
   case({fill_pending,fill_pop})
    2'b10:fill_ack_count<=fill_ack_count+1'b1;
    2'b01:fill_ack_count<=fill_ack_count-1'b1;
    default:begin end
   endcase

   pending_read<=read_fire;
   if(read_fire)begin
    pending_owner<=grant_owner;pending_group<=read_line[8];
    pending_first<=read_first;pending_limit<=read_limit;round_robin<=!grant_owner;
    next_word[grant_owner]<=next_word[grant_owner]+{9'b0,read_words};
   end
   for(i=0;i<2;i=i+1)begin
    if(p_done[i]&&p_done_take[i])p_done[i]<=0;
    if(p_cmd_valid[i]&&p_cmd_ready[i])begin
     p_error[i]<=!command_legal[i];
     if(!command_legal[i])p_done[i]<=1;
     else begin
      active[i]<=1;bank_q[i]<=p_cmd_bank[i];wide_q[i]<=p_cmd_awide[i];rows_q[i]<=p_cmd_rows[4*i+:4];
      total_words[i]<=command_words[i][5:0];sent_words[i]<=0;
      next_word[i]<={1'b0,p_cmd_base[11*i+:11]};end_word[i]<=command_end[i][11:0];
      row_q[i]<=0;tile_q[i]<=0;
     end
    end
    if(pending_read&&pending_owner==1'(i))begin
     fifo_data[i][fifo_tail[i]]<=returning_data;
     fifo_cursor[i][fifo_tail[i]]<=pending_first;fifo_limit[i][fifo_tail[i]]<=pending_limit;
     fifo_tail[i]<=fifo_tail[i]+1'b1;
    end
    if(a_fire[i])begin
     sent_words[i]<=sent_words[i]+1'b1;
     if({1'b0,row_q[i]}+4'd1==rows_q[i])begin row_q[i]<=0;tile_q[i]<=tile_q[i]+1'b1;end
     else row_q[i]<=row_q[i]+1'b1;
     if(sent_words[i]+6'd1==total_words[i])begin active[i]<=0;p_done[i]<=1;end
     if(!fifo_pop[i])fifo_cursor[i][fifo_head[i]]<=fifo_cursor[i][fifo_head[i]]+1'b1;
    end
    if(fifo_pop[i])fifo_head[i]<=fifo_head[i]+1'b1;
    case({(pending_read&&pending_owner==1'(i)),fifo_pop[i]})
     2'b10:fifo_count[i]<=fifo_count[i]+1'b1;
     2'b01:fifo_count[i]<=fifo_count[i]-1'b1;
     default:begin end
    endcase
   end
  end
 end
endmodule
