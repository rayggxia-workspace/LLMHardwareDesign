"""Reuse the same finite record fixture, but drive LC through the actual MC.

This generates a checked-in bench, not production RTL. Actual MC PM is the
qualified control_pm with four original banks; actual LC PM is mutable1KiB.
"""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
s = (HERE/'rtl/tb_lc_native_scope.sv').read_text()
s = s.replace('module tb_lc_native_scope;', 'module tb_mc_lc_native;')
start = s.index(' task automatic send_frame(')
end = s.index(' // Finite DDR', start)
s = s[:start] + s[end:]
s = s.replace(' logic [511:0] active_packet;\n', '')
header = (ROOT/'project/rtl/mother_control_native/mother_control_native64_transport128.sv').read_text().split(');',1)[0]
ports = []
for direction, width, names in re.findall(r'(input|output)\s+wire\s*(\[[^\]]+\])?\s*([^\n]+)', header):
    for name in names.strip().rstrip(',').split(','):
        ports.append((direction, width, name.strip()))
aliases = {'clk_i':'clk', 'rst_ni':'!reset', 'tx_valid':'rx_valid', 'tx_ready':'rx_ready', 'tx_data':'rx_data',
           'tx_target':'rx_target','tx_sop':'rx_sop','tx_eop':'rx_eop', 'tx_credit':'mother_tx_credit',
           'rx_valid':'mother_rx_valid','rx_ready':'mother_rx_ready','rx_data':'mother_rx_data',
           'rx_source':'mother_rx_source','rx_sop':'mother_rx_sop','rx_eop':'mother_rx_eop',
           'transport_drained_i':'idle&&!rx_valid&&!tx_valid&&!inject_valid',
           'local_enabled_i':"{8'd0,prepared}"}
