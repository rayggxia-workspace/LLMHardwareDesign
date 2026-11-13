// Four full W-first records. This is register storage, not a 1RW SRAM.
// One64B DMA return and one128B native M read can run on DIFFERENT banks.
// Result storage/ACK belongs to an independent bounded result owner.
module weight_records #(
 parameter integer KEY_W=128,
 parameter integer MC_CREDITS=32
)(
 input wire clk, reset,
 input wire alloc_valid, output wire alloc_ready,
 input wire [KEY_W-1:0] alloc_key, input wire [31:0] alloc_record,
 input wire alloc_head16, input wire [3:0] alloc_n,
 output reg alloc_ack_valid, input wire alloc_ack_ready,
 output reg alloc_ack_error, output reg [1:0] alloc_ack_bank,
 output reg [15:0] alloc_ack_generation,
 output reg [KEY_W-1:0] alloc_ack_key, output reg [31:0] alloc_ack_record,
 input wire issue_valid, output wire issue_ready,
 input wire [1:0] issue_bank, input wire [15:0] issue_generation,
 input wire [KEY_W-1:0] issue_key, input wire [31:0] issue_record,
 input wire [4:0] issue_beat,
 input wire fill_valid, output wire fill_ready,
 input wire [1:0] fill_bank, input wire [15:0] fill_generation,
 input wire [KEY_W-1:0] fill_key, input wire [31:0] fill_record,
 input wire [4:0] fill_beat, input wire fill_last,
 input wire [511:0] fill_data,
 output reg fill_ack_valid, input wire fill_ack_ready,
 output wire [1:0] fill_ack_bank, output wire [15:0] fill_ack_generation,
 output wire [KEY_W-1:0] fill_ack_key, output wire [31:0] fill_ack_record,
 output wire fill_ack_error,
 input wire start_valid, output wire start_ready,
 input wire [1:0] start_bank, input wire [15:0] start_generation,
 input wire [KEY_W-1:0] start_key, input wire [31:0] start_record,
 input wire [15:0] start_use, input wire [31:0] start_raw_tag,
 // Internal M bridge acknowledgement and immutable bank configuration.
 output wire start_accepted, start_head16, output wire [3:0] start_n,
 output wire w_valid, input wire w_ready,
 output wire [KEY_W-1:0] w_key, output wire [31:0] w_record,
 output wire [1:0] w_bank, output wire [15:0] w_generation, w_use,
 output wire [31:0] w_raw_tag,
 output wire [7:0] w_group_k, w_offset,
 output wire [3:0] w_n,
 output wire w_first, w_last, w_record_last,
 output wire [2:0] w_group_index,
 output wire [1023:0] w_data, output reg [127:0] w_scale,
 input wire consumed_valid, output wire consumed_ready,
 input wire [1:0] consumed_bank, input wire [15:0] consumed_generation,
 input wire [KEY_W-1:0] consumed_key, input wire [31:0] consumed_record,
 input wire [15:0] consumed_use,
 input wire cancel_valid, output wire cancel_ready,
 input wire [1:0] cancel_bank, input wire [15:0] cancel_generation,
 input wire [KEY_W-1:0] cancel_key, input wire [31:0] cancel_record,
 output wire cancel_accepted,
 // Strong external statement: raw/A owner cancellation is drained. The
 // module additionally requires every DMA it issued to have actually returned.
 input wire drain_valid, output wire drain_ready,
 input wire [1:0] drain_bank, input wire [15:0] drain_generation,
 input wire [KEY_W-1:0] drain_key, input wire [31:0] drain_record,
 output reg drain_done_valid, input wire drain_done_ready,
 output reg [1:0] drain_done_bank, output reg [15:0] drain_done_generation,
 output reg [KEY_W-1:0] drain_done_key, output reg [31:0] drain_done_record,
 output reg fault_valid, input wire fault_ready,
 output reg [3:0] fault_op,
 output reg [1:0] fault_bank, output reg [15:0] fault_generation,
 output reg [KEY_W-1:0] fault_key, output reg [31:0] fault_record,
 output reg [6:0] outstanding,
 output wire [3:0] free_mask, ready_mask
);
 localparam [2:0] FREE=0,FILLING=1,FILLED=2,READY=3,STREAM=4,WAIT_CONSUMED=5,CANCELLED=6;
 reg [511:0] data [0:3][0:17]; // 4*1152B=4608B physical register data.
 reg [2:0] state [0:3];
 reg [KEY_W-1:0] key [0:3];reg [31:0] record_id [0:3];
 reg [15:0] generation [0:3], use_id [0:3];
 reg [31:0] raw_tag [0:3];reg [3:0] lanes [0:3];
 reg head [0:3], bad_record [0:3], cancelled [0:3];
 reg [17:0] issued [0:3], received [0:3];reg [5:0] pending [0:3];
 reg [3:0] ack_pending;
 reg [1:0] ack_selected, alloc_cursor;
 reg stream_active;reg [1:0] stream_bank;reg [2:0] stream_beat;
 wire fault_space=!fault_valid||fault_ready;
 wire alloc_space=!alloc_ack_valid||alloc_ack_ready;
 wire drain_space=!drain_done_valid||drain_done_ready;
 function automatic match_owner(input [1:0] b,input [15:0] g,input [KEY_W-1:0] k,input [31:0] r);
  match_owner=state[b]!=FREE&&generation[b]==g&&key[b]==k&&record_id[b]==r;
 endfunction
 function automatic [17:0] complete_mask(input bit h);
  complete_mask=h?18'h3ffff:18'h1ffff;
 endfunction
 function automatic invalid_scale(input [15:0] fp);
  invalid_scale=fp[15]||fp[14:10]==31||fp[14:0]==0;
 endfunction
 reg fill_good, fill_bad_payload;
 always @* begin
  fill_good=0;fill_bad_payload=0;
  if(match_owner(fill_bank,fill_generation,fill_key,fill_record)&&
     (state[fill_bank]==FILLING||state[fill_bank]==CANCELLED)&&fill_beat<18) begin
   fill_good=issued[fill_bank][fill_beat]&&!received[fill_bank][fill_beat]&&
    fill_beat<(head[fill_bank]?18:17)&&fill_last==(fill_beat==(head[fill_bank]?17:16));
  end
  if(fill_beat<16) begin
   for(integer j=0;j<64;j=j+1)
    if((int'(fill_beat[0])*4+j/16)>=int'(lanes[fill_bank])&&fill_data[j*8+:8]!=0)fill_bad_payload=1;
  end else begin
   for(integer j=0;j<32;j=j+1)begin
    if((head[fill_bank]||j<8)&&(j%8)<int'(lanes[fill_bank])&&invalid_scale(fill_data[j*16+:16]))fill_bad_payload=1;
   end
   if(!head[fill_bank]&&fill_data[511:128]!=0)fill_bad_payload=1;
  end
 end
 wire issue_good=match_owner(issue_bank,issue_generation,issue_key,issue_record)&&state[issue_bank]==FILLING&&
  !cancelled[issue_bank]&&issue_beat<(head[issue_bank]?18:17)&&!issued[issue_bank][issue_beat];
 wire start_good=match_owner(start_bank,start_generation,start_key,start_record)&&state[start_bank]==READY&&
  (!head[start_bank]||start_raw_tag[2:0]==0);
 assign start_accepted=start_valid&&start_ready&&start_good;
 assign start_head16=head[start_bank];assign start_n=lanes[start_bank];
 wire consumed_good=match_owner(consumed_bank,consumed_generation,consumed_key,consumed_record)&&
  state[consumed_bank]==WAIT_CONSUMED&&use_id[consumed_bank]==consumed_use;
 wire cancel_good=match_owner(cancel_bank,cancel_generation,cancel_key,cancel_record)&&!cancelled[cancel_bank];
 wire drain_good=match_owner(drain_bank,drain_generation,drain_key,drain_record)&&state[drain_bank]==CANCELLED&&
  pending[drain_bank]==0&&!ack_pending[drain_bank];
 // LC commands have one acceptance slot. True MC request acceptance has
 // its own one-beat/cycle credit port; it does not consume an LC command.
 // Malformed traffic serializes through the single bounded fault slot.
 wire base_controls=!reset&&fault_space&&!(fill_valid&&!fill_good);
 // Cancellation has priority over malformed issue traffic; good issues on
 // other banks remain independent. No ready->valid->cancel_ready loop.
 wire controls=base_controls&&!(issue_valid&&!issue_good&&!cancel_valid);
 // A matching CANCEL is a state transition, not a fault producer. It can
 // rendezvous with one malformed return, whose sole fault receipt stays
 // owned by FILL. Keeping the good-CANCEL acceptance independent of the
 // return tag cuts return validation -> cancel -> RF/raw/A ready without
 // speculatively acknowledging cancellation or adding a payload buffer.
 // A malformed CANCEL still serializes behind malformed FILL exactly once.
 assign cancel_ready=!reset&&fault_space&&(cancel_good||!(fill_valid&&!fill_good));
 assign drain_ready=controls&&!cancel_valid&&drain_space;
 assign consumed_ready=controls&&!cancel_valid&&!drain_valid;
 assign start_ready=controls&&!cancel_valid&&!drain_valid&&!consumed_valid&&!stream_active;
 assign issue_ready=base_controls&&!(cancel_valid&&(!issue_good||(cancel_good&&cancel_bank==issue_bank)))&&
  (!issue_good||int'(outstanding)<MC_CREDITS);
 // START can only mutate a READY bank; ALLOC selects a bank that was
 // FREE before this edge. Their response slots are independent, even
 // when a bad START produces the one fault. Avoid START feedback in
 // allocation readiness while keeping the other LC/fault priorities.
 assign alloc_ready=controls&&!cancel_valid&&!drain_valid&&!consumed_valid&&alloc_space;
 assign fill_ready=!reset&&(fill_good||fault_space);
 wire fire_issue=issue_valid&&issue_ready&&issue_good;
 wire fire_fill=fill_valid&&fill_ready&&fill_good;
 // Successful cancellation implies cancel_good, so malformed FILL never
 // participates in this transition. Keep transport fault arbitration on
 // cancel_ready, while exposing the exact accepted-owner event directly.
 wire fire_cancel=cancel_valid&&!reset&&fault_space&&cancel_good;
 assign cancel_accepted=fire_cancel;
 wire stop_current=fire_cancel&&cancel_bank==stream_bank;
 assign w_valid=!reset&&stream_active&&!cancelled[stream_bank]&&!stop_current;
 assign w_bank=stream_bank;assign w_generation=generation[stream_bank];assign w_use=use_id[stream_bank];
 assign w_key=key[stream_bank];assign w_record=record_id[stream_bank];
 assign w_raw_tag=raw_tag[stream_bank]+(head[stream_bank]?{29'd0,stream_beat}:32'd0);
 assign w_group_k=head[stream_bank]?8'd16:8'd128;
 assign w_offset=head[stream_bank]?8'd0:{1'b0,stream_beat,4'd0};
 assign w_n=lanes[stream_bank];assign w_first=head[stream_bank]||stream_beat==0;
 assign w_last=head[stream_bank]||stream_beat==7;assign w_record_last=stream_beat==7;
 assign w_group_index=head[stream_bank]?stream_beat:3'd0;
 assign w_data={data[stream_bank][{1'b0,stream_beat,1'b1}],data[stream_bank][{1'b0,stream_beat,1'b0}]};
 always @* begin
  w_scale=0;
  for(integer n=0;n<8;n=n+1)if(n<int'(lanes[stream_bank])) begin
   if(!head[stream_bank])w_scale[n*16+:16]=data[stream_bank][16][n*16+:16];
   else if(stream_beat<4)w_scale[n*16+:16]=data[stream_bank][16][(int'(stream_beat)*8+n)*16+:16];
   else w_scale[n*16+:16]=data[stream_bank][17][((int'(stream_beat)-4)*8+n)*16+:16];
  end
 end
 assign fill_ack_bank=ack_selected;assign fill_ack_generation=generation[ack_selected];
 assign fill_ack_key=key[ack_selected];assign fill_ack_record=record_id[ack_selected];assign fill_ack_error=bad_record[ack_selected];
 for(genvar b=0;b<4;b=b+1)begin: status
  assign free_mask[b]=state[b]==FREE;
  assign ready_mask[b]=state[b]==READY;
 end
 task automatic fault(input [3:0] op,input [1:0] b,input [15:0] g,input [KEY_W-1:0] k,input [31:0] r);
  begin fault_valid<=1;fault_op<=op;fault_bank<=b;fault_generation<=g;fault_key<=k;fault_record<=r;end
 endtask
 always @(posedge clk) begin: registers
  integer chosen;reg duplicate;reg [17:0] next_received;
  if(reset) begin
   alloc_ack_valid<=0;fill_ack_valid<=0;drain_done_valid<=0;fault_valid<=0;
   ack_pending<=0;ack_selected<=0;alloc_cursor<=0;stream_active<=0;stream_bank<=0;stream_beat<=0;outstanding<=0;
   alloc_ack_error<=0;alloc_ack_bank<=0;alloc_ack_generation<=0;alloc_ack_key<=0;alloc_ack_record<=0;
   drain_done_bank<=0;drain_done_generation<=0;drain_done_key<=0;drain_done_record<=0;
   fault_op<=0;fault_bank<=0;fault_generation<=0;fault_key<=0;fault_record<=0;
   for(integer b=0;b<4;b=b+1)begin
    state[b]<=FREE;key[b]<=0;record_id[b]<=0;generation[b]<=0;use_id[b]<=0;raw_tag[b]<=0;
    lanes[b]<=0;head[b]<=0;bad_record[b]<=0;cancelled[b]<=0;issued[b]<=0;received[b]<=0;pending[b]<=0;
   end
  end else begin
   if(alloc_ack_valid&&alloc_ack_ready)alloc_ack_valid<=0;
   if(drain_done_valid&&drain_done_ready)drain_done_valid<=0;
   if(fault_valid&&fault_ready)fault_valid<=0;
   outstanding<=outstanding+{6'd0,fire_issue}-{6'd0,fire_fill};
   for(integer b=0;b<4;b=b+1)pending[b]<=pending[b]+{5'd0,fire_issue&&issue_bank==b[1:0]}-{5'd0,fire_fill&&fill_bank==b[1:0]};
   if(fill_ack_valid&&fill_ack_ready)begin
    ack_pending[ack_selected]<=0;fill_ack_valid<=0;
    if(!cancelled[ack_selected]&&state[ack_selected]==FILLED)state[ack_selected]<=bad_record[ack_selected]?FREE:READY;
   end
   if(!fill_ack_valid)begin
    chosen=-1;for(integer b=0;b<4;b=b+1)if(chosen<0&&ack_pending[b])chosen=b;
    if(chosen>=0)begin ack_selected<=chosen[1:0];fill_ack_valid<=1;end
   end
   if(alloc_valid&&alloc_ready)begin
    chosen=-1;duplicate=0;
    for(integer b=0;b<4;b=b+1)begin
     if(state[b]!=FREE&&key[b]==alloc_key&&record_id[b]==alloc_record)duplicate=1;
     if(chosen<0&&state[(int'(alloc_cursor)+b)%4]==FREE)chosen=(int'(alloc_cursor)+b)%4;
    end
    alloc_ack_valid<=1;alloc_ack_key<=alloc_key;alloc_ack_record<=alloc_record;
    alloc_ack_error<=chosen<0||duplicate||alloc_n==0||alloc_n>8;
    if(chosen>=0&&!duplicate&&alloc_n!=0&&alloc_n<=8)begin
     alloc_ack_bank<=chosen[1:0];alloc_ack_generation<=generation[chosen]+1'b1;
     generation[chosen]<=generation[chosen]+1'b1;key[chosen]<=alloc_key;record_id[chosen]<=alloc_record;
     lanes[chosen]<=alloc_n;head[chosen]<=alloc_head16;state[chosen]<=FILLING;
     bad_record[chosen]<=0;cancelled[chosen]<=0;issued[chosen]<=0;received[chosen]<=0;pending[chosen]<=0;
     alloc_cursor<=chosen[1:0]+1'b1;
    end
   end
   if(issue_valid&&issue_ready)begin
    if(issue_good)issued[issue_bank][issue_beat]<=1;
    else fault(1,issue_bank,issue_generation,issue_key,issue_record);
   end
   if(fill_valid&&fill_ready)begin
    if(!fill_good)fault(2,fill_bank,fill_generation,fill_key,fill_record);
    else begin
     data[fill_bank][fill_beat]<=fill_data;received[fill_bank][fill_beat]<=1;
     bad_record[fill_bank]<=bad_record[fill_bank]||fill_bad_payload;
     next_received=received[fill_bank]|(18'd1<<fill_beat);
     if(next_received==complete_mask(head[fill_bank])&&!cancelled[fill_bank]&&!(fire_cancel&&cancel_bank==fill_bank))begin
      state[fill_bank]<=FILLED;ack_pending[fill_bank]<=1;
     end
    end
   end
   if(start_valid&&start_ready)begin
    if(!start_good)fault(3,start_bank,start_generation,start_key,start_record);
    else begin state[start_bank]<=STREAM;use_id[start_bank]<=start_use;raw_tag[start_bank]<=start_raw_tag;
     stream_active<=1;stream_bank<=start_bank;stream_beat<=0;end
   end
   if(w_valid&&w_ready)begin
    if(stream_beat==7)begin state[stream_bank]<=WAIT_CONSUMED;stream_active<=0;end
    else stream_beat<=stream_beat+1'b1;
   end
   if(consumed_valid&&consumed_ready)begin
    if(!consumed_good)fault(4,consumed_bank,consumed_generation,consumed_key,consumed_record);
    else state[consumed_bank]<=FREE;
   end
   if(cancel_valid&&cancel_ready)begin
    if(!cancel_good)fault(5,cancel_bank,cancel_generation,cancel_key,cancel_record);
    else begin cancelled[cancel_bank]<=1;state[cancel_bank]<=CANCELLED;
     if(stream_active&&stream_bank==cancel_bank)stream_active<=0;end
   end
   if(drain_valid&&drain_ready)begin
    if(!drain_good)fault(6,drain_bank,drain_generation,drain_key,drain_record);
    else begin state[drain_bank]<=FREE;drain_done_valid<=1;drain_done_bank<=drain_bank;
     drain_done_generation<=drain_generation;drain_done_key<=drain_key;drain_done_record<=drain_record;end
   end
  end
 end
endmodule
