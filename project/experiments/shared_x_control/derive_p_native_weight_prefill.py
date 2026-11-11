"""Candidate with real ALLOC overlap; baseline stream profile is left intact."""
from pathlib import Path

rtl = Path(__file__).parent / "rtl"
source = (rtl / "p_native_stream_m2_bounded.sv").read_text(encoding="utf-8")


def edit(old, new):
    global source
    assert source.count(old) == 1, old
    source = source.replace(old, new)


edit("module p_native_stream_m2_bounded #(", "module p_native_weight_prefill #(")
edit(" logic pair_hold_valid,pair_prep_second,pair_first_pending,pair_detached,pair_abandon;",
     """ logic pair_hold_valid,pair_prep_second,pair_first_pending,pair_detached,pair_abandon;
 // Independently match the older ALLOC/FILL transaction after switching to
 // the younger record. W payload stays solely in the existing four M banks.
 logic [31:0] saved_allocation_session;
 logic saved_fill_seen;
 wire saved_waiting_fill=pair_hold_valid&&!saved_fill_seen&&
      (pair_prep_second||state==PAIR_ACCEPT_SECOND);""")
edit(" wire fence_body_ok=", """ wire saved_fill_body_ok=control_event==2&&saved_waiting_fill&&
     control_rx_session==saved_allocation_session&&control_rx_record==pair_hold.seq_id&&
     control_data[1:0]==pair_hold.W_bank&&control_data[17:2]==pair_hold.W_generation&&control_data[127:18]==0;
 wire current_fill_fire=control_valid&&control_body&&!control_sop&&control_eop&&fill_body_ok;
 wire fence_body_ok=""")
edit("begin_body_ok||allocation_body_ok||fill_body_ok||ctx_body_ok", "begin_body_ok||allocation_body_ok||fill_body_ok||saved_fill_body_ok||ctx_body_ok")
edit("     pair_hold<='0;pair_hold_valid<=0;", "     pair_hold<='0;saved_allocation_session<=0;saved_fill_seen<=0;pair_hold_valid<=0;")
edit("""         end else if(fill_body_ok)begin
           fill_seen<=1;confirmed_weight_read_bytes<=confirmed_weight_read_bytes+(head?32'd1152:32'd1088);
         end""", """         end else if(fill_body_ok||saved_fill_body_ok)begin
           if(fill_body_ok)fill_seen<=1;
           if(saved_fill_body_ok)saved_fill_seen<=1;
           confirmed_weight_read_bytes<=confirmed_weight_read_bytes+((fill_body_ok?head:pair_hold.head)?32'd1152:32'd1088);
         end""")
edit("""       FILL_WAIT:if(cancelled||scope_cancel)begin load_pending<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;end
         else if(fill_seen&&A_loaded[selected_A_slot]&&current_load_shift<=17)begin
           if(pair_prep_second)begin""", """       FILL_WAIT:if(cancelled||scope_cancel)begin load_pending<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;end
         else if(!pair_prep_second&&pair_candidate&&maximum_W_generation<W_GENERATION_LIMIT&&next_session<SESSION_LIMIT-32'd8)begin
           // The older ALLOC ACK has returned; its W FILL may still be in
           // flight. This is a second real bank allocation, not early READY.
           pair_hold<='{seq_id,col,address,full_k,k,context_id,n,completion_context,way,head,create,final_record,A_first,A_last,A_uses,current_context_generation,current_A_generation,current_use,W_bank,W_generation};
           pair_hold_valid<=1;saved_allocation_session<=allocation_session;saved_fill_seen<=fill_seen||current_fill_fire;
           state<=PAIR_ACCEPT_SECOND;
         end else if(fill_seen&&A_loaded[selected_A_slot]&&current_load_shift<=17&&(!pair_prep_second||saved_fill_seen))begin
           if(pair_prep_second)begin""")
