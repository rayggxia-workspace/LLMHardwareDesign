"""Generate matched streamed vs resident-X K2048 Gate/Up RTL fixtures."""
from pathlib import Path
p=Path(__file__).parent
s=(p/'rtl/tb_p_gateup2048.sv').read_text(encoding='utf-8')
s=s.replace('module tb_p_gateup2048;', "module tb_p_resident_x_compare #(parameter bit RESIDENT=1'b0);")
s=s.replace(' p_native_stream_m2_bounded exec(.*);',''' logic resident_sealed;
 logic [127:0] resident_key;
 logic [9:0] resident_base;
 wire [9:0] copy_destination=RESIDENT?(10'd256+{2'd0,tile_k[10:7],4'd0}):10'd0;
 logic resident_publish,resident_scope_live,bad_copy_ticket;
 if(RESIDENT)begin:resident_provider
   p_native_resident_x_candidate exec(.*);
   resident_x16_directory dir(
    .clk,.reset,.cfg_valid(directory_cfg),.cfg_ready(directory_ready),.cfg_key(scope_data[128+:128]),.cfg_base(10'd256),
    .storage_and_consumers_drained(rx_idle&&copy_idle&&owners==0&&quiescent&&!resident_scope_live),
    .cfg_error(directory_bad),.publish_valid(resident_publish),.publish_ready(directory_publish_ready),.publish_error(directory_pub_bad),
    .header_key(meta_key),.copy_key,.header_k(meta_k),.copy_k,.header_gen(meta_gen),.copy_gen,
    .header_session(meta_session),.copy_session,.header_ticket(meta_ticket),.copy_ticket(copy_ticket^{31'd0,bad_copy_ticket}),
    .header_shift(meta_shift),.copy_base(copy_destination),.copy_ack_prefix(copy_committed_prefix),.copy_done,.copy_error,
    .resident_sealed,.resident_key,.resident_base,.lookup_key(scale_lookup_key),.lookup_k(scale_lookup_kk),
    .lookup_valid(scale_lookup_valid),.lookup_shift(scale_lookup_shift));
   assign exec_contexts=exec.contexts_live;
   assign exec_detached=exec.pair_detached;
   assign exec_state=exec.state;
 end else begin:stream_provider
   p_native_stream_m2_bounded exec(.*);
   assign directory_ready=1;assign directory_publish_ready=1;assign directory_bad=0;assign directory_pub_bad=0;
   assign scale_lookup_valid=data_enabled&&meta_key==scale_lookup_key&&meta_k==scale_lookup_kk;
   assign scale_lookup_shift=meta_shift;
   assign resident_sealed=0;assign resident_key=0;assign resident_base=0;
   assign exec_contexts=exec.contexts_live;
   assign exec_detached=exec.pair_detached;
   assign exec_state=exec.state;
 end
 logic [15:0] exec_contexts;
 logic [4:0] exec_state;
 logic exec_detached;''')
