"""Record and verify handshakes in the programmed FFN RTL fixture."""
import argparse
import gzip
import json
from bisect import bisect_left, bisect_right
from collections import defaultdict
from itertools import zip_longest
from pathlib import Path

from cover_frontier import search
from dma_read import Profile, Read
from event_replay import Operation, Phase, replay
from ffn_a import EVENTS as A_EVENTS, replay_tile as replay_a_tile
from ffn_join import JoinController
from ffn_m import (ALLOC, BEGIN, FILL, FIRST_OPERAND, INPUT, LAST_OPERAND, RAW_READY, RF, Record, Reply,
                   execution_replies, replay_commits, replay_replies)
from ffn_m_issue import ALLOC_CMD, SIDE_WORDS, Command, CommandLink, join_schedule
from ffn_mid import MIN_TICKS, MidTile
from ffn_result import (READBACK_TAG, down_group_addresses, down_readback_words, mid_readback_words,
                        readback_service, sram_word_phases)
from ffn_scatter import scatter_service, stripe_fragments
from ffn_w import BEATS, WeightTrace
from ffn_w_dma import WeightCommandLinks, WeightDmaTrace
from verify_cover_frontier import verify


ANCHOR = ' end else begin: direct_test'
COPY_LAUNCH = '  xcopy_start=1;do @(posedge clk);while(!xcopy_ready);cycle_wait();xcopy_start=0;'
COPY_DELAY = '''  begin: candidate_copy_delay
   integer epoch;
   if($value$plusargs("COPY_DELAY_EPOCH=%d",epoch)&&epoch==int'(tile_generation))cycle_wait();
  end
'''
MONITOR = """  reg [2:0] probe_offer_seen=0;
  reg [2:0] probe_fetch_seen=0;
  reg [31:0] probe_fetch_tag[3];
  always @(posedge clk) if($test$plusargs("TRACE_CONTROL")&&!reset)begin
   if(program_start&&program_ready)$display("CONTROL start %0d",cycle);
   if(program_result&&program_result_take)
    $display("CONTROL result %0d %0d %0d",cycle,terminal_reads,terminal_writes);
   if(control.tx_valid&&control.tx_ready&&control.tx_eop)
    $display("CONTROL call %0d %0d",cycle,control.tx_target);
   if(control.rx_valid&&control.rx_ready&&control.rx_eop)
    $display("CONTROL terminal %0d %0d",cycle,control.rx_source);
   for(integer p=0;p<3;p++)begin
    if(dr_valid[p]&&(!probe_fetch_seen[p]||probe_fetch_tag[p]!=dr_tag[p*32+:32]))
     $display("CONTROL fetch_valid %0d %0d %0d %0d",cycle,p,dr_tag[p*32+:32],dr_address[p*64+:64]);
    if(dr_valid[p]&&dr_ready[p])
     $display("CONTROL fetch %0d %0d %0d %0d",cycle,p,dr_tag[p*32+:32],dr_address[p*64+:64]);
    if(dr_rsp_valid[p]&&dr_rsp_ready[p])
     $display("CONTROL fetch_return %0d %0d %0d",cycle,p,dr_rsp_tag[p*32+:32]);
    if(lc_call[p]&&!probe_offer_seen[p])
     $display("CONTROL offer %0d %0d %0d",cycle,p,lc_owner[p*128+:32]);
    if(lc_call[p]&&lc_call_ready[p])
     $display("CONTROL dispatch %0d %0d %0d",cycle,p,lc_owner[p*128+:32]);
    if(lc_done[p]&&lc_done_ready[p])
     $display("CONTROL done %0d %0d %0d %0d %0d",cycle,p,lc_done_owner[p*128+:32],
              lc_done_reads[p*32+:32],lc_done_writes[p*32+:32]);
    probe_offer_seen[p]<=lc_call[p];
    probe_fetch_seen[p]<=dr_valid[p];
    probe_fetch_tag[p]<=dr_tag[p*32+:32];
   end
  end
"""
ADMISSION_MONITOR = """  reg [31:0] probe_down_session=0;
  wire [2:0] probe_range_ready,probe_exec_ready;
  reg [5:0] probe_ready_previous;
  reg probe_ready_seen=0;
  for(genvar q=0;q<3;q++)begin: admission_port
   assign probe_range_ready[q]=ps[q].node.exec.range_ready;
   assign probe_exec_ready[q]=ps[q].node.exec.exec_ready;
  end
  always @(posedge clk) if($test$plusargs("TRACE_ADMISSION")&&!reset)begin
   if(start_valid&&start_ready)
    $display("RELEASE start %0d",cycle);
   if(stripe_commit_valid&&stripe_commit_ready)
    $display("RELEASE scatter %0d",cycle);
   if(dut.schedule.mid_commit_valid&&dut.schedule.mid_commit_ready)
    $display("RELEASE mid %0d",cycle);
   if(!down_phase&&inspect&&inspect_rsp_take&&aux_v[inspect_p])
    $display("RELEASE mid_read %0d",cycle);
   if(down_take&&(&down_terminal))
    $display("RELEASE down_done %0d",cycle);
   if(stripe_valid&&stripe_ready)
    $display("ADMISSION stripe %0d %0d",cycle,tile_session);
   if(down_phase&&tile_session!=probe_down_session)begin
    $display("ADMISSION down %0d %0d",cycle,tile_session);
    probe_down_session<=tile_session;
   end
   if(!probe_ready_seen||probe_ready_previous!={probe_range_ready,probe_exec_ready})
    $display("ADMISSION ready %0d %0d %0d",cycle,probe_range_ready,probe_exec_ready);
   probe_ready_seen<=1;
   probe_ready_previous<={probe_range_ready,probe_exec_ready};
  end
"""
SCATTER_MONITOR = """  always @(posedge clk) if($test$plusargs("TRACE_SCATTER")&&!reset)begin
   if(copy_start&&copy_ready)
    $display("SCATTER start %0d %0d %0d %0d %0d %0d %0d %0d %0d",cycle,tile_session,
             copy_generation,source_p,gather.way,copy_first,copy_src,copy_ring,copy_words);
   if(cs_valid&&cs_ready)$display("SCATTER read %0d %0d %0d",cycle,cs_address,cs_tag);
   if(cs_rsp_valid&&cs_rsp_ready)$display("SCATTER response %0d %0d",cycle,cs_rsp_tag);
   if(cd_valid&&cd_ready)$display("SCATTER write %0d %0d %0d",cycle,cd_address,cd_tag);
   if(cd_rsp_valid&&cd_rsp_ready)$display("SCATTER ack %0d %0d",cycle,cd_rsp_tag);
   if(copy_done&&copy_take)
    $display("SCATTER done %0d %0d %0d",cycle,copy_prefix,copy_error);
  end
"""
MID_MONITOR = """  always @(posedge clk) if($test$plusargs("TRACE_MID")&&!reset)begin
   if(dut.g_valid&&dut.g_ready)
    $display("MID g_start %0d %0d %0d %0d %0d",cycle,mid_first,dut.g_gate_base,dut.g_up_base,dut.g_mid_base);
   if(dut.gs_valid&&fs_ready[0]&&dut.g_active)
    $display("MID g_req %0d %0d %0d",cycle,dut.gs_write,dut.gs_address);
   if(dut.g_active&&fs_rsp_valid[0]&&dut.gs_rsp_ready)
    $display("MID g_rsp %0d",cycle);
   if(dut.gin&&dut.gin_ready)$display("MID g_in %0d",cycle);
   if(dut.gout&&dut.gout_ready)$display("MID g_out %0d",cycle);
   if(dut.g_done&&dut.g_take)$display("MID g_done %0d",cycle);
   if(dut.mid_cmd&&dut.mid_cmd_ready)
    $display("MID q_start %0d %0d %0d %0d",cycle,mid_first,mid_destination,mid_destination_base);
   if(dut.qr_valid&&dut.qr_ready)
    $display("MID q_req %0d %0d %0d %0d",cycle,dut.qr_write,dut.qr_address,dut.qr_tag);
   if(dut.qs_valid&&dut.qs_ready)
    $display("MID q_rsp %0d %0d",cycle,dut.qs_tag);
   if(dut.q_done&&dut.q_take)$display("MID q_done %0d %0d",cycle,dut.q_words);
  end
"""
RESULT_MONITOR = """  always @(posedge clk) if($test$plusargs("TRACE_RESULT")&&!reset)begin
   if(done_valid&&done_ready)$display("READBACK gate_done %0d",cycle);
   if(inspect&&inspect_req&&aux_ready[inspect_p])
    $display("READBACK request %0d %0d %0d %0d",cycle,down_phase,inspect_p,inspect_addr);
   if(inspect&&inspect_rsp_take&&aux_v[inspect_p])
    $display("READBACK ack %0d %0d %0d %0d %0d",cycle,down_phase,inspect_p,inspect_addr,aux_tag[inspect_p]);
  end
  for(genvar q=0;q<3;q++)begin: result_port
   reg probe_done_previous=0;
   always @(posedge clk) if($test$plusargs("TRACE_RESULT")&&!reset)begin
    if(ps[q].node.sw_valid&&ps[q].node.sw_ready)
     $display("PRESULT write %0d %0d %0d %0d %0d %0d",cycle,q,ps[q].node.sw_ticket[31:0],
              ps[q].node.sw_ticket[63:32],ps[q].node.sw_word,ps[q].node.sw_address);
    if(ps[q].node.sw_ack_valid&&ps[q].node.sw_ack_ready)
     $display("PRESULT ack %0d %0d %0d %0d %0d",cycle,q,ps[q].node.sw_ack_ticket[31:0],
              ps[q].node.sw_ack_ticket[63:32],ps[q].node.sw_ack_word);
    if(ps[q].node.exec.complete_valid&&ps[q].node.exec.complete_ready)
     $display("PRESULT record %0d %0d %0d %0d %0d",cycle,q,ps[q].node.exec.complete_owner[31:0],
              ps[q].node.exec.complete_sequence,ps[q].node.exec.complete_next_k);
    if(ps[q].node_done&&!probe_done_previous)
     $display("PRESULT valid %0d %0d %0d",cycle,q,lc_done_owner[q*128+:32]);
    probe_done_previous<=ps[q].node_done;
   end
  end
"""
M_MONITOR = """  for(genvar q=0;q<3;q++)begin: m_port
   reg [4:0] probe_control_seen=0;
   wire [4:0] probe_control_live={ps[q].node.M.local_valid,ps[q].node.M.command_reply_valid,
      ps[q].node.M.n_rsp_valid&&ps[q].node.M.n_rsp_key==0,ps[q].node.M.n_fill_ack_valid,ps[q].node.M.n_alloc_ack_valid};
   always @(posedge clk) if($test$plusargs("TRACE_M")&&!reset)begin
    if(probe_control_live[0]&&!probe_control_seen[0])
     $display("MEXEC control %0d %0d 1 %0d %0d 2",cycle,q,ps[q].node.M.alloc_session,ps[q].node.M.n_alloc_ack_record);
    if(probe_control_live[1]&&!probe_control_seen[1])
     $display("MEXEC control %0d %0d 2 %0d %0d 2",cycle,q,
              ps[q].node.M.table_session[ps[q].node.M.n_fill_ack_bank],ps[q].node.M.n_fill_ack_record);
    if(probe_control_live[2]&&!probe_control_seen[2])
     $display("MEXEC control %0d %0d 4 %0d %0d %0d",cycle,q,ps[q].node.M.control_session,
              ps[q].node.M.n_rsp_record,ps[q].node.M.n_rsp_snapshot?4:2);
    if(probe_control_live[3]&&!probe_control_seen[3])
     $display("MEXEC control %0d %0d 11 %0d %0d %0d",cycle,q,ps[q].node.M.session,
              ps[q].node.M.command_reply_kind==1?0:ps[q].node.M.record_id,ps[q].node.M.command_reply_kind==0?3:2);
    if(probe_control_live[4]&&!probe_control_seen[4])
     $display("MEXEC control %0d %0d 9 %0d %0d %0d",cycle,q,ps[q].node.M.local_frame[79:48],
              ps[q].node.M.local_frame[111:80],ps[q].node.M.local_length);
    probe_control_seen<=probe_control_live;
    if(ps[q].node.M.tx_end)begin
     case(ps[q].node.M.tx_source)
      1:probe_control_seen[0]<=0;
      2:probe_control_seen[1]<=0;
      4:probe_control_seen[2]<=0;
      11:probe_control_seen[3]<=0;
      9:probe_control_seen[4]<=0;
     endcase
    end
    if(ps[q].node.M.n_exec_valid&&ps[q].node.M.n_exec_ready)
     $display("MEXEC exec %0d %0d %0d %0d %0d %0d",cycle,q,ps[q].node.M.session,
              ps[q].node.M.record_id,ps[q].node.M.exec_offset,ps[q].node.M.handle);
    if(ps[q].node.M.native.w_valid&&ps[q].node.M.native.w_ready&&
       (ps[q].node.M.native.w_first||ps[q].node.M.native.w_record_last))
     $display("MEXEC operand %0d %0d %0d %0d %0d",cycle,q,ps[q].node.M.native.record_id,
              ps[q].node.M.native.w_first,ps[q].node.M.native.w_record_last);
    if(ps[q].node.M.native.pop)
     $display("MEXEC raw %0d %0d %0d",cycle,q,ps[q].node.M.native.record_s[ps[q].node.M.native.raw_slot]);
    if(!ps[q].node.M.tx_valid&&ps[q].node.M.selected_source!=0)
     $display("MEXEC frame %0d %0d %0d %0d %0d %0d",cycle,q,ps[q].node.M.selected_source,
              ps[q].node.M.selected_frame[79:48],ps[q].node.M.selected_frame[111:80],ps[q].node.M.selected_length);
    if(ps[q].node.lr_valid&&ps[q].node.lr_ready&&ps[q].node.lr_eop)
     $display("MEXEC eop %0d %0d %0d %0d %0d",cycle,q,ps[q].node.M.tx_source,
              ps[q].node.M.tx_frame[79:48],ps[q].node.M.tx_frame[111:80]);
    if(ps[q].node.exec.early_exec.exec.g_terminal_valid&&ps[q].node.exec.early_exec.exec.g_terminal_ready)
     $display("MEXEC pop %0d %0d %0d %0d %0d",cycle,q,ps[q].node.exec.early_exec.exec.g_terminal_ticket[31:0],
              ps[q].node.exec.early_exec.exec.g_terminal_ticket[63:32],
              ps[q].node.exec.early_exec.exec.g_terminal_stored);
   end
  end
"""
ISSUE_MONITOR = """  for(genvar q=0;q<3;q++)begin: issue_port
   wire [127:0] side=ps[q].node.exec.early_exec.exec.side_data;
   wire [127:0] command_word=ps[q].node.lc_data;
   reg side_pending=0;
   reg [31:0] side_session=0;
   reg [3:0] previous_op;
   reg [31:0] previous_session,previous_seq;
   always @(posedge clk) if($test$plusargs("TRACE_ISSUE")&&!reset)begin
    if(ps[q].node.exec.early_exec.exec.g_cmd_valid&&ps[q].node.exec.early_exec.exec.g_cmd_ready)
     $display("PISSUE push %0d %0d %0d %0d",cycle,q,ps[q].node.exec.early_exec.exec.command_ticket[31:0],
              ps[q].node.exec.early_exec.exec.command_ticket[63:32]);
    if(ps[q].node.exec.early_exec.exec.side_valid&&ps[q].node.exec.early_exec.exec.side_sop)begin
     if(!side_pending||side_session!=side[63:32])
      $display("PISSUE side %0d %0d %0d %0d %0d %0d",cycle,q,side[19:16],side[63:32],side[95:64],side[23:20]);
     side_pending<=1;side_session<=side[63:32];
    end
    if(ps[q].node.lc_valid&&ps[q].node.lc_ready)begin
     if(ps[q].node.lc_sop)begin
      $display("PISSUE sop %0d %0d %0d %0d %0d %0d",cycle,q,command_word[19:16],
               command_word[63:32],command_word[95:64],command_word[23:20]);
      previous_op<=command_word[19:16];previous_session<=command_word[63:32];previous_seq<=command_word[95:64];
     end
     if(ps[q].node.lc_eop)begin
      if(ps[q].node.lc_sop)
       $display("PISSUE eop %0d %0d %0d %0d %0d",cycle,q,command_word[19:16],command_word[63:32],command_word[95:64]);
      else
       $display("PISSUE eop %0d %0d %0d %0d %0d",cycle,q,previous_op,previous_session,previous_seq);
     end
    end
    if(ps[q].node.exec.early_exec.exec.issue_use_valid&&ps[q].node.exec.early_exec.exec.af_use_ready)
     $display("PISSUE ause %0d %0d %0d %0d",cycle,q,ps[q].node.exec.early_exec.exec.issue_use_session,
              ps[q].node.exec.early_exec.exec.issue_use_record);
    if(ps[q].node.exec.early_exec.exec.af_load_valid&&ps[q].node.exec.early_exec.exec.af_load_ready)
     $display("PISSUE aload %0d %0d %0d %0d %0d %0d %0d",cycle,q,ps[q].node.exec.early_exec.exec.owner[31:0],
              ps[q].node.exec.early_exec.exec.k,ps[q].node.exec.early_exec.exec.af_load_slot,
              ps[q].node.exec.early_exec.exec.af_load_gen,ps[q].node.exec.early_exec.exec.af_load_error);
    if(ps[q].node.exec.early_exec.exec.A_front.w_valid&&ps[q].node.exec.early_exec.exec.af_w_ready)
     $display("PISSUE join %0d %0d %0d %0d %0d %0d %0d %0d %0d",cycle,q,
              ps[q].node.exec.early_exec.exec.owner[31:0],ps[q].node.exec.early_exec.exec.seq_id,
              ps[q].node.exec.early_exec.exec.k,ps[q].node.exec.early_exec.exec.selected_A_slot,
              ps[q].node.exec.early_exec.exec.current_A_generation,ps[q].node.exec.early_exec.exec.current_use,
              ps[q].node.exec.early_exec.exec.W_bank);
    if(ps[q].node.M.n_alloc_valid&&ps[q].node.M.n_alloc_ready)
     $display("PISSUE alloc %0d %0d %0d %0d %0d",cycle,q,ps[q].node.M.session,ps[q].node.M.record_id,
              ps[q].node.M.n_free_mask);
    if(ps[q].node.M.n_alloc_ack_valid&&!ps[q].node.M.alloc_installed)
     $display("PISSUE bank %0d %0d %0d %0d %0d %0d",cycle,q,ps[q].node.M.alloc_session,ps[q].node.M.n_alloc_ack_record,
              ps[q].node.M.n_alloc_ack_bank,ps[q].node.M.n_alloc_ack_generation);
   end
  end
"""
AREAD_MONITOR = """  always @(posedge clk) if($test$plusargs("TRACE_AREAD")&&!reset)begin
   if(xcopy_start&&xcopy_ready)
    $display("AREAD start %0d %0d %0d %0d %0d",cycle,tile_session,tile_k,tile_generation,tile_ticket);
   if(xcopy_u_valid&&xcopy_u_ready)
    $display("AREAD source %0d %0d %0d %0d",cycle,down_phase?int'(mid_source):3,xcopy_u_address,xcopy_u_tag);
   if(xcopy_u_rsp_valid&&xcopy_u_rsp_ready)
    $display("AREAD returned %0d %0d %0d",cycle,down_phase?int'(mid_source):3,xcopy_u_rsp_tag);
   if(xcopy_done&&xcopy_take)
    $display("AREAD done %0d %0d %0d",cycle,xcopy_gen,xcopy_error);
  end
  for(genvar q=0;q<3;q++)begin: aread_port
   reg [10:0] prefix_previous;
   reg [15:0] generation_previous;
   reg seen=0;
   always @(posedge clk) if($test$plusargs("TRACE_AREAD")&&!reset)begin
    if(ps[q].node.exec.early_exec.exec.load_pending&&ps[q].node.exec.early_exec.exec.af_cmd_ready)
     $display("AREAD load %0d %0d %0d %0d %0d %0d %0d",cycle,q,
              ps[q].node.exec.early_exec.exec.owner[31:0],ps[q].node.exec.early_exec.exec.k,
              ps[q].node.exec.early_exec.exec.current_A_generation,ps[q].node.exec.early_exec.exec.selected_A_slot,
              ps[q].node.exec.early_exec.exec.input_word);
    if(ps[q].node.ar_valid&&ps[q].node.ar_ready)
     $display("AREAD read %0d %0d %0d %0d",cycle,q,ps[q].node.ar_address,ps[q].node.ar_tag);
    if(ps[q].node.ar_rsp_valid&&ps[q].node.ar_rsp_ready)
     $display("AREAD response %0d %0d %0d",cycle,q,ps[q].node.ar_rsp_tag);
    if(ps[q].node.cp_valid&&ps[q].node.cp_ready)
     $display("AREAD copy %0d %0d %0d %0d",cycle,q,ps[q].node.cp_address,ps[q].node.cp_tag);
    if(ps[q].node.cp_ack_valid&&ps[q].node.cp_ack_ready)
     $display("AREAD ack %0d %0d %0d",cycle,q,ps[q].node.cp_ack_tag);
    if(!seen||prefix_previous!=ps[q].node.exec.early_exec.exec.effective_copy_prefix||
       generation_previous!=ps[q].node.exec.early_exec.exec.current_window_generation)
     $display("AREAD prefix %0d %0d %0d %0d",cycle,q,
              ps[q].node.exec.early_exec.exec.current_window_generation,
              ps[q].node.exec.early_exec.exec.effective_copy_prefix);
    prefix_previous<=ps[q].node.exec.early_exec.exec.effective_copy_prefix;
    generation_previous<=ps[q].node.exec.early_exec.exec.current_window_generation;
    seen<=1;
   end
  end
"""

