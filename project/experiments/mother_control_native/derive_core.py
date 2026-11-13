"""Text-only derivation of a separate native profile; old ABI stays unchanged.

The checked-in generated RTL is reviewed/tested directly. This script makes the
source relationship explicit; no EDA or functional experiment executes here.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT/'project/rtl/mother_control_v1'
NEW = ROOT/'project/rtl/mother_control_native'
NEW.mkdir(parents=True, exist_ok=True)


def replace(text, old, new):
    assert old in text, old
    return text.replace(old, new)


ports = (OLD/'mc_ports.svh').read_text()
ports = replace(ports, 'input wire [31:0] local_image_id0_i,\n  input wire [31:0] local_image_id1_i,\n  input wire [1:0] local_enabled_i,',
                'input wire [287:0] local_image_ids_i,\n  input wire [8:0] local_enabled_i,')
ports = replace(ports, 'output wire [7:0] trace_live_tokens_o,', 'output wire [15:0] trace_live_tokens_o,')
ports = ports.replace('[1:0] trace_block_active_o','[8:0] trace_block_active_o').replace('[1:0] trace_terminal_full_o','[8:0] trace_terminal_full_o').replace('[1:0] trace_READY_full_o','[8:0] trace_READY_full_o')
ports = replace(ports,'output wire trace_aborting_o','output wire trace_aborting_o,\n  input wire recover_valid_i,\n  output wire recover_ready_o,\n  output wire [31:0] protocol_fault_count_o')
(NEW/'mc_native_ports.svh').write_text(ports)

core = (OLD/'mc_min_controller.sv').read_text()
core = replace(core, '// Bounded mother ISA profile: G_CALL/WAIT/EVENT/MOVI/END, two targets.', '// Separate native profile: nine resident groups, sixteen tokens, nine events.\n// 64-bit execution ISA; packet version 2 adds generation/topology return identity.')
core = replace(core, 'module mc_min_controller', 'module mc_native_controller')
core = replace(core, "32'h00010001", "32'h02500002")
core = replace(core, '`include "mc_ports.svh"', '`include "mc_native_ports.svh"')
core = replace(core, 'event_cache[0:1]', 'event_cache[0:8]')
core = replace(core, 'reg bind_index;', 'reg [3:0] bind_index;')
core = replace(core, 'reg [1:0] binding_consumed;', 'reg [8:0] binding_consumed;')
core = replace(core, 'local_ids[0:1],next_sequence[0:1]', 'local_ids[0:8],next_sequence[0:8]')
core = replace(core, 'reg [1:0] enabled,block_active', 'reg [8:0] enabled,block_active')
core = replace(core, 'reg [2:0] block_token[0:1];', 'reg [3:0] block_token[0:8];')
core = replace(core, 'reg [511:0] context_packet[0:1],terminal_packet[0:1],ready_packet[0:1];', 'reg [511:0] context_packet[0:8];\n  reg [31:0] ready_scalar[0:8];\n  reg [31:0] protocol_fault_count;')
core = replace(core, 'reg [7:0] live_tokens;', 'reg [15:0] live_tokens;')
core = replace(core, '`include "instruction_fetch.svh"', '`include "native_instruction_fetch.svh"')
core = replace(core, '{59\'b0,bind_index,4\'b0}', '{56\'b0,bind_index,4\'b0}')
start = core.index('  wire targets_valid=')
end = core.index('  wire deployed=', start)
core = core[:start]+'''  reg targets_valid,target_snapshot_ok;
  integer ti;
  always @* begin
    targets_valid=local_enabled_i!=0;target_snapshot_ok=1;
    for(ti=0;ti<9;ti=ti+1) begin
      if(local_enabled_i[ti] && local_image_ids_i[32*ti+:32]==0) targets_valid=0;
      if(life==RUNNING && (enabled[ti]!=local_enabled_i[ti] ||
          enabled[ti] && local_ids[ti]!=local_image_ids_i[32*ti+:32])) target_snapshot_ok=0;
    end
  end
'''+core[end:]
core = replace(core, 'wire return_fire=return_valid_i && return_ready_o;', 'wire return_accept=return_valid_i && return_ready_o;\n  wire return_fire=return_accept && return_validated;')
core = replace(core, 'wire return_sb=return_packet_i[24];', 'wire [3:0] return_sb=return_packet_i[24+:4];')
core = replace(core, "return_packet_i[0+:16]==1 && return_packet_i[24+:8]<2", "return_packet_i[0+:16]==2 && return_packet_i[24+:8]<9")
core = replace(core, 'return_packet_i[352+:160]==0', 'return_packet_i[352+:32]==generation && return_packet_i[384+:32]==topology && return_packet_i[416+:96]==0')
start = core.index('  wire ready_binding0=')
end = core.index('  wire return_terminal_ok=', start)
core = core[:start]+'''  reg ready_binding;
  integer rb;
  always @* begin
    ready_binding=0;
    for(rb=0;rb<9;rb=rb+1) if(rb<binding_count && !binding_consumed[rb] &&
        event_cache[rb][8+:8]==return_packet_i[24+:8] &&
        event_cache[rb][0+:8]==return_packet_i[136+:8]) ready_binding=1;
  end
  wire return_READY_ok=return_kind==0 && !ready_full[return_sb] && !terminal_full[return_sb] &&
       ready_binding && return_packet_i[128+:8]==255 && return_packet_i[144+:16]==0 &&
       return_packet_i[192+:96]==0 && return_packet_i[288+:32]==1 && return_packet_i[320+:32]==32'hffffffff;
'''+core[end:]
core = replace(core, "{5'b0,block_token[return_sb]}", "{4'b0,block_token[return_sb]}")
start = core.index('  wire bad_return=')
end = core.index('  wire movi_fields=', start)
core = core[:start]+'''  wire return_validated=(life==RUNNING || life==POISONED) && return_base_ok && (return_READY_ok || return_terminal_ok);
  wire bad_return=return_accept && !return_validated;
  wire incoming_error=return_fire && return_kind==3;
  wire normal_issue=life==RUNNING && deployed && !aborting && !incoming_error && !bad_return;
  reg [15:0] done_tokens;
  reg [8:0] source_events_consumed;
  reg wait_events_clear,event_found,event_available,all_bindings_consumed,bindings_ok;
  reg [3:0] event_slot,event_source;
  integer eb,es,ec;
  always @* begin
    done_tokens=0;source_events_consumed='1;wait_events_clear=1;
    event_found=0;event_slot=0;event_source=0;all_bindings_consumed=1;bindings_ok=1;
    for(eb=0;eb<9;eb=eb+1) begin
      if(terminal_full[eb]) done_tokens=done_tokens|(16'b1<<block_token[eb]);
      if(eb<binding_count) begin
        if(!binding_consumed[eb]) begin
          all_bindings_consumed=0;
          if(event_cache[eb][8+:8]<9) source_events_consumed[event_cache[eb][8+:4]]=0;
        end
        if(event_cache[eb][0+:8]==ib) begin event_found=1;event_slot=4'(eb);event_source=event_cache[eb][8+:4];end
        if(event_cache[eb][0+:8]>=32 || event_cache[eb][8+:8]>=9 || event_cache[eb][16+:112]!=0) bindings_ok=0;
        for(ec=0;ec<9;ec=ec+1) if(ec<eb && (event_cache[ec][0+:8]==event_cache[eb][0+:8] ||
             event_cache[ec][8+:8]==event_cache[eb][8+:8])) bindings_ok=0;
      end
    end
    for(es=0;es<9;es=es+1) if(block_active[es] && wait_mask[{1'b0,block_token[es]}] &&
        (ready_full[es] || !source_events_consumed[es])) wait_events_clear=0;
    event_available=event_found && !binding_consumed[event_slot] && ready_full[event_source];
  end
  wire wait_allocated=wait_mask!=0 && (wait_mask&~{16'b0,live_tokens})==0;
  wire wait_done=(wait_mask&~{16'b0,done_tokens})==0;
'''+core[end:]
start=core.index('  wire [1:0] needed_bindings=')
end=core.index('  wire cfg_meta_ok=',start)
core=core[:start]+core[end:]
core=replace(core, 'cfg_req_total_bytes_i<=4736', 'cfg_req_total_bytes_i<=2320')
core=replace(core, "32'h17630001", "32'h02590003")
core=replace(core, 'binding_count<=2', 'binding_count<=9')
start=core.index('  wire bindings_ok=')
end=core.index('  wire [32:0] read_sum=',start)
core=core[:start]+core[end:]
core=core.replace('next_sequence[ia[0]]','next_sequence[ia[3:0]]').replace('local_ids[ia[0]]','local_ids[ia[3:0]]')
core=replace(core, 'call_word[0+:16]=1;', 'call_word[0+:16]=2;')
core=replace(core, 'call_word[192+:32]=topology;', 'call_word[192+:32]=topology; call_word[224+:32]=generation;')
core=replace(core, '  reg targets_valid,target_snapshot_ok;', "  wire bind_address_ok=bind_address[3:0]==0 && bind_address+64'd16<={48'b0,total};\n  reg targets_valid,target_snapshot_ok;")
core=replace(core, '(seq==BIND_REQ || seq==FETCH_REQ', '(seq==BIND_REQ && bind_address_ok || seq==FETCH_REQ')
core=replace(core, 'if(seq==BIND_CHECK)', 'if(seq==BIND_REQ && !bind_address_ok) fault(6);\n        if(seq==BIND_CHECK)')
core=replace(core, 'assign return_ready_o=rst_ni && !poisoned && life==RUNNING && return_base_ok && (return_READY_ok || return_terminal_ok);', 'assign return_ready_o=rst_ni;\n  assign protocol_fault_count_o=protocol_fault_count;\n  assign recover_ready_o=rst_ni && poisoned && (terminal_full&block_active)==block_active &&\n      !out_valid && !pm_outstanding && !pm_offered;')
core=replace(core, 'bj<2', 'bj<9')
core=replace(core, 'context_packet[bj]<=0; terminal_packet[bj]<=0; ready_packet[bj]<=0;', 'context_packet[bj]<=0; ready_scalar[bj]<=0;')
core=replace(core, 'aborting<=0; result_valid<=0; error_status<=0;', 'aborting<=0; result_valid<=0; error_status<=0; protocol_fault_count<=0;')
core=replace(core, "{15'b0,bind_index}", "{12'b0,bind_index}")
core=replace(core, 'else begin bind_index<=1; seq<=BIND_REQ; end', "else begin bind_index<=bind_index+1'b1; seq<=BIND_REQ; end")
core=replace(core, 'local_ids[0]<=local_image_id0_i; local_ids[1]<=local_image_id1_i;', 'for(bj=0;bj<9;bj=bj+1) local_ids[bj]<=local_image_ids_i[32*bj+:32];')
core=core.replace('ia>=2 || ib>=8','ia>=9 || ib>=16').replace('ia[0]','ia[3:0]').replace('ib[2:0]','ib[3:0]')
core=replace(core, "8'b1<<ib[3:0]", "16'b1<<ib[3:0]")
core=replace(core, 'wait_mask[7:0]', 'wait_mask[15:0]')
core=replace(core, "wait_mask[{2'b0,block_token[bj]}]", "wait_mask[{1'b0,block_token[bj]}]")
core=replace(core, '!event_match0 && !event_match1', '!event_found')
core=replace(core, 'ready_packet[event_source][160+:32]', 'ready_scalar[event_source]')
core=replace(core, 'block_accepted[out_packet[24]]', 'block_accepted[out_packet[24+:4]]')
core=replace(core, 'cancel_sent[out_packet[24]]', 'cancel_sent[out_packet[24+:4]]')
core=replace(core, 'terminal_packet[return_sb]<=return_packet_i; terminal_full[return_sb]<=1;', 'terminal_full[return_sb]<=1;')
core=replace(core, 'else begin ready_packet[return_sb]<=return_packet_i; ready_full[return_sb]<=1; end', 'else begin ready_scalar[return_sb]<=return_packet_i[160+:32]; ready_full[return_sb]<=1; end')
core=replace(core, 'if(life==RUNNING && aborting && !poisoned)', 'if((life==RUNNING || life==POISONED) && aborting)')
start=core.index('          if(block_active[0]')
end=core.index('\n        end\n        if((terminal_full',start)
core=core[:start]+'''          // Ascending deterministic cancellation; one held packet at a time.
          for(bj=8;bj>=0;bj=bj-1) if(block_active[bj] && block_accepted[bj] &&
              !terminal_full[bj] && !cancel_sent[bj] &&
              !(return_fire && return_terminal && return_sb==4'(bj))) begin
            out_packet<=context_packet[bj];out_packet[16+:8]<=1;out_packet[256+:256]<=0;out_valid<=1;
          end'''+core[end:]
core=replace(core, 'if((terminal_full&block_active)==block_active && !out_valid && !pm_outstanding && !pm_offered)', 'if(!poisoned && (terminal_full&block_active)==block_active && !out_valid && !pm_outstanding && !pm_offered)')
core=replace(core, 'begin poisoned<=1; prepared<=0; life<=POISONED; end', 'begin fault(14); poisoned<=1; prepared<=0; life<=POISONED; end')
start=core.index('      if((life==RUNNING && !deployed)')
end=core.index('\n    end\n  end\nendmodule',start)
core=core[:start]+'''      if(bad_return) begin
        if(protocol_fault_count!=32'hffffffff) protocol_fault_count<=protocol_fault_count+1;
        if(life==RUNNING && !result_valid) fault(17);
      end
      if(life==RUNNING && !result_valid && !deployed) begin fault(15);poisoned<=1;prepared<=0;life<=POISONED;end
      if(recover_valid_i && recover_ready_o) begin
        poisoned<=0;prepared<=0;life<=INVALID;seq<=IDLE;aborting<=0;result_valid<=0;
        block_active<=0;block_accepted<=0;terminal_full<=0;ready_full<=0;cancel_sent<=0;live_tokens<=0;ireg_valid<=0;
      end'''+core[end:]
core=core.replace('cfg_req_total_bytes_i<=2320','cfg_req_total_bytes_i<=16384').replace('inst_count<=256','inst_count<=2032')
from mc_loop_extension import extend
core=extend(core)
(NEW/'mc_native_controller.sv').write_text(core)
fetch=(OLD/'instruction_fetch.svh').read_text().replace('compact_image || instruction_version==16\'d1', 'compact_image')
fetch=fetch.replace("wire [8:0] instruction_beats = compact_image ? {1'b0,inst_count[8:1]}+{8'b0,inst_count[0]} :\n                                             inst_count[8:0];","wire [31:0] instruction_beats = compact_image ? {1'b0,inst_count[31:1]}+{31'b0,inst_count[0]} : inst_count;").replace("{51'b0,instruction_beats,4'b0}","{28'b0,instruction_beats,4'b0}")
fetch=fetch.replace("instruction_version==16'd2","instruction_version==16'd3")
(NEW/'native_instruction_fetch.svh').write_text(fetch)

wrapper_ports=ports[:ports.index('  input wire pm_req_ready_i,')]+ports[ports.index('  output wire [3:0] life_o,'):]
wrapper='''// Native nine-resident mother with separate unchanged 16KiB program SRAM.
`timescale 1ns/1ps
module mother_control_native64 #(parameter [31:0] NATIVE_ABI_ID=32'h02500002)(
'''+wrapper_ports+'''
);
  wire pm_req_ready_i,pm_rsp_valid_i,pm_rsp_error_i,pm_req_valid_o,pm_req_write_o,pm_rsp_ready_o;
  wire [127:0] pm_rsp_data_i,pm_req_data_o;
  wire [13:0] pm_req_address_o;
  mc_native_controller #(.STALL_LIMIT(4096),.NATIVE_ABI_ID(NATIVE_ABI_ID)) core(.*);
  control_pm #(.BYTES(16384),.USE_SRAM(1'b1)) program_store(
    .clk_i,.rst_ni,.req_valid_i(pm_req_valid_o),.req_write_i(pm_req_write_o),
    .req_address_i(pm_req_address_o),.req_data_i(pm_req_data_o),.req_ready_o(pm_req_ready_i),
    .rsp_valid_o(pm_rsp_valid_i),.rsp_ready_i(pm_rsp_ready_o),.rsp_data_o(pm_rsp_data_i),.rsp_error_o(pm_rsp_error_i));
endmodule
'''
(NEW/'mother_control_native64.sv').write_text(wrapper)