s=s.replace('p_scope_range_service #(.NATIVE_STREAM_A16(1\'b1))', 'p_scope_range_service #(.NATIVE_STREAM_A16(!RESIDENT),.NATIVE_RESIDENT_X_K2048(RESIDENT))')
a=s.index(' logic directory_cfg,')
b=s.index(' logic mc_req_valid,',a)
s=s[:a]+''' logic directory_cfg,directory_ready,directory_publish_ready,directory_bad,directory_pub_bad;
'''+s[b:]
s=s.replace(' assign directory_publish=meta_valid;assign publish_k=meta_k;assign meta_ready=directory_publish_ready;', ' assign meta_ready=1;')
s=s.replace(".start_P_bases(30'd0)", ".start_P_bases({20'd0,copy_destination})")
a=s.index('  if(ar_valid&&ar_ready)assert(')
b=s.index('  assert(copy_faults',a)
s=s[:a]+'''  if(ar_valid&&ar_ready)begin
   if(RESIDENT)begin assert(resident_sealed&&scale_lookup_valid&&ar_address[9:4]==6'd16+{2'd0,scale_lookup_kk[10:7]})
       else $fatal(1,"resident read outside true committed tile");end
   else begin assert(copy_identity&&copy_gen==stream_window_generation&&copy_k==scale_lookup_kk&&
     {1'b0,ar_address}<copy_prefix[0+:11])else $fatal(1,"stream read before true matching COPY ACK");end
  end
  if(RESIDENT&&req_valid&&req_ready&&req_write&&req_address>=256&&req_address<512)
    assert(!resident_sealed&&cp_valid[0]&&cp_ready[0]&&req_address[9:4]==copy_destination[9:4])
      else $fatal(1,"unexpected overwrite of resident input");
'''+s[b:]
s=s.replace('A_memory[case_id*32+tile*16+word_index/2]','A_memory[tile*16+word_index/2]')
s=s.replace('scopes[0:0]','scopes[0:1]').replace('expect_memory[0:3]','expect_memory[0:7]').replace('DDR_memory[0:543]','DDR_memory[0:1087]')
a=s.index('    assert((mc_req_address')
b=s.index(';',a)
s=s[:a]+'''    assert(mc_req_address[63:23]==0&&mc_req_address[19:0]<20'h04400&&
           mc_req_address[22:20]>=1&&mc_req_address[22:20]<=4&&mc_req_address[5:0]==0)else $fatal(1,"DDR address")'''+s[b:]