decl = '\n'.join(f' logic {w} {n};' for _,w,n in ports if n not in aliases)
connections = ',\n'.join(f'   .{n}({aliases.get(n,n)})' for _,_,n in ports)
outputs = ','.join(n for d,_,n in ports if d == 'output' and n not in aliases)
init = '\n'.join(f'   {n}=0;' for d,_,n in ports if d=='input' and n not in aliases)
extra = f'''
{decl}
 logic mother_tx_credit,mother_rx_valid,mother_rx_ready,mother_rx_sop,mother_rx_eop;
 logic [127:0] mother_rx_data;
 logic [7:0] mother_rx_source;
 logic inject_valid;
 logic [1:0] inject_word;
 logic [511:0] inject_packet;
 assign mother_rx_valid=inject_valid||tx_valid;
 assign mother_rx_data=inject_valid?inject_packet[128*inject_word+:128]:tx_data;
 assign mother_rx_source=inject_valid?8'd8:tx_source;
 assign mother_rx_sop=inject_valid?inject_word==0:tx_sop;
 assign mother_rx_eop=inject_valid?inject_word==3:tx_eop;
 assign tx_ready=mother_rx_ready&&!inject_valid;
 mother_control_native64_transport128 mother(
{connections}
 );
 logic [127:0] mother_image[14];
 string mother_path;
 integer MC_calls,MC_cancels,MC_flits,MC_returns,MC_PM_reads;
 always @(posedge clk)if(reset)begin
   MC_calls<=0;MC_cancels<=0;MC_flits<=0;MC_returns<=0;MC_PM_reads<=0;
 end else begin
   if(rx_valid&&rx_ready)begin
     MC_flits<=MC_flits+1;
     if(rx_sop)begin if(rx_data[16+:8]==0)MC_calls<=MC_calls+1;else MC_cancels<=MC_cancels+1;end
   end
   if(tx_valid&&tx_ready&&tx_eop)MC_returns<=MC_returns+1;
   if(mother.mother.pm_req_valid_o&&mother.mother.pm_req_ready_i&&!mother.mother.pm_req_write_o)
     MC_PM_reads<=MC_PM_reads+1;
   if(result_valid_o)assert(trace_live_tokens_o==0&&trace_block_active_o==0&&!poison_o);
   if(mc_close_valid)assert(mc_close_tag_base=={{pending_tags[0][31:1],1'b0}});
 end
 task automatic mother_config(input logic [2:0] op,input int address=0,input logic [127:0] value=0);
   cfg_req_op_i=op;cfg_req_address_i=14'(address);cfg_req_data_i=value;cfg_req_valid_i=1;
   do @(posedge clk);while(!cfg_req_ready_o);@(negedge clk);cfg_req_valid_i=0;
   while(!cfg_rsp_valid_o)@(negedge clk);
   assert(cfg_rsp_status_o==0);
   if(op==2)assert(cfg_rsp_data_o==mother_image[address>>4]);
   cfg_rsp_ready_i=1;pause();cfg_rsp_ready_i=0;
 endtask
 task automatic run_mother(input int job_sequence,input int mode=0);
   assert(idle&&pending_records==0&&pending_reads==0&&!mc_rsp_valid&&!complete_valid);
   desc_mode=mode;records=0;completed=0;native_confirmed_read_bytes=0;native_confirmed_write_bytes=0;
   start_job_i=7;start_epoch_i=8;start_sequence_i=32'(job_sequence);start_generation_i=1;start_valid_i=1;
   do @(posedge clk);while(!start_ready_o);@(negedge clk);start_valid_i=0;
 endtask
 task automatic take_mother_result(input logic [15:0] status_code,input bit success=0);
   while(!result_valid_o)@(negedge clk);pause(seed%3+2);
   assert(result_status_o==status_code&&result_job_o==7&&result_epoch_o==8&&result_sequence_o==start_sequence_i);
   assert(idle&&pending_records==0&&pending_reads==0&&!mc_rsp_valid&&!complete_valid);
   if(success)assert(records==8&&completed==8&&result_confirmed_read_bytes_o==native_confirmed_read_bytes+128&&
      result_confirmed_write_bytes_o==128&&!result_counter_overflow_o&&!result_saturated_o&&retired_instructions==3);
   result_ready_i=1;pause();result_ready_i=0;pause();assert(life_o==5&&image_valid_o);
 endtask
 wire unused_mother_outputs=^{{{outputs},mother_tx_credit}};
'''
s = s.replace(' // Finite DDR', extra+'\n // Finite DDR', 1)
initial_start = s.index(' initial begin\n   reset=1;')
initial_end = s.index(' wire unused_observed=', initial_start)
old_initial = s[initial_start:initial_end]
prefix = old_initial[:old_initial.index('   pause(3);reset=0;')]
prefix = prefix.replace('rx_valid=0;rx_data=0;rx_sop=0;rx_eop=0;rx_target=0;tx_ready=0;', '')
prefix = prefix.replace('active_packet=0;', '')
scenario = f'''
{init}
   inject_valid=0;inject_word=0;inject_packet=0;
   mother_path="mother.mem";if($value$plusargs("MOTHER_IMAGE=%s",mother_path))begin end
   $readmemh(mother_path,mother_image);
   pause(3);reset=0;pause();boot(1);configure_session(1);
   release_valid_i=1;release_sequence_i=1;release_epoch_i=1;
   do @(posedge clk);while(!release_ready_o);@(negedge clk);release_valid_i=0;
   cfg_req_generation_i=1;cfg_req_total_bytes_i=224;cfg_req_image_id_i=900;cfg_req_topology_id_i=25001;
   cfg_req_abi_id_i=32'h02500002;cfg_req_capacity_id_i=32'h02590003;cfg_req_proof_i=1;
   mother_config(0);
   for(integer i=0;i<14;i=i+1)mother_config(1,16*i,mother_image[i]);
   for(integer i=0;i<14;i=i+1)mother_config(2,16*i);
   mother_config(3);mother_config(4);
   local_image_ids_i=0;local_image_ids_i[31:0]=25001;
   assert(prepared);
   deploy_generation_i=1;deploy_valid_i=1;start_credit_i=1;
   while(life_o!=5)@(negedge clk);
   run_mother(1);take_mother_result(0,1);
   run_mother(2,3);take_mother_result(0,1);
   run_mother(3,1);take_mother_result(36);assert(records==0);
   record_enable=0;run_mother(4);while(!record_valid)@(negedge clk);
   // Wrong-source complete frame provokes real MC fault17 and real CANCEL.
   // It cannot release the still-live P task or the held range record.
   inject_packet=0;inject_packet[0+:16]=2;inject_packet[16+:8]=2;inject_packet[24+:8]=8;
   inject_packet[32+:32]=7;inject_packet[64+:32]=8;inject_packet[96+:32]=4;
   inject_packet[136+:8]=255;inject_packet[320+:32]=32'hffffffff;
   inject_packet[352+:32]=1;inject_packet[384+:32]=25001;inject_valid=1;
   for(integer w=0;w<4;w=w+1)begin inject_word=2'(w);do @(posedge clk);while(!mother_rx_ready);@(negedge clk);end
   inject_valid=0;pause(20);assert(!result_valid_o&&record_valid&&trace_block_active_o[0]);
   record_enable=1;take_mother_result(17);
   assert(MC_calls==4&&MC_cancels==1&&MC_returns==4&&MC_flits==20&&protocol_fault_count_o==1&&frame_fault_count==0&&protocol_fault_cycles==0);
   $display("PASS actual_MC_LC seed=%0d CALL=%0d CANCEL=%0d LC_PM=%0d MC_PM=%0d cycles=%0d",seed,MC_calls,MC_cancels,pm_reads,MC_PM_reads,cycle);
   $fclose(trace_fd);$finish;
 end
'''
s = s[:initial_start]+prefix+scenario+s[initial_end:]
(HERE/'rtl/tb_mc_lc_native.sv').write_text(s)
