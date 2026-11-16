"""Actual MC/LC PM+fetch/CRC+globalDMA joined to typed2 quant/COPY/M/S.

One P, eight bounded scopes. Host boot producer S32 is explicit. This does not
implement the whole FFN outer iterator or qualify three-P throughput.
"""
from pathlib import Path
p=Path(__file__).parent
s=(p/'rtl/tb_p_program_fabric.sv').read_text(encoding='utf-8')
c=(p/'rtl/tb_p_copy_stream.sv').read_text(encoding='utf-8')
s=s.replace('tb_p_program_fabric','tb_p_stream_program')
def chunk(text,begin,end):return text[text.index(begin):text.index(end,text.index(begin))]
s=s.replace(' p_native_record_executor exec(.*);',chunk(c,' logic stream_window_valid',' logic service_valid'))
s=s.replace(".NATIVE_LOCAL_CONTIG(1'b1)",".NATIVE_STREAM_A16(1'b1)")
s=s.replace(chunk(s,' logic directory_cfg',' logic mc_req_valid'),chunk(c,' logic directory_cfg',' logic mc_req_valid'))
s=s.replace('.cfg_key(scope_data[128+:128])','.cfg_key(scopes[case_id][128+:128])')
s=s.replace(".cfg_tiles(6'(scope_data[608+:16]>>7))",".cfg_tiles(6'(scopes[case_id][608+:16]>>7))")
s=s.replace('.a_valid,.a_ready,.a_data,.a_session,.a_beat,','.a_valid(a_valid&&allow_native_A),.a_ready(m_a_ready),.a_data,.a_session,.a_beat,')
s=s.replace(' logic host_mode', ' assign a_ready=m_a_ready&&allow_native_A;\n logic host_mode',1)
s=s.replace(chunk(s,' logic host_mode',' logic [1023:0] scopes'),chunk(c,' logic host_mode',' logic [1023:0] scopes'))
s=s.replace(' assign a_ready=m_a_ready&&allow_native_A;\n logic host_mode',' assign a_ready=m_a_ready&&allow_native_A;\n logic host_mode',1)
# helper tasks for the real U producer and S32 payload.
s=s.replace(' task automatic lc_cfg_send',chunk(c,' function automatic [127:0] make_S32',' initial begin')+' task automatic lc_cfg_send',1)
# Boot changes: copy identity is now driven solely by real epoch COPY.
s=s.replace('  copy_key=0;copy_committed_prefix=0;directory_cfg=0;directory_publish=0;publish_k=0;',chunk(c,'  a_load_proof_ready=0;','  host_mode=1;').replace('  reset=1;service_valid=0;service_done_ready=0;scope_cancel=0;scope_owner=0;scope_data=0;','  reset=1;'))
start=s.index('   copy_key=scopes[ci][128+:128]')
end=s.index('   host_mode=0;pause();start_cycle=',start)
s=s[:start]+'''   directory_cfg=1;do @(posedge clk);while(!directory_ready);@(negedge clk);directory_cfg=0;
'''+s[end:]
producer=chunk(c,'     for(integer tile=0;','    end\n    begin\n     while(!service_done_valid)')
s=s.replace('   fork\n    begin\n     while(MC_returns<ci+1)begin','''   fork
    begin
     while(!scope_valid)@(negedge clk);
'''+producer+'''    end
    begin
     while(MC_returns<ci+1)begin''')
s=s.replace('  assert(accepted==returned&&ACKs==24', '  assert(load_proofs==12&&poison_writes==192&&stale_prefix_checks==60&&real_copy_ACKs==192&&real_copy_reads==192&&real_headers==24&&real_quantizations==12)else $fatal(1,"actual streamed program proof accounting");\n  assert(accepted==returned&&ACKs==24')
s=s.replace('PASS p_program_fabric','PASS p_stream_program')
(p/'rtl/tb_p_stream_program.sv').write_text(s,encoding='utf-8')
s=(p/'p_fabric.sbatch').read_text(encoding='utf-8').replace('p_program_fabric','p_stream_program').replace('p_fabric','p_stream_program').replace('250Pfabric','250PstreamPM')
s=s.replace('--mc-assembler "${MCEXP}/assemble_cases.py"','--mc-assembler "${MCEXP}/assemble_cases.py" --stream-a16')
s=s.replace('"${EXP}/rtl/native_s128_mux2.sv"', '"${EXP}/rtl/native_s128_mux3.sv" "${EXP}/rtl/early_copy_3p.sv"')
s=s.replace('"${EXP}/rtl/p_native_record_executor.sv"','"${EXP}/rtl/p_native_stream_record_executor.sv"')
s=s.replace(' "${ROOT_NATIVE_DIR}/p_scope128_decode.sv"', ' "${ROOT_NATIVE_DIR}/s32_a16_tile_quantizer.sv" "${ROOT_NATIVE_DIR}/copy_scale_header_tx.sv" "${ROOT_NATIVE_DIR}/copy_scale_header_rx.sv" "${ROOT_NATIVE_DIR}/early_copy_epoch_3p.sv" \\\n "${ROOT_NATIVE_DIR}/p_scope128_decode.sv"')
(p/'p_stream_program.sbatch').write_text(s,encoding='utf-8')