a=s.index('pending_data[free_slot]<=DDR_memory')
b=s.index(';',a)
s=s[:a]+'''pending_data[free_slot]<=DDR_memory[(int'(mc_req_address[22:20])-1)*272+int'(mc_req_address[19:6])]'''+s[b:]
s=s.replace('exec.pair_detached;','exec_detached;').replace('if(exec.pair_detached&&!old_detached)','if(exec_detached&&!old_detached)').replace('$countones(exec.contexts_live)','$countones(exec_contexts)').replace('exec.state,','exec_state,')
# Keep the observation point explicitly inside each generated provider.
s=s.replace('assign exec_detached=exec_detached;', 'assign exec_detached=exec.pair_detached;')
s=s.replace(' integer stage_start;', ' integer stage_start,fill_start,fill_cycles,scope0_cycles,scope1_cycles,service_terminal_cycle;')
s=s.replace(' integer load_proofs,poison_writes,stale_prefix_checks;', ' integer load_proofs;')
s=s.replace('load_proofs,poison_writes,stale_prefix_checks','load_proofs')
a=s.index(' initial begin\n\n  boot_cycles')
b=s.index(' initial begin #2000000;',a)
s=s[:a]+''' task automatic transfer_tile(input integer tile,input integer stripe);
  tile_generation=tile_generation+1;tile_k=16'(tile*128);tile_session=32'(stripe+1);tile_ticket=32'(stripe*16+tile+1);proof_accepted=0;
  stage_start=cycle;
  for(integer wi=0;wi<32;wi=wi+1)u_host_word(32+wi,make_S32(tile,wi));
  boot_cycles=boot_cycles+cycle-stage_start;stage_start=cycle;
  q_cmd=1;do @(posedge clk);while(!q_ready);@(negedge clk);q_cmd=0;
  while(!q_done)@(negedge clk);
  assert(!q_error&&!q_cancelled&&q_done_key==scope_data[128+:128]&&q_done_k==tile_k&&q_done_words==16&&q_written_mask==16'hffff&&q_shift==0)
    else $fatal(1,"true S32 producer");
  quant_cycles=quant_cycles+cycle-stage_start;stage_start=cycle;
  lease_start=1;do @(posedge clk);while(!lease_ready);@(negedge clk);lease_start=0;
  h_start=1;do @(posedge clk);while(!h_start_ready);@(negedge clk);h_start=0;
  while(!h_done)@(negedge clk);assert(!h_error);h_take=1;pause();h_take=0;
  header_cycles=header_cycles+cycle-stage_start;stage_start=cycle;
  copy_start=1;do @(posedge clk);while(!copy_start_ready);@(negedge clk);copy_start=0;
  while(!copy_done)@(negedge clk);assert(!copy_error);
  if(RESIDENT)begin
   if(tile==0)begin
    bad_copy_ticket=1;resident_publish=1;pause();
    assert(directory_pub_bad&&!resident_sealed)else $fatal(1,"wrong COPY ticket published");
    resident_publish=0;pause();bad_copy_ticket=0;
   end
   resident_publish=1;assert(directory_publish_ready);pause();resident_publish=0;
   assert(!directory_pub_bad&&resident_sealed==(tile==15))else $fatal(1,"seal without all sixteen true tiles");
  end
  copy_take=1;pause();copy_take=0;
  copy_cycles=copy_cycles+cycle-stage_start;stage_start=cycle;
  if(!RESIDENT)begin
   while(!a_load_proof_valid)@(negedge clk);
   assert(!a_load_proof_error&&a_source_reads_drained&&a_load_proof_key==meta_key&&
    a_load_proof_window_generation==meta_gen&&a_load_proof_window_session==meta_session&&a_load_proof_window_ticket==meta_ticket&&
    a_load_proof_k_elements==meta_k&&a_load_proof_A_generation!=0&&a_load_proof_A_slot==1'(tile)&&a_load_proof_shift==q_shift)
      else $fatal(1,"true streaming LOAD proof");
   a_load_proof_ready=1;pause();a_load_proof_ready=0;load_proofs=load_proofs+1;
   load_wait_cycles=load_wait_cycles+cycle-stage_start;
  end
  proof_accepted=1;release_window=1;do @(posedge clk);while(!release_ready);@(negedge clk);release_window=0;
  assert(rx_idle);q_take=1;pause();q_take=0;
 endtask
 initial begin
  boot_cycles=0;quant_cycles=0;header_cycles=0;copy_cycles=0;load_wait_cycles=0;scope_cycles=0;stage_start=0;
  fill_start=0;fill_cycles=0;scope0_cycles=0;scope1_cycles=0;service_terminal_cycle=0;
  resident_publish=0;resident_scope_live=0;bad_copy_ticket=0;
  a_load_proof_ready=RESIDENT;allow_native_A=1;load_proofs=0;
  reset=1;service_valid=0;service_done_ready=0;scope_cancel=0;scope_owner=0;scope_data=0;
  directory_cfg=0;q_cmd=0;q_take=0;h_start=0;h_take=0;lease_start=0;release_window=0;copy_start=0;copy_take=0;
  tile_generation=0;tile_k=0;tile_session=0;tile_ticket=0;proof_accepted=0;
  uh_valid=0;uh_write=1;uh_rsp_ready=0;uh_address=0;uh_data=0;real_copy_ACKs=0;real_copy_reads=0;real_headers=0;real_quantizations=0;
  host_mode=1;host_valid=0;host_write=1;host_address=0;host_data=0;host_response_ready=0;
  allow_request=1;allow_ACK=1;allow_A_response=1;case_id=0;seed=1;
  if($value$plusargs("SEED=%d",seed))begin end
  vectors="results/p-vectors";if($value$plusargs("VECTORS=%s",vectors))begin end
  trace_path="p-resident.csv";if($value$plusargs("TRACE=%s",trace_path))begin end
  $readmemh({vectors,RESIDENT?"/resident-scopes.mem":"/scopes.mem"},scopes);
  $readmemh({vectors,"/A.mem"},A_memory);$readmemh({vectors,"/DDR.mem"},DDR_memory);$readmemh({vectors,"/expected.mem"},expect_memory);
  trace_file=$fopen(trace_path,"w");assert(trace_file!=0);$fwrite(trace_file,"cycle,event,case,identity,detail,value\\n");
  pause(4);reset=0;pause();scope_data=scopes[0];host_mode=0;
  if(RESIDENT)begin
   fill_start=cycle;directory_cfg=1;do @(posedge clk);while(!directory_ready);@(negedge clk);directory_cfg=0;
   assert(!directory_bad&&!resident_sealed&&resident_base==256);
   for(integer tile=0;tile<16;tile=tile+1)transfer_tile(tile,0);
   fill_cycles=cycle-fill_start;
   assert(resident_sealed&&resident_key==scope_data[128+:128]&&real_copy_ACKs==256);
  end
  for(integer ci=0;ci<2;ci=ci+1)begin
   case_id=ci;scope_data=scopes[ci];scope_owner={32'd1,32'd7,32'd8,32'(ci+1)};host_mode=0;
   pause();start_cycle=32'(cycle);service_valid=1;
   do @(posedge clk);while(!(service_ready&&scope_ready));@(negedge clk);service_valid=0;resident_scope_live=1;
   fork
    begin if(!RESIDENT)for(integer tile=0;tile<16;tile=tile+1)transfer_tile(tile,ci);end
    begin
     while(!service_done_valid)begin
      pause(2+(seed%3));allow_ACK=0;allow_A_response=0;pause(1);allow_ACK=1;allow_A_response=1;
      if(RESIDENT)assert(!directory_ready);
     end
    end
    begin
     while(!service_done_valid)@(negedge clk);
     service_terminal_cycle=cycle;
     assert(service_done_owner==scope_owner&&service_done_ticket==scope_owner[31:0]&&service_done_status==0)
       else $fatal(1,"scope terminal failed status=%0d",service_done_status);
    end
   join
   scope_cycles=service_terminal_cycle-int'(start_cycle);if(ci==0)scope0_cycles=scope_cycles;else scope1_cycles=scope_cycles;
   service_done_ready=1;pause();service_done_ready=0;resident_scope_live=0;pause(2);
   assert(quiescent&&A_live==0&&command_occupied==0&&result_occupied==0&&pending_mask==0)else $fatal(1,"owner leak");
   for(integer way=0;way<2;way=way+1)for(integer outword=0;outword<2;outword=outword+1)
    host_word(0,128+64*ci+32*way+outword,expect_memory[4*ci+2*way+outword]);
   $fwrite(trace_file,"%0d,CASE_DONE,%0d,%0d,%0d,%0d\\n",cycle,ci,scope_cycles,A_reads,ACKs);
  end
  assert(real_quantizations==(RESIDENT?16:32)&&real_copy_ACKs==(RESIDENT?256:512)&&real_copy_ACKs==real_copy_reads&&
    real_headers==(RESIDENT?32:64)&&load_proofs==(RESIDENT?0:32))else $fatal(1,"input accounting");
  assert(accepted==1088&&accepted==returned&&ACKs==8&&writes==8&&completed==64&&record_count==64&&A_reads==512&&pair_detaches==32&&peak_contexts==2)
    else $fatal(1,"execution accounting req=%0d ack=%0d records=%0d reads=%0d pairs=%0d",accepted,ACKs,completed,A_reads,pair_detaches);
  $display("RESIDENT_X_TIMING mode=%0d startup=%0d first=%0d second=%0d accounted_total=%0d fixture_source_boot=%0d quant=%0d header=%0d copy=%0d post_copy_load_wait=%0d",
    RESIDENT,fill_cycles,scope0_cycles,scope1_cycles,fill_cycles+scope0_cycles+scope1_cycles,boot_cycles,quant_cycles,header_cycles,copy_cycles,load_wait_cycles);
  $display("PASS p_resident_x_compare mode=%0d seed=%0d scopes=2 W64=%0d S128ACK=%0d Aread=%0d copy=%0d",
    RESIDENT,seed,accepted,ACKs,A_reads,real_copy_ACKs);
  $fclose(trace_file);$finish;
 end
'''+s[b:]
s=s.replace('assert(copy_faults==0&&rx_rejected==0&&h_rejected==0&&q_rejected==0&&!lease_error)', 'assert(copy_faults==0&&rx_rejected==0&&h_rejected==0&&q_rejected==0&&!lease_error)')
s=s.replace('!rejected_complete&&!directory_bad&&!directory_pub_bad', '!rejected_complete&&!directory_bad&&(!directory_pub_bad||bad_copy_ticket)')
s=s.replace('wire unused_diagnostics=^{directory_cfg,directory_publish,publish_k,', 'wire unused_diagnostics=^{directory_cfg,meta_valid,resident_publish,stream_window_valid,stream_window_key,stream_window_k_elements,stream_window_session,stream_window_ticket,copy_progress_valid,copy_progress_generation,copy_progress_session,copy_progress_ticket,copy_progress_k_elements,resident_scope_live,bad_copy_ticket,directory_pub_bad,')
(p/'rtl/tb_p_resident_x_compare.sv').write_text(s,encoding='utf-8')

