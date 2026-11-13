// Real product candidate. All scope/record tables and serial frame storage
// below are active M logic and must be included in mapping/physical area.
// Numeric profile: static W8A16 only. Dynamic S32xS32 Attention unsupported.
module m_native_leaf_s32 (
 input wire clk,reset,
 input wire lc_valid,output wire lc_ready,input wire lc_sop,lc_eop,input wire [127:0] lc_data,
 output wire lr_valid,input wire lr_ready,output wire lr_sop,lr_eop,output wire [127:0] lr_data,
 input wire a_valid,output wire a_ready,input wire [255:0] a_data,
 input wire [31:0] a_session,input wire [2:0] a_beat,
 output wire mc_req_valid,input wire mc_req_ready,output wire [63:0] mc_req_address,
 output wire [31:0] mc_req_tag,output wire mc_req_channel,output wire [4:0] mc_req_record_beats,
 output wire mc_close_valid,input wire mc_close_ready,output wire [31:0] mc_close_tag_base,
 input wire mc_rsp_valid,output wire mc_rsp_ready,input wire [31:0] mc_rsp_tag,input wire [511:0] mc_rsp_data,
 output wire mc_fence_req_valid,input wire mc_fence_req_ready,
 output wire [31:0] mc_fence_req_cookie,output wire [8:0] mc_fence_req_epoch,
 input wire mc_fence_done_valid,output wire mc_fence_done_ready,
 input wire [31:0] mc_fence_done_cookie,input wire [8:0] mc_fence_done_epoch,
 output wire fault_interrupt
);
 localparam [31:0] ABI=32'h02504d02;
 localparam [3:0] BEGIN_SCOPE=1,ALLOC=2,EXEC=3,CONTEXT=4,RESTORE=5,CANCEL=6,DRAIN=7,FENCE=8;
 reg  n_alloc_valid;
 wire  n_alloc_ready;
 reg [127:0] n_alloc_key;
 reg [31:0] n_alloc_record;
 reg  n_alloc_head16;
 reg [3:0] n_alloc_n;
 wire  n_alloc_ack_valid;
 wire  n_alloc_ack_ready;
 wire  n_alloc_ack_error;
 wire [1:0] n_alloc_ack_bank;
 wire [15:0] n_alloc_ack_generation;
 wire [127:0] n_alloc_ack_key;
 wire [31:0] n_alloc_ack_record;
 wire  n_issue_valid;
 wire  n_issue_ready;
 wire [1:0] n_issue_bank;
 wire [15:0] n_issue_generation;
 wire [127:0] n_issue_key;
 wire [31:0] n_issue_record;
 wire [4:0] n_issue_beat;
 wire  n_fill_valid;
 wire  n_fill_ready;
 wire [1:0] n_fill_bank;
 wire [15:0] n_fill_generation;
 wire [127:0] n_fill_key;
 wire [31:0] n_fill_record;
 wire [4:0] n_fill_beat;
 wire  n_fill_last;
 wire [511:0] n_fill_data;
 wire  n_fill_ack_valid;
 wire  n_fill_ack_ready;
 wire [1:0] n_fill_ack_bank;
 wire [15:0] n_fill_ack_generation;
 wire [127:0] n_fill_ack_key;
 wire [31:0] n_fill_ack_record;
 wire  n_fill_ack_error;
 reg  n_cancel_valid;
 wire  n_cancel_ready;
 reg [1:0] n_cancel_bank;
 reg [15:0] n_cancel_generation;
 reg [127:0] n_cancel_key;
 reg [31:0] n_cancel_record;
 reg  n_drain_valid;
 wire  n_drain_ready;
 reg [1:0] n_drain_bank;
 reg [15:0] n_drain_generation;
 reg [127:0] n_drain_key;
 reg [31:0] n_drain_record;
 wire  n_drain_done_valid;
 wire  n_drain_done_ready;
 wire [1:0] n_drain_done_bank;
 wire [15:0] n_drain_done_generation;
 wire [127:0] n_drain_done_key;
 wire [31:0] n_drain_done_record;
 wire  n_fault_valid;
 wire  n_fault_ready;
 wire [3:0] n_fault_op;
 wire [1:0] n_fault_bank;
 wire [15:0] n_fault_generation;
 wire [127:0] n_fault_key;
 wire [31:0] n_fault_record;
 wire [6:0] n_outstanding;
 wire [3:0] n_free_mask;
 wire [3:0] n_ready_mask;
 reg  n_exec_valid;
 wire  n_exec_ready;
 reg [127:0] n_exec_key;
 reg [31:0] n_exec_record;
 reg [1:0] n_exec_bank;
 reg [15:0] n_exec_generation;
 reg [15:0] n_exec_use;
 reg [31:0] n_exec_raw_tag;
 reg [31:0] n_exec_ticket;
 reg [127:0] n_exec_owner;
 reg [3:0] n_exec_context;
 reg [15:0] n_exec_full_k;
 reg [15:0] n_exec_k_offset;
 reg [15:0] n_exec_kk;
 reg  n_exec_a_slot;
 reg [15:0] n_exec_a_generation;
 reg [47:0] n_exec_a_shifts;
 reg [255:0] n_exec_bias;
 wire  n_a_valid;
 wire  n_a_ready;
 wire [127:0] n_a_key;
 wire [31:0] n_a_record;
 wire  n_a_slot;
 wire [15:0] n_a_generation;
 wire [15:0] n_a_kk;
 wire [15:0] n_a_use;
 wire [2:0] n_a_beat;
 wire [255:0] n_a_data;
 wire  n_input_done_valid;
 wire  n_input_done_ready;
 wire [127:0] n_input_done_key;
 wire [31:0] n_input_done_record;
 wire [1:0] n_input_done_bank;
 wire [15:0] n_input_done_generation;
 wire [15:0] n_input_done_use;
 wire  n_input_done_a_slot;
 wire [15:0] n_input_done_a_generation;
 wire  n_abort_done_valid;
 wire  n_abort_done_ready;
 wire [127:0] n_abort_done_key;
 wire [31:0] n_abort_done_record;
 wire [127:0] n_abort_done_owner;
 wire [3:0] n_abort_done_context;
 wire [15:0] n_abort_done_next_k;
 reg  n_control_valid;
 wire  n_control_ready;
 reg [2:0] n_control_kind;
 reg [3:0] n_control_context;
 reg [127:0] n_control_owner;
 reg [31:0] n_control_ticket;
 reg [15:0] n_control_full_k;
 reg [15:0] n_control_k_offset;
 reg [7:0] n_control_group_k;
 reg [3:0] n_control_n;
 reg [255:0] n_control_previous;
 reg [31:0] n_control_snapshot_ticket;
 reg  n_restore_commit_valid;
 reg [127:0] n_restore_commit_owner;
 reg [3:0] n_restore_commit_context;
 reg [31:0] n_restore_commit_ticket;
 reg [15:0] n_restore_commit_next_k;
 reg [15:0] n_restore_commit_full_k;
 reg [7:0] n_restore_commit_group_k;
 reg [3:0] n_restore_commit_n;
 wire  n_rsp_valid;
 wire  n_rsp_ready;
 wire [2:0] n_rsp_kind;
 wire [3:0] n_rsp_context;
 wire [127:0] n_rsp_owner;
 wire [31:0] n_rsp_tag;
 wire [31:0] n_rsp_ticket;
 wire [127:0] n_rsp_key;
 wire [31:0] n_rsp_record;
 wire [1:0] n_rsp_bank;
 wire [15:0] n_rsp_generation;
 wire [15:0] n_rsp_use;
 wire [15:0] n_rsp_next_k;
 wire [15:0] n_rsp_full_k;
 wire [7:0] n_rsp_group_k;
 wire [3:0] n_rsp_n;
 wire  n_rsp_final;
 wire  n_rsp_snapshot;
 wire [255:0] n_rsp_data;
 wire  n_rsp_error;
 wire  n_native_fault_valid;
 wire  n_native_fault_ready;
 wire [2:0] n_native_fault_kind;
 wire [127:0] n_native_fault_key;
 wire [31:0] n_native_fault_record;
 wire  n_busy;
 wire [2:0] n_scale_count;
 m_native_s32 #(.COMMON_A_SHIFT(1'b1)) native(
  .clk(clk),
  .reset(reset),
  .alloc_valid(n_alloc_valid),
  .alloc_ready(n_alloc_ready),
  .alloc_key(n_alloc_key),
  .alloc_record(n_alloc_record),
  .alloc_head16(n_alloc_head16),
  .alloc_n(n_alloc_n),
  .alloc_ack_valid(n_alloc_ack_valid),
  .alloc_ack_ready(n_alloc_ack_ready),
  .alloc_ack_error(n_alloc_ack_error),
  .alloc_ack_bank(n_alloc_ack_bank),
  .alloc_ack_generation(n_alloc_ack_generation),
  .alloc_ack_key(n_alloc_ack_key),
  .alloc_ack_record(n_alloc_ack_record),
  .issue_valid(n_issue_valid),
  .issue_ready(n_issue_ready),
  .issue_bank(n_issue_bank),
  .issue_generation(n_issue_generation),
  .issue_key(n_issue_key),
  .issue_record(n_issue_record),
  .issue_beat(n_issue_beat),
  .fill_valid(n_fill_valid),
  .fill_ready(n_fill_ready),
  .fill_bank(n_fill_bank),
  .fill_generation(n_fill_generation),
  .fill_key(n_fill_key),
  .fill_record(n_fill_record),
  .fill_beat(n_fill_beat),
  .fill_last(n_fill_last),
  .fill_data(n_fill_data),
  .fill_ack_valid(n_fill_ack_valid),
  .fill_ack_ready(n_fill_ack_ready),
  .fill_ack_bank(n_fill_ack_bank),
  .fill_ack_generation(n_fill_ack_generation),
  .fill_ack_key(n_fill_ack_key),
  .fill_ack_record(n_fill_ack_record),
  .fill_ack_error(n_fill_ack_error),
  .cancel_valid(n_cancel_valid),
  .cancel_ready(n_cancel_ready),
  .cancel_bank(n_cancel_bank),
  .cancel_generation(n_cancel_generation),
  .cancel_key(n_cancel_key),
  .cancel_record(n_cancel_record),
  .drain_valid(n_drain_valid),
  .drain_ready(n_drain_ready),
  .drain_bank(n_drain_bank),
  .drain_generation(n_drain_generation),
  .drain_key(n_drain_key),
  .drain_record(n_drain_record),
  .drain_done_valid(n_drain_done_valid),
  .drain_done_ready(n_drain_done_ready),
  .drain_done_bank(n_drain_done_bank),
  .drain_done_generation(n_drain_done_generation),
  .drain_done_key(n_drain_done_key),
  .drain_done_record(n_drain_done_record),
  .fault_valid(n_fault_valid),
  .fault_ready(n_fault_ready),
  .fault_op(n_fault_op),
  .fault_bank(n_fault_bank),
  .fault_generation(n_fault_generation),
  .fault_key(n_fault_key),
  .fault_record(n_fault_record),
  .outstanding(n_outstanding),
  .free_mask(n_free_mask),
  .ready_mask(n_ready_mask),
  .exec_valid(n_exec_valid),
  .exec_ready(n_exec_ready),
  .exec_key(n_exec_key),
  .exec_record(n_exec_record),
  .exec_bank(n_exec_bank),
  .exec_generation(n_exec_generation),
  .exec_use(n_exec_use),
  .exec_raw_tag(n_exec_raw_tag),
  .exec_ticket(n_exec_ticket),
  .exec_owner(n_exec_owner),
  .exec_context(n_exec_context),
  .exec_full_k(n_exec_full_k),
  .exec_k_offset(n_exec_k_offset),
  .exec_kk(n_exec_kk),
  .exec_a_slot(n_exec_a_slot),
  .exec_a_generation(n_exec_a_generation),
  .exec_a_shifts(n_exec_a_shifts),
  .exec_bias(n_exec_bias),
  .a_valid(n_a_valid),
  .a_ready(n_a_ready),
  .a_key(n_a_key),
  .a_record(n_a_record),
  .a_slot(n_a_slot),
  .a_generation(n_a_generation),
  .a_kk(n_a_kk),
  .a_use(n_a_use),
  .a_beat(n_a_beat),
  .a_data(n_a_data),
  .input_done_valid(n_input_done_valid),
  .input_done_ready(n_input_done_ready),
  .input_done_key(n_input_done_key),
  .input_done_record(n_input_done_record),
  .input_done_bank(n_input_done_bank),
  .input_done_generation(n_input_done_generation),
  .input_done_use(n_input_done_use),
  .input_done_a_slot(n_input_done_a_slot),
  .input_done_a_generation(n_input_done_a_generation),
  .abort_done_valid(n_abort_done_valid),
  .abort_done_ready(n_abort_done_ready),
  .abort_done_key(n_abort_done_key),
  .abort_done_record(n_abort_done_record),
  .abort_done_owner(n_abort_done_owner),
  .abort_done_context(n_abort_done_context),
  .abort_done_next_k(n_abort_done_next_k),
  .control_valid(n_control_valid),
  .control_ready(n_control_ready),
  .control_kind(n_control_kind),
  .control_context(n_control_context),
  .control_owner(n_control_owner),
  .control_ticket(n_control_ticket),
  .control_full_k(n_control_full_k),
  .control_k_offset(n_control_k_offset),
  .control_group_k(n_control_group_k),
  .control_n(n_control_n),
  .control_previous(n_control_previous),
  .control_snapshot_ticket(n_control_snapshot_ticket),
  .restore_commit_valid(n_restore_commit_valid),
  .restore_commit_owner(n_restore_commit_owner),
  .restore_commit_context(n_restore_commit_context),
  .restore_commit_ticket(n_restore_commit_ticket),
  .restore_commit_next_k(n_restore_commit_next_k),
  .restore_commit_full_k(n_restore_commit_full_k),
  .restore_commit_group_k(n_restore_commit_group_k),
  .restore_commit_n(n_restore_commit_n),
  .rsp_valid(n_rsp_valid),
  .rsp_ready(n_rsp_ready),
  .rsp_kind(n_rsp_kind),
  .rsp_context(n_rsp_context),
  .rsp_owner(n_rsp_owner),
  .rsp_tag(n_rsp_tag),
  .rsp_ticket(n_rsp_ticket),
  .rsp_key(n_rsp_key),
  .rsp_record(n_rsp_record),
  .rsp_bank(n_rsp_bank),
  .rsp_generation(n_rsp_generation),
  .rsp_use(n_rsp_use),
  .rsp_next_k(n_rsp_next_k),
  .rsp_full_k(n_rsp_full_k),
  .rsp_group_k(n_rsp_group_k),
  .rsp_n(n_rsp_n),
  .rsp_final(n_rsp_final),
  .rsp_snapshot(n_rsp_snapshot),
  .rsp_data(n_rsp_data),
  .rsp_error(n_rsp_error),
  .native_fault_valid(n_native_fault_valid),
  .native_fault_ready(n_native_fault_ready),
  .native_fault_kind(n_native_fault_kind),
  .native_fault_key(n_native_fault_key),
  .native_fault_record(n_native_fault_record),
  .busy(n_busy),
  .scale_count(n_scale_count));
 reg [15:0] scope_valid,scope_live;
 reg [15:0] scope_generation[0:15];reg [8:0] scope_epoch[0:15];
 reg [127:0] scope_key[0:15],scope_owner[0:15];
 reg [15:0] scope_full_k[0:15],scope_next_k[0:15];reg [3:0] scope_n[0:15];
 reg scope_head[0:15];reg [255:0] scope_bias[0:15];
 reg [3:0] table_valid,table_cancel,table_closed;
 reg [127:0] table_key[0:3];reg [31:0] table_record[0:3],table_session[0:3];
 reg [15:0] table_generation[0:3];reg [8:0] table_epoch[0:3];
 // Cursor replaces the former base register, not an additional record cache.
 reg [63:0] table_base[0:3];reg [3:0] table_channel;
 reg [3:0] table_scope[0:3];reg [15:0] table_scope_generation[0:3];
 reg table_head[0:3];reg [4:0] table_next[0:3];reg [17:0] table_issued[0:3],table_received[0:3];
 reg [1:0] issue_cursor,allocation_cursor;
 reg request_locked;reg [1:0] locked_bank;reg [4:0] locked_beat;reg [63:0] locked_address;
 reg close_locked;reg [1:0] locked_close_bank;
 reg [8:0] transport_epoch;
 reg [1023:0] command_frame;reg command_pending,rx_active;reg [2:0] rx_index;reg [3:0] rx_length;
 reg [31:0] last_session;
 reg local_valid;reg [511:0] local_frame;reg [2:0] local_length;
 // One bounded command reply retains the existing command_frame until TX
 // EOP; no duplicated payload frame or speculative diagnostic capacity.
 reg command_reply_valid;reg [1:0] command_reply_kind;reg [7:0] command_reply_status;
 reg tx_valid;reg [511:0] tx_frame;reg [2:0] tx_index,tx_length;reg [3:0] tx_source;
 reg fence_wait,fence_offered,fence_reply;reg [31:0] fence_cookie;reg [8:0] fence_epoch;
 reg alloc_hold,alloc_installed;reg [63:0] alloc_base;
 reg [31:0] alloc_session;reg [3:0] alloc_scope;reg [15:0] alloc_scope_generation;
 reg drain_hold;reg [31:0] drain_session;reg [127:0] drain_key;
 reg [31:0] exec_session,exec_ticket,control_session;
 reg [127:0] A_key;reg [31:0] A_record;reg A_live,A_slot;
 reg [15:0] A_generation,A_kk,A_use;
 wire [3:0] op=command_frame[19:16];wire [3:0] handle=command_frame[27:24];
 wire [1:0] command_bank=command_frame[29:28];
 wire [31:0] session=command_frame[63:32],record_id=command_frame[95:64];
 wire [15:0] handle_generation=command_frame[111:96],command_bank_generation=command_frame[127:112];
 wire [127:0] word1=command_frame[255:128],word2=command_frame[383:256],word3=command_frame[511:384];
 wire [127:0] word4=command_frame[639:512],word7=command_frame[1023:896];
 wire [255:0] payload=command_frame[895:640];
 wire [2:0] context_kind=command_frame[114:112];
 wire [1:0] exec_bank=word1[1:0];wire [15:0] exec_generation=word1[17:2];
 wire [15:0] exec_offset=word1[49:34];wire [5:0] runtime_shift=word1[88:83];
 function automatic [3:0] command_length(input [3:0] kind);
  case(kind)BEGIN_SCOPE,RESTORE:command_length=8;ALLOC,EXEC:command_length=2;
   CONTEXT,CANCEL,DRAIN,FENCE:command_length=1;default:command_length=0;endcase
 endfunction
 function automatic [127:0] header(input [7:0] event_id,status,input [31:0] command_session,r,
                                   input [2:0] length,input [11:0] flags);
  header={{1'b0,length},flags,r,command_session,status,event_id,ABI};
 endfunction
 wire same_scope=scope_valid[handle]&&scope_generation[handle]==handle_generation;
 reg referenced_scope;reg [1:0] predicted_bank;reg free_found;
 always @*begin
  referenced_scope=0;free_found=0;predicted_bank=0;
  for(integer b=0;b<4;b=b+1)begin
   if(table_valid[b]&&table_scope[b]==handle)referenced_scope=1;
   if(!free_found&&n_free_mask[(int'(allocation_cursor)+b)%4])begin
    free_found=1;predicted_bank=2'((int'(allocation_cursor)+b)%4);
   end
  end
 end
 wire transport_wrap=free_found&&table_generation[predicted_bank]==16'hffff&&table_epoch[predicted_bank]==transport_epoch;
 wire bank_owner=table_valid[command_bank]&&table_generation[command_bank]==command_bank_generation&&
  table_record[command_bank]==record_id&&table_scope[command_bank]==handle&&table_scope_generation[command_bank]==handle_generation;
 wire exec_owner=table_valid[exec_bank]&&table_generation[exec_bank]==exec_generation&&
  table_record[exec_bank]==record_id&&table_scope[exec_bank]==handle&&table_scope_generation[exec_bank]==handle_generation;
 wire cancel_pending=command_pending&&op==CANCEL&&same_scope&&bank_owner;
 // One real registered request offer. It is refilled on acceptance, so
 // the native interface remains II1. Its credit is reserved by the single
 // held offer; same-bank CANCEL waits until that offer is truly accepted.
 wire [1:0] request_bank=locked_bank;wire [4:0] request_beat=locked_beat;
 assign mc_req_valid=request_locked;
 assign mc_req_address=locked_address;
 assign mc_req_tag={table_epoch[request_bank],request_bank,table_generation[request_bank],request_beat};
 assign mc_req_channel=table_channel[request_bank];
 assign mc_req_record_beats=table_head[request_bank]?5'd18:5'd17;
 wire request_fire=mc_req_valid&&mc_req_ready;
 reg request_found;reg [1:0] candidate_bank;reg [4:0] candidate_beat;reg [63:0] candidate_address;
 reg [1:0] candidate_index;integer candidate_next;
 wire [63:0] address_after_issue[0:3];
 for(genvar ab=0;ab<4;ab=ab+1)begin: next_address
  assign address_after_issue[ab]=table_base[ab]+64'd64;
 end
 always @*begin
  request_found=0;candidate_bank=0;candidate_beat=0;candidate_address=0;candidate_index=0;candidate_next=0;
  if((!request_locked||request_fire)&&n_issue_ready&&int'(n_outstanding)+(request_fire?1:0)<32)begin
   for(integer i=0;i<4;i=i+1)begin
    candidate_index=2'(((request_fire?int'(request_bank)+1:int'(issue_cursor))+i)%4);
    candidate_next=int'(table_next[candidate_index])+((request_fire&&request_bank==2'(candidate_index))?1:0);
    if(!request_found&&table_valid[candidate_index]&&!table_cancel[candidate_index]&&
      !(cancel_pending&&command_bank==2'(candidate_index))&&candidate_next<(table_head[candidate_index]?18:17))begin
     request_found=1;candidate_bank=2'(candidate_index);candidate_beat=5'(candidate_next);
     candidate_address=(request_fire&&request_bank==2'(candidate_index))?address_after_issue[candidate_index]:table_base[candidate_index];
    end
   end
  end
 end
 reg close_found;reg [1:0] close_bank;
 always @*begin
  close_found=0;close_bank=0;
  if(close_locked)begin close_found=1;close_bank=locked_close_bank;end
  else for(integer b=0;b<4;b=b+1)begin
   if(!close_found&&table_valid[b]&&table_cancel[b]&&!table_closed[b]&&table_issued[b]!=0&&
     !(request_locked&&locked_bank==2'(b)))begin close_found=1;close_bank=2'(b);end
  end
 end
 assign mc_close_valid=close_found;
 assign mc_close_tag_base={table_epoch[close_bank],close_bank,table_generation[close_bank],5'd0};
 wire [1:0] return_bank=mc_rsp_tag[22:21];wire [4:0] return_beat=mc_rsp_tag[4:0];
 wire return_good=table_valid[return_bank]&&table_epoch[return_bank]==mc_rsp_tag[31:23]&&
  table_generation[return_bank]==mc_rsp_tag[20:5]&&return_beat<18&&
  table_issued[return_bank][return_beat]&&!table_received[return_bank][return_beat];
 wire bad_return=mc_rsp_valid&&!return_good;
 wire bad_fence=mc_fence_done_valid&&!(fence_wait&&fence_offered&&mc_fence_done_cookie==fence_cookie&&mc_fence_done_epoch==fence_epoch);
 wire A_wait_bind=command_pending&&op==EXEC&&a_session==session&&!command_bad;
 wire bad_A=a_valid&&!A_wait_bind&&(!A_live||a_session!=exec_session);
 wire local_space=!local_valid;
 wire event_port_free=local_space&&!bad_return&&!bad_fence&&!bad_A;
 assign mc_rsp_ready=return_good?n_fill_ready:(local_space&&!bad_A);
 assign mc_fence_req_valid=fence_wait&&!fence_offered;
 assign mc_fence_req_cookie=fence_cookie;assign mc_fence_req_epoch=fence_epoch;
 assign mc_fence_done_ready=local_space&&!bad_A&&!bad_return;
 // A diagnostic has priority over other malformed transports. Good data
 // channels stay independent; only the lower-priority bad sender waits.
 assign a_ready=A_wait_bind?1'b0:(bad_A?local_space:n_a_ready);
 assign lc_ready=!command_pending&&!command_reply_valid&&!fence_wait&&!fence_reply&&event_port_free;
 assign lr_valid=tx_valid;assign lr_sop=tx_valid&&tx_index==0;
 assign lr_eop=tx_valid&&tx_index==tx_length-1'b1;assign lr_data=tx_frame[int'(tx_index)*128+:128];
 wire tx_end=lr_valid&&lr_ready&&lr_eop;
 assign fault_interrupt=(local_valid&&local_frame[47:40]!=0)||(command_reply_valid&&command_reply_kind==0)||n_fault_valid||n_native_fault_valid;
 wire common_bad=session<=last_session||command_frame[15:0]!=16'h4d02||command_frame[31:30]!=0||
  command_frame[23:20]!=command_length(op)||
  ((op!=CANCEL&&op!=DRAIN)&&command_bank!=0)||
  ((op!=CANCEL&&op!=DRAIN&&op!=CONTEXT)&&command_bank_generation!=0);
 reg command_bad;reg [7:0] command_error;
 always @*begin
  command_bad=common_bad;command_error=1;
  if(op!=BEGIN_SCOPE&&op!=FENCE&&!same_scope)begin command_bad=1;command_error=2;end
  case(op)
   BEGIN_SCOPE:if(scope_live[handle]||referenced_scope||
    handle_generation!=scope_generation[handle]+1'b1||
    (handle_generation==0&&scope_epoch[handle]==transport_epoch)||word1==0||word2==0||
    word3[15:0]==0||word3[6:0]!=0||word3[19:16]==0||word3[19:16]>8||word3[127:21]!=0||
    word4!=0||word7[31:0]!=32'h53333251||word7[63:32]!=32'h4b313633||word7[127:64]!=0)begin command_bad=1;command_error=3;end
   ALLOC:if(word1[5:0]!=0||word1[127:64]!=0||transport_wrap)begin command_bad=1;command_error=4;end
   EXEC:if(!exec_owner||!n_ready_mask[exec_bank]||!scope_live[handle]||runtime_shift>17||word1[127:121]!=0||
     (!n_busy&&exec_offset!=scope_next_k[handle])||
     exec_offset[6:0]!=0||({1'b0,exec_offset}+17'd128)>{1'b0,scope_full_k[handle]})begin command_bad=1;command_error=5;end
   CONTEXT:if((context_kind!=0&&context_kind!=3&&context_kind!=4)||command_frame[127:115]!=0)begin command_bad=1;command_error=6;end
   RESTORE:if(word2!=scope_owner[handle]||word3[31:16]!=scope_full_k[handle]||word3[43:40]!=scope_n[handle]||
    word3[39:32]!=(scope_head[handle]?16:128)||word3[127:44]!=0||word4[127:32]!=0||word7[127:81]!=0)begin command_bad=1;command_error=7;end
   CANCEL,DRAIN:if(!bank_owner||n_free_mask[command_bank])begin command_bad=1;command_error=8;end
   FENCE:if(record_id!=0||handle!=0||handle_generation!=0||command_bank_generation!=0)begin command_bad=1;command_error=9;end
   default:begin command_bad=1;command_error=10;end
  endcase
 end
 reg [3:0] selected_source;reg [511:0] selected_frame;reg [2:0] selected_length;
 wire rf_identity_bad=n_rsp_owner!=scope_owner[n_rsp_context]||
  (n_rsp_key!=0?(n_rsp_key!=scope_key[n_rsp_context]||(!n_rsp_error&&
   n_rsp_tag!=({exec_session[28:0],3'd0}+(scope_head[n_rsp_context]?32'd7:32'd0)))):
   n_rsp_tag!=control_session);
 always @*begin
  selected_source=0;selected_frame=0;selected_length=2;
  if(n_fault_valid)begin selected_source=7;selected_length=3;selected_frame[127:0]=header(7,{4'd0,n_fault_op},0,n_fault_record,3,0);selected_frame[129:128]=n_fault_bank;selected_frame[145:130]=n_fault_generation;selected_frame[383:256]=n_fault_key;end
  else if(n_native_fault_valid)begin selected_source=8;selected_length=3;selected_frame[127:0]=header(7,{5'd0,n_native_fault_kind},exec_session,n_native_fault_record,3,0);selected_frame[383:256]=n_native_fault_key;end
  else if(command_reply_valid)begin
   selected_source=11;selected_length=command_reply_kind==0?3'd3:3'd2;
   selected_frame[127:0]=header(command_reply_kind==0?8'd7:command_reply_kind==1?8'd10:8'd9,
    command_reply_status,session,command_reply_kind==1?32'd0:record_id,selected_length,0);
   if(command_reply_kind==0)selected_frame[383:256]=same_scope?scope_key[handle]:128'd0;
  end
  else if(local_valid)begin selected_source=9;selected_frame=local_frame;selected_length=local_length;end
  else if(n_input_done_valid)begin
   selected_source=3;selected_frame[127:0]=header(3,{7'd0,n_input_done_key!=A_key},exec_session,n_input_done_record,2,0);
   selected_frame[129:128]=n_input_done_bank;selected_frame[145:130]=n_input_done_generation;
   selected_frame[161:146]=n_input_done_use;selected_frame[162]=n_input_done_a_slot;selected_frame[178:163]=n_input_done_a_generation;
   selected_frame[194:179]=A_kk;selected_frame[226:195]=exec_ticket;
  end else if(n_rsp_valid)begin
   selected_source=4;selected_length=n_rsp_snapshot?3'd4:3'd2;
   selected_frame[127:0]=header(4,{7'd0,n_rsp_error||rf_identity_bad},n_rsp_key!=0?exec_session:control_session,n_rsp_record,selected_length,
     {1'b0,n_rsp_kind,n_rsp_context,2'd0,n_rsp_final,n_rsp_snapshot});
   selected_frame[131:128]=n_rsp_context;selected_frame[135:132]=n_rsp_n;selected_frame[143:136]=n_rsp_group_k;
   selected_frame[159:144]=n_rsp_next_k;selected_frame[175:160]=n_rsp_full_k;selected_frame[207:176]=n_rsp_ticket;
   selected_frame[209:208]=n_rsp_bank;selected_frame[225:210]=n_rsp_generation;selected_frame[241:226]=n_rsp_use;
   if(n_rsp_snapshot)selected_frame[511:256]=n_rsp_data;
  end else if(n_alloc_ack_valid)begin
   selected_source=1;selected_frame[127:0]=header(1,{7'd0,n_alloc_ack_error},alloc_session,n_alloc_ack_record,2,0);
   selected_frame[129:128]=n_alloc_ack_bank;selected_frame[145:130]=n_alloc_ack_generation;
   selected_frame[149:146]=alloc_scope;selected_frame[165:150]=alloc_scope_generation;
  end else if(n_fill_ack_valid)begin
   selected_source=2;selected_frame[127:0]=header(2,{7'd0,n_fill_ack_error||n_fill_ack_key!=table_key[n_fill_ack_bank]},table_session[n_fill_ack_bank],n_fill_ack_record,2,0);
   selected_frame[129:128]=n_fill_ack_bank;selected_frame[145:130]=n_fill_ack_generation;
  end else if(n_abort_done_valid)begin
   selected_source=5;selected_length=4;selected_frame[127:0]=header(5,0,exec_session,n_abort_done_record,4,0);
   selected_frame[131:128]=n_abort_done_context;selected_frame[159:144]=n_abort_done_next_k;
   selected_frame[383:256]=n_abort_done_key;selected_frame[511:384]=n_abort_done_owner;
  end else if(n_drain_done_valid)begin
   selected_source=6;selected_frame[127:0]=header(6,{7'd0,n_drain_done_key!=drain_key},drain_session,n_drain_done_record,2,0);
   selected_frame[129:128]=n_drain_done_bank;selected_frame[145:130]=n_drain_done_generation;
  end else if(fence_reply)begin
   selected_source=10;selected_frame[127:0]=header(8,0,fence_cookie,0,2,0);selected_frame[136:128]=transport_epoch;
  end
 end
 assign n_issue_bank=request_bank;assign n_issue_generation=table_generation[request_bank];assign n_issue_key=table_key[request_bank];
 assign n_issue_record=table_record[request_bank];assign n_issue_beat=request_beat;assign n_issue_valid=request_fire;
 assign n_fill_valid=mc_rsp_valid&&return_good;assign n_fill_bank=return_bank;assign n_fill_generation=mc_rsp_tag[20:5];
 assign n_fill_key=table_key[return_bank];assign n_fill_record=table_record[return_bank];assign n_fill_beat=return_beat;
 assign n_fill_last=return_beat==(table_head[return_bank]?17:16);assign n_fill_data=mc_rsp_data;
 assign n_a_valid=a_valid&&!bad_A&&!A_wait_bind;assign n_a_data=a_data;assign n_a_beat=a_beat;assign n_a_key=A_key;assign n_a_record=A_record;
 assign n_a_slot=A_slot;assign n_a_generation=A_generation;assign n_a_kk=A_kk;assign n_a_use=A_use;
 assign n_alloc_ack_ready=tx_end&&tx_source==1;assign n_fill_ack_ready=tx_end&&tx_source==2;
 assign n_input_done_ready=tx_end&&tx_source==3;assign n_rsp_ready=tx_end&&tx_source==4;
 assign n_abort_done_ready=tx_end&&tx_source==5;assign n_drain_done_ready=tx_end&&tx_source==6;
 assign n_fault_ready=tx_end&&tx_source==7;assign n_native_fault_ready=tx_end&&tx_source==8;
 always @*begin
  n_alloc_valid=0;
  n_alloc_key=0;
  n_alloc_record=0;
  n_alloc_head16=0;
  n_alloc_n=0;
  n_cancel_valid=0;
  n_cancel_bank=0;
  n_cancel_generation=0;
  n_cancel_key=0;
  n_cancel_record=0;
  n_drain_valid=0;
  n_drain_bank=0;
  n_drain_generation=0;
  n_drain_key=0;
  n_drain_record=0;
  n_exec_valid=0;
  n_exec_key=0;
  n_exec_record=0;
  n_exec_bank=0;
  n_exec_generation=0;
  n_exec_use=0;
  n_exec_raw_tag=0;
  n_exec_ticket=0;
  n_exec_owner=0;
  n_exec_context=0;
  n_exec_full_k=0;
  n_exec_k_offset=0;
  n_exec_kk=0;
  n_exec_a_slot=0;
  n_exec_a_generation=0;
  n_exec_a_shifts=0;
  n_exec_bias=0;
  n_control_valid=0;
  n_control_kind=0;
  n_control_context=0;
  n_control_owner=0;
  n_control_ticket=0;
  n_control_full_k=0;
  n_control_k_offset=0;
  n_control_group_k=0;
  n_control_n=0;
  n_control_previous=0;
  n_control_snapshot_ticket=0;
  n_restore_commit_valid=0;
  n_restore_commit_owner=0;
  n_restore_commit_context=0;
  n_restore_commit_ticket=0;
  n_restore_commit_next_k=0;
  n_restore_commit_full_k=0;
  n_restore_commit_group_k=0;
  n_restore_commit_n=0;
  // Control context is an address, sampled only when n_control_valid
  // handshakes. Keep it stable even while invalid: zero-gating it through
  // full command validation creates a false data dependence from scope
  // contents -> valid -> RF read-address mux -> prefix arithmetic.
  n_control_context=handle;
  if(command_pending&&!command_reply_valid&&!command_bad)case(op)
   ALLOC:if(!alloc_hold)begin n_alloc_valid=1;n_alloc_key=scope_key[handle];n_alloc_record=record_id;n_alloc_n=scope_n[handle];n_alloc_head16=scope_head[handle];end
   EXEC:begin
    n_exec_valid=1;n_exec_key=scope_key[handle];n_exec_record=record_id;n_exec_bank=exec_bank;n_exec_generation=exec_generation;
    n_exec_use=word1[33:18];n_exec_raw_tag={session[28:0],3'd0};n_exec_ticket=word1[120:89];
    n_exec_owner=scope_owner[handle];n_exec_context=handle;n_exec_full_k=scope_full_k[handle];n_exec_k_offset=exec_offset;
    n_exec_kk=word1[65:50];n_exec_a_slot=word1[66];n_exec_a_generation=word1[82:67];n_exec_a_shifts={8{runtime_shift}};n_exec_bias=scope_bias[handle];
   end
   CONTEXT,RESTORE:begin
    n_control_valid=1;n_control_kind=op==RESTORE?3'd1:context_kind;n_control_owner=scope_owner[handle];
    n_control_ticket=session;n_control_full_k=scope_full_k[handle];n_control_k_offset=op==RESTORE?word3[15:0]:16'd0;
    n_control_group_k=scope_head[handle]?8'd16:8'd128;n_control_n=scope_n[handle];n_control_previous=payload;
    if(op==RESTORE)begin
     n_control_snapshot_ticket=word4[31:0];n_restore_commit_valid=word7[32];n_restore_commit_owner=word1;
     n_restore_commit_ticket=word7[31:0];n_restore_commit_context=word7[36:33];n_restore_commit_next_k=word7[52:37];
     n_restore_commit_full_k=word7[68:53];n_restore_commit_group_k=word7[76:69];n_restore_commit_n=word7[80:77];
    end
   end
   CANCEL:if(!tx_valid&&!(request_locked&&locked_bank==command_bank))begin
    n_cancel_valid=1;n_cancel_bank=command_bank;n_cancel_generation=command_bank_generation;n_cancel_key=table_key[command_bank];n_cancel_record=record_id;
   end
   DRAIN:if(!drain_hold&&table_cancel[command_bank]&&table_closed[command_bank]&&table_issued[command_bank]==table_received[command_bank])begin
    n_drain_valid=1;n_drain_bank=command_bank;n_drain_generation=command_bank_generation;n_drain_key=table_key[command_bank];n_drain_record=record_id;
   end
   default:begin end
  endcase
 end
 task automatic local_reply(input [7:0] event_id,status,input [31:0] sid,r,input [127:0] fault_key);
  begin local_valid<=1;local_length<=event_id==7?3'd3:3'd2;local_frame<=0;
   local_frame[127:0]<=header(event_id,status,sid,r,event_id==7?3'd3:3'd2,0);
   if(event_id==7)local_frame[383:256]<=fault_key;
  end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   scope_valid<=0;scope_live<=0;table_valid<=0;table_cancel<=0;table_closed<=0;issue_cursor<=0;allocation_cursor<=0;
   request_locked<=0;locked_bank<=0;locked_beat<=0;locked_address<=0;table_channel<=0;transport_epoch<=0;
   close_locked<=0;locked_close_bank<=0;
   command_pending<=0;rx_active<=0;rx_index<=0;rx_length<=0;last_session<=0;
   local_valid<=0;local_frame<=0;local_length<=0;command_reply_valid<=0;command_reply_kind<=0;command_reply_status<=0;tx_valid<=0;tx_frame<=0;tx_index<=0;tx_length<=0;tx_source<=0;
   fence_wait<=0;fence_offered<=0;fence_reply<=0;fence_cookie<=0;fence_epoch<=0;
   alloc_hold<=0;alloc_installed<=0;alloc_base<=0;alloc_session<=0;alloc_scope<=0;alloc_scope_generation<=0;
   drain_hold<=0;drain_session<=0;drain_key<=0;exec_session<=0;exec_ticket<=0;control_session<=0;
   A_key<=0;A_record<=0;A_live<=0;A_slot<=0;A_generation<=0;A_kk<=0;A_use<=0;
   for(integer s=0;s<16;s=s+1)begin scope_generation[s]<=0;scope_epoch[s]<=0;scope_next_k[s]<=0;end
   for(integer b=0;b<4;b=b+1)begin
    table_key[b]<=0;table_record[b]<=0;table_session[b]<=0;table_generation[b]<=0;table_epoch[b]<=0;
    table_base[b]<=0;table_scope[b]<=0;table_scope_generation[b]<=0;table_head[b]<=0;table_next[b]<=0;table_issued[b]<=0;table_received[b]<=0;
   end
  end else begin
   if(lc_valid&&lc_ready)begin
    if(!rx_active)begin
     if(!lc_sop||lc_data[15:0]!=16'h4d02||command_length(lc_data[19:16])==0||
       lc_data[23:20]!=command_length(lc_data[19:16])||lc_eop!=(lc_data[23:20]==1))begin
      local_reply(7,11,lc_data[63:32],lc_data[95:64],0);rx_active<=0;rx_index<=0;
     end else begin
      command_frame[127:0]<=lc_data;rx_length<=lc_data[23:20];
      if(lc_eop)command_pending<=1;else begin rx_active<=1;rx_index<=1;end
     end
    end else if(lc_sop||lc_eop!=({1'b0,rx_index}==rx_length-4'd1))begin
     local_reply(7,12,command_frame[63:32],command_frame[95:64],0);rx_active<=0;rx_index<=0;
    end else begin
     command_frame[int'(rx_index)*128+:128]<=lc_data;
     if(lc_eop)begin command_pending<=1;rx_active<=0;rx_index<=0;end else rx_index<=rx_index+1'b1;
    end
   end
   if(command_pending&&!command_reply_valid)begin
    if(command_bad)begin command_reply_valid<=1;command_reply_kind<=0;command_reply_status<=command_error;command_pending<=0;last_session<=session;end
    else case(op)
     BEGIN_SCOPE:begin
      scope_valid[handle]<=1;scope_generation[handle]<=handle_generation;scope_epoch[handle]<=transport_epoch;
      scope_key[handle]<=word1;scope_owner[handle]<=word2;scope_full_k[handle]<=word3[15:0];scope_n[handle]<=word3[19:16];
      scope_head[handle]<=word3[20];scope_bias[handle]<=payload;
      command_reply_valid<=1;command_reply_kind<=1;command_reply_status<=0;command_pending<=0;last_session<=session;
     end
     ALLOC:if(n_alloc_valid&&n_alloc_ready)begin
      alloc_hold<=1;alloc_installed<=0;alloc_base<=word1[63:0];alloc_session<=session;alloc_scope<=handle;alloc_scope_generation<=handle_generation;
      command_pending<=0;last_session<=session;
     end
     EXEC:if(n_exec_valid&&n_exec_ready)begin
      exec_session<=session;exec_ticket<=word1[120:89];A_key<=scope_key[handle];A_record<=record_id;A_live<=1;
      A_slot<=word1[66];A_generation<=word1[82:67];A_kk<=word1[65:50];A_use<=word1[33:18];command_pending<=0;last_session<=session;
     end
     CONTEXT,RESTORE:if(n_control_valid&&n_control_ready)begin control_session<=session;command_pending<=0;last_session<=session;end
     CANCEL:if(n_cancel_valid&&n_cancel_ready)begin table_cancel[command_bank]<=1;if(table_issued[command_bank]==0)table_closed[command_bank]<=1;command_reply_valid<=1;command_reply_kind<=2;command_reply_status<=0;command_pending<=0;last_session<=session;end
     DRAIN:if(n_drain_valid&&n_drain_ready)begin drain_hold<=1;drain_session<=session;drain_key<=table_key[command_bank];command_pending<=0;last_session<=session;end
     FENCE:if(n_free_mask==15&&n_outstanding==0&&!n_busy&&!tx_valid&&!A_live&&!request_locked&&!close_locked&&
       n_scale_count==0&&!n_rsp_valid&&!n_alloc_ack_valid&&!n_fill_ack_valid&&!n_input_done_valid&&!n_abort_done_valid&&!n_drain_done_valid)begin
      fence_wait<=1;fence_offered<=0;fence_cookie<=session;fence_epoch<=transport_epoch;command_pending<=0;last_session<=session;
     end
     default:begin end
    endcase
   end
   if(n_alloc_ack_valid&&!alloc_installed)begin
    alloc_installed<=1;
    if(!n_alloc_ack_error)begin
     table_valid[n_alloc_ack_bank]<=1;table_cancel[n_alloc_ack_bank]<=0;table_closed[n_alloc_ack_bank]<=0;table_key[n_alloc_ack_bank]<=n_alloc_ack_key;
     table_record[n_alloc_ack_bank]<=n_alloc_ack_record;table_session[n_alloc_ack_bank]<=alloc_session;
     table_generation[n_alloc_ack_bank]<=n_alloc_ack_generation;table_epoch[n_alloc_ack_bank]<=transport_epoch;
     table_base[n_alloc_ack_bank]<=alloc_base;table_channel[n_alloc_ack_bank]<=alloc_base[11];table_scope[n_alloc_ack_bank]<=alloc_scope;
     table_scope_generation[n_alloc_ack_bank]<=alloc_scope_generation;table_head[n_alloc_ack_bank]<=scope_head[alloc_scope];
     table_next[n_alloc_ack_bank]<=0;table_issued[n_alloc_ack_bank]<=0;table_received[n_alloc_ack_bank]<=0;
     allocation_cursor<=n_alloc_ack_bank+1'b1;
    end
   end
   for(integer b=0;b<4;b=b+1)if(table_valid[b]&&n_free_mask[b])table_valid[b]<=0;
   if(request_fire)begin
    request_locked<=0;table_base[request_bank]<=address_after_issue[request_bank];table_issued[request_bank][request_beat]<=1;table_next[request_bank]<=request_beat+1'b1;issue_cursor<=request_bank+1'b1;
    if(request_beat==(table_head[request_bank]?17:16))table_closed[request_bank]<=1;
   end
   if(request_found)begin request_locked<=1;locked_bank<=candidate_bank;locked_beat<=candidate_beat;locked_address<=candidate_address;end
   if(mc_close_valid&&!mc_close_ready&&!close_locked)begin close_locked<=1;locked_close_bank<=close_bank;end
   if(mc_close_valid&&mc_close_ready)begin close_locked<=0;table_closed[close_bank]<=1;end
   if(mc_rsp_valid&&mc_rsp_ready)begin
    if(return_good)table_received[return_bank][return_beat]<=1;
    else begin
     // The stale tag does not establish ownership of the current bank.
     // Never blame a newly allocated object for another epoch's return.
     local_reply(7,13,0,0,0);local_frame[159:128]<=mc_rsp_tag;
    end
   end
   if(mc_fence_req_valid&&mc_fence_req_ready)fence_offered<=1;
   if(mc_fence_done_valid&&mc_fence_done_ready)begin
    if(bad_fence)begin local_reply(7,14,0,0,0);local_frame[159:128]<=mc_fence_done_cookie;local_frame[168:160]<=mc_fence_done_epoch;end
    else begin transport_epoch<=transport_epoch+1'b1;fence_wait<=0;fence_reply<=1;last_session<=0;end
   end
   if(a_valid&&a_ready&&bad_A)begin local_reply(7,15,0,0,0);local_frame[159:128]<=a_session;local_frame[162:160]<=a_beat;end
   if(!tx_valid&&selected_source!=0)begin tx_valid<=1;tx_frame<=selected_frame;tx_length<=selected_length;tx_index<=0;tx_source<=selected_source;end
   if(lr_valid&&lr_ready)begin
    if(lr_eop)begin
     tx_valid<=0;tx_index<=0;
     case(tx_source)
      1:begin alloc_hold<=0;alloc_installed<=0;end
      3:A_live<=0;
      4:if(!n_rsp_error)begin
       scope_next_k[n_rsp_context]<=n_rsp_next_k;
       if(n_rsp_kind<=1)scope_live[n_rsp_context]<=1;
       else if(n_rsp_kind==3||n_rsp_kind==4||(n_rsp_kind==2&&n_rsp_final))scope_live[n_rsp_context]<=0;
      end
      5:begin A_live<=0;scope_next_k[n_abort_done_context]<=n_abort_done_next_k;if(n_abort_done_next_k==scope_full_k[n_abort_done_context])scope_live[n_abort_done_context]<=0;end
      6:drain_hold<=0;
      9:local_valid<=0;
      10:fence_reply<=0;
      11:command_reply_valid<=0;
      default:begin end
     endcase
    end else tx_index<=tx_index+1'b1;
   end
  end
 end
endmodule
