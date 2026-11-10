"""Bounded two-ready-record P experiment; one saved metadata record, no payload copy.

Eligible full K128 pair: two adjacent outputs, one way, two real users of the
same A tile. Both contexts and both W records are truly prepared before issue.
All other typed ranges retain the single-preparation candidate behavior.
"""
from pathlib import Path
p=Path(__file__).parent/'rtl'
s=(p/'p_native_stream_dual_candidate.sv').read_text(encoding='utf-8')
s=s.replace('module p_native_stream_dual_candidate #(', 'module p_native_stream_pair_candidate #(')
s=s.replace('EARLY_DRAIN_SEND,EARLY_DRAIN_WAIT}', 'EARLY_DRAIN_SEND,EARLY_DRAIN_WAIT,PAIR_ACCEPT_SECOND}')
fields=[(32,'seq_id'),(32,'col'),(64,'address'),(16,'full_k'),(16,'k'),(4,'context_id'),(4,'n'),(4,'completion_context'),
        (1,'way'),(1,'head'),(1,'create'),(1,'final_record'),(1,'A_first'),(1,'A_last'),(5,'A_uses'),
        (16,'current_context_generation'),(16,'current_A_generation'),(16,'current_use'),(2,'W_bank'),(16,'W_generation')]
pack="'{"+','.join(n for w,n in fields)+'}'
restore='\n'.join(f'           {n}<=pair_hold.{n};' for w,n in fields)
structure='\n'.join((f'   logic [{w-1}:0] {n};' if w>1 else f'   logic {n};') for w,n in fields)
s=s.replace(' logic [1:0] A_loaded;', ''' logic [1:0] A_loaded;
 typedef struct packed {
'''+structure+'''
 } pair_record_t;
 pair_record_t pair_hold;
 logic pair_hold_valid,pair_prep_second,pair_first_pending,pair_detached,pair_abandon;
 logic [31:0] pair_retire_session,pair_retire_sequence;
 logic [3:0] pair_retire_context;
 logic [15:0] maximum_W_generation;
 wire pair_candidate=scope_data[48+:16]==2&&scope_data[592+:5]==2&&scope_data[656+:2]==1&&
      full_k==128&&k==0&&A_first&&A_uses==2&&final_record;
 wire pair_second_shape=record_full_k==128&&record_k==0&&record_create&&!record_A_first&&record_A_last&&
      record_final&&!record_restore&&!record_spill&&record_n>=1&&record_n<=8&&
      record_context!=context_id&&record_head16==head&&record_way==way;
''')
s=s.replace('W_generation>=W_GENERATION_LIMIT', 'maximum_W_generation>=W_GENERATION_LIMIT')
a=s.index(' assign record_ready=');b=s.index(' assign quarantine=',a)
s=s[:a]+''' assign record_ready=!reset&&scope_live&&record_owner==owner&&
     ((state==IDLE&&(!namespace_needed||cancelled||scope_cancel)&&(!record_A_first||first_window_match||cancelled||scope_cancel))||
      (state==PAIR_ACCEPT_SECOND&&!cancelled&&!scope_cancel&&pair_second_shape&&!namespace_needed));
 wire pair_terminal_match=pair_detached&&g_terminal_ticket[31:0]==pair_retire_session&&
      g_terminal_ticket[63:32]==pair_retire_sequence&&g_terminal_ticket[511:384]==owner;
 wire pair_terminal_valid=pair_terminal_match&&g_terminal_valid;
 wire pair_retiring=pair_terminal_valid||pair_abandon;
 assign complete_valid=!reset&&(pair_retiring||(!pair_detached&&state==COMPLETE));
 assign complete_owner=owner;
 assign complete_sequence=pair_retiring?pair_retire_sequence:seq_id;
 assign complete_context=pair_retiring?pair_retire_context:completion_context;
 assign complete_next_k=pair_retiring?(pair_abandon||g_terminal_error!=0?16'd0:16'd128):(k+(record_progressed?16'd128:16'd0));
 assign complete_error=pair_retiring?(pair_abandon||g_terminal_error!=0):failed;
'''+s[b:]
s=s.replace('assign quiescent=state==IDLE&&contexts_live==0', 'assign quiescent=state==IDLE&&!pair_hold_valid&&!pair_detached&&!pair_abandon&&contexts_live==0')
s=s.replace('assign g_terminal_ready=state==EXEC_WAIT&&g_terminal_ticket==active_exec_ticket;', 'assign g_terminal_ready=pair_terminal_match?complete_ready:(state==EXEC_WAIT&&g_terminal_ticket==active_exec_ticket);')
s=s.replace('''(g_terminal_error!=0||(state==EXEC_WAIT&&(!input_seen||(final_record&&!g_terminal_stored))));''', '''(g_terminal_error!=0||(pair_terminal_match?!g_terminal_stored:
       (state==EXEC_WAIT&&(!input_seen||(final_record&&!g_terminal_stored)))));''')
