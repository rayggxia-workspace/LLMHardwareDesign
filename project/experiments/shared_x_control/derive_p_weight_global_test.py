"""Run the same wide-P fixture through the actual global DMA and real FENCE."""
from pathlib import Path

rtl = Path(__file__).parent / "rtl"
s = (rtl / "tb_p_resident_x_compare.sv").read_text(encoding="utf-8")
g = (rtl / "tb_p_m2_program.sv").read_text(encoding="utf-8")


def edit(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)


edit("module tb_p_resident_x_compare #(parameter logic [2:0] MODE=3'd0, parameter int GROUPS=1);",
     "module tb_p_weight_global #(parameter logic [2:0] MODE=3'd6, parameter int GROUPS=8, parameter logic [31:0] SESSION_LIMIT=32'hffffffe0);")
edit("p_native_weight_prefill #(.FOUR_BANK_LOOKAHEAD(FOUR_BANK))", "p_native_weight_prefill #(.FOUR_BANK_LOOKAHEAD(FOUR_BANK),.SESSION_LIMIT(SESSION_LIMIT))")
edit("p_native_weight_overlap_candidate #(.FOUR_BANK_LOOKAHEAD(1'b1))", "p_native_weight_overlap_candidate #(.FOUR_BANK_LOOKAHEAD(1'b1),.SESSION_LIMIT(SESSION_LIMIT))")
edit("p_native_stream_m2_bounded exec", "p_native_stream_m2_bounded #(.SESSION_LIMIT(SESSION_LIMIT)) exec")
a = s.index(" assign mc_close_ready=1;")
b = s.index(" logic q_cmd", a)
head = s[a:b]
# Only the direct DDR peer constants are removed; keep all real U/P fixtures.
for line in head.splitlines(keepends=True):
    if line.startswith(" assign mc_close_ready=") or line.startswith(" assign mc_fence_"):
        s = s.replace(line, "", 1)
g = g[g.index(" logic [11:0] c_req_valid"):g.index(" always @(posedge clk)begin\n  if(reset)begin\n   cycle<=0")]
for line in g.splitlines(keepends=True):
    if line.startswith(" assign l_mc_"):
        g = g.replace(line, "", 1)
for name, bits in [("req_valid", 9), ("req_address", 576), ("req_tag", 288),
                   ("req_channel", 9), ("req_record_beats", 45), ("rsp_ready", 9),
                   ("close_valid", 9), ("close_tag_base", 288)]:
    old = next(line for line in g.splitlines() if line.startswith(f" assign c_{name}="))
    g = g.replace(old, old[:old.rindex(f",l_mc_{name}")].rsplit(",", 1)[0]+f",{bits}'d0}};", 1)
g = g.replace(" integer decode_case[4],decode_beat[4],decode_record[4],record_bytes_fixture[4];\n", "")
a = g.index(" always_comb begin\n  for(integer lane=0;lane<4;lane=lane+1)begin\n   decode_case")
b = g.index(" always_comb begin\n  response_claimed", a)
g = g[:a]+''' always_comb begin
  for(integer lane=0;lane<4;lane=lane+1)begin
   planned_data[lane]=0;
   if(d_req_address[lane*64+20+:3]>=1&&d_req_address[lane*64+20+:3]<=4&&d_req_address[lane*64+:20]<20'(GROUPS*17408))
     planned_data[lane]=DDR_memory[(int'(d_req_address[lane*64+20+:3])-1)*272*GROUPS+int'(d_req_address[lane*64+6+:14])];
  end
 end
'''+g[b:]
a = g.index("     if(d_req_address[lane*64+:64]>=64'h4000")
b = g.index("     backend_data", a)
g = g[:a]+'''     assert(d_req_address[lane*64+23+:41]==0&&d_req_address[lane*64+20+:3]>=1&&d_req_address[lane*64+20+:3]<=4&&
       d_req_address[lane*64+:20]<20'(GROUPS*17408)&&d_req_address[lane*64+:6]==0&&d_req_tag[lane*64+6+:4]==9)
       else $fatal(1,"W global client/address");
'''+g[b:]
g = g.replace('assert(backend_pending==0&&d_req_valid==0&&d_rsp_valid==0)',
              'assert(backend_pending==0&&d_req_valid==0&&d_rsp_valid==0&&M.table_valid==0&&command_occupied==0&&result_occupied==0)')
a = s.index(" logic [31:0] pending_mask,")
b = s.index(" integer boot_cycles,", a)
s = s[:a]+s[b:]
edit(" integer channel_live[2],last_ACK_cycle,", " integer last_ACK_cycle,")
a = s.index(" always_comb begin\n  free_slot=-1;response_candidate=-1;")
b = s.index(" always @(posedge clk)begin", a)
s = s[:a]+g+s[b:]
edit("cycle<=0;pending_mask<=0;response_slot<=-1;accepted<=0;", "cycle<=0;accepted<=0;")
edit("channel_live[0]<=0;channel_live[1]<=0;last_ACK_cycle<=0;", "last_ACK_cycle<=0;")
a = s.index("    pending_mask[free_slot]<=1;")
b = s.index('    $fwrite(trace_file,"%0d,DDR_REQ', a)
s = s[:a]+"    accepted<=accepted+1;\n"+s[b:]
a = s.index("   if(response_slot<0&&response_candidate>=0)")
b = s.index("   if(ar_valid&&ar_ready)", a)
s = s[:a]+'''   if(mc_rsp_valid&&mc_rsp_ready)begin returned<=returned+1;$fwrite(trace_file,"%0d,DDR_RSP,%0d,%0d,0,0\\n",cycle,case_id,mc_rsp_tag);end
'''+s[b:]
s = s.replace("pending_mask", "backend_pending")
edit(" logic [63:0] backend_pending,planned_pending,response_claimed;",
     """ logic [63:0] backend_pending,planned_pending,response_claimed;
 logic [1:0] hold_weight_responses;
 logic backend_is_younger[64],backend_is_last_beat[64];
 logic [63:0] younger_record_base;""")