WEIGHT_BEATS = ('WEIGHT install ', 'WEIGHT request ', 'WEIGHT returned ', 'WEIGHT filled ')
WEIGHT_FABRIC = ('WEIGHT offer ', 'WEIGHT backend_req ', 'WEIGHT backend_rsp ')
WEIGHT_MONITOR = """  for(genvar q=0;q<3;q++)begin: weight_probe
   reg seen=0,fill_seen=0;
   reg [31:0] previous_tag,previous_fill;
   always @(posedge clk) if($test$plusargs("TRACE_WEIGHT")&&!reset)begin
    if(ps[q].node.M.n_alloc_ack_valid&&!ps[q].node.M.alloc_installed)
     $display("WEIGHT install %0d %0d %0d %0d %0d %0d %0d",cycle,q,ps[q].node.M.alloc_session,
              ps[q].node.M.n_alloc_ack_record,ps[q].node.M.n_alloc_ack_bank,
              ps[q].node.M.n_alloc_ack_generation,ps[q].node.M.alloc_base);
    if(mr_valid[q]&&(!seen||previous_tag!=mr_tag[q]))
     $display("WEIGHT offer %0d %0d %0d %0d %0d %0d",cycle,q,mr_addr[q],mr_tag[q],mr_channel[q],mr_beats[q]);
    if(mr_valid[q]&&mr_ready[q])
     $display("WEIGHT request %0d %0d %0d %0d",cycle,q,mr_addr[q],mr_tag[q]);
    if(mrsp_valid[q]&&mrsp_ready[q])
     $display("WEIGHT returned %0d %0d %0d",cycle,q,mrsp_tag[q]);
    if(ps[q].node.M.n_fill_ack_valid&&(!fill_seen||previous_fill!=ps[q].node.M.n_fill_ack_record))
     $display("WEIGHT filled %0d %0d %0d %0d %0d",cycle,q,ps[q].node.M.n_fill_ack_record,
              ps[q].node.M.n_fill_ack_bank,ps[q].node.M.n_fill_ack_generation);
    seen<=mr_valid[q];previous_tag<=mr_tag[q];
    fill_seen<=ps[q].node.M.n_fill_ack_valid;previous_fill<=ps[q].node.M.n_fill_ack_record;
   end
  end
  if(WITH_SHARED_DMA)begin: weight_backend
   for(genvar q=0;q<4;q++)begin: backend_probe
    always @(posedge clk) if($test$plusargs("TRACE_WEIGHT")&&!reset)begin
     if(actual_shared_dma.d_req[q]&&actual_shared_dma.d_req_ready[q])
      $display("WEIGHT backend_req %0d %0d %0d %0d",cycle,q,actual_shared_dma.d_addr[q*64+:64],actual_shared_dma.d_tag[q*64+:64]);
     if(actual_shared_dma.d_rsp[q]&&actual_shared_dma.d_rsp_ready[q])
      $display("WEIGHT backend_rsp %0d %0d %0d",cycle,q,actual_shared_dma.d_ret_tag[q*64+:64]);
    end
   end
  end
"""