# Strong baseline: one actual U.S A16 fill, then real copies for each stripe.
s=s.replace("parameter bit RESIDENT=1'b0);", """parameter logic [1:0] MODE=2'd0);
 localparam bit RESIDENT=(MODE==2'd1), SOURCE_REUSE=(MODE==2'd2);
 logic source_cfg,source_cfg_ready,source_cfg_bad,source_publish_ready,source_publish_bad,source_scale_valid,source_fill_done;
 logic [5:0] source_shift;
 logic [31:0] source_rejections;
 wire [9:0] source_base=10'd256+(SOURCE_REUSE?{2'd0,tile_k[10:7],4'd0}:10'd0);
 if(SOURCE_REUSE)begin:source_directory
  a_scale_directory32 source_X_directory(.clk,.reset,.cfg_valid(source_cfg),.cfg_ready(source_cfg_ready),
    .cfg_key(scope_data[128+:128]),.cfg_first_kk(16'd0),.cfg_tiles(6'd16),.cfg_stride3(1'b0),
    .storage_released(!source_fill_done&&rx_idle&&copy_idle&&uowners==0),.leases_drained(quiescent&&!resident_scope_live),
    .cfg_rejected(source_cfg_bad),.publish_valid(q_done&&q_take),.publish_ready(source_publish_ready),
    .publish_key(q_done_key),.publish_kk(q_done_k),.publish_shift(q_shift),.publish_written_mask(q_written_mask),
    .publish_error(q_error||q_cancelled),.publish_rejected(source_publish_bad),.lookup_key(scope_data[128+:128]),
    .lookup_kk(tile_k),.lookup_valid(source_scale_valid),.lookup_shift(source_shift),.rejected_publications(source_rejections));
 end else begin:no_source_directory
  assign source_cfg_ready=0;assign source_cfg_bad=0;assign source_publish_ready=0;assign source_publish_bad=0;
  assign source_scale_valid=0;assign source_shift=0;assign source_rejections=0;
 end""")
