"""Two input lifetime contracts, one shared record/control/result owner set."""
from pathlib import Path
p=Path(__file__).parent/'rtl'
s=(p/'p_native_stream_m2_bounded.sv').read_text(encoding='utf-8')
s=s.replace('module p_native_stream_m2_bounded #(', 'module p_native_a16_dual_profile #(')
s=s.replace('Candidate fixed staging input for unregistered streamed service2, zero bias.', 'Typed K2048 local-resident service1 and full-K streamed service2; zero bias.')
s=s.replace(' input logic stream_window_valid,input logic [127:0] stream_window_key,', ''' input logic resident_sealed,input logic [127:0] resident_key,input logic [9:0] resident_base,
 input logic stream_window_valid,input logic [127:0] stream_window_key,''')
s=s.replace('wire pair_candidate=scope_data[48+:16]==2&&', 'wire pair_candidate=native_profile_valid&&')
s=s.replace(' wire [31:0] input_word={16\'d0,scope_data[672+:16]};', ''' wire resident_profile=scope_data[48+:16]==16'd1;
 wire stream_profile=scope_data[48+:16]==16'd2;
 wire native_profile_valid=resident_profile||stream_profile;
 wire resident_matches=resident_sealed&&resident_key==input_key&&
     scope_data[672+:16]=={6'd0,resident_base}&&scope_data[608+:16]==16'd2048;
 wire [31:0] input_word={16'd0,scope_data[672+:16]}+
     (resident_profile?{24'd0,k[10:7],4'd0}:32'd0);''')
s=s.replace("wire first_window_match=stream_window_valid&&stream_window_key==input_key&&\n     stream_window_generation!=0&&stream_window_k_elements==record_k;",
 '''wire first_window_match=resident_profile?resident_matches:
     (stream_window_valid&&stream_window_key==input_key&&stream_window_generation!=0&&stream_window_k_elements==record_k);''')
s=s.replace("wire [10:0] effective_copy_prefix=progress_matches?copy_committed_prefix:11'd0;",
 '''wire [10:0] effective_copy_prefix=resident_profile?
     ((resident_matches&&scale_lookup_valid)?11'd16:11'd0):(progress_matches?copy_committed_prefix:11'd0);''')
s=s.replace('assign scope_ready=!reset&&!scope_live&&quiescent;', 'assign scope_ready=!reset&&!scope_live&&quiescent&&(stream_profile||(resident_profile&&resident_matches));')
s=s.replace('.copy_key,.copy_committed_prefix', '.copy_key(resident_profile?resident_key:copy_key),.copy_committed_prefix')
for field in ('generation','session','ticket'):
    s=s.replace(f'current_window_{field}<=stream_window_{field};',f'current_window_{field}<=resident_profile?0:stream_window_{field};')
assert 'resident_matches' in s and 'first_window_match=resident_profile' in s
(p/'p_native_a16_dual_profile.sv').write_text(s,encoding='utf-8')

