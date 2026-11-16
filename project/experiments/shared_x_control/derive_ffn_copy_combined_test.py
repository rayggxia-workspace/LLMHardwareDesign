"""Compose COPY budget admission with the real three-P shared DMA fixture."""

import argparse
import hashlib
import json
from pathlib import Path

from derive_copy_epoch_rearm import edit, replace_once
from derive_ffn_copy_rearm_test import top as rearm_top


NATIVE = Path("project/rtl/block_local_native")
EXPERIMENT = Path("project/experiments/block_local_native")


def shared_top(source):
    source = edit(source, [
        ("  test_ffn_native_p_node #(.SHARED_MID_SOURCE(WITH_DOWN),.FOUR_BANK_LOOKAHEAD(FOUR_BANK_LOOKAHEAD)) node(\n   .clk,.reset,",
         "  test_ffn_native_p_node #(.SHARED_MID_SOURCE(WITH_DOWN)) node(.clk,.reset,"),
        ("   w_requests<=0;w_responses<=0;\n  end else begin",
         "   w_requests<=0;w_responses<=0;rr<=0;pend<=0;rsp_idx<=-1;\n  end else begin"),
    ])
    text = rearm_top(source)
    return edit(text, [
        ("module test_ffn_three_p_copy_rearm #(", "module test_ffn_copy_combined #("),
        (" reg rearm_valid=0,fence_done_take=0,hold_copy_ack=0;", """ reg fence_done_take=0,hold_copy_ack=0;
 wire rearm_valid;
 reg next_scope=0,launch_enable=1,tile_issue=0,scope_running;
 wire launch_valid,launch_ready,scope_ready;
 wire [15:0] scatter_generation,mid_generation;
 wire [2:0] mf_valid,mf_ready,mf_done,mf_take;
 wire [95:0] mf_cookie,mf_done_cookie;
 wire [26:0] mf_epoch,mf_done_epoch;
 integer m_fences[3],scope_count;
 integer first_purges;
 wire [2:0] m_pending;"""),
        (".namespace_idle(mid_quant_idle),\n  .clk,.reset,.start_valid(start_valid&&admit_new_owner),.start_ready,.start_owner(JOB),",
         ".namespace_idle(mid_quant_idle),.namespace_generation(mid_generation),\n  .clk,.reset,.start_valid(launch_valid&&launch_enable),.start_ready(launch_ready),.start_owner(JOB),"),
        (".namespace_idle(gather_idle),.clk,.reset,", ".namespace_idle(gather_idle),.namespace_generation(scatter_generation),.clk,.reset,"),
        (" reg [15:0] tile_generation=16'hffdf,tile_k=0;", " reg [15:0] tile_generation,tile_k=0;"),
        ("  tile_k=16'(k);tile_generation=tile_generation+1;tile_ticket=tile_ticket+1;",
         "  tile_k=16'(k);tile_issue=1;tile_ticket=tile_ticket+1;cycle_wait();tile_issue=0;"),
        ("test_ffn_native_p_rearm_node #(.SHARED_MID_SOURCE(WITH_DOWN)) node(.namespace_rearm,.s_owners_empty(p_s_empty[p]),.clk,.reset,",
         """test_ffn_native_p_rearm_node #(.SHARED_MID_SOURCE(WITH_DOWN),.FOUR_BANK_LOOKAHEAD(FOUR_BANK_LOOKAHEAD)) node(
   .namespace_rearm,.s_owners_empty(p_s_empty[p]),
   .mc_fence_req_valid(mf_valid[p]),.mc_fence_req_ready(mf_ready[p]),.mc_fence_req_cookie(mf_cookie[p*32+:32]),
   .mc_fence_req_epoch(mf_epoch[p*9+:9]),.mc_fence_done_valid(mf_done[p]),.mc_fence_done_ready(mf_take[p]),
   .mc_fence_done_cookie(mf_done_cookie[p*32+:32]),.mc_fence_done_epoch(mf_done_epoch[p*9+:9]),.clk,.reset,"""),
        ("  wire [383:0] unused_cancel_tag,unused_fence_cookie;\n  wire [107:0] unused_fence_epoch;",
         "  wire [383:0] unused_cancel_tag,all_fence_cookie;\n  wire [107:0] all_fence_epoch;"),
        ("   .c_fence_valid(12'd0),.c_fence_ready(unused_debug[56:45]),.c_fence_cookie(384'd0),.c_fence_epoch(108'd0),\n"
         "   .c_fence_done_valid(unused_debug[68:57]),.c_fence_done_ready(12'hfff),.c_fence_done_cookie(unused_fence_cookie),.c_fence_done_epoch(unused_fence_epoch),",
         """   .c_fence_valid({mf_valid,9'd0}),.c_fence_ready({mf_ready,unused_debug[53:45]}),
   .c_fence_cookie({mf_cookie,288'd0}),.c_fence_epoch({mf_epoch,81'd0}),
   .c_fence_done_valid({mf_done,unused_debug[65:57]}),.c_fence_done_ready({mf_take,9'h1ff}),
   .c_fence_done_cookie(all_fence_cookie),.c_fence_done_epoch(all_fence_epoch),"""),
        ("  wire _unused=^{unused_debug,unused_cancel_tag,unused_fence_cookie,unused_fence_epoch,rsp_tag[287:0],rsp_data[4607:0]};",
         """  assign mf_done_cookie=all_fence_cookie[383:288];
  assign mf_done_epoch=all_fence_epoch[107:81];
  assign {unused_debug[68:66],unused_debug[56:54]}=6'd0;
  wire _unused=^{unused_debug,unused_cancel_tag,all_fence_cookie[287:0],all_fence_epoch[80:0],rsp_tag[287:0],rsp_data[4607:0]};"""),
        ("   w_requests<=0;w_responses<=0;rr<=0;pend<=0;rsp_idx<=-1;", "   w_requests<=0;w_responses<=0;"),
        ("  .outer_scope_idle(gather_idle&&!inspect&&project_valid==0&&project_done_valid==0&&pend==0),",
         "  .outer_scope_idle(!scope_running&&gather_idle&&!inspect&&project_valid==0&&project_done_valid==0),"),
        (" ffn_copy_epoch_fence fence(", """ assign start_ready=scope_ready;
 ffn_copy_scope_admission budget(.scope_valid(start_valid||next_scope),.scope_ready,
  .tile_generation,.scatter_generation,.mid_generation,
  .tile_budget(16'd32),.scatter_budget(16'd12),.mid_budget(16'd3),
  .scope_idle(!scope_running),.admit_new_owner,.fence_done,.rearm_valid,.launch_valid,.launch_ready(launch_enable&&launch_ready));
 always @(posedge clk)begin
  if(reset)begin tile_generation<=16'hffdf;scope_running<=0;scope_count<=0;end
  else begin
   if(namespace_rearm)tile_generation<=0;
   else if(tile_issue)begin
    assert(scope_running&&tile_generation<16'hffff);
    tile_generation<=tile_generation+16'd1;
   end
   if(scope_ready&&(start_valid||next_scope))begin
    assert(!scope_running&&m_pending==0);
    scope_running<=1;scope_count<=scope_count+1;
   end
   if(done_valid&&done_ready)scope_running<=0;
  end
 end
 for(genvar f=0;f<3;f++)begin: fence_accounting
  reg waiting;
  reg [31:0] cookie;
  reg [8:0] epoch;
  assign m_pending[f]=waiting;
  always @(posedge clk)begin
   if(reset)begin waiting<=0;cookie<=0;epoch<=0;m_fences[f]<=0;end
   else begin
    if(mf_valid[f]&&mf_ready[f])begin
     assert(!waiting&&scope_running);
     waiting<=1;cookie<=mf_cookie[f*32+:32];epoch<=mf_epoch[f*9+:9];
    end
    if(mf_done[f]&&mf_take[f])begin
     // MC echoes the request epoch. Only M increments its own epoch after
     // consuming this receipt and reports that increment to the LC provider.
     assert(waiting&&scope_running&&mf_done_cookie[f*32+:32]==cookie&&mf_done_epoch[f*9+:9]==epoch)
       else $fatal(1,"shared DMA FENCE receipt P%0d waiting=%0d active=%0d cookie=%h/%h epoch=%0d/%0d",
         f,waiting,scope_running,mf_done_cookie[f*32+:32],cookie,mf_done_epoch[f*9+:9],epoch);
     waiting<=0;m_fences[f]<=m_fences[f]+1;
    end
   end
  end
 end
 ffn_copy_epoch_fence fence("""),
        ("  assert(COLS==384&&!WITH_DOWN);", "  assert(COLS==384&&!WITH_DOWN&&FOUR_BANK_LOOKAHEAD&&WITH_SHARED_DMA&&!WITH_PROGRAM);"),
        ("    rearm_valid=1;", "    launch_enable=0;next_scope=1;"),
        ("  rearm_valid=0;\n  assert(fence_count==1", "  first_purges=int'(dma_purge_count);\n  assert(m_fences[0]>0&&m_fences[1]>0&&m_fences[2]>0&&m_pending==0&&ddr_idle&&\n    dma_req_count==26112&&dma_rsp_count==26112&&first_purges==1+m_fences[0]+m_fences[1]+m_fences[2]);\n  assert(scope_count==1&&tile_generation==0&&scatter_generation==0&&mid_generation==0&&fence_count==1"),
        ("  tile_generation=0;invocation=1;", "  invocation=1;"),
        ("  run_ffn();\n  verify_mid();\n  assert(fence_count==1&&tile_generation==32&&xcopy_count==32'd3072&&copy_committed==32'd384);",
         """  launch_enable=1;run_ffn();
  verify_mid();
  assert(scope_count==2&&fence_count==1&&tile_generation==32&&scatter_generation==12&&mid_generation==3&&
    xcopy_count==32'd3072&&copy_committed==32'd384&&dma_req_count==52224&&dma_rsp_count==52224&&
    ddr_idle&&m_pending==0&&int'(dma_purge_count)==1+m_fences[0]+m_fences[1]+m_fences[2]&&int'(dma_purge_count)>first_purges);"""),
        ("  $display(\"PASS ffn_copy_rearm old_final=65535 new_final=32 held_ack_cycles=%0d fences=%0d words=%0d scatter=%0d\",blocked_ack_cycles,fence_count,xcopy_count,copy_committed);",
         """  $display("PASS ffn_copy_combined scopes=%0d copy_fences=%0d blocked_ack_cycles=%0d M_fences=%0d,%0d,%0d first_purges=%0d purges=%0d W64=%0d COPY=%0d scatter=%0d",
    scope_count,fence_count,blocked_ack_cycles,m_fences[0],m_fences[1],m_fences[2],first_purges,dma_purge_count,dma_req_count,xcopy_count,copy_committed);"""),
        ("  start_valid=1;do @(posedge clk);while(!start_ready||!admit_new_owner);cycle_wait();start_valid=0;",
         "  if(invocation==0)start_valid=1;\n  do @(posedge clk);while(!start_ready);\n  cycle_wait();start_valid=0;next_scope=0;"),
        (" wire _unused_fixture=^{down_words[0],down_terminal,down_ready};",
         " wire _unused_fixture=^{down_words[0],down_terminal,down_ready,program_ready,program_result,terminal_reads,terminal_writes,down_call,down_take};"),
    ])


