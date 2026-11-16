"""Actual streamed P bridge onto the finite dual issuer; legacy P untouched.

This first bridge retains one prepared record. It establishes executable
compatibility with the new aperture before enabling overlapped W/A preparation.
"""
from pathlib import Path
p=Path(__file__).parent/'rtl'
s=(p/'p_native_stream_record_executor.sv').read_text(encoding='utf-8')
s=s.replace('module p_native_stream_record_executor #(', 'module p_native_stream_dual_candidate #(')
s=s.replace('logic g_cmd_valid,g_cmd_ready,g_native_valid,g_native_ready,g_terminal_valid,g_terminal_ready;', 'logic g_cmd_valid,g_cmd_ready,g_terminal_valid,g_terminal_ready;')
s=s.replace('logic [511:0] g_native_ticket,g_terminal_ticket,g_input_ticket,g_abort_ticket;', 'logic [511:0] g_terminal_ticket,g_input_ticket,g_abort_ticket;')
s=s.replace('logic [7:0] g_native_resource,g_native_service,g_terminal_error;', 'logic [7:0] g_terminal_error;')
s=s.replace('logic [255:0] g_native_payload,g_terminal_data;', '''logic [255:0] g_terminal_data;
 logic issue_use_valid,issue_use_slot,issue_tx_fault,g_abort_error;
 logic [127:0] issue_use_key;
 logic [15:0] issue_use_gen,issue_use_kk,issue_use_sequence;
 logic [31:0] issue_use_record,issue_use_session;
 logic side_valid,side_ready,side_sop,side_eop;
 logic [127:0] side_data;
 logic ctx_ack;''')
s=s.replace('.use_valid(state==A_START),.use_ready(af_use_ready),.use_slot(selected_A_slot),.use_generation(current_A_generation),\n   .use_kk(selected_kk),.use_sequence(current_use),.use_key(input_key),', '.use_valid(issue_use_valid),.use_ready(af_use_ready),.use_slot(issue_use_slot),.use_generation(issue_use_gen),\n   .use_kk(issue_use_kk),.use_sequence(issue_use_sequence),.use_key(issue_use_key),')
s=s.replace('assign a_session=exec_session;', 'assign a_session=issue_use_session;')
s=s.replace('expected_payload[216]=final_record;expected_payload[217]=1;', 'expected_payload[216]=final_record;expected_payload[217]=1;\n     expected_payload[233:218]=current_context_generation;expected_payload[239:234]=current_load_shift;')
s=s.replace('assign g_cmd_valid=state==CTX_PUSH||state==EXEC_PUSH||state==CANCEL_CTX_PUSH;', 'assign g_cmd_valid=state==EXEC_PUSH;')
a=s.index(' wire [511:0] active_ctx_ticket=');b=s.index('   .clk,.reset,.cmd_valid(g_cmd_valid)',a)
s=s[:a]+''' assign g_terminal_ready=state==EXEC_WAIT&&g_terminal_ticket==active_exec_ticket;
 m_dual_exec_issue issuer(
'''+s[b:]
s=s.replace('   .native_valid(g_native_valid),.native_ready(g_native_ready),.native_ticket(g_native_ticket),\n   .native_resource(g_native_resource),.native_service(g_native_service),.native_payload(g_native_payload),', '''   .a_use_valid(issue_use_valid),.a_use_ready(af_use_ready),.a_use_key(issue_use_key),.a_use_slot(issue_use_slot),
   .a_use_generation(issue_use_gen),.a_use_kk(issue_use_kk),.a_use_sequence(issue_use_sequence),
   .a_use_record(issue_use_record),.a_use_session(issue_use_session),
   .side_valid,.side_ready,.side_sop,.side_eop,.side_data,.lc_valid,.lc_ready,.lc_sop,.lc_eop,.lc_data,.tx_fault_valid(issue_tx_fault),''')
