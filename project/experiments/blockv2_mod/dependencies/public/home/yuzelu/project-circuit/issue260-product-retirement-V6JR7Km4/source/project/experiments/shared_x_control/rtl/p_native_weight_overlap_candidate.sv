`timescale 1ns/1ps
// Integration candidate: real serialized product-M aperture and A/guard
// owners. Scope descriptor stays in LC fetch registers; no duplicate scope,
// W payload, A payload, or result storage is introduced by this coordinator.
// Candidate fixed staging input for unregistered streamed service2, zero bias. Partial
// RESTORE/SPILL and mid-record emergency abort are deliberately not admitted
// by this candidate until their true snapshot/proof/drain paths are joined.
module p_native_weight_overlap_candidate #(
 // 0 keeps the paired two-bank candidate. 2 adds two real lookahead owners.
 parameter bit FOUR_BANK_LOOKAHEAD=1'b0,
 parameter logic [31:0] SESSION_LIMIT=32'hffffffe0,
 parameter logic [15:0] A_GENERATION_LIMIT=16'hffff,W_GENERATION_LIMIT=16'hffff
)(
 input logic clk,reset,
 input logic scope_valid,output logic scope_ready,input logic scope_end,scope_cancel,
 input logic [127:0] scope_owner,input logic [1023:0] scope_data,
 input logic record_valid,output logic record_ready,input logic [31:0] record_sequence,
 input logic [127:0] record_owner,input logic [63:0] record_address,
 input logic [15:0] record_full_k,record_k,input logic [31:0] record_col,
 input logic [3:0] record_context,record_n,input logic record_way,record_head16,
 input logic record_create,record_restore,record_final,record_spill,record_A_first,record_A_last,
 input logic [4:0] record_A_uses,
 output logic complete_valid,input logic complete_ready,output logic [127:0] complete_owner,
 output logic [31:0] complete_sequence,output logic [3:0] complete_context,
 output logic [15:0] complete_next_k,output logic complete_error,

 // Header/window admission and actual COPY progress have distinct owners.
 // A new header is insufficient to relabel an old same-key prefix.
 input logic stream_window_valid,input logic [127:0] stream_window_key,
 input logic [15:0] stream_window_generation,stream_window_k_elements,
 input logic [31:0] stream_window_session,stream_window_ticket,
 input logic copy_progress_valid,input logic [15:0] copy_progress_generation,
 input logic [31:0] copy_progress_session,copy_progress_ticket,
 input logic [15:0] copy_progress_k_elements,
 output logic a_load_proof_valid,input logic a_load_proof_ready,
 output logic [127:0] a_load_proof_key,output logic [15:0] a_load_proof_window_generation,
 output logic [31:0] a_load_proof_window_session,a_load_proof_window_ticket,
 output logic [15:0] a_load_proof_k_elements,a_load_proof_A_generation,
 output logic a_load_proof_A_slot,a_load_proof_error,output logic [5:0] a_load_proof_shift,
 output logic a_source_reads_drained,
 input logic [127:0] copy_key,input logic [10:0] copy_committed_prefix,
 output logic [127:0] scale_lookup_key,output logic [15:0] scale_lookup_kk,
 input logic scale_lookup_valid,input logic [5:0] scale_lookup_shift,
 output logic ar_valid,input logic ar_ready,output logic [9:0] ar_address,output logic [31:0] ar_tag,
 input logic ar_rsp_valid,output logic ar_rsp_ready,input logic [31:0] ar_rsp_tag,input logic [127:0] ar_rsp_data,
 output logic sw_valid,input logic sw_ready,output logic [511:0] sw_ticket,
 output logic sw_word,output logic [9:0] sw_address,output logic [127:0] sw_data,
 input logic sw_ack_valid,output logic sw_ack_ready,input logic [511:0] sw_ack_ticket,
 input logic sw_ack_word,sw_ack_error,
 output logic lc_valid,input logic lc_ready,output logic lc_sop,lc_eop,output logic [127:0] lc_data,
 input logic lr_valid,output logic lr_ready,input logic lr_sop,lr_eop,input logic [127:0] lr_data,
 output logic a_valid,input logic a_ready,output logic [255:0] a_data,
 output logic [31:0] a_session,output logic [2:0] a_beat,
 output logic quiescent,quarantine,output logic [31:0] protocol_faults,
 output logic [31:0] confirmed_weight_read_bytes,confirmed_result_write_bytes,
 output logic [1:0] A_live,result_occupied,command_occupied
);
 typedef enum logic [4:0] {IDLE,BEGIN_SEND,BEGIN_WAIT,CTX_PUSH,CTX_ISSUE,CTX_WAIT,
   ALLOC_SEND,ALLOC_WAIT,FILL_WAIT,W_JOIN,EXEC_PUSH,EXEC_ISSUE,A_START,EXEC_WAIT,
   A_CLOSE,A_RELEASE,CANCEL_FLUSH,COMPLETE,QUARANTINE,FENCE_SEND,FENCE_WAIT,FENCE_REARM,
   CANCEL_CTX_PUSH,CANCEL_CTX_ISSUE,CANCEL_CTX_WAIT,EARLY_HALT,EARLY_CANCEL_SEND,EARLY_CANCEL_WAIT,EARLY_DRAIN_SEND,EARLY_DRAIN_WAIT,PAIR_ACCEPT_SECOND} state_t;
 state_t state;
 logic scope_live,cancelled;logic [15:0] current_window_generation;logic [31:0] current_window_session,current_window_ticket;logic [5:0] current_load_shift;
 logic [127:0] owner;
 logic [31:0] seq_id,col;
 logic [63:0] address;
 logic [15:0] full_k,k;
 logic [3:0] context_id,n,completion_context;
 logic way,head,create,final_record,A_first,A_last;
 logic [4:0] A_uses;
 logic failed,load_pending,record_progressed;
 logic [15:0] contexts_live,context_next_k[16];
 logic [15:0] context_generation[16],A_generation_counter[2],A_use_count[2];
 logic [15:0] current_context_generation,current_A_generation,current_use;
 logic [31:0] next_session,control_session,allocation_session,exec_session;
 logic [1:0] W_bank;
 logic [15:0] W_generation;
 logic allocation_seen,fill_seen,input_seen;
 logic fence_seen,fence_rearm_A;logic [31:0] early_cancel_session,early_drain_session;logic early_cancel_seen,early_drain_seen,early_cancel_live;
 logic [31:0] fence_session,fence_count;
 logic [8:0] fence_epoch;
 logic [15:0] context_wrap_allowed;
 logic [1:0] A_loaded;
 typedef struct packed {
   logic [31:0] seq_id;
   logic [31:0] col;
   logic [63:0] address;
   logic [15:0] full_k;
   logic [15:0] k;
   logic [3:0] context_id;
   logic [3:0] n;
   logic [3:0] completion_context;
   logic way;
   logic head;
   logic create;
   logic final_record;
   logic A_first;
   logic A_last;
   logic [4:0] A_uses;
   logic [15:0] current_context_generation;
   logic [15:0] current_A_generation;
   logic [15:0] current_use;
   logic [1:0] W_bank;
   logic [15:0] W_generation;
 } pair_record_t;
 pair_record_t pair_hold;
 logic pair_hold_valid,pair_prep_second,pair_first_pending,pair_detached,pair_abandon;
 // Independently match the older ALLOC/FILL transaction after switching to
 // the younger record. W payload stays solely in the existing four M banks.
 logic [31:0] saved_allocation_session;
 logic saved_fill_seen;
 wire saved_waiting_fill=pair_hold_valid&&!saved_fill_seen&&
      (pair_prep_second||pair_first_pending||state==PAIR_ACCEPT_SECOND);
 logic [31:0] pair_retire_session,pair_retire_sequence;
 logic [3:0] pair_retire_context;
 logic [15:0] maximum_W_generation;
 // Entries contain range metadata and returned W bank identity only. The
 // record stream remains ordered. All A/EXEC/result owners are still the
 // existing executor/guard, and all W payload is still M's four banks.
 typedef struct packed {
   logic [31:0] seq_id,col;
   logic [63:0] address;
   logic [15:0] full_k,k;
   logic [3:0] ctx,n;
   logic way,head,create,restore,fin,spill,A_first,A_last;
   logic [4:0] A_uses;
 } queued_record_t;
 queued_record_t ahead[2];
 logic [1:0] ahead_live,ahead_sent,ahead_allocated,ahead_filled;
 logic ahead_head,ahead_tail,ahead_offer,ahead_index;
 logic [31:0] ahead_session[2];
 logic [15:0] ahead_context_generation[2],ahead_W_generation[2];
 logic [1:0] ahead_W_bank[2];
 logic front_record_ready;
 wire replay_live=FOUR_BANK_LOOKAHEAD&&ahead_live[ahead_head];
 wire replay_prepared=replay_live&&ahead_filled[ahead_head];
 wire replay_unoffered=replay_live&&!ahead_sent[ahead_head]&&
      !(ahead_offer&&ahead_index==ahead_head);
 wire front_record_valid=replay_live?(replay_prepared||((cancelled||scope_cancel)&&replay_unoffered)):record_valid;
 wire [127:0] front_record_owner=replay_live?owner:record_owner;
 wire [31:0] front_record_sequence=replay_live?ahead[ahead_head].seq_id:record_sequence;
 wire [31:0] front_record_col=replay_live?ahead[ahead_head].col:record_col;
 wire [63:0] front_record_address=replay_live?ahead[ahead_head].address:record_address;
 wire [15:0] front_record_full_k=replay_live?ahead[ahead_head].full_k:record_full_k;
 wire [15:0] front_record_k=replay_live?ahead[ahead_head].k:record_k;
 wire [3:0] front_record_context=replay_live?ahead[ahead_head].ctx:record_context;
 wire [3:0] front_record_n=replay_live?ahead[ahead_head].n:record_n;
 wire front_record_way=replay_live?ahead[ahead_head].way:record_way;
 wire front_record_head16=replay_live?ahead[ahead_head].head:record_head16;
 wire front_record_create=replay_live?ahead[ahead_head].create:record_create;
 wire front_record_restore=replay_live?ahead[ahead_head].restore:record_restore;
 wire front_record_final=replay_live?ahead[ahead_head].fin:record_final;
 wire front_record_spill=replay_live?ahead[ahead_head].spill:record_spill;
 wire front_record_A_first=replay_live?ahead[ahead_head].A_first:record_A_first;
 wire front_record_A_last=replay_live?ahead[ahead_head].A_last:record_A_last;
 wire [4:0] front_record_A_uses=replay_live?ahead[ahead_head].A_uses:record_A_uses;
 wire ahead_can_admit=FOUR_BANK_LOOKAHEAD&&!reset&&scope_live&&!cancelled&&!scope_cancel&&
      !(!replay_live&&front_record_ready)&&
      !ahead_live[ahead_tail]&&(pair_prep_second||pair_first_pending||pair_detached)&&
      record_owner==owner&&record_k==k&&record_full_k==full_k&&
      !record_create&&!record_A_first&&!record_restore&&!record_spill&&
      record_n>=1&&record_n<=8&&contexts_live[record_context]&&
      maximum_W_generation+17'd4<{1'b0,W_GENERATION_LIMIT}&&next_session<SESSION_LIMIT-32'd16;
 assign record_ready=ahead_can_admit||(!replay_live&&front_record_ready);
 wire ahead_push=record_valid&&ahead_can_admit;
 wire ahead_pop=front_record_valid&&front_record_ready&&replay_live;
 logic ahead_find,ahead_choice;
 always_comb begin
   ahead_find=0;ahead_choice=ahead_head;
   if(ahead_live[ahead_head]&&!ahead_sent[ahead_head])begin ahead_find=1;ahead_choice=ahead_head;end
   else if(ahead_live[!ahead_head]&&!ahead_sent[!ahead_head])begin ahead_find=1;ahead_choice=!ahead_head;end
 end
 logic [15:0] pair_retire_next_k;
 logic pair_retire_final;
 wire pair_candidate=scope_data[48+:16]==2&&current_use[0]&&current_use<{11'd0,A_uses};
 wire pair_second_shape=front_record_full_k==full_k&&front_record_k==k&&front_record_create==create&&!front_record_A_first&&
      front_record_A_last==(current_use+16'd1=={11'd0,A_uses})&&front_record_A_uses==A_uses&&
      front_record_final==final_record&&!front_record_restore&&!front_record_spill&&front_record_n>=1&&front_record_n<=8&&
      front_record_context!=context_id&&front_record_head16==head;

 wire early_halt=state==EARLY_HALT||state==EARLY_CANCEL_SEND||state==EARLY_CANCEL_WAIT||state==EARLY_DRAIN_SEND||state==EARLY_DRAIN_WAIT;
 wire selected_A_slot=k[7];
 wire [15:0] selected_kk={7'd0,k[15:7]};
 wire [127:0] input_key=scope_data[128+:128];
 wire [31:0] object_base=way?scope_data[288+:32]:scope_data[256+:32];
 wire [127:0] rf_owner={input_key[127:64],object_base+(col>>3),scope_data[320+:32]};
 // Exact range context convention avoids a variable integer divider in LC.
 wire [5:0] local_group={2'd0,context_id}-{2'd0,scope_data[600+:4]}-
     (way?{1'd0,scope_data[592+:5]}:6'd0);
 wire [31:0] output_word={16'd0,(way?scope_data[704+:16]:scope_data[688+:16])}+({26'd0,local_group}<<1);

 // A physical 256B staging window can represent any global K128 tile.
 // The global K remains in A/M tags and scale lookup; only S addressing is local.
 wire [31:0] input_word={16'd0,scope_data[672+:16]};
 wire first_window_match=stream_window_valid&&stream_window_key==input_key&&
     stream_window_generation!=0&&stream_window_k_elements==front_record_k;
 wire current_window_match=stream_window_valid&&stream_window_key==input_key&&
     stream_window_generation==current_window_generation&&stream_window_k_elements==k&&
     stream_window_session==current_window_session&&stream_window_ticket==current_window_ticket;
 wire progress_matches=current_window_match&&copy_progress_valid&&copy_key==input_key&&
     copy_progress_generation==current_window_generation&&copy_progress_k_elements==k&&
     copy_progress_session==current_window_session&&copy_progress_ticket==current_window_ticket;
 wire [10:0] effective_copy_prefix=progress_matches?copy_committed_prefix:11'd0;
 assign scale_lookup_key=input_key;
 assign scale_lookup_kk=k; // Directory uses K-element offset, M/A identity uses tile index.
 assign scope_ready=!reset&&!scope_live&&quiescent;
 wire A_namespace_needed=front_record_A_first&&A_generation_counter[front_record_k[7]]>=A_GENERATION_LIMIT;
 wire namespace_needed=next_session>=SESSION_LIMIT||maximum_W_generation>=W_GENERATION_LIMIT||
     A_namespace_needed||(front_record_create&&context_generation[front_record_context]==16'hffff&&!context_wrap_allowed[front_record_context]);
 assign front_record_ready=!reset&&scope_live&&front_record_owner==owner&&
     ((state==IDLE&&(!namespace_needed||replay_prepared||cancelled||scope_cancel)&&(!front_record_A_first||first_window_match||cancelled||scope_cancel))||
      (state==PAIR_ACCEPT_SECOND&&!cancelled&&!scope_cancel&&pair_second_shape&&(!namespace_needed||replay_prepared)));
 wire pair_terminal_match=pair_detached&&g_terminal_ticket[31:0]==pair_retire_session&&
      g_terminal_ticket[63:32]==pair_retire_sequence&&g_terminal_ticket[511:384]==owner;
 wire pair_terminal_valid=pair_terminal_match&&g_terminal_valid;
 wire pair_retiring=pair_terminal_valid||pair_abandon;
 assign complete_valid=!reset&&(pair_retiring||(!pair_detached&&state==COMPLETE));
 assign complete_owner=owner;
 assign complete_sequence=pair_retiring?pair_retire_sequence:seq_id;
 assign complete_context=pair_retiring?pair_retire_context:completion_context;
 assign complete_next_k=pair_retiring?pair_retire_next_k:(k+(record_progressed?16'd128:16'd0));
 assign complete_error=pair_retiring?(pair_abandon||g_terminal_error!=0):failed;
 assign quarantine=state==QUARANTINE;
 assign quiescent=state==IDLE&&ahead_live==0&&!ahead_offer&&!pair_hold_valid&&!pair_detached&&!pair_abandon&&contexts_live==0&&A_live==0&&guard_quiescent&&af_quiescent&&af_drained;
 logic af_cmd_ready,af_load_valid,af_load_ready,af_load_slot,af_load_error;
 logic [15:0] af_load_gen;
 logic [127:0] af_load_key;
 logic af_w_ready,af_use_ready,af_close_ready,af_release_ready;
 logic [127:0] af_a_key;
 logic af_a_slot;
 logic [15:0] af_a_gen,af_a_kk,af_a_use;
 logic [31:0] af_a_record,af_faults;
 logic [5:0] af_shift;
 logic af_quiescent,af_drained,af_abort_ready,af_rearm_ready;
 wire af_halt=state==CANCEL_FLUSH||state==FENCE_REARM||early_halt;
 wire af_flush=state==CANCEL_FLUSH&&af_quiescent&&af_drained&&guard_quiescent;
 private_a_scaled_fenced_frontend A_front(
   .clk,.reset,.halt(af_halt),.flush(af_flush),
   .rearm_valid(state==FENCE_REARM&&fence_rearm_A),.rearm_ready(af_rearm_ready),.rearm_epoch(fence_count),
   .abort_valid(1'b0),.abort_ready(af_abort_ready),.abort_transport_drained(1'b0),
   .abort_key(128'd0),.abort_slot(1'b0),.abort_generation(16'd0),.abort_kk(16'd0),.abort_use_sequence(16'd0),
   .scale_valid(scale_lookup_valid),.scale_key(input_key),.scale_kk(selected_kk),.scale_shift(scale_lookup_shift),.a_shift(af_shift),
   .cmd_valid(load_pending),.cmd_ready(af_cmd_ready),.cmd_slot(selected_A_slot),
   .cmd_generation(current_A_generation),.cmd_kk(selected_kk),.cmd_planned_uses({11'd0,A_uses}),
   .cmd_key(input_key),.cmd_S_base(input_word[9:0]),.cmd_copy_offset(10'd0),
   .copy_key,.copy_committed_prefix(effective_copy_prefix),
   .load_done_valid(af_load_valid),.load_done_ready(af_load_ready),.load_done_slot(af_load_slot),.load_done_error(af_load_error),
   .load_done_generation(af_load_gen),.load_done_key(af_load_key),
   .s_valid(ar_valid),.s_ready(ar_ready),.s_address(ar_address),.s_tag(ar_tag),
   .response_valid(ar_rsp_valid),.response_ready(ar_rsp_ready),.response_tag(ar_rsp_tag),.response_data(ar_rsp_data),
   .w_valid(state==W_JOIN),.w_ready(af_w_ready),.w_slot(selected_A_slot),.w_generation(current_A_generation),
   .w_kk(selected_kk),.w_use_sequence(current_use),.w_key(input_key),.w_record(seq_id),
   .use_valid(issue_use_valid),.use_ready(af_use_ready),.use_slot(issue_use_slot),.use_generation(issue_use_gen),
   .use_kk(issue_use_kk),.use_sequence(issue_use_sequence),.use_key(issue_use_key),
   .a_valid,.a_ready,.a_data,.a_step(a_beat),.a_weight_record(af_a_record),.a_key(af_a_key),
   .a_slot(af_a_slot),.a_generation(af_a_gen),.a_kk(af_a_kk),.a_use_sequence(af_a_use),
   .close_valid(state==A_CLOSE),.close_ready(af_close_ready),.close_slot(selected_A_slot),.close_generation(current_A_generation),
   .release_valid(state==A_RELEASE),.release_ready(af_release_ready),.release_slot(selected_A_slot),.release_generation(current_A_generation),
   .quiescent(af_quiescent),.source_reads_drained(af_drained),.live_slots(A_live),.fault_cycles(af_faults)
 );

 // No new payload or receipt FIFO. The existing frontend retains its one
 // LOAD receipt under backpressure, along with these current-record registers.
 assign a_load_proof_valid=!reset&&af_load_valid&&!fatal_load&&af_drained;
 assign af_load_ready=fatal_load||(a_load_proof_ready&&af_drained);
 assign a_load_proof_key=af_load_key;
 assign a_load_proof_window_generation=current_window_generation;
 assign a_load_proof_window_session=current_window_session;
 assign a_load_proof_window_ticket=current_window_ticket;
 assign a_load_proof_k_elements=k;
 assign a_load_proof_A_generation=af_load_gen;
 assign a_load_proof_A_slot=af_load_slot;
 assign a_load_proof_error=af_load_error;
 assign a_load_proof_shift=current_load_shift;
 assign a_source_reads_drained=af_drained;
 assign a_session=issue_use_session;
 logic g_cmd_valid,g_cmd_ready,g_terminal_valid,g_terminal_ready;
 logic [511:0] g_terminal_ticket,g_input_ticket,g_abort_ticket;
 logic [7:0] g_terminal_error;
 logic [255:0] g_terminal_data;
 logic issue_use_valid,issue_use_slot,issue_tx_fault,g_abort_error;
 logic [127:0] issue_use_key;
 logic [15:0] issue_use_gen,issue_use_kk,issue_use_sequence;
 logic [31:0] issue_use_record,issue_use_session;
 logic side_valid,side_ready,side_sop,side_eop;
 logic [127:0] side_data;
 logic ctx_ack;
 logic g_terminal_stored,g_terminal_partial,g_input_valid,g_input_error,g_abort_valid;
 logic [15:0] g_abort_next;
 logic control_valid,control_sop,control_eop;
 logic [127:0] control_data;
 logic guard_halted,guard_quarantine,guard_quiescent,g_cancel_ready,g_cancel_one_ready;
 logic [31:0] g_rejected,g_committed;
 logic [31:0] committed_scope_base;
 assign confirmed_result_write_bytes=(g_committed-committed_scope_base)<<4;
 logic [255:0] expected_payload;
 logic [511:0] command_ticket;
 wire cleanup_command=state==CANCEL_CTX_PUSH||state==CANCEL_CTX_ISSUE||state==CANCEL_CTX_WAIT;
 wire ctx_command=state==CTX_PUSH||state==CTX_ISSUE||state==CTX_WAIT||cleanup_command;
 logic cleanup_found;
 logic [3:0] cleanup_context;
 always_comb begin
   cleanup_found=0;cleanup_context=0;
   for(integer i=0;i<16;i=i+1)if(contexts_live[i]&&!cleanup_found)begin cleanup_found=1;cleanup_context=4'(i);end
 end
 wire [4:0] cleanup_offset={1'b0,cleanup_context}-{1'b0,scope_data[600+:4]};
 wire cleanup_way=cleanup_offset>=scope_data[592+:5];
 wire [4:0] cleanup_group=cleanup_offset-(cleanup_way?scope_data[592+:5]:5'd0);
 wire [31:0] cleanup_col=scope_data[544+:32]+({27'd0,cleanup_group}*{16'd0,scope_data[576+:16]});
 always_comb begin
   expected_payload=0;
   expected_payload[0+:32]=next_session;
   expected_payload[32+:32]=ctx_command?32'd0:seq_id;
   expected_payload[64+:32]=next_session;
   expected_payload[96+:4]=context_id;expected_payload[100+:4]=n;
   expected_payload[104+:8]=head?8'd16:8'd128;
   expected_payload[112+:16]=ctx_command?(cleanup_command?context_next_k[context_id]:16'd0):k+16'd128;
   expected_payload[128+:16]=full_k;
   if(cleanup_command)expected_payload[211+:3]=4;
   if(!ctx_command)begin
     expected_payload[144+:2]=W_bank;expected_payload[146+:16]=W_generation;
     expected_payload[162+:16]=current_use;expected_payload[178]=selected_A_slot;
     expected_payload[179+:16]=current_A_generation;expected_payload[195+:16]=selected_kk;
     expected_payload[211+:3]=2;expected_payload[215]=final_record;
     expected_payload[216]=final_record;expected_payload[217]=1;
     expected_payload[233:218]=current_context_generation;expected_payload[239:234]=current_load_shift;
     // A live zero generation is set only after real post-FENCE BEGIN/CTX.
     expected_payload[240]=current_context_generation==0&&contexts_live[context_id];
   end
   command_ticket={owner,rf_owner,input_key,32'h02504d02,owner[31:0],seq_id,next_session};
 end
 assign g_cmd_valid=state==EXEC_PUSH&&!ahead_offer;
 // Native ticket's session remains authoritative after next_session advances.
 wire [511:0] active_exec_ticket={owner,rf_owner,input_key,32'h02504d02,owner[31:0],seq_id,exec_session};
 assign g_terminal_ready=pair_terminal_match?complete_ready:(state==EXEC_WAIT&&g_terminal_ticket==active_exec_ticket);
 m_dual_exec_issue issuer(
   .clk,.reset,.cmd_valid(g_cmd_valid),.cmd_ready(g_cmd_ready),.cmd_ticket(command_ticket),.cmd_job_key(owner),
   .cmd_abi(32'h02500001),.cmd_topology(32'd25001),.cmd_capacity(32'd1),
   .cmd_numeric(32'h53333251),.cmd_layout(32'h4b313633),.cmd_resource(8'd0),.cmd_service(8'd32),
   .cmd_provider(8'd1),.cmd_function(8'd0),.cmd_native_op(16'd0),.cmd_payload(expected_payload),
   .cmd_stored(!ctx_command&&final_record),.cmd_store_words((!ctx_command&&final_record)?2'd2:2'd0),.cmd_destination(output_word[9:0]),
   .a_use_valid(issue_use_valid),.a_use_ready(af_use_ready),.a_use_key(issue_use_key),.a_use_slot(issue_use_slot),
   .a_use_generation(issue_use_gen),.a_use_kk(issue_use_kk),.a_use_sequence(issue_use_sequence),
   .a_use_record(issue_use_record),.a_use_session(issue_use_session),
   .side_valid,.side_ready,.side_sop,.side_eop,.side_data,.lc_valid,.lc_ready,.lc_sop,.lc_eop,.lc_data,.tx_fault_valid(issue_tx_fault),
   .lr_valid,.lr_ready,.lr_sop,.lr_eop,.lr_data,
   .input_consumed_valid(g_input_valid),.input_consumed_ready(1'b1),.input_consumed_ticket(g_input_ticket),.input_consumed_error(g_input_error),
   .native_abort_valid(g_abort_valid),.native_abort_ready(1'b0),.native_abort_ticket(g_abort_ticket),.native_abort_next_k(g_abort_next),.native_abort_error(g_abort_error),
   .control_valid,.control_ready(1'b1),.control_sop,.control_eop,.control_data,
   .cancel_drained_valid(1'b0),.cancel_drained_ready(g_cancel_ready),.cancel_drained_ticket(512'd0),
   .s_valid(sw_valid),.s_ready(sw_ready),.s_ticket(sw_ticket),.s_word(sw_word),.s_address(sw_address),.s_data(sw_data),
   .ack_valid(sw_ack_valid),.ack_ready(sw_ack_ready),.ack_ticket(sw_ack_ticket),.ack_word(sw_ack_word),.ack_error(sw_ack_error),
   .terminal_valid(g_terminal_valid),.terminal_ready(g_terminal_ready),.terminal_ticket(g_terminal_ticket),
   .terminal_error(g_terminal_error),.terminal_stored(g_terminal_stored),.terminal_partial(g_terminal_partial),.terminal_data(g_terminal_data),
   .cancel_valid(1'b0),.cancel_job_key(128'd0),.timeout_valid(1'b0),.clear_quarantine(1'b0),.resume_after_drain(1'b0),
   .cancel_one_valid(1'b0),.cancel_one_ready(g_cancel_one_ready),.cancel_one_ticket(512'd0),
   .halted(guard_halted),.quarantine(guard_quarantine),.quiescent(guard_quiescent),
   .occupied_slots(command_occupied),.result_slots_occupied(result_occupied),.rejected_protocol_events(g_rejected),.committed_words(g_committed)
 );
 logic tx_cmd_valid,tx_cmd_ready,tx_done,tx_payload_ready,tx_reject_valid;
 assign tx_cmd_ready=tx_done&&!ahead_offer;
 logic [7:0] tx_reject_status;
 logic [3:0] tx_opcode;
 logic [2:0] tx_word;
 logic [127:0] tx_payload;
 always_comb begin
   tx_cmd_valid=0;tx_opcode=0;tx_payload=0;
   case(state)
     BEGIN_SEND:begin
       tx_cmd_valid=1;tx_opcode=1;
       case(tx_word)
         1:tx_payload=input_key;
         2:tx_payload=rf_owner;
         3:begin tx_payload[15:0]=full_k;tx_payload[19:16]=n;tx_payload[20]=head;end
         7:tx_payload={64'd0,32'h4b313633,32'h53333251};
         default:tx_payload=0;
       endcase
     end
     CTX_ISSUE,CANCEL_CTX_ISSUE:begin tx_cmd_valid=1;tx_opcode=4;end
     ALLOC_SEND:begin tx_cmd_valid=1;tx_opcode=2;tx_payload={64'd0,address};end
     EARLY_CANCEL_SEND:begin tx_cmd_valid=1;tx_opcode=6;end
     EARLY_DRAIN_SEND:begin tx_cmd_valid=1;tx_opcode=7;end
     FENCE_SEND:begin tx_cmd_valid=1;tx_opcode=8;end
     default:begin end
   endcase
   if(ahead_offer)begin tx_cmd_valid=1;tx_opcode=2;tx_payload={64'd0,ahead[ahead_index].address};end
 end
 m_short_command_tx tx(
   .clk,.reset,.cmd_valid(tx_cmd_valid),.cmd_ready(tx_done),.cmd_opcode(tx_opcode),.cmd_scope(ahead_offer?ahead[ahead_index].ctx:(state==FENCE_SEND?4'd0:context_id)),
   .cmd_scope_generation(ahead_offer?ahead_context_generation[ahead_index]:(state==FENCE_SEND?16'd0:current_context_generation)),.cmd_high16(ahead_offer?16'd0:((state==EARLY_CANCEL_SEND||state==EARLY_DRAIN_SEND)?W_generation:(cleanup_command?16'd4:16'd0))),.cmd_session(next_session),
   .cmd_record(ahead_offer?ahead[ahead_index].seq_id:((state==BEGIN_SEND||state==CTX_ISSUE||state==CANCEL_CTX_ISSUE||state==FENCE_SEND)?32'd0:seq_id)),.cmd_bank((!ahead_offer&&(state==EARLY_CANCEL_SEND||state==EARLY_DRAIN_SEND))?W_bank:2'd0),.word_index(tx_word),
   .payload_valid(1'b1),.payload_ready(tx_payload_ready),.payload_data(tx_payload),
   .lc_valid(side_valid),.lc_ready(side_ready),.lc_sop(side_sop),.lc_eop(side_eop),.lc_data(side_data),.reject_valid(tx_reject_valid),.reject_ready(1'b1),.reject_status(tx_reject_status)
 );
 // Control frames go directly from product M through the guard; only their
 // two-word identity metadata is retained. No assembly/data response FIFO.
 logic control_body,control_drop;
 logic [7:0] control_event;
 logic [31:0] control_rx_session,control_rx_record;
 logic begin_ack;
 wire control_header_ok=control_data[31:0]==32'h02504d02&&control_data[47:40]==0&&control_data[127:112]==16'h2000;
 wire unowned_transport_fault=control_sop&&!control_eop&&control_data[31:0]==32'h02504d02&&
     control_data[39:32]==7&&control_data[47:40]>=13&&control_data[47:40]<=15&&
     control_data[111:48]==0&&control_data[127:112]==16'h3000;
 wire ctx_response_header=control_sop&&!control_eop&&control_data[31:0]==32'h02504d02&&control_data[39:32]==4&&
     control_data[47:40]==0&&control_data[79:48]==control_session&&control_data[111:80]==0&&
     control_data[127:112]=={4'd2,1'b0,(cleanup_command?3'd4:3'd0),context_id,4'd0}&&
     (state==CTX_WAIT||state==CANCEL_CTX_WAIT);
 wire ctx_body_ok=control_event==4&&control_rx_session==control_session&&control_rx_record==0&&
     control_data=={48'd0,control_session,full_k,(cleanup_command?context_next_k[context_id]:16'd0),
                   (head?8'd16:8'd128),n,context_id};
 wire ordinary_control_header=ctx_response_header||control_sop&&!control_eop&&control_header_ok&&
     (control_data[39:32]==1||control_data[39:32]==2||control_data[39:32]==10||control_data[39:32]==8||control_data[39:32]==9||control_data[39:32]==6);
 wire begin_body_ok=control_event==10&&control_rx_session==control_session&&control_rx_record==0&&control_data==0;
 wire allocation_body_ok=control_event==1&&control_rx_session==allocation_session&&control_rx_record==seq_id&&
     control_data[21:18]==context_id&&control_data[37:22]==current_context_generation&&control_data[127:38]==0;
 wire fill_body_ok=control_event==2&&control_rx_session==allocation_session&&control_rx_record==seq_id&&allocation_seen&&
     control_data[1:0]==W_bank&&control_data[17:2]==W_generation&&control_data[127:18]==0;
 wire saved_fill_body_ok=control_event==2&&saved_waiting_fill&&
     control_rx_session==saved_allocation_session&&control_rx_record==pair_hold.seq_id&&
     control_data[1:0]==pair_hold.W_bank&&control_data[17:2]==pair_hold.W_generation&&control_data[127:18]==0;
 wire current_fill_fire=control_valid&&control_body&&!control_sop&&control_eop&&fill_body_ok;
 wire saved_fill_fire=control_valid&&control_body&&!control_sop&&control_eop&&saved_fill_body_ok;
 wire fence_body_ok=control_event==8&&state==FENCE_WAIT&&control_rx_session==fence_session&&control_rx_record==0&&
     control_data[8:0]==fence_epoch+9'd1&&control_data[127:9]==0;

 wire early_cancel_body_ok=control_event==9&&state==EARLY_CANCEL_WAIT&&control_rx_session==early_cancel_session&&control_rx_record==seq_id&&control_data==0;
 wire early_drain_body_ok=control_event==6&&state==EARLY_DRAIN_WAIT&&control_rx_session==early_drain_session&&control_rx_record==seq_id&&
     control_data[1:0]==W_bank&&control_data[17:2]==W_generation&&control_data[127:18]==0;
 logic ahead_alloc_ok,ahead_fill_ok,ahead_match;
 always_comb begin
   ahead_alloc_ok=0;ahead_fill_ok=0;ahead_match=0;
   for(integer j=0;j<2;j=j+1)if(ahead_live[j]&&ahead_sent[j]&&
        control_rx_session==ahead_session[j]&&control_rx_record==ahead[j].seq_id)begin
     if(control_event==1&&!ahead_allocated[j]&&control_data[21:18]==ahead[j].ctx&&
        control_data[37:22]==ahead_context_generation[j]&&control_data[127:38]==0)begin
       ahead_alloc_ok=1;ahead_match=1'(j);
     end
     if(control_event==2&&ahead_allocated[j]&&!ahead_filled[j]&&control_data[1:0]==ahead_W_bank[j]&&
        control_data[17:2]==ahead_W_generation[j]&&control_data[127:18]==0)begin
       ahead_fill_ok=1;ahead_match=1'(j);
     end
   end
 end
 wire ahead_control_fire=control_valid&&control_body&&!control_drop&&!control_sop&&control_eop;
 // Do not issue a new side frame once an EXEC session is reserved. An
 // already offered side frame retains its payload/session to its true EOP.
 wire ahead_can_offer=FOUR_BANK_LOOKAHEAD&&!cancelled&&!scope_cancel&&ahead_find&&
     ((state==IDLE&&!front_record_valid)||(state==FILL_WAIT&&pair_prep_second)||
      state==W_JOIN||state==EXEC_WAIT||state==COMPLETE);
 always_ff @(posedge clk)begin
   if(reset)begin
     ahead_live<=0;ahead_sent<=0;ahead_allocated<=0;ahead_filled<=0;
     ahead_head<=0;ahead_tail<=0;ahead_offer<=0;ahead_index<=0;
     for(integer j=0;j<2;j=j+1)begin
       ahead[j]<='0;ahead_session[j]<=0;ahead_context_generation[j]<=0;
       ahead_W_generation[j]<=0;ahead_W_bank[j]<=0;
     end
   end else if(FOUR_BANK_LOOKAHEAD)begin
     if(ahead_push)begin
       ahead[ahead_tail]<='{record_sequence,record_col,record_address,record_full_k,record_k,
          record_context,record_n,record_way,record_head16,record_create,record_restore,
          record_final,record_spill,record_A_first,record_A_last,record_A_uses};
       ahead_live[ahead_tail]<=1;ahead_sent[ahead_tail]<=0;ahead_allocated[ahead_tail]<=0;ahead_filled[ahead_tail]<=0;
       ahead_context_generation[ahead_tail]<=context_generation[record_context];
       ahead_tail<=!ahead_tail;
     end
     if(ahead_pop)begin ahead_live[ahead_head]<=0;ahead_head<=!ahead_head;end
     if(!ahead_offer&&ahead_can_offer)begin ahead_offer<=1;ahead_index<=ahead_choice;end
     else if(ahead_offer&&tx_done)begin
       ahead_offer<=0;ahead_sent[ahead_index]<=1;ahead_session[ahead_index]<=next_session;
     end
     if(ahead_control_fire&&ahead_alloc_ok)begin
       ahead_allocated[ahead_match]<=1;ahead_W_bank[ahead_match]<=control_data[1:0];
       ahead_W_generation[ahead_match]<=control_data[17:2];
     end
     if(ahead_control_fire&&ahead_fill_ok)ahead_filled[ahead_match]<=1;
   end
 end
 wire fatal_control=control_valid&&!control_drop&&
     (control_body ? (control_sop||!control_eop||!(begin_body_ok||allocation_body_ok||fill_body_ok||saved_fill_body_ok||ahead_alloc_ok||ahead_fill_ok||ctx_body_ok||fence_body_ok||early_cancel_body_ok||early_drain_body_ok)) :
      !(ordinary_control_header||unowned_transport_fault));
 wire fatal_load=af_load_valid&&((af_load_error&&!early_cancel_live)||af_load_slot!=selected_A_slot||
     af_load_gen!=current_A_generation||af_load_key!=input_key);
 wire fatal_input=g_input_valid&&(g_input_ticket!=active_exec_ticket||g_input_error);
 wire fatal_terminal=g_terminal_valid&&g_terminal_ready&&
     (g_terminal_error!=0||(pair_terminal_match?(pair_retire_final!=g_terminal_stored):
       (state==EXEC_WAIT&&(!input_seen||(final_record&&!g_terminal_stored)))));
 wire fatal_operand=a_valid&&a_ready&&
     (af_a_key!=input_key||af_a_slot!=selected_A_slot||af_a_gen!=current_A_generation||
      af_a_kk!=selected_kk||af_a_use!=current_use||af_a_record!=seq_id||
      af_shift!=current_load_shift);
 always_ff @(posedge clk)begin
   if(reset)begin
     pair_hold<='0;saved_allocation_session<=0;saved_fill_seen<=0;pair_hold_valid<=0;pair_prep_second<=0;pair_first_pending<=0;pair_detached<=0;pair_abandon<=0;
     pair_retire_session<=0;pair_retire_sequence<=0;pair_retire_context<=0;pair_retire_next_k<=0;pair_retire_final<=0;maximum_W_generation<=0;
     early_cancel_live<=0;early_cancel_session<=0;early_drain_session<=0;early_cancel_seen<=0;early_drain_seen<=0;current_window_generation<=0;current_window_session<=0;current_window_ticket<=0;current_load_shift<=0;state<=IDLE;scope_live<=0;cancelled<=0;owner<=0;seq_id<=0;col<=0;address<=0;full_k<=0;k<=0;
     context_id<=0;n<=0;completion_context<=0;way<=0;head<=0;create<=0;final_record<=0;A_first<=0;A_last<=0;A_uses<=0;
     contexts_live<=0;record_progressed<=0;
     failed<=0;load_pending<=0;current_context_generation<=0;current_A_generation<=0;current_use<=0;
     next_session<=1;control_session<=0;allocation_session<=0;exec_session<=0;W_bank<=0;W_generation<=0;
     allocation_seen<=0;fill_seen<=0;input_seen<=0;A_loaded<=0;protocol_faults<=0;
     control_body<=0;control_drop<=0;control_event<=0;control_rx_session<=0;control_rx_record<=0;begin_ack<=0;ctx_ack<=0;
     confirmed_weight_read_bytes<=0;committed_scope_base<=0;
     fence_seen<=0;fence_rearm_A<=0;fence_session<=0;fence_count<=0;fence_epoch<=0;context_wrap_allowed<=0;
     for(integer i=0;i<16;i=i+1)begin context_generation[i]<=0;context_next_k[i]<=0;end
     for(integer i=0;i<2;i=i+1)begin A_generation_counter[i]<=0;A_use_count[i]<=0;end
   end else begin
     if(pair_terminal_valid&&complete_ready)begin
       pair_detached<=0;
       if(g_terminal_error==0)begin
         context_next_k[pair_retire_context]<=pair_retire_next_k;
         if(pair_retire_final)contexts_live[pair_retire_context]<=0;
       end
     end
     if(pair_abandon&&complete_ready)pair_abandon<=0;
     if(scope_valid&&scope_ready)begin
       scope_live<=1;owner<=scope_owner;cancelled<=0;
       confirmed_weight_read_bytes<=0;committed_scope_base<=g_committed;
     end
     if(scope_end&&quiescent)scope_live<=0;
     if(scope_cancel&&scope_live)cancelled<=1;
     if(load_pending&&af_cmd_ready)begin
       current_load_shift<=scale_lookup_shift;load_pending<=0;A_generation_counter[selected_A_slot]<=current_A_generation;
     end
     if(af_load_valid&&af_load_ready)begin
       if(!af_load_error&&af_load_slot==selected_A_slot&&af_load_gen==current_A_generation&&af_load_key==input_key)
         A_loaded[selected_A_slot]<=1;
       else if(!(early_cancel_live&&af_load_error&&af_load_slot==selected_A_slot&&af_load_gen==current_A_generation&&af_load_key==input_key))begin state<=QUARANTINE;protocol_faults<=protocol_faults+1'b1;end
     end
     if(g_input_valid)begin
       if(g_input_ticket==active_exec_ticket&&!g_input_error)input_seen<=1;
       else begin state<=QUARANTINE;protocol_faults<=protocol_faults+1'b1;end
     end
     if((tx_cmd_valid&&tx_done)||(g_cmd_valid&&g_cmd_ready))begin
       if(next_session==32'hffffffff)begin state<=QUARANTINE;protocol_faults<=protocol_faults+1'b1;end
       else next_session<=next_session+1'b1;
     end
     if(control_valid)begin
       if(control_drop)begin if(control_eop)control_drop<=0;end
       else if(!control_body)begin
         if(unowned_transport_fault)begin
           // A stale transport return is not attributed to the current W/A
           // owner. Drain its diagnostic frame without releasing that owner.
           control_drop<=1;protocol_faults<=protocol_faults+1'b1;
         end else if(ordinary_control_header)begin
           control_body<=1;control_event<=control_data[39:32];
           control_rx_session<=control_data[79:48];control_rx_record<=control_data[111:80];
         end else begin control_drop<=!control_eop;protocol_faults<=protocol_faults+1'b1;state<=QUARANTINE;end
       end else begin
         control_body<=0;
         if(control_sop||!control_eop)begin control_drop<=!control_eop;protocol_faults<=protocol_faults+1'b1;state<=QUARANTINE;end
         else if(begin_body_ok)begin_ack<=1;
         else if(ctx_body_ok)ctx_ack<=1;
         else if(allocation_body_ok)begin
           W_bank<=control_data[1:0];W_generation<=control_data[17:2];allocation_seen<=1;
           if(control_data[17:2]>maximum_W_generation)maximum_W_generation<=control_data[17:2];
         end else if(ahead_alloc_ok)begin
           if(control_data[17:2]>maximum_W_generation)maximum_W_generation<=control_data[17:2];
         end else if(ahead_fill_ok)begin
           confirmed_weight_read_bytes<=confirmed_weight_read_bytes+(ahead[ahead_match].head?32'd1152:32'd1088);
         end else if(fill_body_ok||saved_fill_body_ok)begin
           if(fill_body_ok)fill_seen<=1;
           if(saved_fill_body_ok)saved_fill_seen<=1;
           confirmed_weight_read_bytes<=confirmed_weight_read_bytes+((fill_body_ok?head:pair_hold.head)?32'd1152:32'd1088);
         end
         else if(early_cancel_body_ok)early_cancel_seen<=1;
         else if(early_drain_body_ok)early_drain_seen<=1;
         else if(fence_body_ok)begin fence_seen<=1;fence_epoch<=control_data[8:0];end
         else begin protocol_faults<=protocol_faults+1'b1;state<=QUARANTINE;end
       end
     end
     case(state)
       IDLE:if(front_record_valid&&scope_live&&front_record_owner==owner&&!cancelled&&!scope_cancel&&namespace_needed&&!replay_live&&!ahead_offer&&guard_quiescent&&af_quiescent&&af_drained)begin
         if(fence_count==32'hffffffff)begin state<=QUARANTINE;protocol_faults<=protocol_faults+1'b1;end
         else begin fence_rearm_A<=A_namespace_needed;fence_seen<=0;state<=FENCE_SEND;end
       end else if(front_record_valid&&front_record_ready)begin
         seq_id<=front_record_sequence;col<=front_record_col;address<=front_record_address;full_k<=front_record_full_k;k<=front_record_k;
         context_id<=front_record_context;completion_context<=front_record_context;n<=front_record_n;way<=front_record_way;head<=front_record_head16;create<=front_record_create;
         final_record<=front_record_final;A_first<=front_record_A_first;A_last<=front_record_A_last;A_uses<=front_record_A_uses;
         failed<=0;record_progressed<=0;allocation_seen<=0;fill_seen<=0;input_seen<=0;begin_ack<=0;
         current_context_generation<=context_generation[front_record_context]+(front_record_create?16'd1:16'd0);
         current_A_generation<=A_generation_counter[front_record_k[7]]+(front_record_A_first?16'd1:16'd0);
         current_use<=front_record_A_first?16'd1:A_use_count[front_record_k[7]]+16'd1;
         if(replay_prepared)begin
           // No repeated ALLOC. The returning bank and FILL are exact.
           allocation_session<=ahead_session[ahead_head];W_bank<=ahead_W_bank[ahead_head];
           W_generation<=ahead_W_generation[ahead_head];allocation_seen<=1;fill_seen<=1;
           if(cancelled||scope_cancel)begin early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;end
           else state<=FILL_WAIT;
         end else if(cancelled||scope_cancel)begin failed<=1;state<=CANCEL_FLUSH;end
         else if(front_record_restore||front_record_spill||front_record_n==0||front_record_n>8||front_record_full_k==0||front_record_k[6:0]!=0||
             (front_record_create&&context_generation[front_record_context]==16'hffff&&!context_wrap_allowed[front_record_context]))begin failed<=1;state<=CANCEL_FLUSH;end
         else begin
           if(front_record_A_first)begin current_window_generation<=stream_window_generation;current_window_session<=stream_window_session;current_window_ticket<=stream_window_ticket;A_loaded[front_record_k[7]]<=0;A_use_count[front_record_k[7]]<=0;load_pending<=1;end
           if(front_record_create)state<=BEGIN_SEND;else state<=ALLOC_SEND;
         end
       end
       BEGIN_SEND:if(tx_cmd_valid&&tx_cmd_ready)begin control_session<=next_session;state<=BEGIN_WAIT;end
       BEGIN_WAIT:if(begin_ack)begin
         context_generation[context_id]<=current_context_generation;
         // Only a FENCE newer than entry into generation FFFF can authorize wrap.
         if(current_context_generation==0||current_context_generation==16'hffff)context_wrap_allowed[context_id]<=0;
         state<=CTX_PUSH;
       end
       CTX_PUSH:begin ctx_ack<=0;control_session<=next_session;state<=CTX_ISSUE;end
       CTX_ISSUE:if(tx_cmd_valid&&tx_cmd_ready)state<=CTX_WAIT;
       CTX_WAIT:if(ctx_ack)begin contexts_live[context_id]<=1;context_next_k[context_id]<=0;state<=ALLOC_SEND;end
       ALLOC_SEND:if(tx_cmd_valid&&tx_cmd_ready)begin allocation_session<=next_session;state<=ALLOC_WAIT;end
       ALLOC_WAIT:if(allocation_seen)state<=FILL_WAIT;

       FILL_WAIT:if(cancelled||scope_cancel)begin load_pending<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;end
         else if(!pair_prep_second&&pair_candidate&&maximum_W_generation<W_GENERATION_LIMIT&&next_session<SESSION_LIMIT-32'd8)begin
           // The older ALLOC ACK has returned; its W FILL may still be in
           // flight. This is a second real bank allocation, not early READY.
           pair_hold<='{seq_id,col,address,full_k,k,context_id,n,completion_context,way,head,create,final_record,A_first,A_last,A_uses,current_context_generation,current_A_generation,current_use,W_bank,W_generation};
           pair_hold_valid<=1;saved_allocation_session<=allocation_session;saved_fill_seen<=fill_seen||current_fill_fire;
           state<=PAIR_ACCEPT_SECOND;
         end else if((pair_prep_second?saved_fill_seen:fill_seen)&&A_loaded[selected_A_slot]&&current_load_shift<=17)begin
           if(pair_prep_second)begin
             // Older W is ready. Keep the younger ALLOC owner and its
             // unconsumed FILL receipt while launching the older EXEC.
             pair_hold<='{seq_id,col,address,full_k,k,context_id,n,completion_context,way,head,create,final_record,A_first,A_last,A_uses,current_context_generation,current_A_generation,current_use,W_bank,W_generation};pair_prep_second<=0;pair_first_pending<=1;
             saved_allocation_session<=allocation_session;saved_fill_seen<=fill_seen||current_fill_fire;
             allocation_session<=saved_allocation_session;fill_seen<=1;
           seq_id<=pair_hold.seq_id;
           col<=pair_hold.col;
           address<=pair_hold.address;
           full_k<=pair_hold.full_k;
           k<=pair_hold.k;
           context_id<=pair_hold.context_id;
           n<=pair_hold.n;
           completion_context<=pair_hold.completion_context;
           way<=pair_hold.way;
           head<=pair_hold.head;
           create<=pair_hold.create;
           final_record<=pair_hold.final_record;
           A_first<=pair_hold.A_first;
           A_last<=pair_hold.A_last;
           A_uses<=pair_hold.A_uses;
           current_context_generation<=pair_hold.current_context_generation;
           current_A_generation<=pair_hold.current_A_generation;
           current_use<=pair_hold.current_use;
           W_bank<=pair_hold.W_bank;
           W_generation<=pair_hold.W_generation;
             state<=W_JOIN;
           end else state<=W_JOIN;
         end

       PAIR_ACCEPT_SECOND:if(cancelled||scope_cancel)begin
         // The second offer was never accepted: no second bank or range owner.
         pair_hold_valid<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;
       end else if(front_record_valid&&front_record_ready)begin
         pair_prep_second<=1;seq_id<=front_record_sequence;col<=front_record_col;address<=front_record_address;
         full_k<=front_record_full_k;k<=front_record_k;context_id<=front_record_context;completion_context<=front_record_context;
         n<=front_record_n;way<=front_record_way;head<=front_record_head16;create<=front_record_create;final_record<=front_record_final;
         A_first<=0;A_last<=front_record_A_last;A_uses<=front_record_A_uses;current_use<=current_use+16'd1;
         current_context_generation<=context_generation[front_record_context]+(front_record_create?16'd1:16'd0);
         failed<=0;record_progressed<=0;allocation_seen<=0;fill_seen<=0;input_seen<=0;begin_ack<=0;
         if(replay_prepared)begin
           allocation_session<=ahead_session[ahead_head];W_bank<=ahead_W_bank[ahead_head];
           W_generation<=ahead_W_generation[ahead_head];allocation_seen<=1;fill_seen<=1;state<=FILL_WAIT;
         end else state<=front_record_create?BEGIN_SEND:ALLOC_SEND;
       end else if(front_record_valid&&(namespace_needed||!pair_second_shape))begin
         // Do not skip the first record's actual FILL or A proof on fallback.
         if(fill_seen&&A_loaded[selected_A_slot]&&current_load_shift<=17)begin
           pair_hold_valid<=0;state<=W_JOIN;
         end
       end

       W_JOIN:if(cancelled||scope_cancel)begin load_pending<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;end
         else if(af_w_ready)state<=EXEC_PUSH;
       EXEC_PUSH:if(g_cmd_valid&&g_cmd_ready)begin exec_session<=next_session;state<=EXEC_ISSUE;end
       EXEC_ISSUE:if(issue_use_valid&&af_use_ready)begin A_use_count[selected_A_slot]<=current_use;state<=EXEC_WAIT;end
       EXEC_WAIT:if(pair_first_pending&&g_input_valid&&g_input_ticket==active_exec_ticket&&!g_input_error)begin
         // INPUT EOP terminates operand leases only. Keep result/command owner
         // in guard2 until the actual RF+two S ACKs and range terminal ACK.
         pair_retire_session<=exec_session;pair_retire_sequence<=seq_id;pair_retire_context<=completion_context;
         pair_retire_next_k<=k+16'd128;pair_retire_final<=final_record;
         pair_detached<=1;pair_first_pending<=0;pair_hold_valid<=0;
           seq_id<=pair_hold.seq_id;
           col<=pair_hold.col;
           address<=pair_hold.address;
           full_k<=pair_hold.full_k;
           k<=pair_hold.k;
           context_id<=pair_hold.context_id;
           n<=pair_hold.n;
           completion_context<=pair_hold.completion_context;
           way<=pair_hold.way;
           head<=pair_hold.head;
           create<=pair_hold.create;
           final_record<=pair_hold.final_record;
           A_first<=pair_hold.A_first;
           A_last<=pair_hold.A_last;
           A_uses<=pair_hold.A_uses;
           current_context_generation<=pair_hold.current_context_generation;
           current_A_generation<=pair_hold.current_A_generation;
           current_use<=pair_hold.current_use;
           W_bank<=pair_hold.W_bank;
           W_generation<=pair_hold.W_generation;
         allocation_session<=saved_allocation_session;
         allocation_seen<=1;fill_seen<=saved_fill_seen||saved_fill_fire;
         input_seen<=0;failed<=0;record_progressed<=0;
         state<=(saved_fill_seen||saved_fill_fire)?W_JOIN:FILL_WAIT;
       end else if(g_terminal_valid&&g_terminal_ready&&!pair_terminal_match)begin
         record_progressed<=1;context_next_k[context_id]<=k+16'd128;
         if(final_record)contexts_live[context_id]<=0;
         if(g_terminal_error!=0||!input_seen||(final_record&&!g_terminal_stored))begin failed<=1;state<=QUARANTINE;end
         else if(cancelled||scope_cancel)state<=CANCEL_FLUSH;
         else if(A_last)state<=A_CLOSE;else state<=COMPLETE;
       end
       A_CLOSE:if(af_close_ready)state<=A_RELEASE;
       A_RELEASE:if(af_release_ready)begin A_loaded[selected_A_slot]<=0;state<=COMPLETE;end

       // Complete the one bounded W fetch for exact existing FILL accounting,
       // while cancelled A issues no new reads and drains held requests.
       // No EXEC/ABORT or fake INPUT/RF event is fabricated for this record.
       EARLY_HALT:if(fill_seen)state<=EARLY_CANCEL_SEND;
       EARLY_CANCEL_SEND:if(tx_cmd_valid&&tx_cmd_ready)begin early_cancel_session<=next_session;state<=EARLY_CANCEL_WAIT;end
       EARLY_CANCEL_WAIT:if(early_cancel_seen)state<=EARLY_DRAIN_SEND;
       EARLY_DRAIN_SEND:if(tx_cmd_valid&&tx_cmd_ready)begin early_drain_session<=next_session;state<=EARLY_DRAIN_WAIT;end
       EARLY_DRAIN_WAIT:if(early_drain_seen)begin
         if(pair_hold_valid)begin
           // Both ready W banks are owned. Retire only the actually drained
           // one as error, then issue exact CANCEL/DRAIN for the saved bank.
           pair_abandon<=1;pair_retire_sequence<=seq_id;pair_retire_context<=completion_context;
           pair_retire_next_k<=k;pair_retire_final<=0;
           pair_hold_valid<=0;pair_prep_second<=0;pair_first_pending<=0;
           seq_id<=pair_hold.seq_id;
           col<=pair_hold.col;
           address<=pair_hold.address;
           full_k<=pair_hold.full_k;
           k<=pair_hold.k;
           context_id<=pair_hold.context_id;
           n<=pair_hold.n;
           completion_context<=pair_hold.completion_context;
           way<=pair_hold.way;
           head<=pair_hold.head;
           create<=pair_hold.create;
           final_record<=pair_hold.final_record;
           A_first<=pair_hold.A_first;
           A_last<=pair_hold.A_last;
           A_uses<=pair_hold.A_uses;
           current_context_generation<=pair_hold.current_context_generation;
           current_A_generation<=pair_hold.current_A_generation;
           current_use<=pair_hold.current_use;
           W_bank<=pair_hold.W_bank;
           W_generation<=pair_hold.W_generation;
           allocation_session<=saved_allocation_session;
           allocation_seen<=1;fill_seen<=saved_fill_seen||
               (control_valid&&control_body&&!control_sop&&control_eop&&saved_fill_body_ok);
           early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;
         end else begin failed<=1;state<=CANCEL_FLUSH;end
       end
       CANCEL_FLUSH:if(af_flush)begin
         A_loaded<=0;
         if(cleanup_found)begin
           context_id<=cleanup_context;current_context_generation<=context_generation[cleanup_context];
           way<=cleanup_way;col<=cleanup_col;
           n<=scope_data[512+:32]-cleanup_col<8 ? 4'(scope_data[512+:32]-cleanup_col) : 4'd8;
           state<=CANCEL_CTX_PUSH;
         end else state<=COMPLETE;
       end
       CANCEL_CTX_PUSH:begin ctx_ack<=0;control_session<=next_session;state<=CANCEL_CTX_ISSUE;end
       CANCEL_CTX_ISSUE:if(tx_cmd_valid&&tx_cmd_ready)state<=CANCEL_CTX_WAIT;
       CANCEL_CTX_WAIT:if(ctx_ack)begin contexts_live[context_id]<=0;state<=CANCEL_FLUSH;end
       COMPLETE:if(complete_valid&&complete_ready&&!pair_retiring)begin early_cancel_live<=0;state<=IDLE;end
       FENCE_SEND:if(tx_cmd_valid&&tx_cmd_ready)begin fence_session<=next_session;state<=FENCE_WAIT;end
       FENCE_WAIT:if(fence_seen)begin
         fence_count<=fence_count+1'b1;context_wrap_allowed<=16'hffff;W_generation<=0;maximum_W_generation<=0;next_session<=1;state<=FENCE_REARM;
       end
       FENCE_REARM:if(!fence_rearm_A||af_rearm_ready)begin
         if(fence_rearm_A)begin
           A_generation_counter[0]<=0;A_generation_counter[1]<=0;A_use_count[0]<=0;A_use_count[1]<=0;A_loaded<=0;
         end
         state<=IDLE;
       end
       QUARANTINE:begin end // Cannot fabricate source/M/ACK drain or a completion.
       default:state<=QUARANTINE;
     endcase
     if(fatal_control||fatal_load||fatal_input||fatal_terminal||fatal_operand||tx_reject_valid||issue_tx_fault||g_abort_valid||guard_quarantine||guard_halted)begin
       state<=QUARANTINE;protocol_faults<=protocol_faults+1'b1;
     end
   end
 end
 wire unused_diagnostics=^{create,A_first,af_a_key,af_a_slot,af_a_gen,af_a_kk,af_a_use,af_a_record,af_shift,
   af_faults,af_abort_ready,g_abort_error,g_cancel_one_ready,issue_use_record,
   g_terminal_partial,g_terminal_data,g_abort_ticket,g_abort_next,g_cancel_ready,g_rejected,g_committed,
   tx_payload_ready,tx_reject_status,input_word[31:10],output_word[31:10],scope_data};
endmodule
