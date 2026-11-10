"""Fixed staging-window native candidate; leave qualified contig RTL intact.

This is the native side of future service2, not service2 registration. The
typed provider keeps rejecting service2 until actual outer/COPY integration.
"""
from pathlib import Path

root = Path(__file__).parent / 'rtl'
s = (root / 'p_native_record_executor.sv').read_text().replace(
    'module p_native_record_executor #(', 'module p_native_stream_record_executor #(')
s = s.replace(' input logic [127:0] copy_key,input logic [10:0] copy_committed_prefix,', '''
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
 input logic [127:0] copy_key,input logic [10:0] copy_committed_prefix,''')
s = s.replace(' logic scope_live,cancelled;', ' logic scope_live,cancelled;logic [15:0] current_window_generation;logic [31:0] current_window_session,current_window_ticket;logic [5:0] current_load_shift;')
s = s.replace("SESSION_LIMIT=32'hfffffff0", "SESSION_LIMIT=32'hffffffe0")
s = s.replace('CANCEL_CTX_PUSH,CANCEL_CTX_ISSUE,CANCEL_CTX_WAIT}', 'CANCEL_CTX_PUSH,CANCEL_CTX_ISSUE,CANCEL_CTX_WAIT,EARLY_HALT,EARLY_CANCEL_SEND,EARLY_CANCEL_WAIT,EARLY_DRAIN_SEND,EARLY_DRAIN_WAIT}')
s = s.replace(' logic fence_seen,fence_rearm_A;', ' logic fence_seen,fence_rearm_A;logic [31:0] early_cancel_session,early_drain_session;logic early_cancel_seen,early_drain_seen,early_cancel_live;')
s = s.replace(' wire selected_A_slot=k[7];', '''
 wire early_halt=state==EARLY_HALT||state==EARLY_CANCEL_SEND||state==EARLY_CANCEL_WAIT||state==EARLY_DRAIN_SEND||state==EARLY_DRAIN_WAIT;
 wire selected_A_slot=k[7];''')
s = s.replace(' wire [31:0] input_word={16\'d0,scope_data[672+:16]}+({16\'d0,selected_kk}<<4);', '''
 // A physical 256B staging window can represent any global K128 tile.
 // The global K remains in A/M tags and scale lookup; only S addressing is local.
 wire [31:0] input_word={16'd0,scope_data[672+:16]};
 wire first_window_match=stream_window_valid&&stream_window_key==input_key&&
     stream_window_generation!=0&&stream_window_k_elements==record_k;
 wire current_window_match=stream_window_valid&&stream_window_key==input_key&&
     stream_window_generation==current_window_generation&&stream_window_k_elements==k&&
     stream_window_session==current_window_session&&stream_window_ticket==current_window_ticket;
 wire progress_matches=current_window_match&&copy_progress_valid&&copy_key==input_key&&
     copy_progress_generation==current_window_generation&&copy_progress_k_elements==k&&
     copy_progress_session==current_window_session&&copy_progress_ticket==current_window_ticket;
 wire [10:0] effective_copy_prefix=progress_matches?copy_committed_prefix:11'd0;''')
s = s.replace('record_owner==owner&&!namespace_needed;', 'record_owner==owner&&(!namespace_needed||cancelled||scope_cancel)&&(!record_A_first||first_window_match||cancelled||scope_cancel);')
s = s.replace('.cmd_copy_offset({selected_kk[5:0],4\'d0}),', ".cmd_copy_offset(10'd0),")
s = s.replace('   .copy_key,.copy_committed_prefix,', '   .copy_key,.copy_committed_prefix(effective_copy_prefix),')
s = s.replace(' wire af_halt=state==CANCEL_FLUSH||state==FENCE_REARM;', ' wire af_halt=state==CANCEL_FLUSH||state==FENCE_REARM||early_halt;')
s = s.replace(" assign af_load_ready=1'b1;", '''
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
 assign a_source_reads_drained=af_drained;''')
s = s.replace('     state<=IDLE;scope_live<=0;', '     early_cancel_live<=0;early_cancel_session<=0;early_drain_session<=0;early_cancel_seen<=0;early_drain_seen<=0;current_window_generation<=0;current_window_session<=0;current_window_ticket<=0;current_load_shift<=0;state<=IDLE;scope_live<=0;')
s = s.replace('       load_pending<=0;A_generation_counter', '       current_load_shift<=scale_lookup_shift;load_pending<=0;A_generation_counter')
s = s.replace('     if(af_load_valid)begin', '     if(af_load_valid&&af_load_ready)begin')
s = s.replace('       else begin state<=QUARANTINE;protocol_faults<=protocol_faults+1\'b1;end\n     end\n     if(g_input_valid)', '       else if(!(early_cancel_live&&af_load_error&&af_load_slot==selected_A_slot&&af_load_gen==current_A_generation&&af_load_key==input_key))begin state<=QUARANTINE;protocol_faults<=protocol_faults+1\'b1;end\n     end\n     if(g_input_valid)')
s = s.replace(' wire fatal_load=af_load_valid&&(af_load_error||af_load_slot!=selected_A_slot||', ' wire fatal_load=af_load_valid&&((af_load_error&&!early_cancel_live)||af_load_slot!=selected_A_slot||')
s = s.replace('         if(record_A_first)begin A_loaded', '         if(record_A_first)begin current_window_generation<=stream_window_generation;current_window_session<=stream_window_session;current_window_ticket<=stream_window_ticket;A_loaded')
s = s.replace('     FENCE_SEND:begin tx_cmd_valid=1;tx_opcode=8;end', '''
     EARLY_CANCEL_SEND:begin tx_cmd_valid=1;tx_opcode=6;end
     EARLY_DRAIN_SEND:begin tx_cmd_valid=1;tx_opcode=7;end
     FENCE_SEND:begin tx_cmd_valid=1;tx_opcode=8;end''')
