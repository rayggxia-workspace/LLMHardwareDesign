"""Add actual bank-backed MC PM and mutable LC PM to the true numeric fixture.

The fixture may backpressure a new task while it boots the next declared A16
image. This boot is visible and timed; it is not a whole-model input producer.
"""
from pathlib import Path
import re

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
s = (HERE / 'rtl/tb_p_native_record_executor.sv').read_text().replace('module tb_p_native_record_executor;', 'module tb_p_program_numeric;')


def ports(path, kind):
    header = path.read_text().split(');', 1)[0]
    header = re.sub(r',\s*(?=(?:input|output)\s+' + kind + ')', ',\n ', header)
    return [(direction, width, name.strip())
            for direction, width, names in re.findall(r'(input|output)\s+' + kind + r'\s*(\[[^\]]+\])?\s*([^\n]+)', header)
            for name in names.strip().rstrip(',').split(',')]


lports = ports(HERE / 'rtl/lc_native_scope_controller.sv', 'logic')
lalias = dict(clk='clk', reset='reset', service_valid='service_valid', service_ready='service_ready&&scope_ready',
              service_owner='scope_owner', service_descriptor='scope_data', service_cancel_valid='scope_cancel',
              service_cancel_ready='cancel_ready', service_done_valid='service_done_valid', service_done_ready='service_done_ready',
              service_done_owner='service_done_owner', service_done_ticket='service_done_ticket',
              service_done_status='service_done_status', service_done_read_bytes='service_done_read_bytes',
              service_done_write_bytes='service_done_write_bytes')
ldecl = '\n'.join(f' logic {w} l_{n};' for _, w, n in lports if n not in lalias)
lconn = ',\n'.join(f'  .{n}({lalias.get(n,"l_"+n)})' for _, _, n in lports)
linit = '\n'.join(f'  l_{n}=0;' for d, _, n in lports if d == 'input' and n not in lalias and not n.startswith(('rx_', 'mc_')) and n != 'tx_ready')
mports = ports(ROOT / 'project/rtl/mother_control_native/mother_control_native64_transport128.sv', 'wire')
malias = dict(clk_i='clk', rst_ni='!reset', tx_valid='m_tx_valid', tx_ready='m_tx_ready', tx_data='l_rx_data',
              tx_target='l_rx_target', tx_sop='l_rx_sop', tx_eop='l_rx_eop', tx_credit='m_tx_credit',
              rx_valid='l_tx_valid', rx_ready='l_tx_ready', rx_data='l_tx_data', rx_source='l_tx_source',
              rx_sop='l_tx_sop', rx_eop='l_tx_eop', local_enabled_i="{8'd0,l_prepared}",
              transport_drained_i='l_idle&&!m_tx_valid&&!l_tx_valid')
