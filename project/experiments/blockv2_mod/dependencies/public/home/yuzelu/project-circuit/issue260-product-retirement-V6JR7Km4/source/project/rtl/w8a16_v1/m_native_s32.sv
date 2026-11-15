// Candidate independent M leaf: 4608B W registers + 512B projection RF,
// finite raw/scale pipes and metadata. No 1024-bit W package escape port.
// All LC/MC command buses below are logical unit contracts, not frozen pins.
module m_native_s32 #(
 parameter integer KEY_W=128,
 parameter integer MC_CREDITS=32,
 // Product ABI has one runtime normalization shift per K128 A tile.
 // The default logical API also permits independent directed head shifts.
 parameter bit COMMON_A_SHIFT=1'b0
)(
 input wire clk, reset,
 input wire alloc_valid, output wire alloc_ready,
 input wire [KEY_W-1:0] alloc_key, input wire [31:0] alloc_record,
 input wire alloc_head16, input wire [3:0] alloc_n,
 output wire alloc_ack_valid, input wire alloc_ack_ready,
 output wire alloc_ack_error, output wire [1:0] alloc_ack_bank,
 output wire [15:0] alloc_ack_generation,
 output wire [KEY_W-1:0] alloc_ack_key, output wire [31:0] alloc_ack_record,
 input wire issue_valid, output wire issue_ready,
 input wire [1:0] issue_bank, input wire [15:0] issue_generation,
 input wire [KEY_W-1:0] issue_key, input wire [31:0] issue_record,
 input wire [4:0] issue_beat,
 input wire fill_valid, output wire fill_ready,
 input wire [1:0] fill_bank, input wire [15:0] fill_generation,
 input wire [KEY_W-1:0] fill_key, input wire [31:0] fill_record,
 input wire [4:0] fill_beat, input wire fill_last,
 input wire [511:0] fill_data,
 output wire fill_ack_valid, input wire fill_ack_ready,
 output wire [1:0] fill_ack_bank, output wire [15:0] fill_ack_generation,
 output wire [KEY_W-1:0] fill_ack_key, output wire [31:0] fill_ack_record,
 output wire fill_ack_error,
 input wire cancel_valid, output wire cancel_ready,
 input wire [1:0] cancel_bank, input wire [15:0] cancel_generation,
 input wire [KEY_W-1:0] cancel_key, input wire [31:0] cancel_record,
 input wire drain_valid, output wire drain_ready,
 input wire [1:0] drain_bank, input wire [15:0] drain_generation,
 input wire [KEY_W-1:0] drain_key, input wire [31:0] drain_record,
 output wire drain_done_valid, input wire drain_done_ready,
 output wire [1:0] drain_done_bank, output wire [15:0] drain_done_generation,
 output wire [KEY_W-1:0] drain_done_key, output wire [31:0] drain_done_record,
 output wire fault_valid, input wire fault_ready,
 output wire [3:0] fault_op,
 output wire [1:0] fault_bank, output wire [15:0] fault_generation,
 output wire [KEY_W-1:0] fault_key, output wire [31:0] fault_record,
 output wire [6:0] outstanding, output wire [3:0] free_mask, ready_mask,
 // One native record in execution; other W banks may fill/reuse meanwhile.
 input wire exec_valid, output wire exec_ready,
 input wire [KEY_W-1:0] exec_key, input wire [31:0] exec_record,
 input wire [1:0] exec_bank, input wire [15:0] exec_generation, exec_use,
 input wire [31:0] exec_raw_tag, exec_ticket,
 input wire [127:0] exec_owner, input wire [3:0] exec_context,
 input wire [15:0] exec_full_k, exec_k_offset, exec_kk,
 input wire exec_a_slot, input wire [15:0] exec_a_generation,
 input wire [47:0] exec_a_shifts, input wire [255:0] exec_bias,
 input wire a_valid, output wire a_ready,
 input wire [KEY_W-1:0] a_key, input wire [31:0] a_record,
 input wire a_slot, input wire [15:0] a_generation, a_kk, a_use,
 input wire [2:0] a_beat, input wire [255:0] a_data,
 // Actual final operand event. Acceptance releases W input ownership only.
 output wire input_done_valid, input wire input_done_ready,
 output wire [KEY_W-1:0] input_done_key, output wire [31:0] input_done_record,
 output wire [1:0] input_done_bank, output wire [15:0] input_done_generation, input_done_use,
 output wire input_done_a_slot, output wire [15:0] input_done_a_generation,
 // Cancel reports the actual completed head prefix; no atomic rollback.
 output wire abort_done_valid, input wire abort_done_ready,
 output wire [KEY_W-1:0] abort_done_key, output wire [31:0] abort_done_record,
 output wire [127:0] abort_done_owner, output wire [3:0] abort_done_context,
 output wire [15:0] abort_done_next_k,
 // CREATE/RESTORE/SPILL/DROP. STEP is reserved for actual raw results.
 input wire control_valid, output wire control_ready,
 input wire [2:0] control_kind, input wire [3:0] control_context,
 input wire [127:0] control_owner, input wire [31:0] control_ticket,
 input wire [15:0] control_full_k, control_k_offset,
 input wire [7:0] control_group_k, input wire [3:0] control_n,
 input wire [255:0] control_previous,
 // Proof produced by the finite external two-slot S-write guard only after
 // BOTH actual 128-bit destination writes ACK. A request bit is not proof.
 input wire [31:0] control_snapshot_ticket,
 input wire restore_commit_valid,
 input wire [127:0] restore_commit_owner,
 input wire [3:0] restore_commit_context,
 input wire [31:0] restore_commit_ticket,
 input wire [15:0] restore_commit_next_k, restore_commit_full_k,
 input wire [7:0] restore_commit_group_k, input wire [3:0] restore_commit_n,
 // One held RF response. FINAL/SPILL capture into the external 2x32B guard
 // releases the RF; actual S ACK is later and has an independent identity.
 output wire rsp_valid, input wire rsp_ready,
 output wire [2:0] rsp_kind, output wire [3:0] rsp_context,
 output wire [127:0] rsp_owner, output wire [31:0] rsp_tag, rsp_ticket,
 output wire [KEY_W-1:0] rsp_key, output wire [31:0] rsp_record,
 output wire [1:0] rsp_bank, output wire [15:0] rsp_generation, rsp_use,
 output wire [15:0] rsp_next_k, rsp_full_k,
 output wire [7:0] rsp_group_k, output wire [3:0] rsp_n,
 output wire rsp_final, rsp_snapshot, output wire [255:0] rsp_data,
 output wire rsp_error,
 output reg native_fault_valid, input wire native_fault_ready,
 output reg [2:0] native_fault_kind,
 output reg [KEY_W-1:0] native_fault_key, output reg [31:0] native_fault_record,
 output wire busy, output wire [2:0] scale_count
);
 wire ws_ready, ws_accepted, ws_head;wire [3:0] ws_n;
 wire w_valid,w_ready,w_first,w_last,w_record_last;
 wire [KEY_W-1:0] w_key;wire [31:0] w_record,w_raw_tag;
 wire [1:0] w_bank;wire [15:0] w_generation,w_use;
 wire [7:0] w_group_k,w_offset;wire [3:0] w_n;wire [2:0] w_group_index;
 wire [1023:0] w_data;wire [127:0] w_scale;
 wire consumed_ready,cancel_accepted,weight_drain_ready;
 reg active,feeding,aborting,abort_pending,done_pending;
 reg [KEY_W-1:0] key;reg [31:0] record_id,ticket;
 reg [1:0] bank;reg [15:0] generation,use_id;
 reg [127:0] owner;reg [3:0] context_id;
 reg [15:0] full_k,k_offset,kk,committed_next;
 reg head,a_slot_id;reg [15:0] a_generation_id;
 reg [47:0] a_shifts;reg [255:0] bias;
 reg [3:0] expected_groups,retired_groups;
 wire nf_space=!native_fault_valid||native_fault_ready;
 reg shifts_bad;
 always @* begin
  shifts_bad=0;
  for(integer i=0;i<8;i=i+1)if((ws_head||i==0)&&exec_a_shifts[i*6+:6]>17)shifts_bad=1;
 end
 wire exec_bad=exec_full_k==0||exec_full_k[6:0]!=0||exec_k_offset[6:0]!=0||
  ({1'b0,exec_k_offset}+17'd128)>{1'b0,exec_full_k}||shifts_bad;
 wire rf_pending;
 assign exec_ready=!reset&&!active&&!aborting&&!abort_pending&&!rf_pending&&!control_valid&&nf_space&&ws_ready;
 wire exec_fire=exec_valid&&exec_ready;
 wire drain_current=active&&drain_bank==bank&&drain_generation==generation&&drain_key==key&&drain_record==record_id;
 assign drain_ready=!drain_current&&weight_drain_ready;
 weight_records #(.KEY_W(KEY_W),.MC_CREDITS(MC_CREDITS)) weights(
  .clk(clk),.reset(reset),
  .alloc_valid(alloc_valid),.alloc_ready(alloc_ready),.alloc_key(alloc_key),.alloc_record(alloc_record),
  .alloc_head16(alloc_head16),.alloc_n(alloc_n),.alloc_ack_valid(alloc_ack_valid),.alloc_ack_ready(alloc_ack_ready),
  .alloc_ack_error(alloc_ack_error),.alloc_ack_bank(alloc_ack_bank),.alloc_ack_generation(alloc_ack_generation),
  .alloc_ack_key(alloc_ack_key),.alloc_ack_record(alloc_ack_record),
  .issue_valid(issue_valid),.issue_ready(issue_ready),.issue_bank(issue_bank),.issue_generation(issue_generation),
  .issue_key(issue_key),.issue_record(issue_record),.issue_beat(issue_beat),
  .fill_valid(fill_valid),.fill_ready(fill_ready),.fill_bank(fill_bank),.fill_generation(fill_generation),
  .fill_key(fill_key),.fill_record(fill_record),.fill_beat(fill_beat),.fill_last(fill_last),.fill_data(fill_data),
  .fill_ack_valid(fill_ack_valid),.fill_ack_ready(fill_ack_ready),.fill_ack_bank(fill_ack_bank),
  .fill_ack_generation(fill_ack_generation),.fill_ack_key(fill_ack_key),.fill_ack_record(fill_ack_record),.fill_ack_error(fill_ack_error),
  .start_valid(exec_valid&&exec_ready&&!exec_bad),.start_ready(ws_ready),
  .start_bank(exec_bank),.start_generation(exec_generation),.start_key(exec_key),.start_record(exec_record),
  .start_use(exec_use),.start_raw_tag(exec_raw_tag),.start_accepted(ws_accepted),.start_head16(ws_head),.start_n(ws_n),
  .w_valid(w_valid),.w_ready(w_ready),.w_key(w_key),.w_record(w_record),.w_bank(w_bank),
  .w_generation(w_generation),.w_use(w_use),.w_raw_tag(w_raw_tag),.w_group_k(w_group_k),.w_offset(w_offset),
  .w_n(w_n),.w_first(w_first),.w_last(w_last),.w_record_last(w_record_last),.w_group_index(w_group_index),
  .w_data(w_data),.w_scale(w_scale),
  .consumed_valid(done_pending&&input_done_ready),.consumed_ready(consumed_ready),
  .consumed_bank(bank),.consumed_generation(generation),.consumed_key(key),.consumed_record(record_id),.consumed_use(use_id),
  .cancel_valid(cancel_valid),.cancel_ready(cancel_ready),.cancel_bank(cancel_bank),
  .cancel_generation(cancel_generation),.cancel_key(cancel_key),.cancel_record(cancel_record),
  .cancel_accepted(cancel_accepted),
  .drain_valid(drain_valid&&!drain_current),.drain_ready(weight_drain_ready),.drain_bank(drain_bank),.drain_generation(drain_generation),
  .drain_key(drain_key),.drain_record(drain_record),.drain_done_valid(drain_done_valid),.drain_done_ready(drain_done_ready),
  .drain_done_bank(drain_done_bank),.drain_done_generation(drain_done_generation),.drain_done_key(drain_done_key),.drain_done_record(drain_done_record),
  .fault_valid(fault_valid),.fault_ready(fault_ready),.fault_op(fault_op),.fault_bank(fault_bank),
  .fault_generation(fault_generation),.fault_key(fault_key),.fault_record(fault_record),
  .outstanding(outstanding),.free_mask(free_mask),.ready_mask(ready_mask));
 // The full record identity is retained outside the reusable W banks.
 assign input_done_valid=done_pending&&consumed_ready;
 assign input_done_key=key;assign input_done_record=record_id;assign input_done_bank=bank;
 assign input_done_generation=generation;assign input_done_use=use_id;
 assign input_done_a_slot=a_slot_id;assign input_done_a_generation=a_generation_id;
 wire cancel_current=cancel_accepted&&active&&cancel_bank==bank&&
  cancel_generation==generation&&cancel_key==key&&cancel_record==record_id;
 assign abort_done_valid=abort_pending;assign abort_done_key=key;assign abort_done_record=record_id;
 assign abort_done_owner=owner;assign abort_done_context=context_id;assign abort_done_next_k=committed_next;
 assign busy=active;
 reg [127:0] scales [0:3];reg [31:0] tags [0:3];reg [2:0] groups [0:3];
 reg [1:0] read_ptr,write_ptr;reg [2:0] count;
 assign scale_count=count;
 wire raw_valid,raw_ready,raw_error,raw_in_ready;
 wire [31:0] raw_tag;wire [3:0] raw_n;wire [255:0] raw_data;
 wire rf_cmd_ready,rf_cmd_valid,rf_rsp_valid,rf_rsp_ready,rf_rsp_error,rf_rsp_final;
 wire [2:0] rf_rsp_kind;wire [3:0] rf_rsp_context,rf_rsp_n;
 wire [127:0] rf_rsp_owner;wire [31:0] rf_rsp_tag;
 wire [15:0] rf_rsp_next_k,rf_rsp_full_k;wire [7:0] rf_rsp_group_k;wire [255:0] rf_rsp_data;
 wire from_raw=active&&raw_valid&&count!=0;
 wire rf_metadata_space;
 assign raw_ready=active&&count!=0&&rf_cmd_ready&&rf_metadata_space;
 wire pop=raw_valid&&raw_ready;
 wire metadata_space=count<4||pop;
 wire [2:0] expected_beat=head?w_group_index:w_offset[6:4];
 wire a_match=a_key==key&&a_record==record_id&&a_slot==a_slot_id&&a_generation==a_generation_id&&
  a_kk==kk&&a_use==use_id&&a_beat==expected_beat;
 wire operands=active&&feeding&&!aborting&&!cancel_current&&w_valid&&a_valid&&a_match&&(!w_last||metadata_space);
 assign w_ready=active&&feeding&&!aborting&&!cancel_current&&a_valid&&a_match&&raw_in_ready&&(!w_last||metadata_space);
 assign a_ready=active&&feeding&&!aborting&&!cancel_current&&
  (a_match?(w_valid&&raw_in_ready&&(!w_last||metadata_space)):nf_space);
 wire push=w_valid&&w_ready&&w_last;
 wire flush_raw=aborting&&count==0&&!rf_pending;
 m_group_s32 raw(.clk(clk),.reset(reset||flush_raw),.in_valid(operands),.in_ready(raw_in_ready),
  .in_first(w_first),.in_last(w_last),.in_tag(w_raw_tag),.in_group_k(w_group_k),.in_offset(w_offset),
  .in_k(5'd16),.in_n(w_n),.in_a(a_data),.in_w(w_data),
  .out_valid(raw_valid),.out_ready(raw_ready),.out_tag(raw_tag),.out_n(raw_n),.out_data(raw_data),.out_error(raw_error));
 // RF now accepts head STEP at II1. Its three finite arithmetic/response
 // owners need matching in-order metadata, not a single overwritten latch.
 // Four 37-bit entries (18.5 B) carry no numerical result payload. This
 // storage, its pointers and mux are counted in M area.
 reg [36:0] rf_metadata [0:3];
 reg [1:0] rf_read_ptr,rf_write_ptr;reg [2:0] rf_count;
 reg record_error_reported;
 wire rsp_from_raw=rf_metadata[rf_read_ptr][36];
 wire response_record_last=rf_metadata[rf_read_ptr][35];
 wire [2:0] requested_kind=rf_metadata[rf_read_ptr][34:32];
 wire [31:0] response_ticket=rf_metadata[rf_read_ptr][31:0];
 assign rf_pending=rf_count!=0;
 wire restore_proof=restore_commit_valid&&restore_commit_owner==control_owner&&
  restore_commit_context==control_context&&restore_commit_ticket==control_snapshot_ticket&&
  restore_commit_next_k==control_k_offset&&restore_commit_full_k==control_full_k&&
  restore_commit_group_k==control_group_k&&restore_commit_n==control_n;
 wire control_bad=control_kind==2||control_kind>4||(control_kind==1&&!restore_proof);
 assign control_ready=!reset&&!active&&rf_cmd_ready&&rf_metadata_space;
 wire manual=control_valid&&control_ready;
 // raw_n is checked against latched record N below, not reusable bank N.
 reg [3:0] active_n;
 wire raw_identity_bad=raw_error||raw_tag!=tags[read_ptr]||raw_n!=active_n;
 wire [15:0] step_offset=k_offset+(head?{9'd0,groups[read_ptr],4'd0}:16'd0);
 wire [7:0] step_group=head?8'd16:8'd128;
 wire [16:0] step_next={1'b0,step_offset}+{9'd0,step_group};
 assign rf_cmd_valid=(from_raw&&rf_metadata_space)||manual;
 projection_context_s32 contexts(.clk(clk),.reset(reset),.cmd_valid(rf_cmd_valid),.cmd_ready(rf_cmd_ready),
  .cmd_kind(from_raw?(raw_identity_bad?3'd7:3'd2):(control_bad?3'd7:control_kind)),
  .cmd_context(from_raw?context_id:control_context),.cmd_owner(from_raw?owner:control_owner),
  .cmd_tag(from_raw?tags[read_ptr]:control_ticket),.cmd_full_k(from_raw?full_k:control_full_k),
  .cmd_k_offset(from_raw?step_offset:control_k_offset),.cmd_group_k(from_raw?step_group:control_group_k),
  .cmd_n(from_raw?active_n:control_n),.cmd_final(from_raw&&step_next=={1'b0,full_k}),
  .cmd_a_shift(from_raw?(COMMON_A_SHIFT?a_shifts[5:0]:a_shifts[(head?int'(groups[read_ptr]):0)*6+:6]):6'd0),
  .cmd_partial(raw_data),.cmd_previous(control_previous),.cmd_bias(bias),.cmd_scale_fp16(scales[read_ptr]),
  .rsp_valid(rf_rsp_valid),.rsp_ready(rf_rsp_ready),.rsp_kind(rf_rsp_kind),.rsp_context(rf_rsp_context),
  .rsp_owner(rf_rsp_owner),.rsp_tag(rf_rsp_tag),.rsp_next_k(rf_rsp_next_k),.rsp_final(rf_rsp_final),
  .rsp_full_k(rf_rsp_full_k),.rsp_group_k(rf_rsp_group_k),.rsp_n(rf_rsp_n),
  .rsp_data(rf_rsp_data),.rsp_error(rf_rsp_error));
 // One completion per native record, not eight external head commands.
 // Every successful intermediate head STEP still retires through the real
 // RF/scale pipeline. The first error is exposed once; its queued suffix
 // drains internally and cannot update the mismatched RF cursor.
 wire internal_response=rsp_from_raw&&(aborting||cancel_current||record_error_reported||
  (!response_record_last&&!rf_rsp_error));
 assign rsp_valid=rf_rsp_valid&&!internal_response;
 assign rf_rsp_ready=internal_response||rsp_ready;
 assign rsp_kind=requested_kind;assign rsp_context=rf_rsp_context;assign rsp_owner=rf_rsp_owner;
 assign rsp_tag=rf_rsp_tag;assign rsp_ticket=response_ticket;
 assign rsp_key=rsp_from_raw?key:{KEY_W{1'b0}};assign rsp_record=rsp_from_raw?record_id:32'd0;
 assign rsp_bank=rsp_from_raw?bank:2'd0;assign rsp_generation=rsp_from_raw?generation:16'd0;
 assign rsp_use=rsp_from_raw?use_id:16'd0;
 assign rsp_next_k=rf_rsp_next_k;assign rsp_full_k=rf_rsp_full_k;assign rsp_group_k=rf_rsp_group_k;assign rsp_n=rf_rsp_n;
 assign rsp_final=rf_rsp_final;assign rsp_data=rf_rsp_data;assign rsp_error=rf_rsp_error;
 assign rsp_snapshot=!rf_rsp_error&&(requested_kind==3||(requested_kind==2&&rf_rsp_final));
 wire rsp_fire=rf_rsp_valid&&rf_rsp_ready;
 wire rf_cmd_fire=rf_cmd_valid&&rf_cmd_ready;
 assign rf_metadata_space=rf_count<4||rsp_fire;
 always @(posedge clk)begin
  if(reset)begin
   active<=0;feeding<=0;aborting<=0;abort_pending<=0;done_pending<=0;
   key<=0;record_id<=0;ticket<=0;bank<=0;generation<=0;use_id<=0;
   owner<=0;context_id<=0;full_k<=0;k_offset<=0;kk<=0;committed_next<=0;head<=0;
   a_slot_id<=0;a_generation_id<=0;a_shifts<=0;bias<=0;active_n<=0;
   expected_groups<=0;retired_groups<=0;read_ptr<=0;write_ptr<=0;count<=0;
   rf_read_ptr<=0;rf_write_ptr<=0;rf_count<=0;record_error_reported<=0;
   native_fault_valid<=0;native_fault_kind<=0;native_fault_key<=0;native_fault_record<=0;
  end else begin
   if(native_fault_valid&&native_fault_ready)native_fault_valid<=0;
   if(exec_fire&&exec_bad)begin native_fault_valid<=1;native_fault_kind<=1;native_fault_key<=exec_key;native_fault_record<=exec_record;end
   if(a_valid&&a_ready&&!a_match)begin native_fault_valid<=1;native_fault_kind<=2;native_fault_key<=a_key;native_fault_record<=a_record;end
   if(ws_accepted)begin
    active<=1;feeding<=1;aborting<=0;abort_pending<=0;done_pending<=0;
    key<=exec_key;record_id<=exec_record;ticket<=exec_ticket;bank<=exec_bank;
    generation<=exec_generation;use_id<=exec_use;owner<=exec_owner;context_id<=exec_context;
    full_k<=exec_full_k;k_offset<=exec_k_offset;kk<=exec_kk;committed_next<=exec_k_offset;
    head<=ws_head;active_n<=ws_n;a_slot_id<=exec_a_slot;a_generation_id<=exec_a_generation;
    a_shifts<=exec_a_shifts;bias<=exec_bias;expected_groups<=ws_head?4'd8:4'd1;retired_groups<=0;record_error_reported<=0;
   end
   count<=count+{2'd0,push}-{2'd0,pop};
   rf_count<=rf_count+{2'd0,rf_cmd_fire}-{2'd0,rsp_fire};
   if(push)begin scales[write_ptr]<=w_scale;tags[write_ptr]<=w_raw_tag;groups[write_ptr]<=w_group_index;write_ptr<=write_ptr+1'b1;end
   if(pop)read_ptr<=read_ptr+1'b1;
   if(w_valid&&w_ready&&w_record_last)begin feeding<=0;done_pending<=1;end
   if(input_done_valid&&input_done_ready)done_pending<=0;
   if(rsp_fire)begin
    rf_read_ptr<=rf_read_ptr+1'b1;
    if(rsp_from_raw)begin
     retired_groups<=retired_groups+1'b1;
     if(!rf_rsp_error)committed_next<=rf_rsp_next_k;
     else record_error_reported<=1;
    end
   end
   if(rf_cmd_fire)begin
    rf_metadata[rf_write_ptr]<={from_raw,from_raw&&(!head||groups[read_ptr]==7),from_raw?3'd2:control_kind,from_raw?ticket:control_ticket};
    rf_write_ptr<=rf_write_ptr+1'b1;
   end
   if(active&&!aborting&&!abort_pending&&!cancel_current&&!feeding&&!done_pending&&count==0&&!rf_pending&&retired_groups==expected_groups)active<=0;
   if(cancel_current)begin aborting<=1;feeding<=0;done_pending<=0;end
   if(flush_raw)begin aborting<=0;abort_pending<=1;end
   if(abort_done_valid&&abort_done_ready)begin abort_pending<=0;active<=0;end
  end
 end
 // Identity checks above use saved metadata. These original-bank mirrors
 // deliberately do not feed any result or scale after early bank release.
 wire unused_weight_identity=^{w_key,w_record,w_bank,w_generation,w_use,rf_rsp_kind};
endmodule