s=s.replace('   if(reset)begin\n     early_cancel_live', '''   if(reset)begin
     pair_hold<='0;pair_hold_valid<=0;pair_prep_second<=0;pair_first_pending<=0;pair_detached<=0;pair_abandon<=0;
     pair_retire_session<=0;pair_retire_sequence<=0;pair_retire_context<=0;maximum_W_generation<=0;
     early_cancel_live''')
s=s.replace('   end else begin\n     if(scope_valid', '''   end else begin
     if(pair_terminal_valid&&complete_ready)begin pair_detached<=0;contexts_live[pair_retire_context]<=0;end
     if(pair_abandon&&complete_ready)pair_abandon<=0;
     if(scope_valid''')
s=s.replace('W_bank<=control_data[1:0];W_generation<=control_data[17:2];allocation_seen<=1;', '''W_bank<=control_data[1:0];W_generation<=control_data[17:2];allocation_seen<=1;
           if(control_data[17:2]>maximum_W_generation)maximum_W_generation<=control_data[17:2];''')
s=s.replace('else if(fill_seen&&A_loaded[selected_A_slot]&&current_load_shift<=17)state<=W_JOIN;', '''else if(fill_seen&&A_loaded[selected_A_slot]&&current_load_shift<=17)begin
           if(pair_prep_second)begin
             // Exchange the sole saved record with the current prepared one.
             pair_hold<='''+pack+''';pair_prep_second<=0;pair_first_pending<=1;
'''+restore+'''
             state<=W_JOIN;
           end else if(pair_candidate&&maximum_W_generation<W_GENERATION_LIMIT&&next_session<SESSION_LIMIT-32'd8)begin
             pair_hold<='''+pack+''';pair_hold_valid<=1;state<=PAIR_ACCEPT_SECOND;
           end else state<=W_JOIN;
         end

       PAIR_ACCEPT_SECOND:if(cancelled||scope_cancel)begin
         // The second offer was never accepted: no second bank or range owner.
         pair_hold_valid<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;
       end else if(record_valid&&record_ready)begin
         pair_prep_second<=1;seq_id<=record_sequence;col<=record_col;address<=record_address;
         full_k<=record_full_k;k<=record_k;context_id<=record_context;completion_context<=record_context;
         n<=record_n;way<=record_way;head<=record_head16;create<=record_create;final_record<=record_final;
         A_first<=0;A_last<=1;A_uses<=record_A_uses;current_use<=16'd2;
         current_context_generation<=context_generation[record_context]+16'd1;
         failed<=0;record_progressed<=0;allocation_seen<=0;fill_seen<=0;input_seen<=0;begin_ack<=0;
         state<=BEGIN_SEND;
       end else if(record_valid&&(namespace_needed||!pair_second_shape))begin
         // Complete the prepared first normally; re-evaluate the held record
         // using the ordinary contract without destroying its VALID.
         pair_hold_valid<=0;state<=W_JOIN;
       end''')
s=s.replace('       EXEC_WAIT:if(g_terminal_valid&&g_terminal_ready)begin', '''       EXEC_WAIT:if(pair_first_pending&&g_input_valid&&g_input_ticket==active_exec_ticket&&!g_input_error)begin
         // INPUT EOP terminates operand leases only. Keep result/command owner
         // in guard2 until the actual RF+two S ACKs and range terminal ACK.
         pair_retire_session<=exec_session;pair_retire_sequence<=seq_id;pair_retire_context<=completion_context;
         pair_detached<=1;pair_first_pending<=0;pair_hold_valid<=0;
'''+restore+'''
         allocation_seen<=1;fill_seen<=1;input_seen<=0;failed<=0;record_progressed<=0;state<=W_JOIN;
       end else if(g_terminal_valid&&g_terminal_ready&&!pair_terminal_match)begin''')
s=s.replace('       EARLY_DRAIN_WAIT:if(early_drain_seen)begin failed<=1;state<=CANCEL_FLUSH;end', '''       EARLY_DRAIN_WAIT:if(early_drain_seen)begin
         if(pair_hold_valid)begin
           // Both ready W banks are owned. Retire only the actually drained
           // one as error, then issue exact CANCEL/DRAIN for the saved bank.
           pair_abandon<=1;pair_retire_sequence<=seq_id;pair_retire_context<=completion_context;
           pair_hold_valid<=0;pair_prep_second<=0;pair_first_pending<=0;
'''+restore+'''
           allocation_seen<=1;fill_seen<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_CANCEL_SEND;
         end else begin failed<=1;state<=CANCEL_FLUSH;end
       end''')
s=s.replace('COMPLETE:if(complete_valid&&complete_ready)', 'COMPLETE:if(complete_valid&&complete_ready&&!pair_retiring)')
s=s.replace('context_wrap_allowed<=16\'hffff;W_generation<=0;', 'context_wrap_allowed<=16\'hffff;W_generation<=0;maximum_W_generation<=0;')
(p/'p_native_stream_pair_candidate.sv').write_text(s,encoding='utf-8')