# From the last accepted CALL flit, the LC accepts the frame, reads PM and
# metadata, then presents the first 64 B fetch. CRC scans 124 bytes after the
# final data handshake. The two following edges consume CRC and assert service.
CALL_TO_FETCH = 46
DESCRIPTOR_CHECK_TICKS = 125  # DMA phase ends one edge after the final beat.
DONE_TO_TERMINAL_FRAME = 5
TERMINAL_FRAME_WITH_BUBBLE = 5
TERMINAL_EOP_OFFSET = 3
GATE_UP_STRIPES = 58
DOWN_GROUPS = 6
DOWN_SCOPE_COLUMNS = 384
P_COUNT = 3
ALL_P = (1 << P_COUNT) - 1
GATE_UP_COLUMNS = 11008
STRIPE_COLUMNS = 192
MID_COLUMNS = 128


def require(condition, message):
    if not condition:
        raise ValueError(message)


def instrument(source, destination):
    rtl = source.read_text(encoding='utf-8')
    if rtl.count(ANCHOR) != 1 or rtl.count(COPY_LAUNCH) != 1:
        raise ValueError('expected the unique programmed FFN block and COPY launch')
    rtl = rtl.replace(COPY_LAUNCH, COPY_DELAY + COPY_LAUNCH)
    with destination.open('x', encoding='utf-8', newline='\n') as output:
        output.write(rtl.replace(ANCHOR, MONITOR + ADMISSION_MONITOR + SCATTER_MONITOR + MID_MONITOR
                                 + RESULT_MONITOR + M_MONITOR + ISSUE_MONITOR + AREAD_MONITOR + WEIGHT_MONITOR + ANCHOR))


def read_trace(source, result_trace=None, *, m=False, issue=False, aread=False, weight=None, wdma=False):
    open_calls = {}
    scopes = []
    admission = {'ready': [], 'stripe': [], 'down': []}
    upstream = []
    scatter = []
    mid = []
    start = result = program = None
    passed = False
    result_prefixes = ('PRESULT ', 'READBACK ')
    if m:
        result_prefixes += ('MEXEC ',)
    if issue:
        result_prefixes += ('PISSUE ',)
    if aread:
        result_prefixes += ('AREAD ',)
    weight_prefixes = WEIGHT_BEATS
    if wdma:
        weight_prefixes += WEIGHT_FABRIC
    for line in source:
        if weight is not None and line.startswith(weight_prefixes):
            _, kind, *fields = line.split()
            weight.record(kind, *map(int, fields))
            continue
        if aread and line.startswith('K_PROFILE '):
            profile = {key: int(value) for key, value in (field.split('=') for field in line.split()[1:])}
            result_trace['AREAD', 'profile'].append(tuple(profile[key] for key in
                ('phase', 'scope', 'k', 'header', 'copy', 'proof', 'released')))
        if result_trace is not None and line.startswith(result_prefixes):
            domain, kind, *fields = line.split()
            require(kind in {'PRESULT': ('write', 'ack', 'record', 'valid'),
                             'READBACK': ('gate_done', 'request', 'ack'),
                             'MEXEC': ('exec', 'operand', 'raw', 'control', 'frame', 'eop', 'pop'),
                             'PISSUE': ('push', 'side', 'sop', 'eop', 'ause', 'aload', 'join', 'alloc', 'bank'),
                             'AREAD': A_EVENTS}[domain],
                    f'unexpected {domain} event {kind}')
            result_trace[domain, kind].append(tuple(map(int, fields)))
        if line.startswith('PROGRAM_PROFILE '):
            require(program is None, 'duplicate programmed FFN profile')
            program = dict(item.split('=') for item in line.split()[1:])
        if line.startswith('PASS ffn_three_p_native ') and ' program=1 ' in line:
            passed = True
        if line.startswith('ADMISSION '):
            _, kind, *fields = line.split()
            require(kind in admission, 'unknown admission event')
            admission[kind].append(tuple(map(int, fields)))
        if line.startswith('RELEASE '):
            _, kind, tick = line.split()
            upstream.append((kind, int(tick)))
        if line.startswith('SCATTER '):
            _, kind, *fields = line.split()
            scatter.append((kind, *map(int, fields)))
        if line.startswith('MID '):
            _, kind, *fields = line.split()
            mid.append((kind, *map(int, fields)))
        if not line.startswith('CONTROL '):
            continue
        _, kind, raw_tick, *fields = line.split()
        tick = int(raw_tick)
        values = tuple(map(int, fields))
        if kind == 'start':
            require(start is None and not values, 'duplicate or malformed program start')
            start = tick
        elif kind == 'result':
            require(result is None and len(values) == 2, 'duplicate or malformed program result')
            result = tick, *values
        else:
            client, *fields = values
            require(0 <= client < 3 and start is not None and tick >= start, 'invalid LC event')
            if kind == 'call':
                require(client not in open_calls, f'new CALL before LC {client} retired')
                open_calls[client] = {'client': client}
                scopes.append(open_calls[client])
            require(client in open_calls, f'LC {client} event without CALL')
            open_calls[client].setdefault(kind, []).append((tick, *fields))
            if wdma and kind in ('call', 'fetch', 'fetch_return'):
                weight.record(kind, tick, *values)
            if kind == 'terminal':
                del open_calls[client]
    require(passed and start is not None and result is not None and not open_calls and program is not None,
            'incomplete programmed FFN trace')
    require(len(scopes) == 192, 'expected all 192 native calls')
    return scopes, start, result, program, admission, upstream, scatter, mid


