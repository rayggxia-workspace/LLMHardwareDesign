// Candidate LC range service, not a mother instruction per raw K16 beat.
// One descriptor covers <=16 output contexts and a K128 interval. The mapper
// chooses the interval/chunk; head records contain eight real K16 groups in M.
// Six *issued* metadata tickets bound four W holders plus two real results.
// The extra two tickets add 106 register bits, not W/RF/result data capacity.
// A consumer must honor A_FIRST/A_LAST/planned uses with actual A-slot leases.
// A queued FINAL/SPILL completes only at the external result service's ACK.
// Reset requires the system's transport drain; owner128 rejects stale epochs.
module record_range_iterator (
 input wire clk, reset,
 input wire job_valid, output wire job_ready,
 input wire [127:0] job_owner,
 input wire [31:0] job_sequence_base,
 input wire [63:0] job_weight_base, job_weight_base1,
 input wire [1:0] job_ways,
 input wire [31:0] job_columns, job_first_col,
 input wire [15:0] job_col_stride,
 input wire [4:0] job_groups,
 input wire [3:0] job_first_context,
 input wire [15:0] job_full_k, job_k_begin, job_k_end,
 input wire job_head16,
 input wire cancel_valid, input wire [127:0] cancel_owner,
 output reg record_valid, input wire record_ready,
 output reg [127:0] record_owner,
 output reg [31:0] record_sequence,
 output reg [63:0] record_address,
 output reg [15:0] record_bytes, record_full_k, record_k,
 output reg [31:0] record_col,
 output reg [3:0] record_context, record_n,
 output reg record_way,
 output reg record_head16, record_create, record_restore, record_final, record_spill,
 output reg record_A_first, record_A_last,
 output reg [4:0] record_A_uses,
 input wire complete_valid, output wire complete_ready,
 input wire [127:0] complete_owner,
 input wire [31:0] complete_sequence,
 input wire [3:0] complete_context,
 input wire [15:0] complete_next_k,
 input wire complete_error,
 output reg rejected_complete,
 output reg done_valid, input wire done_ready,
 output reg [127:0] done_owner,
 output reg done_error, done_cancelled,
 output reg [31:0] done_issued, done_completed,
 output reg [31:0] done_failed_sequence,
 output reg [15:0] done_failed_next_k
);
 reg busy, stopping, cancelled, failed, exhausted;
 reg [127:0] owner;
 reg [31:0] sequence_id, columns, first_col;
 reg [63:0] weight_base, weight_base1;
 reg [1:0] ways;
 reg cursor_way;
 reg [15:0] col_stride, full_k, k_begin, k_end, cursor_k;
 reg [4:0] groups, cursor_col;
 reg [3:0] first_context;
 reg head16;
 reg [5:0] tickets;
 reg [31:0] ticket_sequence [0:5];
 reg [3:0] ticket_context [0:5];
 reg [15:0] ticket_next [0:5];
 reg [2:0] offer_slot;
 reg [31:0] issued, completed;
 reg [31:0] failed_sequence;
 reg [15:0] failed_next_k;
 reg free_found, match_found;
 reg [2:0] free_slot, match_slot;
 always @* begin
  free_found=0;free_slot=0;match_found=0;match_slot=0;
  for(integer s=0;s<6;s=s+1) begin
   if(!tickets[s] && !free_found) begin free_found=1;free_slot=3'(s);end
   if(tickets[s] && complete_owner==owner && complete_sequence==ticket_sequence[s] &&
      complete_context==ticket_context[s] && !match_found) begin
    match_found=1;match_slot=3'(s);
   end
  end
 end
 assign complete_ready=!reset && busy && match_found;
 assign job_ready=!reset && !busy && !done_valid;
 wire record_fire=record_valid && record_ready;
 wire complete_fire=complete_valid && complete_ready;
 wire cancel_fire=cancel_valid && busy && cancel_owner==owner;
 wire [63:0] requested_last_col={32'd0,job_first_col}+
     ({59'd0,job_groups}-64'd1)*{48'd0,job_col_stride};
 wire [6:0] requested_contexts={2'd0,job_groups}*{5'd0,job_ways};
 wire [63:0] requested_records={57'd0,requested_contexts}*
     (({48'd0,job_k_end}-{48'd0,job_k_begin})>>7);
 wire [63:0] requested_end_address=job_weight_base+
     (((requested_last_col>>3)*({48'd0,job_full_k}>>7)+
       ({48'd0,job_k_end}>>7)-64'd1)*(job_head16?64'd1152:64'd1088))+
     (job_head16?64'd1152:64'd1088);
 wire [63:0] requested_end_address1=requested_end_address-job_weight_base+job_weight_base1;
 wire job_bad=job_groups==0 || job_groups>16 ||
     (job_ways!=1 && job_ways!=2) ||
     ({3'd0,job_first_context}+requested_contexts)>16 || job_first_col[2:0]!=0 ||
     job_col_stride<8 || job_col_stride[2:0]!=0 || requested_last_col>={32'd0,job_columns} ||
     job_full_k==0 || job_full_k[6:0]!=0 || job_k_begin[6:0]!=0 || job_k_end[6:0]!=0 ||
     job_k_begin>=job_k_end || job_k_end>job_full_k || job_weight_base[5:0]!=0 ||
     requested_end_address<job_weight_base || requested_end_address[63:48]!=0 ||
     (job_ways==2 && (job_weight_base1[5:0]!=0 || requested_end_address1<job_weight_base1 ||
                     requested_end_address1[63:48]!=0)) ||
     ({32'd0,job_sequence_base}+requested_records)>64'h100000000;
 wire [63:0] current_col={32'd0,first_col}+{59'd0,cursor_col}*{48'd0,col_stride};
 wire [63:0] current_record_index=(current_col>>3)*({48'd0,full_k}>>7)+({48'd0,cursor_k}>>7);
 always @(posedge clk) begin
  if(reset) begin
   busy<=0;stopping<=0;cancelled<=0;failed<=0;exhausted<=0;tickets<=0;
   record_valid<=0;done_valid<=0;rejected_complete<=0;
   record_owner<=0;record_sequence<=0;record_address<=0;record_bytes<=0;
   record_full_k<=0;record_k<=0;record_col<=0;record_context<=0;record_n<=0;
   record_way<=0;weight_base1<=0;ways<=0;cursor_way<=0;
   record_head16<=0;record_create<=0;record_restore<=0;record_final<=0;record_spill<=0;
   record_A_first<=0;record_A_last<=0;record_A_uses<=0;
   done_owner<=0;done_error<=0;done_cancelled<=0;done_issued<=0;done_completed<=0;
   done_failed_sequence<=32'hffffffff;done_failed_next_k<=0;
   failed_sequence<=32'hffffffff;failed_next_k<=0;
   owner<=0;sequence_id<=0;columns<=0;first_col<=0;weight_base<=0;
   col_stride<=0;full_k<=0;k_begin<=0;k_end<=0;cursor_k<=0;groups<=0;cursor_col<=0;
   first_context<=0;head16<=0;offer_slot<=0;issued<=0;completed<=0;
  end else begin
   rejected_complete<=complete_valid && !complete_ready;
   if(done_valid && done_ready) done_valid<=0;
   if(job_valid && job_ready) begin
    done_owner<=job_owner;done_error<=job_bad;done_cancelled<=0;
    done_issued<=0;done_completed<=0;
    done_failed_sequence<=32'hffffffff;done_failed_next_k<=0;
    if(job_bad) done_valid<=1;
    else begin
     busy<=1;stopping<=0;cancelled<=0;failed<=0;exhausted<=0;
     owner<=job_owner;sequence_id<=job_sequence_base;weight_base<=job_weight_base;
     weight_base1<=job_weight_base1;ways<=job_ways;cursor_way<=0;
     columns<=job_columns;first_col<=job_first_col;col_stride<=job_col_stride;
     full_k<=job_full_k;k_begin<=job_k_begin;k_end<=job_k_end;cursor_k<=job_k_begin;
     groups<=job_groups;cursor_col<=0;first_context<=job_first_context;head16<=job_head16;
     tickets<=0;issued<=0;completed<=0;
     failed_sequence<=32'hffffffff;failed_next_k<=0;
    end
   end
   if(cancel_fire) begin stopping<=1;cancelled<=1;end
   if(complete_fire) begin
    tickets[match_slot]<=0;completed<=completed+1'b1;
    if(complete_error || complete_next_k!=ticket_next[match_slot]) begin
     failed<=1;stopping<=1;
     if(!failed) begin failed_sequence<=complete_sequence;failed_next_k<=complete_next_k;end
    end
   end
   if(record_fire) begin
    record_valid<=0;tickets[offer_slot]<=1;
    ticket_sequence[offer_slot]<=record_sequence;ticket_context[offer_slot]<=record_context;
    ticket_next[offer_slot]<=record_k+16'd128;
    issued<=issued+1'b1;sequence_id<=sequence_id+1'b1;
    if(cursor_col+1'b1==groups) begin
     cursor_col<=0;
     if(!cursor_way && ways==2) cursor_way<=1;
     else begin
      cursor_way<=0;
      if(cursor_k+16'd128==k_end) exhausted<=1;
      else cursor_k<=cursor_k+16'd128;
     end
    end else cursor_col<=cursor_col+1'b1;
   end
   // An offered record is held even on cancel/error until its handshake;
   // then it is a real ticket and must be cancelled/drained downstream.
   if(busy && !stopping && !cancel_fire && !record_valid && !exhausted && free_found &&
      !(complete_fire && (complete_error || complete_next_k!=ticket_next[match_slot]))) begin
    record_valid<=1;offer_slot<=free_slot;record_owner<=owner;record_sequence<=sequence_id;
    record_address<=(cursor_way ? weight_base1 : weight_base)+current_record_index*(head16?64'd1152:64'd1088);
    record_bytes<=head16?16'd1152:16'd1088;record_full_k<=full_k;record_k<=cursor_k;
    record_col<=current_col[31:0];record_context<=4'({1'b0,first_context}+cursor_col+(cursor_way?groups:5'd0));
    record_way<=cursor_way;
    record_n<=({32'd0,columns}-current_col)>=8?4'd8:4'(columns-current_col[31:0]);
    record_head16<=head16;record_create<=cursor_k==0;
    record_restore<=cursor_k==k_begin && k_begin!=0;
    record_final<=cursor_k+16'd128==full_k;
    record_spill<=cursor_k+16'd128==k_end && k_end!=full_k;
    record_A_first<=cursor_col==0 && !cursor_way;
    record_A_last<=cursor_col+1'b1==groups && (ways==1 || cursor_way);
    record_A_uses<=5'(groups*{3'd0,ways});
   end
   if(busy && (exhausted || stopping) && !record_valid && tickets==0 && !record_fire) begin
    busy<=0;done_valid<=1;done_owner<=owner;done_error<=failed;
    done_cancelled<=cancelled;done_issued<=issued;done_completed<=completed;
    done_failed_sequence<=failed_sequence;done_failed_next_k<=failed_next_k;
   end
  end
 end
endmodule