mdecl = '\n'.join(f' logic {w} {n};' for _, w, n in mports if n not in malias)
mconn = ',\n'.join(f'  .{n}({malias.get(n,n)})' for _, _, n in mports)
minit = '\n'.join(f'  {n}=0;' for d, _, n in mports if d == 'input' and n not in malias)
unused = ','.join(f'l_{n}' for d, _, n in lports if d == 'output' and n not in lalias)
unused += ',' + ','.join(n for d, _, n in mports if d == 'output' and n not in malias)
extra = f'''
{ldecl}
{mdecl}
 logic m_tx_valid,m_tx_ready,m_tx_credit,source_prepared;
 logic [127:0] kernel_image[22],mother_image[25];
 logic [31:0] kernel_crc;
 integer MC_calls,MC_returns,MC_PM_reads,LC_PM_reads,scope_returns;
 logic [1:0] scope_pending;
 logic [31:0] scope_tags[2];
 integer scope_due[2];logic scope_response_slot;
 assign l_rx_valid=m_tx_valid&&source_prepared;
 assign m_tx_ready=l_rx_ready&&source_prepared;
 lc_native_scope_controller local_control(
{lconn}
 );
 mother_control_native64_transport128 mother(
{mconn}
 );
 // Descriptor peer has exactly the two requested64B halves. Weight and scope
 // traffic still use separately bounded peers in this fixture; real global
 // fabric/51.2GB/s qualification is a subsequent gate, not inferred here.
 assign l_mc_req_ready=!scope_pending[l_mc_req_tag[0]]&&!l_mc_rsp_valid;
 assign l_mc_close_ready=1;
 always @(posedge clk)begin
  if(reset)begin
   MC_calls<=0;MC_returns<=0;MC_PM_reads<=0;LC_PM_reads<=0;scope_returns<=0;
   scope_pending<=0;l_mc_rsp_valid<=0;l_mc_rsp_data<=0;l_mc_rsp_tag<=0;scope_response_slot<=0;
   scope_due[0]<=0;scope_due[1]<=0;
  end else begin
   if(l_rx_valid&&l_rx_ready&&l_rx_sop)begin
    assert(l_rx_data[23:16]==0&&l_rx_target==0)else $fatal(1,"unexpected task/cancel");MC_calls<=MC_calls+1;
    $fwrite(trace_file,"%0d,MC_CALL,%0d,%0d,0,0\\n",cycle,case_id,l_rx_data[127:96]);
   end
   if(l_tx_valid&&l_tx_ready&&l_tx_eop)begin
    assert(l_retired_instructions==3)else $fatal(1,"actual three-instruction LC kernel");
    MC_returns<=MC_returns+1;$fwrite(trace_file,"%0d,LC_RETURN,%0d,0,0,0\\n",cycle,case_id);
   end
   if(l_pm_trace_valid)begin LC_PM_reads<=LC_PM_reads+1;$fwrite(trace_file,"%0d,LC_PM,%0d,%0d,0,0\\n",cycle,case_id,l_pm_trace_address);end
   if(mother.mother.pm_req_valid_o&&mother.mother.pm_req_ready_i&&!mother.mother.pm_req_write_o)begin
    MC_PM_reads<=MC_PM_reads+1;$fwrite(trace_file,"%0d,MC_PM,%0d,%0d,0,0\\n",cycle,case_id,mother.mother.pm_req_address_o);
   end
   if(l_mc_req_valid&&l_mc_req_ready)begin
    assert(l_mc_req_record_beats==2&&l_mc_req_address==64'h4000+64'(case_id)*128+(l_mc_req_tag[0]?64'd64:0))else $fatal(1,"actual descriptor deployment");
    scope_pending[l_mc_req_tag[0]]<=1;scope_tags[l_mc_req_tag[0]]<=l_mc_req_tag;scope_due[l_mc_req_tag[0]]<=cycle+3+seed%3;
    $fwrite(trace_file,"%0d,SCOPE_REQ,%0d,%0d,%0d,0\\n",cycle,case_id,l_mc_req_tag,l_mc_req_address);
   end
   if(l_mc_rsp_valid&&l_mc_rsp_ready)begin l_mc_rsp_valid<=0;scope_pending[scope_response_slot]<=0;scope_returns<=scope_returns+1;$fwrite(trace_file,"%0d,SCOPE_RSP,%0d,%0d,0,0\\n",cycle,case_id,l_mc_rsp_tag);end
   if(!l_mc_rsp_valid)begin
    if(scope_pending[1]&&scope_due[1]<=cycle)begin l_mc_rsp_valid<=1;scope_response_slot<=1;l_mc_rsp_tag<=scope_tags[1];l_mc_rsp_data<=scopes[case_id][512+:512];end
    else if(scope_pending[0]&&scope_due[0]<=cycle)begin l_mc_rsp_valid<=1;scope_response_slot<=0;l_mc_rsp_tag<=scope_tags[0];l_mc_rsp_data<=scopes[case_id][0+:512];end
   end
   assert(l_protocol_fault_cycles==0&&frame_fault_count==0&&protocol_fault_count_o==0)else $fatal(1,"actual MC LC fault");
  end
 end
 task automatic lc_cfg_send(input logic[1:0] op);
  l_cfg_op=op;l_cfg_valid=1;do @(posedge clk);while(!l_cfg_ready);@(negedge clk);l_cfg_valid=0;
  while(!l_cfg_rsp_valid)@(negedge clk);assert(l_cfg_status==0)else $fatal(1,"LCboot status");
  l_cfg_rsp_ready=1;pause();l_cfg_rsp_ready=0;
 endtask
 task automatic mother_config(input logic[2:0] op,input logic[13:0] address_word=0,input logic[127:0] value=0);
  cfg_req_op_i=op;cfg_req_address_i=address_word;cfg_req_data_i=value;cfg_req_valid_i=1;
  do @(posedge clk);while(!cfg_req_ready_o);@(negedge clk);cfg_req_valid_i=0;
  while(!cfg_rsp_valid_o)@(negedge clk);assert(cfg_rsp_status_o==0)else $fatal(1,"MCboot status %0d",cfg_rsp_status_o);
  if(op==2)assert(cfg_rsp_data_o==mother_image[int'(address_word)>>4])else $fatal(1,"actual MC PM readback");
  cfg_rsp_ready_i=1;pause();cfg_rsp_ready_i=0;
 endtask
 wire unused_program_outputs=^{{{unused},m_tx_credit}};
'''
s = s.replace(' initial begin\n  reset=1;', extra + '\n initial begin\n  reset=1;', 1)
s = s.replace('service_valid=0;service_done_ready=0;scope_cancel=0;scope_owner=0;scope_data=0;', '')
s = s.replace('.cfg_key(scope_data[128+:128])', '.cfg_key(scopes[case_id][128+:128])')
s = s.replace('.publish_key(scope_data[128+:128])', '.publish_key(scopes[case_id][128+:128])')
s = s.replace(".cfg_tiles(6'(scope_data[608+:16]>>7))", ".cfg_tiles(6'(scopes[case_id][608+:16]>>7))")
boot = f'''
{linit}
{minit}
  source_prepared=0;
  l_transport_drained=1;l_session_topology=25001;
  l_cfg_generation=1;l_cfg_abi=32'h02500002;l_cfg_capacity=32'h02510001;l_cfg_bytes=352;
  $readmemh({{vectors,"/kernel.mem"}},kernel_image);$readmemh({{vectors,"/mother.mem"}},mother_image);
  if($value$plusargs("CRC=%h",kernel_crc))begin end else $fatal(1,"kernel CRC missing");
  pause(4);reset=0;pause();
  lc_cfg_send(0);
  for(integer wi=0;wi<22;wi=wi+1)begin l_cfg_address=14'(wi*16);l_cfg_data=kernel_image[wi];lc_cfg_send(1);end
  l_cfg_crc=kernel_crc;lc_cfg_send(2);assert(l_certified);
  l_session_generation=1;l_session_valid=1;do @(posedge clk);while(!l_session_ready);@(negedge clk);l_session_valid=0;
  release_valid_i=1;release_sequence_i=1;release_epoch_i=1;
  do @(posedge clk);while(!release_ready_o);@(negedge clk);release_valid_i=0;
  cfg_req_generation_i=1;cfg_req_total_bytes_i=400;cfg_req_image_id_i=900;cfg_req_topology_id_i=25001;
  cfg_req_abi_id_i=32'h02500002;cfg_req_capacity_id_i=32'h02590003;cfg_req_proof_i=1;
  mother_config(0);
  for(integer wi=0;wi<25;wi=wi+1)mother_config(1,14'(wi*16),mother_image[wi]);
  for(integer wi=0;wi<25;wi=wi+1)mother_config(2,14'(wi*16));
  mother_config(3);mother_config(4);local_image_ids_i[31:0]=25001;
  deploy_generation_i=1;deploy_valid_i=1;start_credit_i=1;while(life_o!=5)@(negedge clk);
  start_job_i=7;start_epoch_i=8;start_sequence_i=1;start_generation_i=1;start_valid_i=1;
  do @(posedge clk);while(!start_ready_o);@(negedge clk);start_valid_i=0;
'''
s = s.replace('  pause(4);reset=0;pause();', boot, 1)
s = s.replace("case_id=ci;scope_data=scopes[ci];scope_owner={32'd1,32'd7,32'd8,32'(ci+1)};", 'case_id=ci;')
s = s.replace('copy_key=scope_data[128+:128]', 'copy_key=scopes[ci][128+:128]')
s = s.replace("word_id<(int'(scope_data[608+:16])>>3)", "word_id<(int'(scopes[ci][608+:16])>>3)")
s = s.replace('service_valid=1;\n   do @(posedge clk);while(!(service_ready&&scope_ready));@(negedge clk);service_valid=0;', 'source_prepared=1;')
s = s.replace('   service_done_ready=1;pause();service_done_ready=0;pause(2);', '   source_prepared=0;while(MC_returns<ci+1)@(negedge clk);pause(2);')
s = s.replace('while(!service_done_valid)begin', 'while(MC_returns<ci+1)begin')
s = s.replace('while(!service_done_valid)@(negedge clk);', 'while(MC_returns<ci+1)@(negedge clk);')
s = s.replace('  $display("PASS p_native_record_executor', '''  while(!result_valid_o)@(negedge clk);
  assert(result_status_o==0&&result_confirmed_read_bytes_o==21184&&result_confirmed_write_bytes_o==384&&MC_calls==8&&MC_returns==8&&LC_PM_reads==184&&scope_returns==16&&l_retired_instructions==3)else $fatal(1,"actual MC LC accounting status%0d reads%0d writes%0d CALL%0d return%0d LCpm%0d scope%0d instr%0d",result_status_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,MC_calls,MC_returns,LC_PM_reads,scope_returns,l_retired_instructions);
  result_ready_i=1;pause();result_ready_i=0;
  $display("PASS p_program_numeric''')
(HERE / 'rtl/tb_p_program_numeric.sv').write_text(s)
