"""Keep the validated stream wrapper; qualify an independent resident X provider."""
from pathlib import Path
p=Path(__file__).parent/'rtl'
s=(p/'p_native_stream_m2_bounded.sv').read_text(encoding='utf-8')
s=s.replace('module p_native_stream_m2_bounded #(', 'module p_native_resident_x_candidate #(')
s=s.replace('Candidate fixed staging input for unregistered streamed service2, zero bias.', 'Resident X service1 candidate: sealed K2048 ordinary S128 window and zero bias.')
a=s.index(' // Header/window admission')
b=s.index(' output logic a_load_proof_valid',a)
s=s[:a]+''' // Sealing is derived from sixteen exact COPY write-ack proofs.
 input logic resident_sealed,input logic [127:0] resident_key,input logic [9:0] resident_base,
'''+s[b:]
s=s.replace(' input logic [127:0] copy_key,input logic [10:0] copy_committed_prefix,\n','')
s=s.replace('logic scope_live,cancelled;logic [15:0] current_window_generation;logic [31:0] current_window_session,current_window_ticket;logic [5:0] current_load_shift;',
            'logic scope_live,cancelled;logic [5:0] current_load_shift;')
s=s.replace('scope_data[48+:16]==2&&current_use[0]', 'scope_data[48+:16]==1&&current_use[0]')
a=s.index(' // A physical 256B staging')
b=s.index(' wire A_namespace_needed',a)
s=s[:a]+''' // No staging alias: base points at K=0 of the sealed 4096B window.
 wire [9:0] input_word=resident_base+{2'd0,k[10:7],4'd0};
 wire matches_resident=resident_sealed&&resident_key==input_key&&
     scope_data[672+:16]=={6'd0,resident_base}&&scope_data[608+:16]==16'd2048&&
     scope_data[48+:16]==16'd1;
 wire [10:0] effective_copy_prefix=(matches_resident&&scale_lookup_valid)?11'd16:11'd0;
 assign scale_lookup_key=input_key;
 assign scale_lookup_kk=k;
 assign scope_ready=!reset&&!scope_live&&quiescent&&matches_resident;
'''+s[b:]
s=s.replace('first_window_match','matches_resident')
s=s.replace('.cmd_S_base(input_word[9:0])','.cmd_S_base(input_word)')
s=s.replace('.copy_key,.copy_committed_prefix', '.copy_key(resident_key),.copy_committed_prefix')
for field in ('generation','session','ticket'):
    s=s.replace(f'=current_window_{field};','=0;')
    s=s.replace(f'current_window_{field}<=0;','')
    s=s.replace(f'current_window_{field}<=stream_window_{field};','')
s=s.replace('tx_reject_status,input_word[31:10],','tx_reject_status,')
assert 'stream_window_' not in s and 'current_window_' not in s
(p/'p_native_resident_x_candidate.sv').write_text(s,encoding='utf-8')

