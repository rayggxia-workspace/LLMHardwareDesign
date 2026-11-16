"""Real K2048 Gate/Up projection, 16 streaming A tiles and bounded pair preparation."""
from pathlib import Path
p=Path(__file__).parent;s=(p/'rtl/tb_p_long_stream.sv').read_text(encoding='utf-8')
s=s.replace('p_long_stream','p_gateup2048').replace('p_native_stream_record_executor exec','p_native_stream_m2_bounded exec')
s=s.replace('A_memory[0:1375],expect_memory[0:1]','A_memory[0:255],expect_memory[0:3]').replace('DDR_memory[0:1461]','DDR_memory[0:543]')
s=s.replace("assert(mc_req_address>=64'h100000+64'(case_id)*64'h10000&&mc_req_address<64'h100000+64'd1462*64)","assert((mc_req_address>=64'h100000&&mc_req_address<64'h104400)||(mc_req_address>=64'h200000&&mc_req_address<64'h204400))")
s=s.replace("DDR_memory[int'((mc_req_address-64'h100000)>>6)]", "DDR_memory[mc_req_address>=64'h200000 ? 272+int'((mc_req_address-64'h200000)>>6) : int'((mc_req_address-64'h100000)>>6)]")
s=s.replace(' integer cycle,seed,',' integer boot_cycles,quant_cycles,header_cycles,copy_cycles,load_wait_cycles,scope_cycles,peak_contexts,pair_detaches;\n integer stage_start;\n logic old_detached;\n integer cycle,seed,')
s=s.replace('   cycle<=0;pending_mask<=0;','   peak_contexts<=0;pair_detaches<=0;old_detached<=0;\n   cycle<=0;pending_mask<=0;')
s=s.replace('   cycle<=cycle+1;\n   if(mc_req_valid', '''   cycle<=cycle+1;
   old_detached<=exec.pair_detached;
   if(exec.pair_detached&&!old_detached)pair_detaches<=pair_detaches+1;
   if($countones(exec.contexts_live)>peak_contexts)peak_contexts<=$countones(exec.contexts_live);
   if(mc_req_valid''')
s=s.replace('  a_load_proof_ready=0;', '  boot_cycles=0;quant_cycles=0;header_cycles=0;copy_cycles=0;load_wait_cycles=0;scope_cycles=0;stage_start=0;\n  a_load_proof_ready=0;',1)
s=s.replace('      for(integer wi=0;wi<32;wi=wi+1)u_host_word(32+wi,make_S32(tile,wi));', '      stage_start=cycle;for(integer wi=0;wi<32;wi=wi+1)u_host_word(32+wi,make_S32(tile,wi));boot_cycles=boot_cycles+cycle-stage_start;stage_start=cycle;')
s=s.replace('      lease_start=1;', '      quant_cycles=quant_cycles+cycle-stage_start;stage_start=cycle;\n      lease_start=1;')
s=s.replace('      // RX has a new header', '      header_cycles=header_cycles+cycle-stage_start;\n      // RX has a new header')
s=s.replace('      copy_start=1;', '      stage_start=cycle;copy_start=1;')
s=s.replace('      while(!a_load_proof_valid)@(negedge clk);allow_native_A=0;', '      copy_cycles=copy_cycles+cycle-stage_start;stage_start=cycle;\n      while(!a_load_proof_valid)@(negedge clk);allow_native_A=0;load_wait_cycles=load_wait_cycles+cycle-stage_start;')
s=s.replace('   service_done_ready=1;pause();', '   scope_cycles=cycle-int\'(start_cycle);service_done_ready=1;pause();')
s=s.replace("   for(integer outword=0;outword<int'(scope_data[592+:5])*2;outword=outword+1)host_word(0,128+outword,expect_memory[ci*4+outword]);", '   for(integer way=0;way<2;way=way+1)for(integer outword=0;outword<2;outword=outword+1)\n     host_word(0,128+32*way+outword,expect_memory[2*way+outword]);')
s=s.replace('load_proofs==86&&poison_writes==1376&&stale_prefix_checks==430&&real_copy_ACKs==1376&&real_copy_reads==1376&&real_headers==172&&real_quantizations==86','load_proofs==16&&poison_writes==256&&stale_prefix_checks==80&&real_copy_ACKs==256&&real_copy_reads==256&&real_headers==32&&real_quantizations==16')
s=s.replace('accepted==returned&&ACKs==2&&writes==2&&completed==86&&record_count==86&&A_reads==1376','accepted==544&&accepted==returned&&ACKs==4&&writes==4&&completed==32&&record_count==32&&A_reads==256&&pair_detaches==16&&peak_contexts==2')
s=s.replace('  $display("PASS p_gateup2048 seed=%0d cases=1 fullK11008', '  $display("GATEUP_TIMING scope=%0d fixture_source_boot=%0d quant=%0d header=%0d copy=%0d post_copy_load_wait=%0d pair_detaches=%0d peak_ctx=%0d",scope_cycles,boot_cycles,quant_cycles,header_cycles,copy_cycles,load_wait_cycles,pair_detaches,peak_contexts);\n  $display("PASS p_gateup2048 seed=%0d cases=1 fullK2048')
(p/'rtl/tb_p_gateup2048.sv').write_text(s,encoding='utf-8')
s=(p/'p_stream_m2_bounded.sbatch').read_text(encoding='utf-8').replace('p_stream_m2_bounded','p_gateup2048').replace('250M2Pbound','250GateUp2048')
s=s.replace('make_p_executor_vectors.py --records "${RECORDS}"','make_p_gateup2048_vectors.py')
s=s.replace('RECORDS=/public/home/yuzelu/project-circuit/issue250-weight-20261111-33/vectors/records.txt','')
(p/'p_gateup2048.sbatch').write_text(s,encoding='utf-8')
