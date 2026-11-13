"""Wrap the previously executed three-P FFN fixture with a local rearm test."""

import argparse
import hashlib
import json
from pathlib import Path

from derive_copy_epoch_rearm import edit, replace_once


def top(text):
    text = edit(text, [
        ("module test_ffn_three_p_native #(", "module test_ffn_three_p_copy_rearm #("),
        (" reg reset=1,start_valid=0,done_ready=0;", """ reg reset=1,start_valid=0,done_ready=0;
 reg rearm_valid=0,fence_done_take=0,hold_copy_ack=0;
 wire rearm_ready,fence_done,admit_new_owner,namespace_rearm,x_quant_idle,mid_quant_idle,gather_idle;
 wire [2:0] p_s_empty,xp_raw_ack_valid;
 integer invocation=0,blocked_ack_cycles,fence_count;"""),
        (" ffn_gate_up_mid #(.TOTAL_COLUMNS(COLS)) dut(.clk,.reset,.start_valid,.start_ready,.start_owner(JOB),",
         """ ffn_gate_up_mid_rearm #(.TOTAL_COLUMNS(COLS)) dut(.namespace_rearm,.namespace_idle(mid_quant_idle),
  .clk,.reset,.start_valid(start_valid&&admit_new_owner),.start_ready,.start_owner(JOB),"""),
        (" ffn_stripe_commit gather(.clk,.reset,", " ffn_stripe_commit_rearm gather(.namespace_rearm,.namespace_idle(gather_idle),.clk,.reset,"),
        (" s32_stripe_copy scatter(.clk,.reset,", " s32_stripe_copy_rearm scatter(.namespace_rearm,.clk,.reset,"),
        (" reg [15:0] tile_generation=0,tile_k=0;", " reg [15:0] tile_generation=16'hffdf,tile_k=0;"),
        (" wire [31:0] tile_session=32'(down_phase?STRIPES+1+down_index:stripe_index+1);",
         " wire [31:0] tile_session=32'(64*invocation+(down_phase?STRIPES+1+down_index:stripe_index+1));"),
        (" copy_scale_header_tx x_header(.clk,.reset,", " copy_scale_header_tx_rearm x_header(.namespace_rearm,.clk,.reset,"),
        (" early_copy_epoch_3p xcopy(.clk,.reset,", " early_copy_epoch_3p_rearm xcopy(.namespace_rearm,.clk,.reset,"),
        (" s32_a16_tile_quantizer quant(.clk,.reset,",
         " s32_a16_tile_quantizer_rearm quant(.namespace_rearm,.namespace_idle(x_quant_idle),.clk,.reset,"),
        (" test_ffn_native_p_node #(.SHARED_MID_SOURCE(WITH_DOWN)) node(.clk,.reset,",
         " test_ffn_native_p_rearm_node #(.SHARED_MID_SOURCE(WITH_DOWN)) node(.namespace_rearm,.s_owners_empty(p_s_empty[p]),.clk,.reset,"),
        (".cp_ack_valid(xp_ack_valid[p]),.cp_ack_ready(xp_ack_ready[p])",
         ".cp_ack_valid(xp_raw_ack_valid[p]),.cp_ack_ready(xp_ack_ready[p]&&!hold_copy_ack)"),
        (" assign mid_ready=mode==0||cycle%13>=4;", """ assign mid_ready=mode==0||cycle%13>=4;
 assign xp_ack_valid=xp_raw_ack_valid&{3{!hold_copy_ack}};
 // These wires are the direct, single-clock routes in this fixture. Each
 // independent S response-owner queue is also checked at the fence boundary.
 wire copy_transport_drained=!(|{hf_valid,ha_valid,xcopy_u_valid,xcopy_u_rsp_valid,
      xp_valid,xp_raw_ack_valid,cs_valid,cs_rsp_valid,cd_valid,cd_rsp_valid,fs_valid,fs_rsp_valid,q_req,q_rsp});
 ffn_copy_epoch_fence fence(.clk,.reset,.rearm_valid,.rearm_ready,.done_valid(fence_done),.done_ready(fence_done_take),
  .outer_scope_idle(gather_idle&&!inspect&&project_valid==0&&project_done_valid==0&&pend==0),
  .header_tx_idle(header_idle),.header_rx_idle(window_idle),.copy_idle(xcopy_idle),.scatter_idle(copy_drained),
  .x_quant_idle,.mid_quant_idle,.p_a_drained(pr_q),.s_owners_empty({u_owners==0,p_s_empty}),
  .copy_transport_drained,.admit_new_owner,.namespace_rearm);
 always @(posedge clk)begin
  if(reset)begin
   fence_count<=0;blocked_ack_cycles<=0;
  end else begin
   if(namespace_rearm)fence_count<=fence_count+1;
   if(rearm_valid&&hold_copy_ack)begin
    assert(p_s_empty!=3'b111&&!xcopy_idle&&!rearm_ready&&!namespace_rearm&&
      !admit_new_owner&&xcopy_identity&&xcopy_gen==16'hffff);
    blocked_ack_cycles<=blocked_ack_cycles+1;
   end
  end
 end"""),
        ("   w_requests<=0;w_responses<=0;rr<=0;pend<=0;rsp_idx<=-1;\n  end else begin",
         """   w_requests<=0;w_responses<=0;rr<=0;pend<=0;rsp_idx<=-1;
  end else if(namespace_rearm)begin
   cycle<=cycle+1;stripe_index<=0;mid_retired<=0;loads<=0;copy_writes<=0;
   project_terms<=0;w_requests<=0;w_responses<=0;
  end else begin"""),
        (" integer start_cycle,down_start;", " integer start_cycle;"),
    ])
    start = text.index("  start_cycle=cycle;\n")
    end = text.index("  if(WITH_DOWN)begin\n   assert(pr_q", start)
    main = text[start:end]
    main = replace_once(main, "while(!start_ready);", "while(!start_ready||!admit_new_owner);")
    read_start = main.index("  for(integer k=0;k<TILES;k++)")
    main, readback = main[:read_start], main[read_start:]
    body = """  assert(COLS==384&&!WITH_DOWN);
  fork
   run_ffn();
   begin
    while(tile_generation!=16'hffff)cycle_wait();
    hold_copy_ack=1;
    while(xp_raw_ack_valid==0)cycle_wait();
    rearm_valid=1;
    repeat(7)cycle_wait();
    assert(blocked_ack_cycles==7&&fence_count==0);
    hold_copy_ack=0;
   end
  join
  while(!fence_done)cycle_wait();
  rearm_valid=0;
  assert(fence_count==1&&!admit_new_owner&&!xcopy_identity&&xcopy_prefix==0&&
    xcopy_count==32'd1536&&copy_committed==32'd192&&x_shift_valid);
  repeat(3)cycle_wait();
  assert(fence_done&&!admit_new_owner&&fence_count==1);
  fence_done_take=1;cycle_wait();fence_done_take=0;
  assert(!fence_done&&admit_new_owner);
  // Read every old Mid word after rearm, before reusing S for the next scope.
  verify_mid();
  tile_generation=0;invocation=1;
  assert(dir_cfg_ready);dir_cfg=1;cycle_wait();dir_cfg=0;
  run_ffn();
  verify_mid();
  assert(fence_count==1&&tile_generation==32&&xcopy_count==32'd3072&&copy_committed==32'd384);
  $display("PASS ffn_copy_rearm old_final=65535 new_final=32 held_ack_cycles=%0d fences=%0d words=%0d scatter=%0d",blocked_ack_cycles,fence_count,xcopy_count,copy_committed);
  $finish;
 end
 task automatic run_ffn;
""" + main + """ endtask
 task automatic verify_mid;
""" + readback + """ endtask
 wire _unused_fixture=^{down_words[0],down_terminal,down_ready};
"""
    end_print = text.index(" wire [130:0] _unused_stats=", end)
    return text[:start] + body + text[end_print:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-lock", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    lock = json.loads(args.source_lock.read_text(encoding="utf-8"))["source_sha256"]

    def frozen(name):
        path = "project/experiments/block_local_native/" + name
        raw = (args.root / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == lock[path]
        return raw.decode("utf-8")

    (args.out / "test_ffn_three_p_copy_rearm.sv").write_text(top(frozen("test_ffn_three_p_native.sv")), encoding="utf-8")
    node = edit(frozen("test_ffn_native_p_node.sv"), [
        ("module test_ffn_native_p_node #(", "module test_ffn_native_p_rearm_node #("),
        (" input logic clk,reset,allow_req,allow_rsp,", " input wire namespace_rearm,output wire s_owners_empty,\n input logic clk,reset,allow_req,allow_rsp,"),
        (" copy_scale_header_rx rx(.clk,.reset,", " assign s_owners_empty=owners==0;\n copy_scale_header_rx_rearm rx(.namespace_rearm,.clk,.reset,"),
    ])
    (args.out / "test_ffn_native_p_rearm_node.sv").write_text(node, encoding="utf-8")
    # The fixture has exactly 12 scatter and three Mid quantizer generations
    # before the fence. Start those local counters near exhaustion only here.
    for stem, old, new in (
        ("ffn_stripe_commit_rearm", "source<=0;way<=0;epoch<=0;", "source<=0;way<=0;epoch<=16'hfff3;"),
        ("ffn_gate_up_mid_rearm", "if(reset)begin quant_epoch<=0;", "if(reset)begin quant_epoch<=16'hfffc;"),
    ):
        source = (args.generated / (stem + ".sv")).read_text(encoding="utf-8")
        (args.out / (stem + ".sv")).write_text(replace_once(source, old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
