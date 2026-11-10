"""Generalize the bounded pair to successive K128 tiles and odd A-use tails."""
from pathlib import Path
p=Path(__file__).parent/'rtl'
s=(p/'p_native_stream_pair_candidate.sv').read_text(encoding='utf-8')
s=s.replace('module p_native_stream_pair_candidate #(', 'module p_native_stream_m2_bounded #(')
a=s.index(' wire pair_candidate=');b=s.index(' wire early_halt=',a)
s=s[:a]+''' logic [15:0] pair_retire_next_k;
 logic pair_retire_final;
 wire pair_candidate=scope_data[48+:16]==2&&current_use[0]&&current_use<{11'd0,A_uses};
 wire pair_second_shape=record_full_k==full_k&&record_k==k&&record_create==create&&!record_A_first&&
      record_A_last==(current_use+16'd1=={11'd0,A_uses})&&record_A_uses==A_uses&&
      record_final==final_record&&!record_restore&&!record_spill&&record_n>=1&&record_n<=8&&
      record_context!=context_id&&record_head16==head;

'''+s[b:]
s=s.replace("(pair_abandon||g_terminal_error!=0?16'd0:16'd128)", 'pair_retire_next_k')
s=s.replace('pair_terminal_match?!g_terminal_stored:', 'pair_terminal_match?(pair_retire_final!=g_terminal_stored):')
s=s.replace('pair_retire_context<=0;maximum_W_generation<=0;', 'pair_retire_context<=0;pair_retire_next_k<=0;pair_retire_final<=0;maximum_W_generation<=0;')
s=s.replace('if(pair_terminal_valid&&complete_ready)begin pair_detached<=0;contexts_live[pair_retire_context]<=0;end', '''if(pair_terminal_valid&&complete_ready)begin
       pair_detached<=0;
       if(g_terminal_error==0)begin
         context_next_k[pair_retire_context]<=pair_retire_next_k;
         if(pair_retire_final)contexts_live[pair_retire_context]<=0;
       end
     end''')
s=s.replace("A_first<=0;A_last<=1;A_uses<=record_A_uses;current_use<=16'd2;", "A_first<=0;A_last<=record_A_last;A_uses<=record_A_uses;current_use<=current_use+16'd1;")
s=s.replace("current_context_generation<=context_generation[record_context]+16'd1;", "current_context_generation<=context_generation[record_context]+(record_create?16'd1:16'd0);")
s=s.replace('         state<=BEGIN_SEND;\n       end else if(record_valid&&(namespace_needed||!pair_second_shape))', '         state<=record_create?BEGIN_SEND:ALLOC_SEND;\n       end else if(record_valid&&(namespace_needed||!pair_second_shape))')
s=s.replace('pair_retire_session<=exec_session;pair_retire_sequence<=seq_id;pair_retire_context<=completion_context;', '''pair_retire_session<=exec_session;pair_retire_sequence<=seq_id;pair_retire_context<=completion_context;
         pair_retire_next_k<=k+16'd128;pair_retire_final<=final_record;''')
s=s.replace('pair_abandon<=1;pair_retire_sequence<=seq_id;pair_retire_context<=completion_context;', '''pair_abandon<=1;pair_retire_sequence<=seq_id;pair_retire_context<=completion_context;
           pair_retire_next_k<=k;pair_retire_final<=0;''')
(p/'p_native_stream_m2_bounded.sv').write_text(s,encoding='utf-8')