edit("if(backend_pending[entry]&&!response_claimed[entry]&&",
     """if(backend_pending[entry]&&!response_claimed[entry]&&
       !(backend_is_last_beat[entry]&&(hold_weight_responses==1||
         (hold_weight_responses==2&&backend_is_younger[entry])))&&""")
edit("     backend_data[backend_free[lane]]<=planned_data[lane];",
     """     backend_data[backend_free[lane]]<=planned_data[lane];
     backend_is_younger[backend_free[lane]]<=d_req_address[lane*64+:64]>=younger_record_base&&
        d_req_address[lane*64+:64]<younger_record_base+64'd1088;
     backend_is_last_beat[backend_free[lane]]<=(int'(d_req_address[lane*64+:20])%1088)==1024;""")
edit('  cancel_test=$test$plusargs("CANCEL_FOUR");cancel_phase=0;',
     '  cancel_test=$test$plusargs("CANCEL_FOUR");cancel_phase=0;hold_weight_responses=0;')
edit("   integer cancel_start,cancel_latency,old_exec,old_drains,old_acks,old_errors;",
     "   integer cancel_start,cancel_latency,old_exec,old_drains,old_acks,old_errors,expected_drains,prior_completions;\n   bit cancel_after_first_exec;")
edit("""   transfer_tile(0,2);transfer_tile(1,2);
   while($countones(M.table_valid)!=4||weight_inflight<2||command_occupied!=0||exec_state!=5'd8)@(negedge clk);
   old_exec=native_execs;old_drains=drain_commands;old_acks=ACKs;old_errors=cancel_error_count;cancel_start=cycle;""",
     """   cancel_after_first_exec=$test$plusargs("CANCEL_DURING_OVERLAP");
   assert(!cancel_after_first_exec||EARLY_EXEC);
   prior_completions=completed;
   transfer_tile(0,2);
   while(completed<prior_completions+2*GROUPS||M.table_valid!=0||command_occupied!=0||result_occupied!=0||exec_state!=0)@(negedge clk);
   hold_weight_responses=1;
   transfer_tile(1,2);
   while($countones(M.table_valid)!=4||weight_inflight<2||command_occupied!=0||exec_state!=5'd8)@(negedge clk);
   expected_drains=4;
   if(cancel_after_first_exec)begin
    old_exec=native_execs;
    hold_weight_responses=2;
    while(native_execs==old_exec)@(negedge clk);
    assert(native_execs==old_exec+1&&command_occupied!=0&&$countones(M.table_valid)==4&&
       |(backend_pending&younger_pending_mask)) else $fatal(1,"older EXEC must overlap true younger backend data");
    expected_drains=3;
   end
   old_exec=native_execs;old_drains=drain_commands;old_acks=ACKs;old_errors=cancel_error_count;cancel_start=cycle;""")
edit(" logic [63:0] younger_record_base;",
     """ logic [63:0] younger_record_base;
 wire [63:0] younger_pending_mask;
 for(genvar entry=0;entry<64;entry=entry+1)begin: tagged_responses
  assign younger_pending_mask[entry]=backend_is_younger[entry];
 end
 always @(posedge clk)begin
  if(reset)younger_record_base<=0;
  else if(case_id==2&&record_valid&&record_ready&&record_k==16'd128&&record_context==4'd1)
   younger_record_base<=record_address;
 end""")
edit("   cancel_phase=1;scope_cancel=1;assert(cancel_ready);pause();scope_cancel=0;",
     "   cancel_phase=1;scope_cancel=1;hold_weight_responses=0;assert(cancel_ready);pause();scope_cancel=0;")
edit("drain_commands==old_drains+4&&cancel_error_count>=old_errors+4&&",
     "drain_commands==old_drains+expected_drains&&cancel_error_count>=old_errors+expected_drains&&")
edit("cancel_latency,4,cancel_error_count-old_errors,32*GROUPS*17,ACKs-old_acks);",
     "cancel_latency,expected_drains,cancel_error_count-old_errors,32*GROUPS*17,ACKs-old_acks);")
edit("&&pair_detaches==32*GROUPS&&peak_contexts==2*GROUPS)",
     "&&(SESSION_LIMIT==32'hffffffe0 ? pair_detaches==32*GROUPS : (pair_detaches>0&&pair_detaches<=32*GROUPS))&&peak_contexts==2*GROUPS)")
edit('  $fclose(trace_file);$finish;', '''  assert(backend_requests==accepted&&backend_returns==returned&&debug_beats==0&&debug_descriptors==0)
    else $fatal(1,"actual global DMA conservation");
  assert(SESSION_LIMIT==32'hffffffe0 ? backend_purges==1 : backend_purges>1)
    else $fatal(1,"FENCE coverage missing");
  $display("REAL_WEIGHT_GLOBAL_PASS requests=%0d returns=%0d purges=%0d",backend_requests,backend_returns,backend_purges);
  $fclose(trace_file);$finish;''')
(rtl / "tb_p_weight_global.sv").write_text(s, encoding="utf-8")