edit("""           end else if(pair_candidate&&maximum_W_generation<W_GENERATION_LIMIT&&next_session<SESSION_LIMIT-32'd8)begin
             pair_hold<='{seq_id,col,address,full_k,k,context_id,n,completion_context,way,head,create,final_record,A_first,A_last,A_uses,current_context_generation,current_A_generation,current_use,W_bank,W_generation};pair_hold_valid<=1;state<=PAIR_ACCEPT_SECOND;
           end else state<=W_JOIN;""", """           end else state<=W_JOIN;""")
edit("""         // Complete the prepared first normally; re-evaluate the held record
         // using the ordinary contract without destroying its VALID.
         pair_hold_valid<=0;state<=W_JOIN;
       end""", """         // Do not skip the first record's actual FILL or A proof on fallback.
         if(fill_seen&&A_loaded[selected_A_slot]&&current_load_shift<=17)begin
           pair_hold_valid<=0;state<=W_JOIN;
         end
       end""")
edit("""           allocation_seen<=1;fill_seen<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_CANCEL_SEND;
         end else begin failed<=1;state<=CANCEL_FLUSH;end""", """           allocation_session<=saved_allocation_session;
           allocation_seen<=1;fill_seen<=saved_fill_seen||
               (control_valid&&control_body&&!control_sop&&control_eop&&saved_fill_body_ok);
           early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;
         end else begin failed<=1;state<=CANCEL_FLUSH;end""")
edit(" parameter logic [31:0] SESSION_LIMIT=32'hffffffe0,", """ // 0 keeps the paired two-bank candidate. 2 adds two real lookahead owners.
 parameter bit FOUR_BANK_LOOKAHEAD=1'b0,
 parameter logic [31:0] SESSION_LIMIT=32'hffffffe0,""")
start=source.index(" input logic record_valid,")
end=source.index(" output logic complete_valid,",start)
record_ports=source[start:end]
import re
source=source[:start]+re.sub(r"\brecord_", "in_record_", record_ports)+source[end:]
edit(" logic [15:0] pair_retire_next_k;", """ // Entries contain range metadata and returned W bank identity only. The
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
 logic record_ready;
 wire replay_live=FOUR_BANK_LOOKAHEAD&&ahead_live[ahead_head];
 wire replay_prepared=replay_live&&ahead_filled[ahead_head];
 wire replay_unoffered=replay_live&&!ahead_sent[ahead_head]&&
      !(ahead_offer&&ahead_index==ahead_head);
 wire record_valid=replay_live?(replay_prepared||((cancelled||scope_cancel)&&replay_unoffered)):in_record_valid;
 wire [127:0] record_owner=replay_live?owner:in_record_owner;
 wire [31:0] record_sequence=replay_live?ahead[ahead_head].seq_id:in_record_sequence;
 wire [31:0] record_col=replay_live?ahead[ahead_head].col:in_record_col;
 wire [63:0] record_address=replay_live?ahead[ahead_head].address:in_record_address;
 wire [15:0] record_full_k=replay_live?ahead[ahead_head].full_k:in_record_full_k;
 wire [15:0] record_k=replay_live?ahead[ahead_head].k:in_record_k;
 wire [3:0] record_context=replay_live?ahead[ahead_head].ctx:in_record_context;
 wire [3:0] record_n=replay_live?ahead[ahead_head].n:in_record_n;
 wire record_way=replay_live?ahead[ahead_head].way:in_record_way;
 wire record_head16=replay_live?ahead[ahead_head].head:in_record_head16;
 wire record_create=replay_live?ahead[ahead_head].create:in_record_create;
 wire record_restore=replay_live?ahead[ahead_head].restore:in_record_restore;
 wire record_final=replay_live?ahead[ahead_head].fin:in_record_final;
 wire record_spill=replay_live?ahead[ahead_head].spill:in_record_spill;
 wire record_A_first=replay_live?ahead[ahead_head].A_first:in_record_A_first;
 wire record_A_last=replay_live?ahead[ahead_head].A_last:in_record_A_last;
 wire [4:0] record_A_uses=replay_live?ahead[ahead_head].A_uses:in_record_A_uses;
 wire ahead_can_admit=FOUR_BANK_LOOKAHEAD&&!reset&&scope_live&&!cancelled&&!scope_cancel&&
      !(!replay_live&&record_ready)&&
      !ahead_live[ahead_tail]&&(pair_prep_second||pair_first_pending||pair_detached)&&
      in_record_owner==owner&&in_record_k==k&&in_record_full_k==full_k&&
      !in_record_create&&!in_record_A_first&&!in_record_restore&&!in_record_spill&&
      in_record_n>=1&&in_record_n<=8&&contexts_live[in_record_context]&&
      maximum_W_generation+17'd4<{1'b0,W_GENERATION_LIMIT}&&next_session<SESSION_LIMIT-32'd16;
 assign in_record_ready=ahead_can_admit||(!replay_live&&record_ready);
 wire ahead_push=in_record_valid&&ahead_can_admit;
 wire ahead_pop=record_valid&&record_ready&&replay_live;
 logic ahead_find,ahead_choice;
 always_comb begin
   ahead_find=0;ahead_choice=ahead_head;
   if(ahead_live[ahead_head]&&!ahead_sent[ahead_head])begin ahead_find=1;ahead_choice=ahead_head;end
   else if(ahead_live[!ahead_head]&&!ahead_sent[!ahead_head])begin ahead_find=1;ahead_choice=!ahead_head;end
 end
 logic [15:0] pair_retire_next_k;""")