s = s.replace('.cmd_high16(cleanup_command?16\'d4:16\'d0)', ".cmd_high16((state==EARLY_CANCEL_SEND||state==EARLY_DRAIN_SEND)?W_generation:(cleanup_command?16'd4:16'd0))")
s = s.replace('.cmd_bank(2\'d0)', ".cmd_bank((state==EARLY_CANCEL_SEND||state==EARLY_DRAIN_SEND)?W_bank:2'd0)")
s = s.replace('control_data[39:32]==10||control_data[39:32]==8)', 'control_data[39:32]==10||control_data[39:32]==8||control_data[39:32]==9||control_data[39:32]==6)')
s = s.replace(' wire fatal_control=', '''
 wire early_cancel_body_ok=control_event==9&&state==EARLY_CANCEL_WAIT&&control_rx_session==early_cancel_session&&control_rx_record==seq_id&&control_data==0;
 wire early_drain_body_ok=control_event==6&&state==EARLY_DRAIN_WAIT&&control_rx_session==early_drain_session&&control_rx_record==seq_id&&
     control_data[1:0]==W_bank&&control_data[17:2]==W_generation&&control_data[127:18]==0;
 wire fatal_control=''')
s = s.replace('fill_body_ok||fence_body_ok)', 'fill_body_ok||fence_body_ok||early_cancel_body_ok||early_drain_body_ok)')
s = s.replace('         else if(fence_body_ok)', '         else if(early_cancel_body_ok)early_cancel_seen<=1;\n         else if(early_drain_body_ok)early_drain_seen<=1;\n         else if(fence_body_ok)')
s = s.replace('scope_live&&record_owner==owner&&namespace_needed&&', 'scope_live&&record_owner==owner&&!cancelled&&!scope_cancel&&namespace_needed&&')
s = s.replace('       FILL_WAIT:if(fill_seen&&A_loaded[selected_A_slot]&&scale_lookup_valid&&scale_lookup_shift<=17)state<=W_JOIN;', '''
       FILL_WAIT:if(cancelled||scope_cancel)begin load_pending<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;end
         else if(fill_seen&&A_loaded[selected_A_slot]&&scale_lookup_valid&&scale_lookup_shift<=17)state<=W_JOIN;''')
s = s.replace('       W_JOIN:if(af_w_ready)state<=EXEC_PUSH;', '''
       W_JOIN:if(cancelled||scope_cancel)begin load_pending<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;end
         else if(af_w_ready)state<=EXEC_PUSH;''')
s = s.replace('       CANCEL_FLUSH:if(af_flush)begin', '''
       // Complete the one bounded W fetch for exact existing FILL accounting,
       // while cancelled A issues no new reads and drains held requests.
       // No EXEC/ABORT or fake INPUT/RF event is fabricated for this record.
       EARLY_HALT:if(fill_seen)state<=EARLY_CANCEL_SEND;
       EARLY_CANCEL_SEND:if(tx_cmd_valid&&tx_cmd_ready)begin early_cancel_session<=next_session;state<=EARLY_CANCEL_WAIT;end
       EARLY_CANCEL_WAIT:if(early_cancel_seen)state<=EARLY_DRAIN_SEND;
       EARLY_DRAIN_SEND:if(tx_cmd_valid&&tx_cmd_ready)begin early_drain_session<=next_session;state<=EARLY_DRAIN_WAIT;end
       EARLY_DRAIN_WAIT:if(early_drain_seen)begin failed<=1;state<=CANCEL_FLUSH;end
       CANCEL_FLUSH:if(af_flush)begin''')
s = s.replace('       COMPLETE:if(complete_valid&&complete_ready)state<=IDLE;', '       COMPLETE:if(complete_valid&&complete_ready)begin early_cancel_live<=0;state<=IDLE;end')
# RX metadata owns staging only until true LOAD proof. The A lease captures
# shift, so released or replaced RX metadata cannot govern an existing use.
s = s.replace('tx_payload[88:83]=scale_lookup_shift;', 'tx_payload[88:83]=current_load_shift;')
s = s.replace('!scale_lookup_valid||af_shift!=scale_lookup_shift', 'af_shift!=current_load_shift')
s = s.replace('fill_seen&&A_loaded[selected_A_slot]&&scale_lookup_valid&&scale_lookup_shift<=17', 'fill_seen&&A_loaded[selected_A_slot]&&current_load_shift<=17')
s = s.replace('// First registration is full LOCAL_CONTIG_RANGE and zero bias.', '// Candidate fixed staging input for unregistered streamed service2, zero bias.')
(root / 'p_native_stream_record_executor.sv').write_text(s)