s=s.replace(".cmd_destination(10'd256)", ".cmd_destination(source_base)")
s=s.replace(".start_key(q_done_key),.start_generation(tile_generation),.start_kk(q_done_k),.start_written_mask(q_written_mask),",
 """ .start_key(SOURCE_REUSE?scope_data[128+:128]:q_done_key),.start_generation(tile_generation),
  .start_kk(SOURCE_REUSE?tile_k:q_done_k),.start_written_mask(SOURCE_REUSE?(source_scale_valid?16'hffff:16'd0):q_written_mask),""")
s=s.replace(".start_ticket(tile_ticket),.start_shift(q_shift)", ".start_ticket(tile_ticket),.start_shift(SOURCE_REUSE?source_shift:q_shift)")
s=s.replace(".start_producer_error(q_error||q_cancelled)", ".start_producer_error(SOURCE_REUSE?!source_scale_valid:(q_error||q_cancelled))")
s=s.replace(".start_U_base(10'd256)", ".start_U_base(source_base)")
a=s.index('  stage_start=cycle;\n  for(integer wi=0;wi<32;')
b=s.index('  lease_start=1;',a)
quant_body=s[a:b]
s=s[:a]+'''  if(!SOURCE_REUSE)quantize_tile(tile);
  else begin assert(source_fill_done&&source_scale_valid);stage_start=cycle;end
'''+s[b:]
a=s.index(' task automatic transfer_tile(')
s=s[:a]+''' task automatic quantize_tile(input integer tile);
'''+quant_body+''' endtask
'''+s[a:]
s=s.replace("a_load_proof_shift==q_shift)", "a_load_proof_shift==(SOURCE_REUSE?source_shift:q_shift))")
s=s.replace("assert(rx_idle);q_take=1;pause();q_take=0;", "assert(rx_idle);if(!SOURCE_REUSE)begin q_take=1;pause();q_take=0;end")
s=s.replace("resident_publish=0;resident_scope_live=0;bad_copy_ticket=0;",
            "resident_publish=0;resident_scope_live=0;bad_copy_ticket=0;source_cfg=0;source_fill_done=0;")