s=s.replace('.native_abort_next_k(g_abort_next),', '.native_abort_next_k(g_abort_next),.native_abort_error(g_abort_error),')
s=s.replace('   .halted(guard_halted)',"   .cancel_one_valid(1'b0),.cancel_one_ready(),.cancel_one_ticket(512'd0),\n   .halted(guard_halted)")
s=s.replace('logic guard_halted,guard_quarantine,guard_quiescent,g_cancel_ready;', 'logic guard_halted,guard_quarantine,guard_quiescent,g_cancel_ready,g_cancel_one_ready;')
s=s.replace('.cancel_one_ready(),', '.cancel_one_ready(g_cancel_one_ready),')
s=s.replace('CTX_ISSUE,CANCEL_CTX_ISSUE:begin tx_cmd_valid=g_native_valid;tx_opcode=4;end', 'CTX_ISSUE,CANCEL_CTX_ISSUE:begin tx_cmd_valid=1;tx_opcode=4;end')
a=s.index('     EXEC_ISSUE:begin');b=s.index('     EARLY_CANCEL_SEND:',a);s=s[:a]+s[b:]
s=s.replace('   .lc_valid,.lc_ready,.lc_sop,.lc_eop,.lc_data,.reject_valid(tx_reject_valid)', '   .lc_valid(side_valid),.lc_ready(side_ready),.lc_sop(side_sop),.lc_eop(side_eop),.lc_data(side_data),.reject_valid(tx_reject_valid)')
s=s.replace(' assign g_native_ready=(state==CTX_ISSUE||state==EXEC_ISSUE||state==CANCEL_CTX_ISSUE)&&tx_cmd_ready;\n','')
s=s.replace(' wire ordinary_control_header=', ''' wire ctx_response_header=control_sop&&!control_eop&&control_data[31:0]==32'h02504d02&&control_data[39:32]==4&&
     control_data[47:40]==0&&control_data[79:48]==control_session&&control_data[111:80]==0&&
     control_data[127:112]=={4'd2,1'b0,(cleanup_command?3'd4:3'd0),context_id,4'd0}&&
     (state==CTX_WAIT||state==CANCEL_CTX_WAIT);
 wire ctx_body_ok=control_event==4&&control_rx_session==control_session&&control_rx_record==0&&
     control_data=={48'd0,control_session,full_k,(cleanup_command?context_next_k[context_id]:16'd0),
                   (head?8'd16:8'd128),n,context_id};
 wire ordinary_control_header=ctx_response_header||''')
s=s.replace('fill_body_ok||fence_body_ok||', 'fill_body_ok||ctx_body_ok||fence_body_ok||')
s=s.replace('control_rx_record<=0;begin_ack<=0;', 'control_rx_record<=0;begin_ack<=0;ctx_ack<=0;')
s=s.replace('if(tx_cmd_valid&&tx_cmd_ready)begin\n       if(next_session', 'if((tx_cmd_valid&&tx_cmd_ready)||(g_cmd_valid&&g_cmd_ready))begin\n       if(next_session')
s=s.replace('else if(begin_body_ok)begin_ack<=1;', 'else if(begin_body_ok)begin_ack<=1;\n         else if(ctx_body_ok)ctx_ack<=1;')
a=s.index('       CTX_PUSH:');b=s.index('       ALLOC_SEND:',a)
s=s[:a]+'''       CTX_PUSH:begin ctx_ack<=0;control_session<=next_session;state<=CTX_ISSUE;end
       CTX_ISSUE:if(tx_cmd_valid&&tx_cmd_ready)state<=CTX_WAIT;
       CTX_WAIT:if(ctx_ack)begin contexts_live[context_id]<=1;context_next_k[context_id]<=0;state<=ALLOC_SEND;end
'''+s[b:]
s=s.replace('       EXEC_ISSUE:if(g_native_valid&&g_native_ready)state<=A_START;\n       A_START:if(af_use_ready)', '       EXEC_ISSUE:if(issue_use_valid&&af_use_ready)')
a=s.index('       CANCEL_CTX_PUSH:');b=s.index('       COMPLETE:',a)
s=s[:a]+'''       CANCEL_CTX_PUSH:begin ctx_ack<=0;control_session<=next_session;state<=CANCEL_CTX_ISSUE;end
       CANCEL_CTX_ISSUE:if(tx_cmd_valid&&tx_cmd_ready)state<=CANCEL_CTX_WAIT;
       CANCEL_CTX_WAIT:if(ctx_ack)begin contexts_live[context_id]<=0;state<=CANCEL_FLUSH;end
'''+s[b:]
s=s.replace('fatal_operand||tx_reject_valid||', 'fatal_operand||tx_reject_valid||issue_tx_fault||')
s=s.replace('af_faults,af_abort_ready,g_native_ticket,g_native_resource,g_native_service,g_native_payload,','af_faults,af_abort_ready,g_abort_error,g_cancel_one_ready,issue_use_record,')
(p/'p_native_stream_dual_candidate.sv').write_text(s,encoding='utf-8')