def first_ready(edges, ticks, mask, release):
    index = bisect_right(ticks, release) - 1
    require(index >= 0, 'missing P readiness at release')
    for tick, range_ready, exec_ready in edges[index:]:
        if range_ready & exec_ready & mask == mask:
            return max(tick, release)
    raise ValueError('no common P readiness after release')


def controller_triggers(upstream):
    """Derive each release from producer handshakes and the fixture's rules."""
    events = iter(upstream)

    def accept(kind):
        seen, tick = next(events, ('missing', -1))
        require(seen == kind, f'expected {kind} producer handshake, saw {seen}')
        return tick

    require(all(a[1] < b[1] for a, b in zip(upstream, upstream[1:])),
            'producer handshakes are out of order')
    trigger = accept('start')
    produced = committed = 0
    releases = {}
    for session in range(1, GATE_UP_STRIPES + 1):
        # The ring advances through DECIDE and STRIPE_SEND, then the
        # registered gather presents the work one edge after acceptance.
        releases[session] = trigger, 3
        trigger = accept('scatter')
        produced += min(STRIPE_COLUMNS, GATE_UP_COLUMNS - produced)
        while produced - committed >= MID_COLUMNS:
            trigger = accept('mid')
            committed += MID_COLUMNS
    require(produced == committed == GATE_UP_COLUMNS, 'incomplete Mid production')
    for _ in range(committed // MID_COLUMNS * 16):
        trigger = accept('mid_read')
    for group in range(DOWN_GROUPS):
        # Fixture switches to Down after the last Mid read ACK and samples
        # readiness one edge later. Other groups follow the prior DONE.
        releases[GATE_UP_STRIPES + group + 1] = trigger, 2 if group == 0 else 1
        trigger = accept('down_done')
    require(next(events, None) is None, 'unexpected additional producer handshake')
    return releases


def trace_action(name, ticks, stages, after=()):
    return {'id': name, 'after': after,
            'bindings': [{'id': name, 'site': 'P0', 'ticks': ticks, 'resources': [],
                          'nets': [], 'scratch_words': 0, 'event_stages': stages}]}


def p_result_addresses(session, client):
    if session > GATE_UP_STRIPES:
        return tuple(down_group_addresses(session - GATE_UP_STRIPES - 1, DOWN_GROUPS, client))
    first = STRIPE_COLUMNS * (session - 1)
    width = min(STRIPE_COLUMNS, GATE_UP_COLUMNS - first)
    return tuple(fragment.scratch + word for fragment in stripe_fragments(first, width)
                 if fragment.client == client for word in range(fragment.words))


def ordered_scopes(scopes):
    return sorted(scopes, key=lambda row: (row['dispatch'][0][1], row['client']))


def p_k_slices(owner):
    return (GATE_UP_COLUMNS if owner > GATE_UP_STRIPES else 2048) // 128


def m_records(scopes):
    """Expected record order, context, and store policy from FFN geometry."""
    records = defaultdict(list)
    sequence = 0
    for scope in ordered_scopes(scopes):
        client = scope['client']
        dispatch, owner = scope['dispatch'][0]
        contexts = len(p_result_addresses(owner, client)) // 2
        slices = p_k_slices(owner)
        for k in range(slices):
            for context in range(contexts):
                sequence += 1
                # A_LAST closes and releases the input slot. The first
                # member of a pair retires directly from the detached guard.
                retire_delay = 3 if context + 1 == contexts else context % 2
                records[client].append(Record(sequence, dispatch, owner, k * 128, context,
                                              k + 1 == slices, retire_delay))
    return records


def weight_address(client, record):
    """Address of an unheaded K128 weight record in the programmed fixture."""
    if record.scope > GATE_UP_STRIPES:
        base = 0x06000000
        first = DOWN_SCOPE_COLUMNS * (record.scope - GATE_UP_STRIPES - 1)
        group = record.context
    else:
        groups = len(p_result_addresses(record.scope, client)) // 4
        way, group = divmod(record.context, groups)
        base = (way + 1) * 0x02000000
        first = STRIPE_COLUMNS * (record.scope - 1)
    column = first + 8 * client + 24 * group
    index = (column // 8) * p_k_slices(record.scope) + record.k // 128
    return base + 64 * BEATS * index


def read_linked_weight(source, scopes, events, mode, seed, *, wjoin=False, lookahead=True, copy_delay_epoch=0):
    links, addresses = {}, {}
    side = defaultdict(list)
    joins = defaultdict(list)
    for tick, client, *fields in events['PISSUE', 'side']:
        side[client].append(Command(tick, *fields))
    if not wjoin:
        for tick, client, _, sequence, *_ in events['PISSUE', 'join']:
            joins[client].append((tick, sequence))
    records_by_client = m_records(scopes)
    join_driver = None
    if wjoin:
        tiles = [(scope, k, header, phase == 1) for phase, scope, k, header, *_ in events['AREAD', 'profile']]
        join_driver = JoinController(records_by_client, tiles, mode, lookahead=lookahead,
                                     copy_delay_epoch=copy_delay_epoch)
    for client, records in records_by_client.items():
        addresses[client] = {record.sequence: weight_address(client, record) for record in records}
        link = CommandLink({record.sequence: record.stores for record in records})
        link.run(joins[client], side[client], (), until=0)
        links[client] = link
    weight = WeightDmaTrace(mode, seed, CALL_TO_FETCH,
                            links=WeightCommandLinks(links, addresses, join_driver=join_driver))
    source.seek(0)
    for line in source:
        if line.startswith(WEIGHT_BEATS + WEIGHT_FABRIC + ('CONTROL call ', 'CONTROL fetch ',
                                                         'CONTROL fetch_return ', 'CONTROL result ')):
            _, kind, *fields = line.split()
            weight.record(kind, *map(int, fields))
    return weight


def m_control_replies(client, rows, records):
    intents = [Reply(*row) for row in rows]
    record_ids = {record.sequence for record in records}
    weight = {ALLOC: {}, FILL: {}}
    contexts = {BEGIN: set(), RF: set()}
    for reply in intents:
        require(reply.words == 2 and reply.source in (ALLOC, FILL, BEGIN, RF),
                f'P{client} unexpected M control request')
        if reply.source in weight:
            by_record = weight[reply.source]
            require(reply.sequence in record_ids and reply.sequence not in by_record,
                    f'P{client} M weight control identity differs')
            by_record[reply.sequence] = reply
        else:
            require(reply.sequence == 0 and reply.session not in contexts[reply.source],
                    f'P{client} M context control identity differs')
            contexts[reply.source].add(reply.session)
    require(weight[ALLOC].keys() == weight[FILL].keys() == record_ids and
            all(weight[ALLOC][row.sequence].session == weight[FILL][row.sequence].session and
                row.dispatch < weight[ALLOC][row.sequence].ready < weight[FILL][row.sequence].ready
                for row in records), f'P{client} M ALLOC/FILL coverage or ordering differs')
    expected_contexts = sum(record.k == 0 for record in records)
    require(len(contexts[BEGIN]) == len(contexts[RF]) == expected_contexts,
            f'P{client} M context reply coverage differs')
    return intents


def check_issue(client, observed, records, controls, weight=None):
    loads, generations = {}, [0, 0]
    for tick, scope, k, slot, generation, error in observed['aload']:
        require(slot == (k // 128) % 2 and k % 128 == 0 and error == 0 and (scope, k) not in loads,
                f'P{client} A load proof identity differs')
        generations[slot] += 1
        require(generation == generations[slot], f'P{client} A load generation differs')
        loads[scope, k] = tick, generation
    require(loads.keys() == {(record.scope, record.k) for record in records}, f'P{client} A proof coverage differs')

    joins = observed['join']
    require(len(joins) == len(records), f'P{client} W/A join coverage differs')
    for (tick, scope, sequence, k, slot, generation, use, _), record in zip(joins, records):
        require((scope, sequence, k, use) == (record.scope, record.sequence, record.k, record.context + 1)
                and slot == (k // 128) % 2, f'P{client} W/A join identity differs')
        loaded, expected_generation = loads[scope, k]
        require(record.dispatch < loaded and loaded + 2 <= tick and generation == expected_generation,
                f'P{client} W/A join used an unpublished A generation')
    side = [Command(*row) for row in observed['side']]
    require(all(SIDE_WORDS.get(command.opcode) == command.words and
                (command.sequence > 0 if command.opcode == ALLOC_CMD else command.sequence == 0)
                for command in side), f'P{client} unsupported M command or length')
    completions = weight.completed[client] if weight is not None else ()
    coupled = getattr(weight, 'issue', None)
    if coupled is not None:
        predicted = coupled[client]
    else:
        link = CommandLink({record.sequence: record.stores for record in records})
        fills = [reply for reply in controls if reply.source == FILL] if weight is None else []
        predicted = link.run([(row[0], row[2]) for row in joins], side, fills, weight_completions=completions)
    require(predicted.pushes == observed['push'], f'P{client} EXEC queue admission differs')
    require([(tick, c.opcode, c.session, c.sequence, c.words) for tick, c in predicted.commands] == observed['sop'],
            f'P{client} M command SOP differs')
    require([(tick + c.words - 1, c.opcode, c.session, c.sequence) for tick, c in predicted.commands] == observed['eop'],
            f'P{client} M command EOP differs')
    require(predicted.executions == observed['ause'], f'P{client} A use did not match M EXEC admission')
    require(predicted.allocations == observed['alloc'] and predicted.bank_acks == observed['bank'],
            f'P{client} W allocation mask, bank, or generation differs')
    require(sorted((r.ready, r.source, r.session, r.sequence, r.words) for r in predicted.controls)
            == sorted((r.ready, r.source, r.session, r.sequence, r.words) for r in controls),
            f'P{client} M control readiness differs')
    filled = {reply.sequence: tick + reply.words for tick, reply in predicted.replies if reply.source == FILL}
    bank = {sequence: index for _, _, sequence, index, _ in predicted.bank_acks}
    require(all(filled[row[2]] + 2 <= row[0] and bank[row[2]] == row[-1] for row in joins),
            f'P{client} W/A join used a W bank before matching FILL')
    report = {
        'commands': len(predicted.commands), 'a_loads': len(loads), 'allocations': len(predicted.allocations),
        'full_bank_waits': len(predicted.bank_waits),
        'alloc_ack_waits': len(predicted.alloc_ack_waits),
        'lookahead_waits': sum(push[0] > join[0] + 1 for push, join in zip(predicted.pushes, joins)),
    }
    if weight is not None:
        require(predicted.bank_acks == weight.installs[client], f'P{client} W DMA installs differ')
        owners = {item.sequence: (item.bank, item.generation) for item in completions}
        expected = [(reply.ready, reply.sequence, *owners[reply.sequence])
                    for reply in predicted.controls if reply.source == FILL]
        require(expected == weight.filled[client], f'P{client} W FILL ACK arbitration differs')
        report.update({'weight_completions': len(completions), 'fill_ack_waits': len(predicted.fill_ack_waits)})
    return predicted, report


def check_m_execution(scopes, trace, mode, *, issue=False, join_eops=None, weight=None):
    lanes = {kind: defaultdict(list) for kind in ('exec', 'operand', 'raw', 'control', 'frame', 'eop', 'pop')}
    for kind, lane in lanes.items():
        for tick, client, *fields in trace['MEXEC', kind]:
            require(0 <= client < P_COUNT, f'invalid M lane P{client}')
            lane[client].append((tick, *fields))
    issue_lanes = defaultdict(lambda: defaultdict(list))
    if issue:
        for kind in ('push', 'side', 'sop', 'eop', 'ause', 'aload', 'join', 'alloc', 'bank'):
            for tick, client, *fields in trace['PISSUE', kind]:
                require(0 <= client < P_COUNT, f'invalid P command lane P{client}')
                issue_lanes[client][kind].append((tick, *fields))

    stores, retired = {}, {}
    report = {'executions': 0, 'replies': 0, 'max_input_wait': 0, 'max_rf_wait': 0, 'overlapping_execs': 0}
    for client, records in m_records(scopes).items():
        observed = {kind: lane[client] for kind, lane in lanes.items()}
        starts = observed['exec']
        require(len(starts) == len(records), f'P{client} EXEC coverage differs')
        controls = m_control_replies(client, observed['control'], records)
        issue_trace = None
        if issue:
            issue_trace, issue_report = check_issue(client, issue_lanes[client], records, controls, weight)
            starts = [(tick, session, sequence, record.k, record.context)
                      for (tick, session, sequence), record in zip(issue_trace.executions, records, strict=True)]
            require(starts == observed['exec'], f'P{client} replayed M EXEC admission differs')
            totals = report.setdefault('issue', dict.fromkeys(issue_report, 0))
            for key, value in issue_report.items():
                totals[key] += value

        operands, products = [], []
        intents = controls.copy()
        previous_tick = previous_session = 0
        for (tick, session, sequence, offset, context), record in zip(starts, records):
            require((sequence, offset, context) == (record.sequence, record.k, record.context)
                    and max(previous_tick, record.dispatch) < tick and previous_session < session,
                    f'P{client} EXEC sequence, K offset, context, or session differs')
            previous_tick, previous_session = tick, session
            operands.extend(((tick + FIRST_OPERAND, sequence, 1, 0), (tick + LAST_OPERAND, sequence, 0, 1)))
            products.append((tick + RAW_READY, sequence))
            if not issue:
                intents.extend(execution_replies(tick, session, sequence, record.stores))
        require(operands == observed['operand'], f'P{client} operand stream timing differs')
        require(products == observed['raw'], f'P{client} raw dot timing differs')

        frames, eops, input_eop, rf_eop, fill_eop = [], [], {}, {}, {}
        replies = issue_trace.replies if issue else replay_replies(client, intents)
        for tick, reply in replies:
            identity = reply.source, reply.session, reply.sequence
            end = tick + reply.words
            if join_eops is not None and reply.sequence and reply.source in (ALLOC, FILL, INPUT):
                join_eops[client][reply.source, reply.sequence] = end
            frames.append((tick, *identity, reply.words))
            eops.append((end, *identity))
            if reply.source == INPUT:
                input_eop[reply.sequence] = end
                report['max_input_wait'] = max(report['max_input_wait'], tick - reply.ready)
            if reply.source == RF and reply.sequence:
                rf_eop[reply.sequence] = end
                report['max_rf_wait'] = max(report['max_rf_wait'], tick - reply.ready)
            if reply.source == FILL:
                fill_eop[reply.sequence] = end
        require(frames == observed['frame'], f'P{client} M reply arbitration differs')
        require(eops == observed['eop'], f'P{client} M reply EOP differs')
        report['replies'] += len(frames)

        commits = replay_commits(client, mode, [(rf_eop[record.sequence], record.stores) for record in records])
        pop = []
        previous_input = previous_rf = 0
        active = []
        for (tick, session, sequence, _, _), record, grants in zip(starts, records, commits):
            active = [end for end in active if end >= tick]
            require(max(previous_input, fill_eop[sequence]) < tick and len(active) < 2,
                    f'P{client} EXEC exceeded M ownership or preceded FILL')
            report['overlapping_execs'] += previous_rf >= tick
            previous_input, previous_rf = input_eop[sequence], rf_eop[sequence]
            terminal = grants[-1].start
            active.append(terminal)
            pop.append((terminal, session, sequence, int(record.stores)))
            retired[client, sequence] = terminal + record.retire_delay, record.scope
            if record.stores:
                stores[client, sequence] = grants[0].end
        require(pop == observed['pop'], f'P{client} guard terminal differs')
        if issue:
            pop_ticks = [row[0] for row in pop]
            require(all(index - bisect_left(pop_ticks, tick) < 2
                        for index, (tick, _, _) in enumerate(issue_trace.pushes)),
                    f'P{client} EXEC queue accepted with both guard slots live')
        report['executions'] += len(records)
    return stores, retired, report


def check_a_reads(scopes, trace, mode, m_retired, *, copy_delay_epoch=0):
    """Replay COPY and A using header release and replayed prior P retirement."""
    previous_retire = {}
    for p, records in m_records(scopes).items():
        for record in records:
            previous_retire[p, record.scope, record.k + 128] = m_retired[p, record.sequence][0]

    expected = defaultdict(list)
    expected['prefix'].extend((0, p, 0, 0) for p in range(P_COUNT))
    a_generations = [0, 0]
    tiles = [(owner, tile * 128) for owner in sorted({s['dispatch'][0][1] for s in scopes})
             for tile in range(p_k_slices(owner))]
    require(0 <= copy_delay_epoch <= len(tiles), 'COPY delay epoch is outside the programmed tile sequence')
    proofs = {}
    max_proof_wait = 0
    for epoch, (tile, profile) in enumerate(zip_longest(tiles, trace['AREAD', 'profile']), 1):
        require(tile is not None and profile is not None, 'A read K profile coverage differs')
        phase, scope, k, header, copy, proof, released = profile
        down = scope > GATE_UP_STRIPES
        require(tile == (scope, k) and phase == int(down), 'A read K profile identity differs')
        slot = (k // 128) % 2
        a_generations[slot] += 1
        generation = a_generations[slot]
        loads = [max(header - 2, previous_retire[p, scope, k] + 2) if k else header - 2
                 for p in range(P_COUNT)]
        start = header + int(epoch == copy_delay_epoch)
        events, accepted = replay_a_tile(mode, start, scope, k, epoch, epoch, loads, generation, down=down)
        require((copy, proof, released) == (events['done'][0][0] + 1, accepted + 1, accepted + 2),
                f'COPY, A proof, or lease release differs in scope {scope}, K={k}')
        for kind, rows in events.items():
            expected[kind].extend(rows)
        proofs[scope, k] = accepted
        expected['aload'].extend((accepted, p, scope, k, slot, generation, 0) for p in range(P_COUNT))
        max_proof_wait = max(max_proof_wait, accepted - max(tick for tick, _, _ in events['response']))

    for kind, rows in expected.items():
        domain = 'PISSUE' if kind == 'aload' else 'AREAD'
        for wanted, actual in zip_longest(sorted(rows), sorted(trace[domain, kind])):
            require(wanted == actual, f'{domain} {kind} differs: replay {wanted}, trace {actual}')
    return ({'tiles': len(tiles), 'copy_writes': len(expected['copy']), 'a_reads': len(expected['read']),
             'proofs': len(expected['aload']), 'max_wait_after_last_read': max_proof_wait}, proofs)


def check_wa_joins(scopes, trace, retired, eops, proofs, *, lookahead):
    sampled_proofs = defaultdict(dict)
    if proofs is None:
        for tick, p, scope, k, *_ in trace['PISSUE', 'aload']:
            sampled_proofs[p][scope, k] = tick
    observed = defaultdict(list)
    for tick, p, _, sequence, *_ in trace['PISSUE', 'join']:
        observed[p].append((tick, sequence))
    count = 0
    for p, records in m_records(scopes).items():
        retirement = {record.sequence: retired[p, record.sequence][0] for record in records}
        joins = join_schedule(records, proofs if proofs is not None else sampled_proofs[p],
                              eops[p], retirement, lookahead=lookahead)
        for expected, actual in zip_longest(joins, observed[p]):
            require(expected == actual, f'P{p} W/A join differs: replay {expected}, trace {actual}')
        count += len(joins)
    return {'bindings': count, 'lookahead': lookahead, 'a_proof': 'replayed' if proofs is not None else 'sampled'}


def check_p_results(scopes, trace, mode, m_stores=None, m_retired=None):
    writes, acks, records = (defaultdict(list) for _ in range(3))
    for kind, target in (('write', writes), ('ack', acks)):
        for tick, client, ticket, sequence, word, *address in trace['PRESULT', kind]:
            target[client].append((tick, ticket, sequence, word, *address))
    for tick, client, owner, sequence, next_k in trace['PRESULT', 'record']:
        records[owner, client].append((tick, sequence, next_k))
    ready = {(owner, client): tick for tick, client, owner in trace['PRESULT', 'valid']}
    require(len(ready) == len(trace['PRESULT', 'valid']) == len(scopes), 'P result VALID coverage differs')
    require(set(writes) == set(acks) == set(range(P_COUNT)), 'P store client coverage differs')

    cursors = [0] * P_COUNT
    tickets = [0] * P_COUNT
    next_sequence = 1
    operations, expected = [], []
    valid, down, down_values = {}, {}, {}
    for scope in ordered_scopes(scopes):
        client = scope['client']
        dispatch, owner = scope['dispatch'][0]
        done, _, read_bytes, write_bytes = scope['done'][0]
        key = owner, client
        addresses = p_result_addresses(owner, client)
        start, end = cursors[client], cursors[client] + len(addresses)
        cursors[client] = end
        issued, returned = writes[client][start:end], acks[client][start:end]
        slices = p_k_slices(owner)
        records_per_slice = len(addresses) // 2
        completed = records.pop(key, ())
        require(len(issued) == len(returned) == len(addresses) == write_bytes // 16
                and write_bytes % 16 == 0 and len(completed) == slices * records_per_slice
                and read_bytes == len(completed) * 1088,
                f'P{client} scope {owner} result traffic differs')
        previous = dispatch
        for index, (tick, sequence, next_k) in enumerate(completed):
            require(previous < tick < done and sequence == next_sequence + index
                    and next_k == (index // records_per_slice + 1) * 128,
                    f'P{client} scope {owner} record identity or K progress differs')
            if m_retired is not None:
                require((tick, owner) == m_retired.get((client, sequence)),
                        f'P{client} scope {owner} M record retirement differs')
            previous = tick
        next_sequence += len(completed)

        for index, (record, sequence, _) in enumerate(completed[-records_per_slice:]):
            first = 2 * index
            write0, write1 = issued[first:first + 2]
            ack0, ack1 = returned[first:first + 2]
            ticket = write0[1]
            require(ticket > tickets[client], f'P{client} result ticket reused or out of order')
            tickets[client] = ticket
            for word, (request, ack) in enumerate(((write0, ack0), (write1, ack1))):
                address = addresses[first + word]
                require(request[1:] == (ticket, sequence, word, address)
                        and ack[1:] == (ticket, sequence, word)
                        and dispatch < request[0] < ack[0] < record,
                        f'P{client} scope {owner} result address, ticket or ordering differs')
                if owner > GATE_UP_STRIPES:
                    down_values[f'P{client}:{address}'] = f'Down:{owner}:{client}:{sequence}:{word}'
            phases = tuple(Phase.from_spec(item['kind'], item['ticks'], item)
                           for word in range(2)
                           for item in sram_word_phases(client, mode, f'word{word}'))
            release = write0[0] if m_stores is None else m_stores[client, sequence]
            operations.append(Operation(phases, release=release))
            final = index + 1 == records_per_slice
            expected.append((key, (write0[0], ack0[0], write1[0], ack1[0]), record, final))
    require(not records and all(cursors[p] == len(writes[p]) == len(acks[p]) for p in range(P_COUNT)),
            'unexpected P result records or store transactions')

    capacity = dict.fromkeys((f'P{client}.S.{port}' for client in range(P_COUNT)
                              for port in ('request', 'response')), 1)
    grants = replay(operations, capacity)
    for (key, observed, record, final), operation in zip(expected, grants):
        request0, _, ack0, request1, _, ack1 = operation
        require((request0.start, ack0.start, request1.start, ack1.start) == observed,
                f'P scope {key} result store handshake differs')
        if final:
            # The last record goes through guard terminal, A close, A release,
            # and executor COMPLETE. The iterator exposes VALID two edges later.
            complete = ack1.start + 4
            require(complete == record and complete + 2 == ready.get(key),
                    f'P scope {key} range drain differs')
            valid[key] = complete + 2
            if key[0] > GATE_UP_STRIPES:
                down[key[0]] = max(down.get(key[0], 0), valid[key])

    completions = {}
    for scope in scopes:
        actual, owner, _, _ = scope['done'][0]
        key = owner, scope['client']
        predicted = down.get(owner, valid[key])
        require(actual == predicted, f'P scope {key} DONE handshake differs')
        completions[key] = predicted
    return completions, list(down.values()), down_values, {
        'stores': sum(cursors), 'records': next_sequence - 1, 'scopes': len(valid),
        'max_valid_to_done': max(completions[key] - tick for key, tick in valid.items()),
    }


def replay_readback(words, mode, release, published):
    service = readback_service(words, mode)
    windows = {f'P{client}:{address}': {'site': f'P{client}', 'offset': address * 16, 'bytes': 16}
               for client, address in words}
    require(windows.keys() == published.keys(), 'readback footprint differs from published results')
    hardware = {
        'resources': {resource: 1 for phase in service['phases'] for resource in phase['claims']},
        'nets': {}, 'sites': {f'P{p}': {'bytes': 16384, 'words': 1024} for p in range(P_COUNT)},
        'event_model': {'kind': 'qualified-event-model-v1', 'timing': 'replay',
                        'value_bytes': dict.fromkeys(published.values(), 16), 'windows': windows,
                        'initial_copies': published.copy(), 'routes': {},
                        'services': {'publish': {'ticks': release, 'claims': {}}, 'readback': service}},
    }
    tasks = [trace_action('publish', release, [{'service': 'publish'}]),
             trace_action('readback', service['ticks'], [{'service': 'readback', 'input_policy': 'resident',
                                                            'inputs': published}], after=('publish',))]
    plan = search(tasks, hardware, width=1)
    verify(tasks, hardware, (), plan)
    phases = plan['tasks'][-1]['evaluation']['events'][0]['phases']
    return [(phases[3 * index]['start'], phases[3 * index + 2]['start']) for index in range(len(words))]


def check_readback(upstream, trace, mode, down_done, result, last_terminal, published):
    last_mid = max(tick for kind, tick in upstream if kind == 'mid')
    require(trace['READBACK', 'gate_done'] == [(last_mid + 2,)], 'Gate/Up controller DONE differs')
    mid_words = mid_readback_words(GATE_UP_COLUMNS // MID_COLUMNS)
    down_words = down_readback_words(DOWN_GROUPS, P_COUNT)
    requests, acks = [], []
    phase_acks = []
    for phase, (words, release) in enumerate(((mid_words, last_mid + 3), (down_words, down_done[-1] + 1))):
        receipts = replay_readback(words, mode, release, published[phase])
        for (request, ack), (client, address) in zip(receipts, words):
            requests.append((request, phase, client, address))
            acks.append((ack, phase, client, address, READBACK_TAG))
        phase_acks.append([ack for _, ack in receipts])
    require(requests == trace['READBACK', 'request'], 'result readback request differs')
    require(acks == trace['READBACK', 'ack'], 'result readback ACK differs')
    require(result == phase_acks[1][-1] + 1 and last_terminal < phase_acks[1][-1],
            'program result acceptance differs')
    replacements = {'mid_read': phase_acks[0], 'down_done': down_done}
    for kind, ticks in replacements.items():
        require([tick for event, tick in upstream if event == kind] == ticks, f'{kind} producer differs')
    predictions = {kind: iter(ticks) for kind, ticks in replacements.items()}
    return [(kind, next(predictions[kind]) if kind in predictions else tick) for kind, tick in upstream], {
        'mid_words': len(mid_words), 'down_words': len(down_words), 'last_mid_ack': phase_acks[0][-1],
        'last_down_ack': phase_acks[1][-1], 'result_accept': result,
    }


def scatter_problem(fragments, mode, producer_ready, session):
    service = scatter_service(fragments, mode)
    resources = {r: 1 for phase in service['phases'] for r in phase['claims']}
    resources.update(service['hold_claims'])
    windows, values, inputs, outputs = {}, {}, {}, {}

    def window(client, address):
        site = f'P{client}'
        name = f'{site}:{address}'
        windows[name] = {'site': site, 'offset': address * 16, 'bytes': 16}
        return name

    for fragment in fragments:
        for word in range(fragment.words):
            source = window(fragment.client, fragment.scratch + word)
            destination = window(0, fragment.destination(word))
            require(destination not in outputs, 'scatter writes the same ring word twice')
            value = f'{source}@{session}'
            values[value] = 16
            inputs[source] = outputs[destination] = value

    tasks = [trace_action('producer', producer_ready, [{'service': 'producer'}]),
             trace_action('scatter', service['ticks'], [{'service': 'scatter', 'inputs': inputs, 'outputs': outputs}],
                          after=('producer',))]
    hardware = {'resources': resources, 'nets': {},
                'sites': {f'P{p}': {'bytes': 16384, 'words': 1024} for p in range(P_COUNT)},
                'event_model': {'kind': 'qualified-event-model-v1', 'timing': 'replay',
                                'value_bytes': values, 'windows': windows, 'initial_copies': inputs.copy(),
                                'routes': {}, 'services': {'producer': {'ticks': producer_ready, 'claims': {}},
                                                           'scatter': service}}}
    return tasks, hardware


def append_mid_actions(tasks, hardware, resident, tiles):
    """Retain unconsumed ring words across stripes and bind each tile to them."""
    spec = hardware['event_model']

    def window(client, address):
        site = f'P{client}'
        name = f'{site}:{address}'
        spec['windows'][name] = {'site': site, 'offset': address * 16, 'bytes': 16}
        return name

    for name, value in resident.items():
        client, address = name.split(':')
        window(int(client[1]), int(address))
        spec['initial_copies'][name] = value
        spec['value_bytes'][value] = 16
    produced = tasks[-1]['bindings'][0]['event_stages'][0]['outputs']
    require(not resident.keys() & produced.keys(), 'scatter overwrites an unconsumed ring word')
    resident.update(produced)
    spec['services']['decide'] = {'ticks': 1, 'claims': {}}
    for tile in tiles:
        inputs, outputs = {}, {}
        for client, address in sorted(tile.input_words()):
            name = window(client, address)
            require(name in resident, f'Mid read without a produced ring word at {name}')
            inputs[name] = resident.pop(name)
        for client, address in sorted(tile.output_words()):
            name = window(client, address)
            value = f'Mid:{tile.first}:{address}'
            spec['value_bytes'][value] = 16
            outputs[name] = value
        name = f'Mid:{tile.first}'
        claims = tile.claims()
        hardware['resources'].update(claims)
        spec['services'][name] = {'ticks': MIN_TICKS, 'claims': claims,
                                  'ffn_mid': {'mode': tile.mode, 'first': tile.first}}
        stages = [{'service': 'decide'}, {'service': name, 'input_policy': 'resident',
                                         'inputs': inputs, 'outputs': outputs}]
        tasks.append(trace_action(name, MIN_TICKS + 1, stages, after=(tasks[-1]['id'],)))


def check_scatter(scopes, upstream, observed, mode, observed_mid=None, p_done=None):
    by_session = {}
    for scope in scopes:
        done, session, _, _ = scope['done'][0]
        if session <= GATE_UP_STRIPES:
            owners = by_session.setdefault(session, {})
            require(scope['client'] not in owners, 'duplicate P completion in stripe')
            owners[scope['client']] = done if p_done is None else p_done[session, scope['client']]

    generation = words = cursor = 0
    commits = []
    latencies = []
    resident = {}
    consumed = 0
    mid_cursor = 0
    mid_commits = []
    ack_to_publish = []
    published = {}
    for session in range(1, GATE_UP_STRIPES + 1):
        completion = by_session.get(session, {})
        require(set(completion) == set(range(P_COUNT)), f'incomplete P completions for stripe {session}')
        first = STRIPE_COLUMNS * (session - 1)
        width = min(STRIPE_COLUMNS, GATE_UP_COLUMNS - first)
        fragments = stripe_fragments(first, width)
        ready = max(completion.values()) + 1
        tasks, hardware = scatter_problem(fragments, mode, ready, session)
        tiles = []
        if observed_mid is not None:
            while consumed + MID_COLUMNS <= first + width:
                tiles.append(MidTile(mode, consumed))
                consumed += MID_COLUMNS
            append_mid_actions(tasks, hardware, resident, tiles)
        plan = search(tasks, hardware, width=1)
        verify(tasks, hardware, (), plan)
        starts = {p['kind']: p['start'] for p in plan['tasks'][1]['evaluation']['events'][0]['phases']}
        stripe_events = []
        for index, fragment in enumerate(fragments):
            prefix = f'fragment{index}'
            generation += 1
            stripe_events.append(('start', starts[f'{prefix}.start'], session, generation, fragment.client,
                                  fragment.way, fragment.first, fragment.scratch, fragment.ring, fragment.words))
            for word in range(fragment.words):
                name = f'{prefix}.word{word}'
                tag = generation << 16 | word
                stripe_events.extend((
                    ('read', starts[f'{name}.read'], fragment.scratch + word, tag),
                    ('response', starts[f'{name}.response'], tag),
                    ('write', starts[f'{name}.write'], fragment.destination(word), tag),
                    ('ack', starts[f'{name}.ack'], tag),
                ))
            stripe_events.append(('done', starts[f'{prefix}.done'], fragment.words, 0))
            words += fragment.words
        for expected in stripe_events:
            actual = observed[cursor] if cursor < len(observed) else None
            require(actual == expected, f'stripe {session} scatter differs: expected {expected}, saw {actual}')
            cursor += 1
        commits.append(starts['commit'])
        latencies.append(starts['commit'] - ready)
        for tile, row in zip(tiles, plan['tasks'][2:]):
            event = row['evaluation']['events'][-1]
            end, expected = tile.run(event['start'])
            require(end == event['end'], f'Mid completion differs for tile {tile.first}')
            for predicted_event in expected:
                actual = observed_mid[mid_cursor] if mid_cursor < len(observed_mid) else None
                require(actual == predicted_event, f'Mid {tile.first} differs: expected {predicted_event}, saw {actual}')
                mid_cursor += 1
            mid_commits.append(end - 1)
            ack_to_publish.append(end - 1 - expected[-2][1])
            require(not published.keys() & event['outputs'].keys(), 'Mid publication overwrites a readback word')
            published.update(event['outputs'])

    require(cursor == len(observed), 'unexpected scatter trace entries')
    require([tick for kind, tick in upstream if kind == 'scatter'] == commits, 'scatter commit differs')
    predictions = {'scatter': iter(commits)}
    report = {'scatter': {'stripes': len(commits), 'fragments': generation, 'words': words,
                          'min_cycles': min(latencies), 'max_cycles': max(latencies)}}
    if observed_mid is not None:
        require(mid_cursor == len(observed_mid) and not resident and consumed == GATE_UP_COLUMNS,
                'incomplete Mid trace or unconsumed ring words')
        require([tick for kind, tick in upstream if kind == 'mid'] == mid_commits, 'Mid publication differs')
        predictions['mid'] = iter(mid_commits)
        report['mid'] = {'tiles': len(mid_commits), 'events': mid_cursor,
                         'max_last_ack_to_publish': max(ack_to_publish)}
    releases = [(kind, next(predictions[kind]) if kind in predictions else tick) for kind, tick in upstream]
    return releases, report, published


def replay_group(group, trigger, delay, is_down):
    """Use the same qualified event IR and checker as DP for one scope group."""
    origin = min(trigger, *(offer for offer, _ in group.values())) - 1
    services, tasks = {}, []
    hardware = {
        'resources': {f'P{client}': 1 for client in range(P_COUNT)},
        'sites': {'P0': {'words': 0, 'bytes': 0}}, 'nets': {},
        'event_model': {'kind': 'qualified-event-model-v1', 'timing': 'replay',
                        'routes': {}, 'windows': {}, 'value_bytes': {}, 'services': services},
    }

    def add(name, phases, waits=()):
        ticks = sum(t for _, t, _ in phases)
        services[name] = {'ticks': ticks, 'claims': {}}
        if len(phases) == 1:
            services[name]['claims'] = dict.fromkeys(phases[0][2], 1)
        else:
            services[name]['phases'] = [{'kind': kind, 'ticks': t, 'claims': dict.fromkeys(resources, 1)}
                                         for kind, t, resources in phases]
        tasks.append({'id': name, 'event_after': list(waits),
                      'bindings': [{'id': name, 'site': 'P0', 'ticks': ticks, 'resources': [], 'nets': [],
                                    'scratch_words': 0, 'event_stages': [{'service': name}]}]})

    def edge(task, source, target):
        return {'task': task, 'from': [0, source], 'to': [0, target]}

    add('controller', (('producer', trigger - origin, ()), ('release', delay, ())))
    if is_down:
        for client, (offer, _) in group.items():
            add(f'descriptor{client}', (('stage', offer - origin, ()),))
        waits = [edge('controller', 'release', 'stage')]
        waits.extend(edge(f'descriptor{client}', 'stage', 'stage') for client in group)
        add('dispatch', (('stage', 1, tuple(hardware['resources'])),), waits)
    else:
        for client, (offer, _) in group.items():
            add(f'P{client}', (('descriptor', offer - origin, ()), ('dispatch', 1, (f'P{client}',))),
                (edge('controller', 'release', 'dispatch'),))
    for width in (1, 8):
        plan = search(tasks, hardware, width=width)
        verify(tasks, hardware, (), plan)
        rows = {row['id']: row['evaluation']['events'][0] for row in plan['tasks']}
        for client, (_, actual) in group.items():
            event = rows['dispatch'] if is_down else rows[f'P{client}']['phases'][-1]
            require(origin + event['start'] == actual, f'candidate replay admission differs for P{client}')


def check_admission(scopes, transfers, admission, upstream=None):
    edges = admission['ready']
    require(edges and all(len(row) == 3 and 0 <= row[1] <= ALL_P and 0 <= row[2] <= ALL_P
                          for row in edges), 'missing or invalid P readiness trace')
    ticks = [row[0] for row in edges]
    require(ticks[0] == 0 and all(a < b for a, b in zip(ticks, ticks[1:])),
            'unordered or truncated P readiness trace')
    expected_sessions = (
        ('stripe', range(1, GATE_UP_STRIPES + 1)),
        ('down', range(GATE_UP_STRIPES + 1, GATE_UP_STRIPES + DOWN_GROUPS + 1)),
    )
    release = {}
    for kind, sessions in expected_sessions:
        rows = admission[kind]
        require(all(len(row) == 2 for row in rows) and
                [session for _, session in rows] == list(sessions) and
                all(a[0] < b[0] for a, b in zip(rows, rows[1:])), f'invalid {kind} releases')
        # The registered Gate/Up gather first asserts project_valid after
        # accepting the stripe. Down's fixture waits one edge on phase entry;
        # after subsequent groups it samples readiness in the same cycle.
        for tick, session in rows:
            release[session] = tick + (kind == 'stripe' or session == GATE_UP_STRIPES + 1)

    by_session = {}
    for scope, grants in zip(scopes, transfers):
        session = scope['offer'][0][1]
        group = by_session.setdefault(session, {})
        require(scope['client'] not in group, 'duplicate P in admission group')
        group[scope['client']] = grants[-1].end, scope['dispatch'][0][0]
    require(by_session.keys() == release.keys(), 'admission session coverage differs')
    triggers = controller_triggers(upstream) if upstream is not None else None
    if triggers is not None:
        require({session: tick + delay for session, (tick, delay) in triggers.items()} == release,
                'producer-derived controller release differs')

    report = {kind: {'calls': 0, 'waiting_calls': 0, 'max_wait': 0,
                     'max_controller_wait': 0, 'max_peer_wait': 0, 'max_node_wait': 0}
              for kind, _ in expected_sessions}
    for session, group in by_session.items():
        require(set(group) == set(range(P_COUNT)), f'missing P in session {session}')
        is_down = session > GATE_UP_STRIPES
        last_descriptor = max(offer for offer, _ in group.values())
        for client, (offer, actual) in group.items():
            descriptor = last_descriptor if is_down else offer
            eligible = max(descriptor, release[session])
            predicted = first_ready(edges, ticks, ALL_P if is_down else 1 << client, eligible)
            require(predicted == actual, f'admission timing differs for session {session}, P{client}: '
                    f'expected {predicted}, saw {actual}')
            stats = report['down' if is_down else 'stripe']
            stats['calls'] += 1
            stats['waiting_calls'] += predicted > offer
            stats['max_wait'] = max(stats['max_wait'], predicted - offer)
            stats['max_controller_wait'] = max(stats['max_controller_wait'], max(0, release[session] - offer))
            stats['max_peer_wait'] = max(stats['max_peer_wait'], eligible - max(offer, release[session]))
            stats['max_node_wait'] = max(stats['max_node_wait'], predicted - eligible)
        if triggers is not None:
            replay_group(group, *triggers[session], is_down)
    return report


def check(source, mode, seed, *, admission=False, phase_release=False, scatter=False, mid=False, readback=False,
          m=False, issue=False, aread=False, copy_delay_epoch=0, wa_join=False, lookahead=True, wfill=False,
          wdma=False, wlink=False, wjoin=False):
    aread = aread or wjoin or copy_delay_epoch != 0
    wa_join = wa_join or aread or not lookahead
    wlink = wlink or wjoin
    wdma = wdma or wlink
    issue = issue or wa_join or wfill or wdma
    m = m or issue
    readback = readback or m
    result_trace = defaultdict(list) if readback else None
    weight = None
    if not wlink:
        weight = WeightDmaTrace(mode, seed, CALL_TO_FETCH) if wdma else WeightTrace() if wfill else None
    scopes, start, result, program, sampled_admission, upstream, observed_scatter, observed_mid = read_trace(
        source, result_trace, m=m, issue=issue, aread=aread, weight=weight, wdma=wdma and not wlink)
    if wlink:
        weight = read_linked_weight(source, scopes, result_trace, mode, seed, wjoin=wjoin,
                                    lookahead=lookahead, copy_delay_epoch=copy_delay_epoch)
    if weight is not None:
        weight.validate()
    transfers = []
    sequence = [0] * 3
    read_bytes = write_bytes = 0
    for index, scope in enumerate(scopes):
        client = scope['client']
        sequence[client] += 1
        serial = sequence[client]
        prefix = f'CALL {index + 1}, LC {client}'
        require(all(len(scope.get(event, ())) == count for event, count in
                    (('call', 1), ('fetch_valid', 2), ('fetch', 2), ('fetch_return', 2),
                     ('offer', 1), ('dispatch', 1), ('done', 1), ('terminal', 1))),
                f'{prefix} missing or duplicated events')
        (call,), = scope['call']
        (offer, offer_owner), = scope['offer']
        (dispatch, dispatch_owner), = scope['dispatch']
        (done, done_owner, reads, writes), = scope['done']
        (terminal,), = scope['terminal']
        require(offer_owner == dispatch_owner == done_owner == serial and offer <= dispatch <= done < terminal,
                f'{prefix} service ownership or boundaries differ')
        read_bytes += reads + 128
        write_bytes += writes
        addr = 4096 + 128 * index
        expected = ((serial * 2, addr), (serial * 2 + 1, addr + 64))
        require(tuple(row[1:] for row in scope['fetch_valid']) ==
                tuple(row[1:] for row in scope['fetch']) == expected, f'{prefix} descriptor identity differs')
        require(sorted(row[1] for row in scope['fetch_return']) == [serial * 2, serial * 2 + 1],
                f'{prefix} returned tags differ')
        require(tuple(row[0] for row in scope['fetch_valid']) ==
                (call + CALL_TO_FETCH, scope['fetch'][0][0] + 1), f'{prefix} source VALID timing differs')
        transfers.append(Operation((
            Phase('decode CALL', CALL_TO_FETCH),
            Phase('descriptor DMA', 1, dma_read=Read(client, addr, 128, 2)),
            Phase('CRC and service offer', DESCRIPTOR_CHECK_TICKS),
        ), release=call))

    p_done = None
    m_stores = m_retired = None
    join_eops = defaultdict(dict) if wa_join else None
    if m:
        m_stores, m_retired, m_report = check_m_execution(scopes, result_trace, mode, issue=issue,
                                                          join_eops=join_eops, weight=weight)
    if readback:
        p_done, down_done, down_values, p_report = check_p_results(scopes, result_trace, mode, m_stores, m_retired)
    terminals = []
    for scope in scopes:
        client = scope['client']
        done, owner, _, _ = scope['done'][0]
        if p_done is not None:
            done = p_done[owner, client]
        terminals.append(Operation((
            Phase('terminal packet and receive bubble', TERMINAL_FRAME_WITH_BUBBLE, (('MC.rx', 1),), client),
        ), release=done + DONE_TO_TERMINAL_FRAME))
    profile = Profile.from_spec({'ffn_provider': {'mode': mode, 'seed': seed}})
    grants = replay(transfers + terminals, {'MC.rx': 1}, dma_profile=profile)
    terminal_ticks = []
    for scope, transfer, terminal in zip(scopes, grants[:len(scopes)], grants[len(scopes):]):
        beats = transfer[1].dma_beats
        require(tuple(beat.reserved for beat in beats) == tuple(row[0] for row in scope['fetch'])
                and sorted((beat.delivered, scope['fetch'][i][1]) for i, beat in enumerate(beats)) ==
                scope['fetch_return'], 'descriptor DMA handshakes differ')
        require(transfer[-1].end == scope['offer'][0][0], 'CRC or service offer timing differs')
        terminal_ticks.append(terminal[0].start + TERMINAL_EOP_OFFSET)
        require(terminal_ticks[-1] == scope['terminal'][0][0], 'terminal arbitration or framing differs')
    require((int(program['calls']), int(program['confirmed_reads']), int(program['confirmed_writes'])) ==
            (len(scopes), read_bytes, write_bytes) and result[1:] == (read_bytes, write_bytes),
            'program byte accounting differs')
    require(result[0] > max(terminal_ticks), 'program result preceded child retirement')
    report = {'calls': len(scopes), 'descriptor_beats': 2 * len(scopes), 'start': start,
              'result_accept': result[0], 'read_bytes': read_bytes, 'write_bytes': write_bytes,
              'longest_service_offer_wait': max(s['dispatch'][0][0] - s['offer'][0][0] for s in scopes),
              'longest_done_to_terminal': max(s['terminal'][0][0] - s['done'][0][0] for s in scopes)}
    if scatter or mid or readback:
        upstream, data_report, mid_values = check_scatter(scopes, upstream, observed_scatter, mode,
                                                          observed_mid if mid or readback else None, p_done)
        report.update(data_report)
    if readback:
        upstream, report['readback'] = check_readback(upstream, result_trace, mode, down_done, result[0],
                                                       max(terminal_ticks), (mid_values, down_values))
        report['p_results'] = p_report
    if m:
        report['m_execution'] = m_report
    proofs = None
    if aread:
        report['a_reads'], proofs = check_a_reads(scopes, result_trace, mode, m_retired,
                                                  copy_delay_epoch=copy_delay_epoch)
    if wa_join:
        report['wa_joins'] = check_wa_joins(scopes, result_trace, m_retired, join_eops, proofs, lookahead=lookahead)
    if wjoin:
        driver = weight.links.join_driver
        expected = defaultdict(list)
        for tick, client, _, sequence, *_ in result_trace['PISSUE', 'join']:
            expected[client].append((tick, sequence))
        require(all(lane.joined == expected[p] for p, lane in driver.lanes.items()) and driver.proofs == proofs,
                'live A proof or W/A binding differs')
        retirements = {(p, record.sequence): (lane.retired[record.sequence], record.scope)
                       for p, lane in driver.lanes.items() for record in lane.records}
        require(retirements == m_retired, 'live P record retirement differs')
        report['wa_joins']['drives_command_issue'] = True
    if wdma:
        report['weight_dma'] = dict(weight.counts)
    if admission or phase_release or scatter or mid or readback:
        report['admission'] = check_admission(scopes, grants[:len(scopes)], sampled_admission,
                                              upstream if phase_release or scatter or mid or readback else None)
    if phase_release or scatter or mid or readback:
        report['phase_replay_calls_per_strategy'] = len(scopes)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prepare = sub.add_parser('instrument')
    prepare.add_argument('source', type=Path)
    prepare.add_argument('destination', type=Path)
    verify = sub.add_parser('check')
    verify.add_argument('log', type=Path)
    verify.add_argument('--mode', type=int, choices=(0, 1), required=True)
    verify.add_argument('--seed', type=int, default=25001)
    verify.add_argument('--admission', action='store_true')
    verify.add_argument('--phase-release', action='store_true')
    verify.add_argument('--scatter', action='store_true')
    verify.add_argument('--mid', action='store_true')
    verify.add_argument('--result', action='store_true')
    verify.add_argument('--m', action='store_true', help='verify M EXEC through result acceptance')
    verify.add_argument('--issue', action='store_true', help='verify P command issue through result acceptance')
    verify.add_argument('--aread', action='store_true', help='also replay COPY and private A SRAM handshakes')
    verify.add_argument('--copy-delay-epoch', type=int, default=0, help='launch COPY one cycle later in this tile epoch')
    verify.add_argument('--wa-join', action='store_true', help='also verify P bindings from A proof and reply EOPs')
    verify.add_argument('--no-lookahead', action='store_true', help='verify the fixture with W lookahead disabled')
    verify.add_argument('--wfill', action='store_true', help='drive W FILL from DMA beat receipts')
    verify.add_argument('--wdma', action='store_true', help='replay W and descriptor traffic through the shared DMA')
    verify.add_argument('--wlink', action='store_true', help='couple M bank allocation, shared DMA, and FILL replies')
    verify.add_argument('--wjoin', action='store_true', help='drive bindings from A proofs and live M/DMA')
    args = parser.parse_args()
    if args.action == 'instrument':
        instrument(args.source, args.destination)
    else:
        open_log = gzip.open if args.log.suffix == '.gz' else open
        with open_log(args.log, 'rt', encoding='utf-8') as source:
            print(json.dumps(check(source, args.mode, args.seed, admission=args.admission,
                                   phase_release=args.phase_release, scatter=args.scatter, mid=args.mid,
                                   readback=args.result, m=args.m, issue=args.issue, aread=args.aread,
                                   copy_delay_epoch=args.copy_delay_epoch, wa_join=args.wa_join,
                                   lookahead=not args.no_lookahead, wfill=args.wfill, wdma=args.wdma,
                                   wlink=args.wlink, wjoin=args.wjoin), indent=2))


if __name__ == '__main__':
    main()
