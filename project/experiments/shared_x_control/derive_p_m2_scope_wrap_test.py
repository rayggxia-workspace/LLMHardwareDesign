"""Accelerate only initial handle counters; exercise actual FENCE/CRC/data paths."""
from pathlib import Path
p=Path(__file__).parent
s=(p/'rtl/tb_p_m2_program.sv').read_text(encoding='utf-8').replace('tb_p_m2_program','tb_p_m2_scope_wrap').replace('PASS p_m2_program','PASS p_m2_scope_wrap')
s=s.replace(' logic backend_fence_live;',' integer wrapped_execs,early_fence_test;\n logic backend_fence_live;')
s=s.replace('   backend_pending<=0;backend_requests<=0;', '   wrapped_execs<=0;backend_pending<=0;backend_requests<=0;')
s=s.replace('   if(d_fence_valid&&d_fence_ready)begin', '''   if(lc_valid&&lc_ready&&lc_sop&&lc_data[19:16]==3&&lc_data[111:96]==0)begin
    assert(backend_purges>=2+early_fence_test&&exec.fence_count!=0)else $fatal(1,"wrapped generation escaped before actual FENCE");
    wrapped_execs<=wrapped_execs+1;
    $fwrite(trace_file,"%0d,WRAPPED_SCOPE_EXEC,%0d,%0d,0,0\\n",cycle,case_id,lc_data[95:64]);
   end
   if(d_fence_valid&&d_fence_ready)begin''')
s=s.replace('  pause(4);reset=0;pause();', '''  pause(4);reset=0;pause();
  // Two counters start at 65534 only in the generated fixture reset views.
  // No valid/live/epoch/authorization/result owner is initialized artificially.
  assert(exec.context_generation[0]==16'hfffe&&M.scope_generation[0]==16'hfffe)
   else $fatal(1,"near-wrap fixture didn't retain counters");
''')
s=s.replace('backend_purges==1&&debug_beats', 'backend_purges==2+early_fence_test&&wrapped_execs!=0&&debug_beats')
s=s.replace('cases=8 cycles=%0d requests=', 'cases=8 wrapped_execs=%0d true_purges=%0d cycles=%0d requests=')
s=s.replace('seed,cycle,accepted,returned,ACKs,completed,A_reads);', 'seed,wrapped_execs,backend_purges,cycle,accepted,returned,ACKs,completed,A_reads);')
s=s.replace('  pause(4);reset=0;pause();', '  early_fence_test=0;if($value$plusargs("EARLY_FENCE=%d",early_fence_test))begin end\n  pause(4);reset=0;pause();')
(p/'rtl/tb_p_m2_scope_wrap.sv').write_text(s,encoding='utf-8')
s=(p/'p_m2_program.sbatch').read_text(encoding='utf-8').replace('250M2program','250M2ScopeWrap').replace('p_m2_program','p_m2_scope_wrap')
s=s.replace('sha256sum "${EXP}"/rtl', 'srun --exclusive --ntasks=1 --cpus-per-task=10 /usr/bin/python3.11 -B "${EXP}/make_p_m2_wrap_seed.py" --p "${EXP}/rtl/p_native_stream_m2_bounded.sv" --m "${M_SOURCE_DIR}/m_native_leaf_s32.sv" --out results/wrap-seed --early-fence "${P_WRAP_EARLY_FENCE:-0}" --stale-permit-control "${P_WRAP_STALE_PERMIT_CONTROL:-0}"\nsha256sum results/wrap-seed/*.sv "${EXP}"/rtl')
s=s.replace('"${EXP}/rtl/p_native_stream_m2_bounded.sv" "${EXP}/rtl/p_scope_range_service.sv"', 'results/wrap-seed/p_native_stream_m2_bounded.sv "${EXP}/rtl/p_scope_range_service.sv"')
s=s.replace('"${M_SOURCE_DIR}/m_native_leaf_s32.sv" "${M_SOURCE_DIR}/m_native_s32.sv"', 'results/wrap-seed/m_native_leaf_s32.sv "${M_SOURCE_DIR}/m_native_s32.sv"')
s=s.replace('"+CRC=${CRC}"', '"+CRC=${CRC}" "+EARLY_FENCE=${P_WRAP_EARLY_FENCE:-0}"')
(p/'p_m2_scope_wrap.sbatch').write_text(s,encoding='utf-8')