def native_node(source):
    return edit(source, [
        ("module test_ffn_native_p_node #(", "module test_ffn_native_p_rearm_node #("),
        (" input logic clk,reset,allow_req,allow_rsp,", """ input wire namespace_rearm,output wire s_owners_empty,
 output wire mc_fence_req_valid,input wire mc_fence_req_ready,
 output wire [31:0] mc_fence_req_cookie,output wire [8:0] mc_fence_req_epoch,
 input wire mc_fence_done_valid,output wire mc_fence_done_ready,
 input wire [31:0] mc_fence_done_cookie,input wire [8:0] mc_fence_done_epoch,
 input logic clk,reset,allow_req,allow_rsp,"""),
        (" copy_scale_header_rx rx(.clk,.reset,", " assign s_owners_empty=owners==0;\n copy_scale_header_rx_rearm rx(.namespace_rearm,.clk,.reset,"),
        (" logic mc_fence_req_valid,mc_fence_done_ready;\n logic [31:0] mc_fence_req_cookie;\n logic [8:0] mc_fence_req_epoch;\n"
         " m_native_leaf_s32 M(.mc_fence_req_ready(1'b0),.mc_fence_done_valid(1'b0),\n"
         "   .mc_fence_done_cookie(32'd0),.mc_fence_done_epoch(9'd0),.*);", " m_native_leaf_s32 M(.*);"),
        ("&&rejected_frames==0&&!mc_fence_req_valid", "&&rejected_frames==0"),
    ])


