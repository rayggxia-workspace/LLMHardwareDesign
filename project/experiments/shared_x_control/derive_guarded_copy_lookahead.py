"""Emit a no-payload COPY lookahead variant and its full-program A/B fixture."""

import argparse
import hashlib
import json
from pathlib import Path

from derive_copy_epoch_rearm import edit


EXP = Path("project/experiments/block_local_native")


def core(text):
    start = text.index("module early_copy_3p_rearm #(")
    end = text.index("  input logic clk,reset,halt,", start)
    text = text[:start] + """// The topology may certify an independent source response path per COPY.
// Retain that fact with the request until every accepted response drains.
module early_copy_3p_rearm_lookahead(
 input wire namespace_rearm,start_source_independent,
""" + text[end:]
    return edit(text, [
        ("logic active,failed,request_pending,inflight;", "logic active,failed,request_pending,inflight,source_independent;"),
        ("active<=0;failed<=0;request_pending<=0;inflight<=0;", "active<=0;failed<=0;request_pending<=0;inflight<=0;source_independent<=0;"),
        ("active<=1;failed<=0;key_q<=start_key;generation_q<=start_generation;",
         "active<=1;failed<=0;key_q<=start_key;generation_q<=start_generation;\n          source_independent<=start_source_independent;"),
        ("(PREFETCH_NEXT_WORD||hold_full==0)", "(source_independent||hold_full==0)"),
    ])


def epoch(text):
    start = text.index(" // STREAM can route")
    end = text.index(" always @(posedge clk)", start)
    text = text[:start] + """ // Only the U.S route can certify that the next read response cannot
 // delay a previous P write ACK. Shared ordered S routes serialize.
 early_copy_3p_rearm_lookahead data_copy(.start_words(tile_shape?start_words:11'd0),.*);
""" + text[end:]
    return edit(text, [
        ("module early_copy_epoch_3p_rearm(", "module early_copy_epoch_3p_rearm_lookahead("),
        (" input wire namespace_rearm,", " input wire namespace_rearm,start_source_independent,"),
    ])


MONITOR = """ integer copy_lookahead=0,lookahead_x_reads,x_reads,mid_reads;
 reg [10:0] copy_read_index;
 reg [10:0] acked_prefix[3];
 wire source_independent=copy_lookahead==1&&!down_phase;
 always @(posedge clk)begin
  if(reset)begin
   lookahead_x_reads<=0;x_reads<=0;mid_reads<=0;copy_read_index<=0;
   for(integer p=0;p<3;p++)acked_prefix[p]<=0;
  end else begin
   if(xcopy_start&&xcopy_ready)begin
    copy_read_index<=0;
    for(integer p=0;p<3;p++)acked_prefix[p]<=0;
   end
   for(integer p=0;p<3;p++)if(xp_ack_valid[p]&&xp_ack_ready[p])begin
    assert(xp_ack_tag[p*32+:11]==acked_prefix[p]);
    acked_prefix[p]<=acked_prefix[p]+11'd1;
   end
   if(xcopy_u_valid&&xcopy_u_ready)begin
    assert(xcopy_u_tag[10:0]==copy_read_index);
    if(down_phase)mid_reads<=mid_reads+1;
    else x_reads<=x_reads+1;
    if(acked_prefix[0]<copy_read_index||acked_prefix[1]<copy_read_index||acked_prefix[2]<copy_read_index)begin
     assert(source_independent)else $fatal(1,"COPY read overlapped its own ordered S ACK");
     lookahead_x_reads<=lookahead_x_reads+1;
    end
    copy_read_index<=copy_read_index+11'd1;
   end
   if(xcopy_done&&xcopy_take)begin
    assert(copy_read_index==16&&acked_prefix[0]==16&&acked_prefix[1]==16&&acked_prefix[2]==16);
   end
  end
 end
"""


def full_top(text):
    return edit(text, [
        (" early_copy_epoch_3p xcopy(", MONITOR + " early_copy_epoch_3p_rearm_lookahead xcopy(.namespace_rearm(1'b0),.start_source_independent(source_independent),"),
        ("  trace_tiles=$test$plusargs(\"TRACE_TILES\");", """  trace_tiles=$test$plusargs("TRACE_TILES");
  if(!$value$plusargs("COPY_LOOKAHEAD=%d",copy_lookahead)||copy_lookahead<0||copy_lookahead>1)
    $fatal(1,"set COPY_LOOKAHEAD=0 or 1");"""),
        ("  $display(\"PASS ffn_three_p_native", """  assert(x_reads==STRIPES*16*16&&mid_reads==(WITH_DOWN?6*86*16:0)&&
    (copy_lookahead==1?lookahead_x_reads>0:lookahead_x_reads==0));
  $display("COPY_LOOKAHEAD_PROFILE mode=%0d X_reads=%0d X_reads_before_previous_ACK=%0d Mid_reads=%0d",
    copy_lookahead,x_reads,lookahead_x_reads,mid_reads);
  $display("PASS ffn_three_p_native"""),
    ])


def full_runner(text):
    return edit(text, [
        ("sha256sum -c \"$root/source.sha256\" > \"$root/source-check.log\"", "sha256sum -c \"$root/source.sha256\" > \"$root/source-check.log\"\nsha256sum -c \"$root/candidate.sha256\" > \"$root/candidate-check.log\""),
        ('"$EXP"/{test_ffn_native_p_node,test_ffn_three_p_native}.sv',
         '"$EXP/test_ffn_native_p_node.sv" "$root/lookahead"/{test_ffn_three_p_native,early_copy_3p_rearm_lookahead,early_copy_epoch_3p_rearm_lookahead}.sv'),
        ('     log="$out/mode-$mode-initial-$initial.log"',
         '     for lookahead in 0 1; do\n     log="$out/mode-$mode-initial-$initial-lookahead-$lookahead.log"'),
        ('+TRACE_TILES "+verilator+seed+$seed"', '+TRACE_TILES "+COPY_LOOKAHEAD=$lookahead" "+verilator+seed+$seed"'),
        ('     grep -q "PASS ffn_three_p_native columns=$cols " "$log"',
         '     grep -q "PASS ffn_three_p_native columns=$cols " "$log"\n     grep -q "^COPY_LOOKAHEAD_PROFILE mode=$lookahead " "$log"\n     done'),
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-lock", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    lock = json.loads(args.source_lock.read_text(encoding="utf-8"))

    def frozen(root, path, expected):
        raw = (root / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"COPY lookahead source does not match lock: {path}")
        return raw.decode("utf-8")

    top = EXP / "test_ffn_three_p_native.sv"
    runner = EXP / "job_ffn_native.sh"
    files = {"test_ffn_three_p_native.sv": full_top(frozen(args.root, top, lock["source_sha256"][top.as_posix()])),
             "job_ffn_native.sh": full_runner(frozen(args.root, runner, lock["source_sha256"][runner.as_posix()]))}
    for stem, convert in (("early_copy_3p_rearm", core), ("early_copy_epoch_3p_rearm", epoch)):
        name = stem + ".sv"
        files[stem + "_lookahead.sv"] = convert(frozen(args.generated, name, lock["rearm_sha256"][name]))
    generated = {}
    for name, result in files.items():
        raw = result.encode("utf-8")
        (args.out / name).write_bytes(raw)
        generated[name] = hashlib.sha256(raw).hexdigest()
    (args.out / "lookahead.json").write_text(json.dumps(generated, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