edit("(state==IDLE&&(!namespace_needed||cancelled||scope_cancel)", "(state==IDLE&&(!namespace_needed||replay_prepared||cancelled||scope_cancel)")
edit("pair_second_shape&&!namespace_needed));", "pair_second_shape&&(!namespace_needed||replay_prepared)));")
edit("assign quiescent=state==IDLE&&!pair_hold_valid", "assign quiescent=state==IDLE&&ahead_live==0&&!ahead_offer&&!pair_hold_valid")
edit("assign g_cmd_valid=state==EXEC_PUSH;", "assign g_cmd_valid=state==EXEC_PUSH&&!ahead_offer;")
edit(" logic tx_cmd_valid,tx_cmd_ready,tx_payload_ready,tx_reject_valid;", """ logic tx_cmd_valid,tx_cmd_ready,tx_done,tx_payload_ready,tx_reject_valid;
 assign tx_cmd_ready=tx_done&&!ahead_offer;""")
edit("""     default:begin end
   endcase
 end
 m_short_command_tx tx(""", """     default:begin end
   endcase
   if(ahead_offer)begin tx_cmd_valid=1;tx_opcode=2;tx_payload={64'd0,ahead[ahead_index].address};end
 end
 m_short_command_tx tx(""")
edit(".cmd_ready(tx_cmd_ready),.cmd_opcode(tx_opcode),.cmd_scope(state==FENCE_SEND?4'd0:context_id),",
     ".cmd_ready(tx_done),.cmd_opcode(tx_opcode),.cmd_scope(ahead_offer?ahead[ahead_index].ctx:(state==FENCE_SEND?4'd0:context_id)),")
edit(".cmd_scope_generation(state==FENCE_SEND?16'd0:current_context_generation),.cmd_high16((state==EARLY_CANCEL_SEND||state==EARLY_DRAIN_SEND)?W_generation:(cleanup_command?16'd4:16'd0))",
     ".cmd_scope_generation(ahead_offer?ahead_context_generation[ahead_index]:(state==FENCE_SEND?16'd0:current_context_generation)),.cmd_high16(ahead_offer?16'd0:((state==EARLY_CANCEL_SEND||state==EARLY_DRAIN_SEND)?W_generation:(cleanup_command?16'd4:16'd0)))")