def with_generation_output(text, signal, original, initial):
    return edit(text, [
        ("output wire namespace_idle,", "output wire namespace_idle,output wire [15:0] namespace_generation,"),
        (" assign namespace_idle=", f" assign namespace_generation={signal};\n assign namespace_idle="),
        (original, initial),
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-lock", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    lock = json.loads(args.source_lock.read_text(encoding="utf-8"))["source_sha256"]

    def frozen(path):
        raw = (args.root / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != lock[path.as_posix()]:
            raise ValueError(f"combined source does not match lock: {path}")
        return raw.decode("utf-8")

    files = {
        "test_ffn_copy_combined.sv": shared_top(frozen(EXPERIMENT / "test_ffn_three_p_native.sv")),
        "test_ffn_native_p_rearm_node.sv": native_node(frozen(EXPERIMENT / "test_ffn_native_p_node.sv")),
        "p_stream_scope_node.sv": replace_once(frozen(NATIVE / "p_stream_scope_node.sv"),
            "p_native_weight_prefill #(.FOUR_BANK_LOOKAHEAD(1'b1))", "p_native_weight_prefill #(.FOUR_BANK_LOOKAHEAD(1'b1),.SESSION_LIMIT(32'd96))"),
    }
    for stem, signal, old, new in (
        ("ffn_stripe_commit_rearm", "epoch", "source<=0;way<=0;epoch<=0;", "source<=0;way<=0;epoch<=16'hfff3;"),
        ("ffn_gate_up_mid_rearm", "quant_epoch", "if(reset)begin quant_epoch<=0;", "if(reset)begin quant_epoch<=16'hfffc;"),
    ):
        name = stem + ".sv"
        files[name] = with_generation_output((args.generated / name).read_text(encoding="utf-8"), signal, old, new)
    for name, result in files.items():
        (args.out / name).write_bytes(result.encode("utf-8"))


if __name__ == "__main__":
    main()