s=s.replace("  for(integer ci=0;ci<2;ci=ci+1)begin",
'''  if(SOURCE_REUSE)begin
   fill_start=cycle;source_cfg=1;do @(posedge clk);while(!source_cfg_ready);@(negedge clk);source_cfg=0;
   assert(!source_cfg_bad);
   for(integer tile=0;tile<16;tile=tile+1)begin
    tile_generation=tile_generation+1;tile_k=16'(tile*128);quantize_tile(tile);
    assert(source_publish_ready);q_take=1;pause();q_take=0;
    assert(!source_publish_bad&&source_scale_valid&&source_shift==q_shift);
   end
   source_fill_done=1;fill_cycles=cycle-fill_start;
  end
  for(integer ci=0;ci<2;ci=ci+1)begin''')
s=s.replace("  assert(copy_faults==0", """  if(SOURCE_REUSE&&source_fill_done)begin
   assert(source_rejections==0&&!source_cfg_ready);
   if(unv&&unready&&unw&&una>=256&&una<512)$fatal(1,"source resident window overwritten");
  end
  assert(copy_faults==0""")
s=s.replace("real_quantizations==(RESIDENT?16:32)", "real_quantizations==((RESIDENT||SOURCE_REUSE)?16:32)")
s=s.replace("    RESIDENT,fill_cycles,", "    MODE,fill_cycles,")
s=s.replace("    RESIDENT,seed,accepted,", "    MODE,seed,accepted,")
s=s.replace("unused_diagnostics=^{directory_cfg,","unused_diagnostics=^{source_cfg,source_fill_done,source_cfg_ready,source_cfg_bad,source_publish_ready,source_publish_bad,source_rejections,directory_cfg,")
(p/'rtl/tb_p_resident_x_compare.sv').write_text(s,encoding='utf-8')

# Wider qualified scope and one executor switching between the two providers.
s=s.replace("parameter logic [1:0] MODE=2'd0);","parameter logic [1:0] MODE=2'd0, parameter int GROUPS=1);")
s=s.replace("SOURCE_REUSE=(MODE==2'd2);","SOURCE_REUSE=(MODE==2'd2), COMBINED=(MODE==2'd3), HAS_RESIDENT=RESIDENT||COMBINED;\n wire use_resident=HAS_RESIDENT&&scope_data[48+:16]==16'd1;")
s=s.replace("copy_destination=RESIDENT?", "copy_destination=use_resident?")
s=s.replace(" if(RESIDENT)begin:resident_provider\n   p_native_resident_x_candidate exec(.*);",
''' if(COMBINED)begin:dual_provider
   p_native_a16_dual_profile exec(.*);
   assign exec_contexts=exec.contexts_live;
   assign exec_detached=exec.pair_detached;
   assign exec_state=exec.state;
 end else if(RESIDENT)begin:resident_provider
   p_native_resident_x_candidate exec(.*);
   assign exec_contexts=exec.contexts_live;
   assign exec_detached=exec.pair_detached;
   assign exec_state=exec.state;
 end else begin:stream_provider
   p_native_stream_m2_bounded exec(.*);
   assign exec_contexts=exec.contexts_live;
   assign exec_detached=exec.pair_detached;
   assign exec_state=exec.state;
 end
 if(HAS_RESIDENT)begin:resident_directory
   logic dir_lookup_valid;
   logic [5:0] dir_shift;''')