edit(".cmd_record((state==BEGIN_SEND||state==CTX_ISSUE||state==CANCEL_CTX_ISSUE||state==FENCE_SEND)?32'd0:seq_id),.cmd_bank((state==EARLY_CANCEL_SEND||state==EARLY_DRAIN_SEND)?W_bank:2'd0)",
     ".cmd_record(ahead_offer?ahead[ahead_index].seq_id:((state==BEGIN_SEND||state==CTX_ISSUE||state==CANCEL_CTX_ISSUE||state==FENCE_SEND)?32'd0:seq_id)),.cmd_bank((!ahead_offer&&(state==EARLY_CANCEL_SEND||state==EARLY_DRAIN_SEND))?W_bank:2'd0)")
edit(" wire fatal_control=", """ logic ahead_alloc_ok,ahead_fill_ok,ahead_match;
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
     ((state==IDLE&&!record_valid)||(state==FILL_WAIT&&pair_prep_second)||
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
       ahead[ahead_tail]<='{in_record_sequence,in_record_col,in_record_address,in_record_full_k,in_record_k,
          in_record_context,in_record_n,in_record_way,in_record_head16,in_record_create,in_record_restore,
          in_record_final,in_record_spill,in_record_A_first,in_record_A_last,in_record_A_uses};
       ahead_live[ahead_tail]<=1;ahead_sent[ahead_tail]<=0;ahead_allocated[ahead_tail]<=0;ahead_filled[ahead_tail]<=0;
       ahead_context_generation[ahead_tail]<=context_generation[in_record_context];
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
 wire fatal_control=""")
edit("saved_fill_body_ok||ctx_body_ok", "saved_fill_body_ok||ahead_alloc_ok||ahead_fill_ok||ctx_body_ok")
edit("if((tx_cmd_valid&&tx_cmd_ready)||(g_cmd_valid&&g_cmd_ready))", "if((tx_cmd_valid&&tx_done)||(g_cmd_valid&&g_cmd_ready))")
edit("""         end else if(fill_body_ok||saved_fill_body_ok)begin""", """         end else if(ahead_alloc_ok)begin
           if(control_data[17:2]>maximum_W_generation)maximum_W_generation<=control_data[17:2];
         end else if(ahead_fill_ok)begin
           confirmed_weight_read_bytes<=confirmed_weight_read_bytes+(ahead[ahead_match].head?32'd1152:32'd1088);
         end else if(fill_body_ok||saved_fill_body_ok)begin""")
edit("&&namespace_needed&&guard_quiescent", "&&namespace_needed&&!replay_live&&!ahead_offer&&guard_quiescent")
edit("""         if(cancelled||scope_cancel)begin failed<=1;state<=CANCEL_FLUSH;end
         else if(record_restore""", """         if(replay_prepared)begin
           // No repeated ALLOC. The returning bank and FILL are exact.
           allocation_session<=ahead_session[ahead_head];W_bank<=ahead_W_bank[ahead_head];
           W_generation<=ahead_W_generation[ahead_head];allocation_seen<=1;fill_seen<=1;
           if(cancelled||scope_cancel)begin early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;end
           else state<=FILL_WAIT;
         end else if(cancelled||scope_cancel)begin failed<=1;state<=CANCEL_FLUSH;end
         else if(record_restore""")
edit("""         state<=record_create?BEGIN_SEND:ALLOC_SEND;
       end else if(record_valid&&(namespace_needed||!pair_second_shape))""", """         if(replay_prepared)begin
           allocation_session<=ahead_session[ahead_head];W_bank<=ahead_W_bank[ahead_head];
           W_generation<=ahead_W_generation[ahead_head];allocation_seen<=1;fill_seen<=1;state<=FILL_WAIT;
         end else state<=record_create?BEGIN_SEND:ALLOC_SEND;
       end else if(record_valid&&(namespace_needed||!pair_second_shape))""")
# Preserve the original P executor aperture. Only the internal replay mux
# should see the distinct name used for the ordered frontend.
start=source.index(" typedef enum")
names="|".join(sorted(set(re.findall(r"\brecord_\w+", record_ports))))
source=source[:start].replace("in_record_", "record_")+re.sub(
    rf"\b({names})\b", r"front_\1", source[start:]).replace("in_record_", "record_")
(rtl / "p_native_weight_prefill.sv").write_text(source, encoding="utf-8")