a=s.index('.lookup_valid(scale_lookup_valid),.lookup_shift(scale_lookup_shift));')
b=s.index(' logic [15:0] exec_contexts;',a)
s=s[:a]+'''.lookup_valid(dir_lookup_valid),.lookup_shift(dir_shift));
   assign scale_lookup_valid=use_resident?dir_lookup_valid:(data_enabled&&meta_key==scale_lookup_key&&meta_k==scale_lookup_kk);
   assign scale_lookup_shift=use_resident?dir_shift:meta_shift;
 end else begin:no_resident_directory
   assign directory_ready=1;assign directory_publish_ready=1;assign directory_bad=0;assign directory_pub_bad=0;
   assign scale_lookup_valid=data_enabled&&meta_key==scale_lookup_key&&meta_k==scale_lookup_kk;
   assign scale_lookup_shift=meta_shift;
   assign resident_sealed=0;assign resident_key=0;assign resident_base=0;
 end
'''+s[b:]
s=s.replace('.NATIVE_STREAM_A16(!RESIDENT),.NATIVE_RESIDENT_X_K2048(RESIDENT)', '.NATIVE_STREAM_A16(!HAS_RESIDENT),.NATIVE_RESIDENT_X_K2048(RESIDENT),.NATIVE_DUAL_A16(COMBINED)')
s=s.replace('if(RESIDENT)begin assert(resident_sealed','if(use_resident)begin assert(resident_sealed')
s=s.replace('if(RESIDENT&&req_valid','if(HAS_RESIDENT&&req_valid')
s=s.replace('scopes[0:1];logic [127:0] A_memory[0:255],expect_memory[0:7]','scopes[0:1],resident_scopes[0:1];logic [127:0] A_memory[0:255],expect_memory[0:8*GROUPS-1]')
s=s.replace('DDR_memory[0:1087]','DDR_memory[0:1088*GROUPS-1]')
s=s.replace("mc_req_address[19:0]<20'h04400", "mc_req_address[19:0]<20'(GROUPS*17408)")
s=s.replace("-1)*272+int'", "-1)*272*GROUPS+int'")
s=s.replace('  if(RESIDENT)begin\n   if(tile==0)', '  if(use_resident)begin\n   if(tile==0)')
s=s.replace('  if(!RESIDENT)begin\n   while(!a_load_proof_valid)', '  if(!use_resident)begin\n   while(!a_load_proof_valid)')
s=s.replace('  $readmemh({vectors,RESIDENT?"/resident-scopes.mem":"/scopes.mem"},scopes);',
            '  $readmemh({vectors,"/scopes.mem"},scopes);$readmemh({vectors,"/resident-scopes.mem"},resident_scopes);')
s=s.replace('pause();scope_data=scopes[0];host_mode=0;\n  if(RESIDENT)',
            'pause();scope_data=HAS_RESIDENT?resident_scopes[0]:scopes[0];host_mode=0;\n  if(HAS_RESIDENT)')
s=s.replace('case_id=ci;scope_data=scopes[ci];', 'case_id=ci;scope_data=(RESIDENT||(COMBINED&&ci==0))?resident_scopes[ci]:scopes[ci];')
s=s.replace('service_valid=0;resident_scope_live=1;', 'service_valid=0;resident_scope_live=1;a_load_proof_ready=use_resident;')
s=s.replace('begin if(!RESIDENT)for(integer tile=', 'begin if(!use_resident)for(integer tile=')
s=s.replace('if(RESIDENT)assert(!directory_ready);','if(HAS_RESIDENT)assert(!directory_ready);')
s=s.replace('outword<2;outword=outword+1)', 'outword<2*GROUPS;outword=outword+1)')
s=s.replace('expect_memory[4*ci+2*way+outword]', 'expect_memory[4*GROUPS*ci+2*GROUPS*way+outword]')
s=s.replace('load_proofs==(RESIDENT?0:32)', 'load_proofs==(RESIDENT?0:(COMBINED?16:32))')
s=s.replace('accepted==1088&&accepted==returned&&ACKs==8&&writes==8&&completed==64&&record_count==64&&A_reads==512&&pair_detaches==32&&peak_contexts==2',
            'accepted==1088*GROUPS&&accepted==returned&&ACKs==8*GROUPS&&writes==8*GROUPS&&completed==64*GROUPS&&record_count==64*GROUPS&&A_reads==512&&pair_detaches==32*GROUPS&&peak_contexts==2*GROUPS')
s=s.replace('mode=%0d seed=%0d scopes=2 W64=', 'mode=%0d seed=%0d scopes=2 groups=%0d W64=')
s=s.replace('MODE,seed,accepted,ACKs', 'MODE,seed,GROUPS,accepted,ACKs')
(p/'rtl/tb_p_resident_x_compare.sv').write_text(s,encoding='utf-8')

# Lazy source retention has no full-X barrier before the first projection.
s=s.replace("parameter logic [1:0] MODE=2'd0", "parameter logic [2:0] MODE=3'd0")
s=s.replace("(MODE==2'd1), SOURCE_REUSE=(MODE==2'd2), COMBINED=(MODE==2'd3),",
            "(MODE==3'd1), SOURCE_REUSE=(MODE==3'd2||MODE==3'd4), COMBINED=(MODE==3'd3), LAZY_SOURCE=(MODE==3'd4),")
s=s.replace(" wire use_resident=HAS_RESIDENT", " wire source_tile_reuse=SOURCE_REUSE&&(!LAZY_SOURCE||case_id!=0);\n wire use_resident=HAS_RESIDENT")
s=s.replace("SOURCE_REUSE?scope_data[128+:128]:q_done_key", "source_tile_reuse?scope_data[128+:128]:q_done_key")
s=s.replace("SOURCE_REUSE?tile_k:q_done_k", "source_tile_reuse?tile_k:q_done_k")
s=s.replace("SOURCE_REUSE?(source_scale_valid?16'hffff:16'd0):q_written_mask", "source_tile_reuse?(source_scale_valid?16'hffff:16'd0):q_written_mask")
s=s.replace("SOURCE_REUSE?source_shift:q_shift", "source_tile_reuse?source_shift:q_shift")
s=s.replace("SOURCE_REUSE?!source_scale_valid:(q_error||q_cancelled)", "source_tile_reuse?!source_scale_valid:(q_error||q_cancelled)")
s=s.replace("if(!SOURCE_REUSE)quantize_tile(tile);", "if(!source_tile_reuse)quantize_tile(tile);")
s=s.replace("assert(rx_idle);if(!SOURCE_REUSE)begin q_take=1;pause();q_take=0;end",
 """assert(rx_idle);if(!source_tile_reuse)begin
   if(SOURCE_REUSE)assert(source_publish_ready);
   q_take=1;pause();q_take=0;
   if(SOURCE_REUSE)assert(!source_publish_bad&&source_scale_valid&&source_shift==q_shift);
  end""")
s=s.replace("   for(integer tile=0;tile<16;tile=tile+1)begin\n    tile_generation=tile_generation+1;",
            "   if(!LAZY_SOURCE)for(integer tile=0;tile<16;tile=tile+1)begin\n    tile_generation=tile_generation+1;")
s=s.replace("source_fill_done=1;fill_cycles=cycle-fill_start;", "source_fill_done=!LAZY_SOURCE;fill_cycles=cycle-fill_start;")
s=s.replace("service_done_ready=0;resident_scope_live=0;pause(2);", "service_done_ready=0;resident_scope_live=0;if(LAZY_SOURCE)source_fill_done=1;pause(2);")
(p/'rtl/tb_p_resident_x_compare.sv').write_text(s,encoding='utf-8')

